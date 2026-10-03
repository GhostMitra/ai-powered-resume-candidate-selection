import json
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional

class AuditService:
    @staticmethod
    def generate_audit_report(
        batch_id: str,
        batch_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        
        now = datetime.utcnow().isoformat()
        
        report_body = {
            "metadata": {
                "batch_id": batch_id,
                "generated_at": now,
                "system_id": "Tech-Spec Use Case 9",
                "code_version": "v1.1.1",
                "taxonomy_version": "2026.09"
            },
            "models": {
                "chat_model": batch_data.get("model_info", {}).get("chat_model", "nemotron-3-nano-4b"),
                "embedding_model": "nomic-embed-text-v1.5",
                "temperature": 0.0,
                "seed": 42
            },
            "inputs": {
                "resume_count": batch_data.get("funnel", {}).get("uploaded", 0),
                "roles_count": len(batch_data.get("roles", []))
            },
            "config": batch_data.get("screening_config", {}),
            "funnel": batch_data.get("funnel", {}),
            "roles": batch_data.get("roles", []),
            "integrity_summary": batch_data.get("integrity_summary", []),
            "duplicates": batch_data.get("duplicates", []),
            "fairness_test": batch_data.get("fairness_test", None),
            "shortlist": batch_data.get("shortlist", []),
            "redirects": batch_data.get("redirects", []),
            "could_not_process": batch_data.get("could_not_process", [])
        }

        # Compute canonical SHA-256 hash of JSON content
        canonical_json_str = json.dumps(report_body, sort_keys=True)
        sha256_hash = hashlib.sha256(canonical_json_str.encode("utf-8")).hexdigest()

        return {
            "batch_id": batch_id,
            "created_at": now,
            "sha256": sha256_hash,
            "report": report_body
        }

    @staticmethod
    def render_audit_html(report_doc: Dict[str, Any]) -> str:
        report = report_doc.get("report", {})
        meta = report.get("metadata", {})
        models = report.get("models", {})
        funnel = report.get("funnel", {})
        sha = report_doc.get("sha256", "")

        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Audit Report - Batch {meta.get('batch_id')}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #1e293b; padding: 40px; max-width: 900px; margin: auto; }}
        h1, h2, h3 {{ color: #0f172a; }}
        .badge {{ background: #e2e8f0; padding: 4px 8px; border-radius: 4px; font-size: 0.85em; font-weight: 600; }}
        .hash-box {{ background: #f8fafc; border: 1px solid #cbd5e1; padding: 12px; border-radius: 6px; font-family: monospace; word-break: break-all; margin-bottom: 24px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #e2e8f0; padding: 10px; text-align: left; }}
        th {{ background: #f1f5f9; }}
    </style>
</head>
<body>
    <h1>AI-Powered Resume Screening & Candidate Matching — Audit Report</h1>
    <div class="hash-box">
        <strong>Report SHA-256 Signature:</strong> {sha}
    </div>
    
    <h2>1. Run Metadata</h2>
    <table>
        <tr><th>Batch ID</th><td>{meta.get('batch_id')}</td></tr>
        <tr><th>Generated At</th><td>{meta.get('generated_at')}</td></tr>
        <tr><th>System ID</th><td>{meta.get('system_id')}</td></tr>
        <tr><th>Code Version</th><td>{meta.get('code_version')}</td></tr>
    </table>

    <h2>2. Model Infrastructure</h2>
    <table>
        <tr><th>LLM Model</th><td>{models.get('chat_model')}</td></tr>
        <tr><th>Embedding Model</th><td>{models.get('embedding_model')}</td></tr>
        <tr><th>Temperature</th><td>{models.get('temperature')}</td></tr>
        <tr><th>Seed</th><td>{models.get('seed')}</td></tr>
    </table>

    <h2>3. Screening Funnel</h2>
    <table>
        <tr><th>Uploaded Resumes</th><td>{funnel.get('uploaded', 0)}</td></tr>
        <tr><th>Processable Resumes</th><td>{funnel.get('processable', 0)}</td></tr>
        <tr><th>Unique Candidates</th><td>{funnel.get('unique', 0)}</td></tr>
        <tr><th>Passed Eligibility Gates</th><td>{funnel.get('passed_any_gate', 0)}</td></tr>
        <tr><th>Scored Candidates</th><td>{funnel.get('scored', 0)}</td></tr>
    </table>

    <h2>4. Final Shortlist Summary</h2>
    <table>
        <thead>
            <tr><th>Rank</th><th>Candidate ID</th><th>Match Score</th><th>Skill</th><th>Experience</th><th>Education</th><th>Lane</th></tr>
        </thead>
        <tbody>
"""
        for item in report.get("shortlist", []):
            html += f"""
            <tr>
                <td>#{item.get('rank', '-')}</td>
                <td>{item.get('candidate_id')}</td>
                <td><strong>{item.get('match_score_percentage')}%</strong></td>
                <td>{item.get('skill_score')}%</td>
                <td>{item.get('experience_score')}%</td>
                <td>{item.get('education_score')}%</td>
                <td><span class="badge">{item.get('lane', 'SHORTLISTED')}</span></td>
            </tr>"""

        html += """
        </tbody>
    </table>
</body>
</html>"""
        return html
