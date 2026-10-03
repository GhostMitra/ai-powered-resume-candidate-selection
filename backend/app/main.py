import uuid
import json
import logging
import os
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, status, Query, Body
from fastapi.responses import HTMLResponse, JSONResponse, Response, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.schemas import (
    BatchScreeningResponse,
    WeightConfig,
    ParsedJobDescription,
    ProcessingError,
    ScreeningConfig,
    GateRule,
    GateImpact,
    FairnessTestResult
)
from app.agent.langgraph_flow import (
    screening_agent_app,
    save_batch_state,
    get_batch_state,
    re_run_independent_node,
    fact_extraction_and_gates_node,
    multi_role_scoring_node,
    audit_node
)
from app.sample_data.synthetic_data import SAMPLE_JDS, SAMPLE_RESUMES
from app.services.llm_service import llm_service
from app.services.gate_engine import GateEvaluatorService
from app.services.audit_service import AuditService
from app.services.fairness_service import FairnessService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api_main")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="AI-Powered Resume Screening & Candidate-Job Matching System API"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files if frontend build directory exists (Docker container environment)
STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.exists(STATIC_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="static_assets")

@app.get("/")
def read_root():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "version": "1.1.1",
        "lm_studio_connected": llm_service.is_lm_studio_online(),
        "lm_studio_url": settings.LM_STUDIO_BASE_URL,
        "throughput_metrics": llm_service.get_throughput_metrics()
    }

@app.get("/api/v1/health")
def health_check():
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "version": "1.1.1",
        "lm_studio_connected": llm_service.is_lm_studio_online(),
        "lm_studio_url": settings.LM_STUDIO_BASE_URL,
        "throughput_metrics": llm_service.get_throughput_metrics()
    }

@app.get("/api/v1/samples")
def get_sample_presets():
    return {
        "sample_jds": SAMPLE_JDS,
        "sample_resumes": SAMPLE_RESUMES
    }

@app.post("/api/v1/parse-jd", response_model=ParsedJobDescription)
def parse_job_description_endpoint(jd_text: str = Form(...)):
    if not jd_text or not jd_text.strip():
        raise HTTPException(status_code=400, detail="Job description text cannot be empty.")
    return llm_service.parse_job_description(jd_text)

@app.post("/api/v1/screen/batch", response_model=BatchScreeningResponse)
async def screen_candidate_batch(
    jd_text: str = Form(...),
    resumes: List[UploadFile] = File(default=[]),
    roles_json: Optional[str] = Form(None),
    config_json: Optional[str] = Form(None),
    skill_weight: float = Form(0.60),
    experience_weight: float = Form(0.25),
    education_weight: float = Form(0.15)
):
    if not resumes or len(resumes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No resumes uploaded! Please upload at least one candidate resume."
        )

    batch_id = f"batch_{uuid.uuid4().hex[:8]}"

    roles_specs = []
    if roles_json:
        try:
            roles_specs = json.loads(roles_json)
        except Exception:
            pass

    if not roles_specs:
        roles_specs = [{
            "jd_id": "PRIMARY",
            "jd_text": jd_text,
            "is_primary": True,
            "gates": [
                {"id": "cgpa_min", "label": "CGPA >= 6.5", "field": "cgpa_10", "op": ">=", "value": 6.5, "enabled": True, "on_missing": "review"},
                {"id": "no_backlogs", "label": "No Active Backlogs", "field": "active_backlogs", "op": "==", "value": 0, "enabled": True, "on_missing": "pass"}
            ]
        }]

    cfg = ScreeningConfig()
    if config_json:
        try:
            cfg = ScreeningConfig(**json.loads(config_json))
        except Exception as e:
            logger.warning(f"Config parse warning: {e}")

    cfg.dimensions.skill = skill_weight
    cfg.dimensions.experience = experience_weight
    cfg.dimensions.education = education_weight

    resume_files_payload = []
    for upload in resumes:
        content_bytes = await upload.read()
        resume_files_payload.append({
            "filename": upload.filename,
            "content_bytes": content_bytes
        })

    initial_state = {
        "batch_id": batch_id,
        "jd_raw_text": jd_text,
        "roles_specs": roles_specs,
        "resume_files": resume_files_payload,
        "config": cfg,
        "extracted_resumes": [],
        "integrity_reports": {},
        "facts": {},
        "scrubbed_resumes": [],
        "duplicate_groups": [],
        "gate_results": {},
        "gate_impacts": {},
        "parsed_jds": {},
        "parsed_candidates": {},
        "shortlist_results": [],
        "redirects": [],
        "could_not_process": [],
        "step_traces": {},
        "audit_report": None
    }

    final_state = screening_agent_app.invoke(initial_state)

    save_batch_state(batch_id, final_state)

    shortlist = final_state.get("shortlist_results", [])
    redirects = final_state.get("redirects", [])
    duplicates = final_state.get("duplicate_groups", [])
    could_not_process = final_state.get("could_not_process", [])
    parsed_jds = final_state.get("parsed_jds", {})
    primary_jd = next(iter(parsed_jds.values())) if parsed_jds else ParsedJobDescription(role_title="Target Role")
    step_traces = final_state.get("step_traces", {})

    funnel_stats = {
        "uploaded": len(resumes),
        "processable": len(final_state.get("extracted_resumes", [])),
        "unique": len(final_state.get("scrubbed_resumes", [])),
        "passed_any_gate": len(final_state.get("parsed_candidates", [])),
        "scored": len(shortlist)
    }

    return BatchScreeningResponse(
        batch_id=batch_id,
        status="COMPLETED",
        total_uploaded=len(resumes),
        processed_count=len(shortlist),
        failed_count=len(could_not_process),
        parsed_jd=primary_jd,
        roles=roles_specs,
        shortlist=shortlist,
        redirects=redirects,
        duplicates=duplicates,
        could_not_process=could_not_process,
        weights_used=WeightConfig(skill_weight=skill_weight, experience_weight=experience_weight, education_weight=education_weight),
        screening_config=cfg,
        funnel=funnel_stats,
        throughput_metrics=llm_service.get_throughput_metrics(),
        langgraph_step_traces=step_traces
    )

@app.get("/api/v1/batches/{id}")
def get_batch_status(id: str):
    cached_state = get_batch_state(id)
    if not cached_state:
        raise HTTPException(status_code=404, detail=f"Batch '{id}' not found.")
    
    shortlist = cached_state.get("shortlist_results", [])
    redirects = cached_state.get("redirects", [])
    duplicates = cached_state.get("duplicate_groups", [])
    could_not_process = cached_state.get("could_not_process", [])
    parsed_jds = cached_state.get("parsed_jds", {})
    primary_jd = next(iter(parsed_jds.values())) if parsed_jds else ParsedJobDescription(role_title="Target Role")
    
    return {
        "batch_id": id,
        "status": "COMPLETED",
        "parsed_jd": primary_jd,
        "roles": cached_state.get("roles_specs", []),
        "shortlist": shortlist,
        "redirects": redirects,
        "duplicates": duplicates,
        "could_not_process": could_not_process,
        "step_traces": cached_state.get("step_traces", {}),
        "throughput_metrics": llm_service.get_throughput_metrics()
    }

@app.post("/api/v1/batches/{id}/re-evaluate")
def re_evaluate_batch(id: str, payload: Dict[str, Any] = Body(...)):
    cached_state = get_batch_state(id)
    if not cached_state:
        raise HTTPException(status_code=404, detail=f"Batch '{id}' not found in session.")

    new_cfg_dict = payload.get("config")
    if new_cfg_dict:
        cached_state["config"] = ScreeningConfig(**new_cfg_dict)

    cached_state.update(multi_role_scoring_node(cached_state))
    cached_state.update(audit_node(cached_state))
    save_batch_state(id, cached_state)

    shortlist = cached_state.get("shortlist_results", [])
    redirects = cached_state.get("redirects", [])
    
    return {
        "batch_id": id,
        "status": "RE_EVALUATED",
        "shortlist": shortlist,
        "redirects": redirects
    }

@app.post("/api/v1/batches/{id}/gates/preview")
def gate_impact_preview(id: str, gates: List[GateRule] = Body(...)):
    cached_state = get_batch_state(id)
    if not cached_state:
        return [GateImpact(rule_id=g.id, label=g.label, fails=0, fail_pct=0.0, unique_fails=0, missing_data=0) for g in gates]

    all_cand_facts = [{"candidate_id": item["candidate_id"], "facts": item["facts"]} for item in cached_state.get("scrubbed_resumes", [])]
    impacts = GateEvaluatorService.compute_gate_impact(gates, all_cand_facts)
    return impacts

@app.get("/api/v1/batches/{id}/audit")
def get_audit_report(id: str, format: str = Query("json")):
    cached_state = get_batch_state(id)
    if not cached_state or not cached_state.get("audit_report"):
        raise HTTPException(status_code=404, detail=f"Audit report for batch '{id}' not found.")

    report_doc = cached_state["audit_report"]

    if format.lower() == "pdf" or format.lower() == "html":
        html_content = AuditService.render_audit_html(report_doc)
        return HTMLResponse(content=html_content, status_code=200)

    return JSONResponse(content=report_doc, status_code=200)

@app.post("/api/v1/batches/{id}/fairness-test", response_model=FairnessTestResult)
def run_fairness_test(id: str):
    cached_state = get_batch_state(id)
    if not cached_state:
        raise HTTPException(status_code=404, detail=f"Batch '{id}' not found.")

    parsed_jds = cached_state.get("parsed_jds", {})
    primary_jd = next(iter(parsed_jds.values())) if parsed_jds else ParsedJobDescription(role_title="Target Role")
    candidates = list(cached_state.get("parsed_candidates", {}).values())
    cfg = cached_state.get("config", ScreeningConfig())

    res = FairnessService.run_counterfactual_test(primary_jd, candidates, cfg)
    return res

@app.post("/api/v1/agent/re-run-step", response_model=BatchScreeningResponse)
def re_run_agent_step_endpoint(
    batch_id: str = Form(...),
    step_name: str = Form(...),
    skill_weight: Optional[float] = Form(None),
    experience_weight: Optional[float] = Form(None),
    education_weight: Optional[float] = Form(None)
):
    try:
        updated_state = re_run_independent_node(batch_id, step_name)
        
        shortlist = updated_state.get("shortlist_results", [])
        could_not_process = updated_state.get("could_not_process", [])
        parsed_jds = updated_state.get("parsed_jds", {})
        primary_jd = next(iter(parsed_jds.values())) if parsed_jds else ParsedJobDescription(role_title="General Role")
        step_traces = updated_state.get("step_traces", {})
        cfg = updated_state.get("config", ScreeningConfig())
        
        return BatchScreeningResponse(
            batch_id=batch_id,
            status="COMPLETED",
            total_uploaded=len(updated_state.get("resume_files", [])),
            processed_count=len(shortlist),
            failed_count=len(could_not_process),
            parsed_jd=primary_jd,
            roles=updated_state.get("roles_specs", []),
            shortlist=shortlist,
            redirects=updated_state.get("redirects", []),
            duplicates=updated_state.get("duplicate_groups", []),
            could_not_process=could_not_process,
            weights_used=WeightConfig(skill_weight=cfg.dimensions.skill, experience_weight=cfg.dimensions.experience, education_weight=cfg.dimensions.education),
            screening_config=cfg,
            langgraph_step_traces=step_traces
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Re-running node step failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
