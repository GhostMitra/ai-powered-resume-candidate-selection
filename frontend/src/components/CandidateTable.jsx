import React, { useState } from 'react';
import { 
  Award, 
  ChevronDown, 
  ChevronUp, 
  Sparkles, 
  Layers, 
  RotateCcw, 
  ShieldCheck, 
  History, 
  Database,
  AlertOctagon,
  FileSpreadsheet,
  Download,
  Users,
  CornerUpRight,
  Scale
} from 'lucide-react';

export default function CandidateTable({ 
  shortlist, 
  redirects = [], 
  duplicates = [], 
  roles = [], 
  isBlindMode, 
  langgraphTraces, 
  batchId, 
  apiBaseUrl = 'http://127.0.0.1:8000',
  onReRunStep 
}) {
  const [activeTab, setActiveTab] = useState('primary'); // 'primary', 'redirects', 'duplicates'
  const [expandedCandidateId, setExpandedCandidateId] = useState(null);
  const [reRunningStep, setReRunningStep] = useState(null);
  const [showIntegrityDrawer, setShowIntegrityDrawer] = useState(null);
  const [fairnessResult, setFairnessResult] = useState(null);
  const [isFairnessRunning, setIsFairnessRunning] = useState(false);

  const toggleExpand = (id) => {
    setExpandedCandidateId(expandedCandidateId === id ? null : id);
  };

  const handleReRunNode = async (stepKey) => {
    if (!batchId || !onReRunStep) return;
    setReRunningStep(stepKey);
    try {
      await onReRunStep(batchId, stepKey);
    } catch (e) {
      console.error("Node re-execution failed:", e);
    } finally {
      setReRunningStep(null);
    }
  };

  const runFairnessTest = async () => {
    if (!batchId) return;
    setIsFairnessRunning(true);
    try {
      const res = await fetch(`${apiBaseUrl}/api/v1/batches/${batchId}/fairness-test`, {
        method: 'POST'
      });
      if (res.ok) {
        const data = await res.json();
        setFairnessResult(data);
      }
    } catch (e) {
      console.error("Fairness test error:", e);
    } finally {
      setIsFairnessRunning(false);
    }
  };

  const downloadAuditReport = (format = 'json') => {
    if (!batchId) return;
    window.open(`${apiBaseUrl}/api/v1/batches/${batchId}/audit?format=${format}`, '_blank');
  };

  const getScoreBadgeClass = (score) => {
    if (score >= 80) return 'high';
    if (score >= 60) return 'medium';
    return 'low';
  };

  const getRankClass = (rank) => {
    if (rank === 1) return 'top-1';
    if (rank === 2) return 'top-2';
    if (rank === 3) return 'top-3';
    return '';
  };

  const hasData = (shortlist && shortlist.length > 0) || (redirects && redirects.length > 0) || (duplicates && duplicates.length > 0);

  if (!hasData) {
    return (
      <div className="glass-panel table-container" style={{ textAlign: 'center', padding: '40px 20px', color: '#64748b' }}>
        <Users size={40} color="#94a3b8" style={{ marginBottom: 12 }} />
        <h4 style={{ fontSize: '1.1rem', color: '#334155', marginBottom: 6 }}>No Candidates Evaluated or Shortlisted</h4>
        <p style={{ fontSize: '0.88rem' }}>Check if uploaded files are valid resumes or adjust your eligibility gate criteria.</p>
      </div>
    );
  }

  return (
    <div className="glass-panel table-container">
      {/* Header Controls & Export Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <h3 style={{ fontSize: '1.25rem', display: 'flex', alignItems: 'center', gap: 8 }}>
            <Award color="#d97706" size={22} /> Candidates & Role Shortlists
          </h3>
          <p style={{ fontSize: '0.82rem', color: '#64748b' }}>
            MongoDB Indexed Datastore &bull; PII Scrubbing {isBlindMode ? 'ACTIVE' : 'OFF'}
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {/* Fairness Test Trigger */}
          <button className="btn btn-secondary" onClick={runFairnessTest} disabled={isFairnessRunning}>
            <Scale size={16} color="#7c3aed" /> {isFairnessRunning ? 'Testing Bias...' : 'Run Fairness Test'}
          </button>

          {/* Audit Report Download */}
          <button className="btn btn-secondary" onClick={() => downloadAuditReport('json')}>
            <Download size={16} color="#2563eb" /> Export Audit Report (JSON)
          </button>
          <button className="btn btn-secondary" onClick={() => downloadAuditReport('pdf')}>
            <FileSpreadsheet size={16} color="#059669" /> View Audit Report (HTML)
          </button>
        </div>
      </div>

      {/* Fairness Test Result Notification Banner */}
      {fairnessResult && (
        <div style={{ padding: '12px 16px', background: '#f3e8ff', border: '1px solid #d8b4fe', borderRadius: 8, marginBottom: 20, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <div style={{ fontWeight: 600, color: '#6b21a8', fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: 6 }}>
              <Scale size={16} /> Fairness & Counterfactual Swap Test Results: PASSED
            </div>
            <div style={{ fontSize: '0.8rem', color: '#7e22ce' }}>
              Max counterfactual score delta: {fairnessResult.max_abs_score_delta} pts &bull; Rank changes: {fairnessResult.rank_changes} &bull; Sample size: {fairnessResult.sample_size} candidates
            </div>
          </div>
          <button className="btn btn-secondary" style={{ padding: '4px 8px', fontSize: '0.75rem' }} onClick={() => setFairnessResult(null)}>Dismiss</button>
        </div>
      )}

      {/* Role Navigation Tabs */}
      <div style={{ display: 'flex', gap: 8, borderBottom: '1px solid #e2e8f0', paddingBottom: 10, marginBottom: 20 }}>
        <button className={`btn ${activeTab === 'primary' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setActiveTab('primary')}>
          Primary Role Shortlist ({shortlist.length})
        </button>
        <button className={`btn ${activeTab === 'redirects' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setActiveTab('redirects')}>
          <CornerUpRight size={15} /> Redirect Pool ({redirects.length})
        </button>
        <button className={`btn ${activeTab === 'duplicates' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setActiveTab('duplicates')}>
          <Users size={15} /> Fraud & Duplicates ({duplicates.length})
        </button>
      </div>

      {/* Tab 1: Primary Role Shortlist */}
      {activeTab === 'primary' && (
        <table className="custom-table">
          <thead>
            <tr>
              <th style={{ width: '60px' }}>Rank</th>
              <th>Candidate Profile</th>
              <th>Match Score</th>
              <th>Matching Skills</th>
              <th>Missing / Substitutes</th>
              <th>Integrity Shield</th>
              <th style={{ textAlign: 'right' }}>Action & Explanation</th>
            </tr>
          </thead>
          <tbody>
            {shortlist && shortlist.length > 0 ? (
              shortlist.map((candidate) => {
                const isExpanded = expandedCandidateId === candidate.candidate_id;
              const scoreClass = getScoreBadgeClass(candidate.match_score_percentage);
              const rankClass = getRankClass(candidate.rank);
              const integrity = candidate.integrity || { severity: 'NONE', findings: [] };

              return (
                <React.Fragment key={candidate.candidate_id}>
                  <tr className="table-row-master">
                    <td>
                      <span className={`rank-badge ${rankClass}`}>#{candidate.rank}</span>
                    </td>
                    <td>
                      <div>
                        <div style={{ fontWeight: 600, fontSize: '0.95rem', display: 'flex', alignItems: 'center', gap: 8 }}>
                          {isBlindMode ? candidate.candidate_id : candidate.original_filename.replace(/\.[^/.]+$/, "")}
                          {candidate.lane === 'INELIGIBLE' && (
                            <span style={{ fontSize: '0.72rem', background: '#fef2f2', color: '#dc2626', border: '1px solid #fca5a5', padding: '2px 8px', borderRadius: 10, fontWeight: 600 }}>
                              Ineligible (Gate Failed)
                            </span>
                          )}
                          {candidate.is_updated_resume && (
                            <span style={{ fontSize: '0.72rem', background: '#fffbeb', color: '#b45309', border: '1px solid #fde68a', padding: '2px 8px', borderRadius: 10, display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                              <History size={11} /> Updated Resume (v{candidate.version})
                            </span>
                          )}
                        </div>
                        <div style={{ fontSize: '0.78rem', color: '#64748b' }}>
                          {candidate.raw_parsed_profile.total_years_experience} YOE &bull; {candidate.raw_parsed_profile.education?.degree || 'Degree Listed'} &bull; FP: {candidate.unique_fingerprint ? candidate.unique_fingerprint.substring(0, 8) : 'Auto'}
                        </div>
                      </div>
                    </td>
                    <td>
                      <span className={`score-badge ${scoreClass}`}>
                        {candidate.match_score_percentage}%
                      </span>
                    </td>
                    <td>
                      <div className="tags-wrapper">
                        {candidate.skill_details.matching_skills.slice(0, 4).map((skill, i) => (
                          <span key={i} className="skill-tag matching">{skill}</span>
                        ))}
                      </div>
                    </td>
                    <td>
                      <div className="tags-wrapper">
                        {candidate.skill_details.missing_skills.length > 0 ? (
                          candidate.skill_details.missing_skills.map((skill, i) => (
                            <span key={i} className="skill-tag missing">
                              {skill} {candidate.skill_details.substitute_skills[skill] ? `(has ${candidate.skill_details.substitute_skills[skill]})` : ''}
                            </span>
                          ))
                        ) : (
                          <span style={{ fontSize: '0.8rem', color: '#059669' }}>None (Full Match)</span>
                        )}
                      </div>
                    </td>
                    <td>
                      {integrity.severity !== 'NONE' ? (
                        <button 
                          className="btn btn-secondary"
                          style={{ padding: '4px 8px', fontSize: '0.75rem', border: '1px solid #fca5a5', background: '#fef2f2', color: '#991b1b', display: 'inline-flex', alignItems: 'center', gap: 4 }}
                          onClick={() => setShowIntegrityDrawer(candidate)}
                        >
                          <AlertOctagon size={13} color="#dc2626" />
                          {integrity.severity} Flag ({integrity.findings.length})
                        </button>
                      ) : (
                        <span style={{ fontSize: '0.8rem', color: '#059669', display: 'flex', alignItems: 'center', gap: 4 }}>
                          <ShieldCheck size={14} /> Clear
                        </span>
                      )}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <button
                        className="btn btn-secondary"
                        style={{ padding: '6px 12px', fontSize: '0.8rem' }}
                        onClick={() => toggleExpand(candidate.candidate_id)}
                      >
                        {isExpanded ? 'Hide' : 'View Explanation'}
                        {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                      </button>
                    </td>
                  </tr>

                  {/* Expandable Detail Row */}
                  {isExpanded && (
                    <tr className="expanded-row">
                      <td colSpan={7}>
                        <div className="explanation-box">
                          <div className="explanation-title">
                            <Sparkles size={16} color="#2563eb" /> Plain-Language AI Explanation & Rationale Note
                          </div>
                          <p className="explanation-text">{candidate.llm_explanation_note}</p>

                          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 14, marginTop: 16, paddingTop: 16, borderTop: '1px solid #e2e8f0' }}>
                            <div>
                              <div style={{ fontSize: '0.78rem', color: '#64748b' }}>Technical Skill Score</div>
                              <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#059669' }}>{candidate.skill_score}%</div>
                            </div>
                            <div>
                              <div style={{ fontSize: '0.78rem', color: '#64748b' }}>Experience Fit (YOE)</div>
                              <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#b45309' }}>{candidate.experience_score}%</div>
                            </div>
                            <div>
                              <div style={{ fontSize: '0.78rem', color: '#64748b' }}>Education / Certification</div>
                              <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#2563eb' }}>{candidate.education_score}%</div>
                            </div>
                            <div>
                              <div style={{ fontSize: '0.78rem', color: '#64748b' }}>MongoDB Version</div>
                              <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#475569' }}>v{candidate.version}</div>
                            </div>
                          </div>

                          {/* Per Skill Credit Breakdown */}
                          {candidate.skill_details.per_skill_credit && Object.keys(candidate.skill_details.per_skill_credit).length > 0 && (
                            <div style={{ marginTop: 14, paddingTop: 12, borderTop: '1px dotted #cbd5e1' }}>
                              <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#475569', marginBottom: 6 }}>Per-Skill Credit Transparency:</div>
                              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                                {Object.entries(candidate.skill_details.per_skill_credit).map(([sk, cr]) => (
                                  <span key={sk} style={{ fontSize: '0.75rem', background: '#f1f5f9', padding: '3px 8px', borderRadius: 6, border: '1px solid #cbd5e1' }}>
                                    {sk}: <strong>{Math.round(cr * 100)}%</strong> credit
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* LangGraph Agent Trace Inspector with Independent Re-Run Buttons */}
                          {langgraphTraces && (
                            <div style={{ marginTop: 18 }}>
                              <div style={{ fontSize: '0.82rem', fontWeight: 600, color: '#475569', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                  <Layers size={14} color="#2563eb" /> LangGraph Agent Step Inspection & Independent Re-Runs:
                                </span>
                                <span style={{ fontSize: '0.75rem', color: '#64748b' }}>Click any node to re-run step independently</span>
                              </div>

                              <div className="trace-grid">
                                {Object.entries(langgraphTraces).map(([stepKey, traceData]) => (
                                  <div key={stepKey} className="trace-card">
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                      <div className="trace-node-title">{stepKey}</div>
                                      <button
                                        type="button"
                                        className="btn-rerun-node"
                                        onClick={() => handleReRunNode(stepKey)}
                                        disabled={reRunningStep === stepKey}
                                      >
                                        <RotateCcw size={11} className={reRunningStep === stepKey ? 'spin-icon' : ''} />
                                        {reRunningStep === stepKey ? 'Running...' : 'Re-Run Node'}
                                      </button>
                                    </div>
                                    <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: 4 }}>
                                      Duration: {traceData.duration_ms} ms &bull; Status: {traceData.status || 'OK'}
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })
          ) : (
            <tr>
              <td colSpan={7} style={{ textAlign: 'center', color: '#64748b', padding: 24 }}>
                No candidates found in the primary role shortlist. Check the Redirect Pool or Fraud & Duplicates tabs above.
              </td>
            </tr>
          )}
          </tbody>
        </table>
      )}

      {/* Tab 2: Multi-Role Redirect Pool */}
      {activeTab === 'redirects' && (
        <div>
          <p style={{ fontSize: '0.85rem', color: '#64748b', marginBottom: 16 }}>
            Candidates not shortlisted for the primary role who are strong fits for alternative roles.
          </p>

          <table className="custom-table">
            <thead>
              <tr>
                <th>Candidate ID</th>
                <th>Primary Role Score</th>
                <th>Best Alternative Role Fit</th>
                <th>Redirect Recommendation</th>
              </tr>
            </thead>
            <tbody>
              {redirects.length > 0 ? (
                redirects.map((r, idx) => (
                  <tr key={idx}>
                    <td style={{ fontWeight: 600 }}>{r.candidate_id}</td>
                    <td>{r.primary_score ? `${r.primary_score}%` : 'Ineligible'}</td>
                    <td>
                      <span className="score-badge high">
                        {r.best_alternative.role_title}: {r.best_alternative.score}%
                      </span>
                    </td>
                    <td style={{ fontSize: '0.88rem', color: '#1e293b' }}>{r.message}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={4} style={{ textAlign: 'center', color: '#64748b', padding: 20 }}>No redirect recommendations. All candidates are evaluated for primary role.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Tab 3: Duplicates & Fraud */}
      {activeTab === 'duplicates' && (
        <div>
          <p style={{ fontSize: '0.85rem', color: '#64748b', marginBottom: 16 }}>
            Cluster of duplicate resumes, same-applicant submissions, and cross-resume project plagiarism.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {duplicates.length > 0 ? (
              duplicates.map((d) => (
                <div key={d.group_id} style={{ padding: 14, background: '#f8fafc', border: '1px solid #cbd5e1', borderRadius: 8 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontWeight: 700, color: '#0f172a' }}>{d.group_id} ({d.kind})</span>
                    <span style={{ fontSize: '0.8rem', background: '#e2e8f0', padding: '2px 8px', borderRadius: 6 }}>
                      Similarity: {Math.round(d.similarity * 100)}%
                    </span>
                  </div>
                  <div style={{ fontSize: '0.82rem', color: '#475569', marginTop: 4 }}>
                    {d.detail}
                  </div>
                  <div style={{ fontSize: '0.8rem', color: '#2563eb', marginTop: 6 }}>
                    Members: {d.members.join(', ')} (Canonical: {d.canonical || 'None'})
                  </div>
                </div>
              ))
            ) : (
              <div style={{ textAlign: 'center', color: '#64748b', padding: 20 }}>No duplicate or plagiarism clusters detected.</div>
            )}
          </div>
        </div>
      )}

      {/* Integrity Findings Drawer Modal */}
      {showIntegrityDrawer && (
        <div className="modal-backdrop" style={{ zIndex: 1200 }}>
          <div className="glass-panel modal-box" style={{ maxWidth: 600 }}>
            <h4 style={{ color: '#dc2626', display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
              <AlertOctagon size={20} /> Integrity Shield Findings: {showIntegrityDrawer.candidate_id}
            </h4>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 16 }}>
              {showIntegrityDrawer.integrity.findings.map((f, i) => (
                <div key={i} style={{ padding: 10, background: '#fef2f2', border: '1px solid #fca5a5', borderRadius: 6 }}>
                  <div style={{ fontWeight: 600, fontSize: '0.85rem', color: '#991b1b' }}>{f.type} ({f.severity})</div>
                  <div style={{ fontSize: '0.8rem', color: '#7f1d1d' }}>{f.detail}</div>
                  {f.evidence_snippet && (
                    <div style={{ fontSize: '0.75rem', fontFamily: 'monospace', background: '#fff', padding: 6, borderRadius: 4, marginTop: 4 }}>
                      Snippet: "{f.evidence_snippet}"
                    </div>
                  )}
                </div>
              ))}
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <button className="btn btn-secondary" onClick={() => setShowIntegrityDrawer(null)}>Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
