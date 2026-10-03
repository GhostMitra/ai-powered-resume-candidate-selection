import time
import re
from typing import List, Dict, Any, Optional, TypedDict
from langgraph.graph import StateGraph, END
from app.schemas import (
    ParsedJobDescription,
    ParsedCandidateProfile,
    CandidateEvaluationResult,
    ProcessingError,
    ScreeningConfig,
    WeightConfig,
    GateRule,
    GateResult,
    GateImpact,
    IntegrityReport,
    DuplicateGroup,
    RoleRedirect,
    RoleFit,
    CandidateEducation,
    SkillMatchDetail
)
from app.services.file_parser import FileParserService
from app.services.integrity_shield import IntegrityShieldService
from app.services.pii_scrubber import PIIAnonymizerService
from app.services.dedup_service import DedupService
from app.services.gate_engine import FactExtractorService, GateEvaluatorService
from app.services.scoring_engine import ScoringEngineService
from app.services.llm_service import llm_service
from app.services.audit_service import AuditService
from app.db.mongodb import mongo_store

BATCH_STATE_CACHE: Dict[str, Any] = {}

def save_batch_state(batch_id: str, state: Dict[str, Any]):
    BATCH_STATE_CACHE[batch_id] = state

def get_batch_state(batch_id: str) -> Optional[Dict[str, Any]]:
    return BATCH_STATE_CACHE.get(batch_id)

class AgentScreeningState(TypedDict):
    batch_id: str
    jd_raw_text: str
    roles_specs: List[Dict[str, Any]]
    resume_files: List[Dict[str, Any]]
    config: ScreeningConfig
    
    extracted_resumes: List[Dict[str, Any]]
    integrity_reports: Dict[str, IntegrityReport]
    facts: Dict[str, Any]
    scrubbed_resumes: List[Dict[str, Any]]
    duplicate_groups: List[DuplicateGroup]
    gate_results: Dict[str, Dict[str, GateResult]]
    gate_impacts: Dict[str, List[GateImpact]]
    parsed_jds: Dict[str, ParsedJobDescription]
    parsed_candidates: Dict[str, ParsedCandidateProfile]
    shortlist_results: List[CandidateEvaluationResult]
    redirects: List[RoleRedirect]
    could_not_process: List[ProcessingError]
    step_traces: Dict[str, Any]
    audit_report: Optional[Dict[str, Any]]

# --- NODE 1: Ingestion & Tamper Shield ---
def ingestion_and_shield_node(state: AgentScreeningState) -> Dict[str, Any]:
    start_time = time.time()
    extracted = []
    failed = []
    integrity_reports = {}
    cfg = state.get("config", ScreeningConfig())
    jd_text = state.get("jd_raw_text", "")

    for idx, f in enumerate(state["resume_files"]):
        filename = f["filename"]
        raw_bytes = f["content_bytes"]
        
        raw_text, error = FileParserService.parse_file_content(filename, raw_bytes)
        if error:
            failed.append(error)
        else:
            cid = f"Candidate #{idx + 101}"
            sanitized_text, rep, stripped_spans = IntegrityShieldService.scan_and_sanitize(
                filename=filename,
                file_bytes=raw_bytes,
                raw_text=raw_text,
                candidate_id=cid,
                jd_text=jd_text,
                config=cfg.integrity
            )
            integrity_reports[cid] = rep
            
            email_match = re.search(PIIAnonymizerService.EMAIL_REGEX, raw_text)
            phone_match = re.search(PIIAnonymizerService.PHONE_REGEX, raw_text)
            email = email_match.group(0) if email_match else ""
            phone = phone_match.group(0) if phone_match else ""

            extracted.append({
                "candidate_id": cid,
                "filename": filename,
                "raw_text": raw_text,
                "sanitized_text": sanitized_text,
                "extracted_email": email,
                "extracted_phone": phone,
                "stripped_spans": stripped_spans
            })

    traces = state.get("step_traces", {})
    traces["Node_1_Ingestion_Shield"] = {
        "status": "COMPLETED",
        "duration_ms": round((time.time() - start_time) * 1000, 2),
        "total": len(state["resume_files"]),
        "valid": len(extracted),
        "failed": len(failed)
    }

    return {
        "extracted_resumes": extracted,
        "integrity_reports": integrity_reports,
        "could_not_process": failed,
        "step_traces": traces
    }

# --- NODE 2: Fact Extraction & Gate Evaluation ---
def fact_extraction_and_gates_node(state: AgentScreeningState) -> Dict[str, Any]:
    start_time = time.time()
    extracted = state["extracted_resumes"]
    roles_specs = state.get("roles_specs", [])
    
    facts_map = {}
    scrubbed = []
    
    for item in extracted:
        cid = item["candidate_id"]
        facts = FactExtractorService.extract_facts(item["raw_text"])
        facts_map[cid] = facts
        
        fingerprint = mongo_store.generate_candidate_fingerprint(
            email=item["extracted_email"],
            phone=item["extracted_phone"],
            raw_text_sample=item["raw_text"]
        )
        
        scrubbed_text = PIIAnonymizerService.anonymize_text(item["sanitized_text"])
        
        scrubbed.append({
            "candidate_id": cid,
            "filename": item["filename"],
            "sanitized_text": item["sanitized_text"],
            "scrubbed_text": scrubbed_text,
            "fingerprint": fingerprint,
            "facts": facts,
            "extracted_email": item["extracted_email"],
            "extracted_phone": item["extracted_phone"]
        })

    # Evaluate gates per role
    gate_results: Dict[str, Dict[str, GateResult]] = {}
    gate_impacts: Dict[str, List[GateImpact]] = {}

    all_cand_facts = [{"candidate_id": item["candidate_id"], "facts": item["facts"]} for item in scrubbed]

    for rspec in roles_specs:
        jd_id = rspec.get("jd_id", "PRIMARY")
        gates = [GateRule(**g) if isinstance(g, dict) else g for g in rspec.get("gates", [])]
        
        gate_results[jd_id] = {}
        for item in scrubbed:
            cid = item["candidate_id"]
            res = GateEvaluatorService.evaluate_candidate_gates(cid, jd_id, gates, item["facts"])
            gate_results[jd_id][cid] = res
            
        gate_impacts[jd_id] = GateEvaluatorService.compute_gate_impact(gates, all_cand_facts)

    traces = state.get("step_traces", {})
    traces["Node_2_Gates"] = {
        "status": "COMPLETED",
        "duration_ms": round((time.time() - start_time) * 1000, 2),
        "candidates_evaluated": len(scrubbed)
    }

    return {
        "facts": facts_map,
        "scrubbed_resumes": scrubbed,
        "gate_results": gate_results,
        "gate_impacts": gate_impacts,
        "step_traces": traces
    }

# --- NODE 3: Dedup & Plagiarism Check ---
def dedup_and_plagiarism_node(state: AgentScreeningState) -> Dict[str, Any]:
    start_time = time.time()
    scrubbed = state["scrubbed_resumes"]
    cfg = state.get("config", ScreeningConfig())

    dup_groups = DedupService.detect_duplicates(scrubbed, cfg.dedup)

    traces = state.get("step_traces", {})
    traces["Node_3_Dedup"] = {
        "status": "COMPLETED",
        "duration_ms": round((time.time() - start_time) * 1000, 2),
        "duplicates_found": len(dup_groups)
    }

    return {
        "duplicate_groups": dup_groups,
        "step_traces": traces
    }

# --- NODE 4: Structured Parse ---
def structured_parse_node(state: AgentScreeningState) -> Dict[str, Any]:
    start_time = time.time()
    scrubbed = state["scrubbed_resumes"]
    roles_specs = state.get("roles_specs", [])

    parsed_jds: Dict[str, ParsedJobDescription] = {}
    for rspec in roles_specs:
        jd_id = rspec.get("jd_id", "PRIMARY")
        jd_text = rspec.get("jd_text", state.get("jd_raw_text", ""))
        parsed_jds[jd_id] = llm_service.parse_job_description(jd_text)

    parsed_candidates: Dict[str, ParsedCandidateProfile] = {}
    for item in scrubbed:
        cid = item["candidate_id"]
        filename = item["filename"]
        text = item["scrubbed_text"]
        fingerprint = item["fingerprint"]
        
        profile = llm_service.parse_resume(text, cid, filename)
        profile.unique_fingerprint = fingerprint
        
        mongo_res = mongo_store.save_or_update_resume(
            candidate_id=cid,
            filename=filename,
            raw_text_scrubbed=text,
            parsed_profile=profile.model_dump(),
            fingerprint=fingerprint
        )
        
        parsed_candidates[cid] = profile

    traces = state.get("step_traces", {})
    traces["Node_4_Structured_Parse"] = {
        "status": "COMPLETED",
        "duration_ms": round((time.time() - start_time) * 1000, 2),
        "parsed_jds_count": len(parsed_jds),
        "parsed_candidates_count": len(parsed_candidates)
    }

    return {
        "parsed_jds": parsed_jds,
        "parsed_candidates": parsed_candidates,
        "step_traces": traces
    }

# --- NODE 5: Project Plagiarism & Multi-Role Scoring ---
def multi_role_scoring_node(state: AgentScreeningState) -> Dict[str, Any]:
    start_time = time.time()
    parsed_jds = state["parsed_jds"]
    parsed_cands = state["parsed_candidates"]
    gate_results = state["gate_results"]
    integrity_reports = state["integrity_reports"]
    dup_groups = state.get("duplicate_groups", [])
    cfg = state.get("config", ScreeningConfig())

    proj_groups = DedupService.detect_project_plagiarism(list(parsed_cands.values()), cfg.dedup)
    all_dup_groups = dup_groups + proj_groups

    primary_jd_id = next(iter(parsed_jds.keys())) if parsed_jds else "PRIMARY"
    primary_jd = parsed_jds.get(primary_jd_id, ParsedJobDescription(role_title="Target Role"))

    shortlist_results = []
    role_fits_map: Dict[str, List[RoleFit]] = {}

    for cid, cand in parsed_cands.items():
        role_fits_map[cid] = []
        
        # Check primary role gate result
        primary_gate_res = gate_results.get(primary_jd_id, {}).get(cid)
        passed_primary_gate = primary_gate_res.passed if primary_gate_res else True
        failed_rules = primary_gate_res.failed_rules if primary_gate_res else []

        for jd_id, p_jd in parsed_jds.items():
            g_res = gate_results.get(jd_id, {}).get(cid)
            if g_res and not g_res.passed:
                continue

            total_score, skill_score, exp_score, edu_score, skill_details = ScoringEngineService.evaluate_candidate(
                p_jd, cand, cfg
            )

            role_fits_map[cid].append(RoleFit(
                jd_id=jd_id,
                role_title=p_jd.role_title,
                score=total_score
            ))

        # Always score against primary role for complete candidate table view
        total_score, skill_score, exp_score, edu_score, skill_details = ScoringEngineService.evaluate_candidate(
            primary_jd, cand, cfg
        )

        integ_rep = integrity_reports.get(cid, IntegrityReport(candidate_id=cid))
        
        # Determine Lane
        lane = "SHORTLISTED"
        if not passed_primary_gate:
            lane = "INELIGIBLE"
        elif integ_rep.severity == "HIGH":
            lane = "NEEDS_REVIEW"
        elif any(g.kind in ["EXACT", "SAME_APPLICANT"] and cid in g.members and g.canonical != cid for g in dup_groups):
            lane = "DUPLICATE"

        explanation = llm_service.generate_explanation(
            candidate_id=cid,
            match_score=total_score,
            matching_skills=skill_details.matching_skills,
            missing_skills=skill_details.missing_skills,
            substitute_skills=skill_details.substitute_skills,
            candidate_yoe=cand.total_years_experience,
            required_yoe=primary_jd.min_years_experience
        )

        if not passed_primary_gate and failed_rules:
            explanation = f"[INELIGIBLE: Failed Gate ({', '.join(failed_rules)})] " + explanation

        eval_res = CandidateEvaluationResult(
            candidate_id=cid,
            original_filename=cand.original_filename,
            unique_fingerprint=cand.unique_fingerprint,
            rank=1,
            match_score_percentage=total_score,
            skill_score=skill_score,
            experience_score=exp_score,
            education_score=edu_score,
            skill_details=skill_details,
            llm_explanation_note=explanation,
            raw_parsed_profile=cand,
            integrity=integ_rep,
            lane=lane
        )
        shortlist_results.append(eval_res)

    # Rank shortlist (Shortlisted & Needs Review ranked first, Ineligible ranked after)
    shortlist_results.sort(key=lambda x: (0 if x.lane in ["SHORTLISTED", "NEEDS_REVIEW"] else 1, -x.match_score_percentage))
    for idx, item in enumerate(shortlist_results):
        item.rank = idx + 1

    # Multi-Role Redirect Panel Generation
    redirects: List[RoleRedirect] = []
    top_k = cfg.shortlist.top_k
    min_redirect = cfg.shortlist.redirect_min_score

    for item in shortlist_results:
        cid = item.candidate_id
        is_shortlisted = item.lane == "SHORTLISTED" and item.rank <= top_k and item.match_score_percentage >= cfg.shortlist.min_score
        
        if not is_shortlisted:
            alt_fits = [rf for rf in role_fits_map.get(cid, []) if rf.jd_id != primary_jd_id and rf.score >= min_redirect]
            if alt_fits:
                alt_fits.sort(key=lambda x: x.score, reverse=True)
                best = alt_fits[0]
                redirects.append(RoleRedirect(
                    candidate_id=cid,
                    primary_score=item.match_score_percentage if item.lane != "INELIGIBLE" else None,
                    best_alternative=best,
                    other_fits=alt_fits[1:],
                    message=f"Not a fit for {primary_jd.role_title} ({item.match_score_percentage:.0f}%), but {best.score:.0f}% for {best.role_title}."
                ))

    traces = state.get("step_traces", {})
    traces["Node_5_Multi_Role_Scoring"] = {
        "status": "COMPLETED",
        "duration_ms": round((time.time() - start_time) * 1000, 2),
        "total_evaluated_count": len(shortlist_results),
        "shortlisted_count": sum(1 for x in shortlist_results if x.lane == "SHORTLISTED"),
        "ineligible_count": sum(1 for x in shortlist_results if x.lane == "INELIGIBLE"),
        "redirects_count": len(redirects)
    }

    return {
        "duplicate_groups": all_dup_groups,
        "shortlist_results": shortlist_results,
        "redirects": redirects,
        "step_traces": traces
    }

# --- NODE 6: Audit Report Assembly ---
def audit_node(state: AgentScreeningState) -> Dict[str, Any]:
    start_time = time.time()
    batch_id = state.get("batch_id", "batch_default")
    
    batch_summary = {
        "screening_config": state.get("config", ScreeningConfig()).model_dump(),
        "funnel": {
            "uploaded": len(state.get("resume_files", [])),
            "processable": len(state.get("extracted_resumes", [])),
            "unique": len(state.get("scrubbed_resumes", [])),
            "passed_any_gate": len(state.get("parsed_candidates", [])),
            "scored": len(state.get("shortlist_results", []))
        },
        "roles": state.get("roles_specs", []),
        "shortlist": [item.model_dump() for item in state.get("shortlist_results", [])],
        "redirects": [r.model_dump() for r in state.get("redirects", [])],
        "duplicates": [d.model_dump() for d in state.get("duplicate_groups", [])],
        "could_not_process": [e.model_dump() for e in state.get("could_not_process", [])]
    }

    audit_rep = AuditService.generate_audit_report(batch_id, batch_summary)

    traces = state.get("step_traces", {})
    traces["Node_6_Audit"] = {
        "status": "COMPLETED",
        "duration_ms": round((time.time() - start_time) * 1000, 2),
        "sha256": audit_rep["sha256"]
    }

    return {
        "audit_report": audit_rep,
        "step_traces": traces
    }

# Build LangGraph State Graph
def build_screening_graph():
    builder = StateGraph(AgentScreeningState)
    
    builder.add_node("node_ingestion_shield", ingestion_and_shield_node)
    builder.add_node("node_fact_gates", fact_extraction_and_gates_node)
    builder.add_node("node_dedup", dedup_and_plagiarism_node)
    builder.add_node("node_structured_parse", structured_parse_node)
    builder.add_node("node_scoring_redirect", multi_role_scoring_node)
    builder.add_node("node_audit", audit_node)
    
    builder.set_entry_point("node_ingestion_shield")
    builder.add_edge("node_ingestion_shield", "node_fact_gates")
    builder.add_edge("node_fact_gates", "node_dedup")
    builder.add_edge("node_dedup", "node_structured_parse")
    builder.add_edge("node_structured_parse", "node_scoring_redirect")
    builder.add_edge("node_scoring_redirect", "node_audit")
    builder.add_edge("node_audit", END)
    
    return builder.compile()

screening_agent_app = build_screening_graph()

def re_run_independent_node(batch_id: str, step_name: str, new_config: Optional[ScreeningConfig] = None) -> Dict[str, Any]:
    cached_state = get_batch_state(batch_id)
    if not cached_state:
        raise ValueError(f"Batch state '{batch_id}' not found in active session cache.")
        
    if new_config:
        cached_state["config"] = new_config

    if step_name == "Node_2_Gates":
        cached_state.update(fact_extraction_and_gates_node(cached_state))
        cached_state.update(structured_parse_node(cached_state))
        cached_state.update(multi_role_scoring_node(cached_state))
        cached_state.update(audit_node(cached_state))

    elif step_name == "Node_4_Structured_Parse":
        cached_state.update(structured_parse_node(cached_state))
        cached_state.update(multi_role_scoring_node(cached_state))
        cached_state.update(audit_node(cached_state))

    elif step_name == "Node_5_Multi_Role_Scoring":
        cached_state.update(multi_role_scoring_node(cached_state))
        cached_state.update(audit_node(cached_state))

    save_batch_state(batch_id, cached_state)
    return cached_state
