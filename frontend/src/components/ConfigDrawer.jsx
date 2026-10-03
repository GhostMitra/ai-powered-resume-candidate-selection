import React, { useState, useEffect } from 'react';
import { Sliders, X, Filter, Clock, ShieldAlert, Layers, CheckCircle2, Plus, Trash2, Edit3 } from 'lucide-react';

export default function ConfigDrawer({ config, onSave, onClose, batchId, apiBaseUrl }) {
  const [activeTab, setActiveTab] = useState('gates'); // Open directly to gates per user request!
  const [dimensions, setDimensions] = useState(config.dimensions || { skill: 0.60, experience: 0.25, education: 0.15 });
  const [evidence, setEvidence] = useState(config.evidence || { listed: 0.2, project: 0.4, experience: 0.4, mode: 'strongest', undated_recency: 0.8 });
  const [recency, setRecency] = useState(config.recency || { enabled: true, floor: 0.2 });
  
  // User Editable Gate Rules
  const [gates, setGates] = useState([
    { id: 'cgpa_min', label: 'CGPA >= 6.5', field: 'cgpa_10', op: '>=', value: 6.5, enabled: true, on_missing: 'review' },
    { id: 'no_backlogs', label: 'No Active Backlogs', field: 'active_backlogs', op: '==', value: 0, enabled: true, on_missing: 'pass' },
    { id: 'grad_year_2027', label: 'Graduating Year == 2027', field: 'graduation_year', op: '==', value: 2027, enabled: true, on_missing: 'pass' }
  ]);

  const [gateImpacts, setGateImpacts] = useState([]);

  // New Gate Form state
  const [newGate, setNewGate] = useState({
    field: 'cgpa_10',
    op: '>=',
    value: '6.5',
    on_missing: 'review',
    label: ''
  });

  useEffect(() => {
    fetchGateImpacts();
  }, [gates]);

  const fetchGateImpacts = async () => {
    if (!batchId) return;
    try {
      const res = await fetch(`${apiBaseUrl}/api/v1/batches/${batchId}/gates/preview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(gates)
      });
      if (res.ok) {
        const data = await res.json();
        setGateImpacts(data);
      }
    } catch (e) {
      console.warn("Gate preview failed:", e);
    }
  };

  const handleDimensionChange = (key, val) => {
    const num = parseFloat(val);
    const updated = { ...dimensions, [key]: num };
    const remaining = 1.0 - num;
    const otherKeys = Object.keys(dimensions).filter(k => k !== key);
    const sumOthers = otherKeys.reduce((acc, k) => acc + dimensions[k], 0);
    
    if (sumOthers > 0) {
      otherKeys.forEach(k => {
        updated[k] = Math.max(0, Math.round(((dimensions[k] / sumOthers) * remaining) * 100) / 100);
      });
    }
    setDimensions(updated);
  };

  const handleGateToggle = (id) => {
    setGates(gates.map(g => g.id === id ? { ...g, enabled: !g.enabled } : g));
  };

  const handleGateFieldUpdate = (id, key, val) => {
    setGates(gates.map(g => g.id === id ? { ...g, [key]: val } : g));
  };

  const handleRemoveGate = (id) => {
    setGates(gates.filter(g => g.id !== id));
  };

  const handleAddGate = () => {
    const parsedVal = !isNaN(newGate.value) ? parseFloat(newGate.value) : newGate.value;
    const autoLabel = newGate.label.trim() || `${newGate.field} ${newGate.op} ${newGate.value}`;
    const created = {
      id: `gate_${Date.now()}`,
      label: autoLabel,
      field: newGate.field,
      op: newGate.op,
      value: parsedVal,
      enabled: true,
      on_missing: newGate.on_missing
    };
    setGates([...gates, created]);
    setNewGate({ field: 'cgpa_10', op: '>=', value: '6.5', on_missing: 'review', label: '' });
  };

  const handleApply = () => {
    const updatedConfig = {
      ...config,
      dimensions,
      evidence,
      recency
    };
    onSave(updatedConfig, gates);
    onClose();
  };

  return (
    <div className="modal-backdrop" style={{ zIndex: 1100 }}>
      <div className="glass-panel modal-box" style={{ maxWidth: 780, width: '92%' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20, borderBottom: '1px solid #e2e8f0', paddingBottom: 14 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Sliders color="#2563eb" size={24} />
            <h3 style={{ fontSize: '1.25rem', margin: 0 }}>Recruiter Pipeline Configuration</h3>
          </div>
          <button className="btn btn-secondary" style={{ padding: 6 }} onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        {/* Navigation Tabs */}
        <div style={{ display: 'flex', gap: 8, marginBottom: 20, borderBottom: '1px solid #e2e8f0', paddingBottom: 8 }}>
          <button className={`btn ${activeTab === 'gates' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setActiveTab('gates')}>
            <Filter size={15} /> Editable Eligibility Gates
          </button>
          <button className={`btn ${activeTab === 'dimensions' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setActiveTab('dimensions')}>
            Dimensions
          </button>
          <button className={`btn ${activeTab === 'evidence' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setActiveTab('evidence')}>
            Skill Evidence
          </button>
          <button className={`btn ${activeTab === 'recency' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setActiveTab('recency')}>
            Recency Decay
          </button>
        </div>

        {/* Tab: User Editable Eligibility Gates */}
        {activeTab === 'gates' && (
          <div>
            <p style={{ fontSize: '0.82rem', color: '#64748b', marginBottom: 16 }}>
              Hard screening rules run BEFORE the LLM. Ineligible candidates skip LLM parsing to save compute. Customize fields, operators, values, and missing data policies below:
            </p>

            {/* List of Editable Gates */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginBottom: 20 }}>
              {gates.map((g) => {
                const impact = gateImpacts.find(i => i.rule_id === g.id);
                return (
                  <div key={g.id} style={{ padding: 14, background: '#f8fafc', border: '1px solid #cbd5e1', borderRadius: 8 }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                        <input type="checkbox" checked={g.enabled} onChange={() => handleGateToggle(g.id)} style={{ width: 18, height: 18 }} />
                        <input
                          type="text"
                          value={g.label}
                          onChange={e => handleGateFieldUpdate(g.id, 'label', e.target.value)}
                          style={{ fontWeight: 600, fontSize: '0.92rem', border: '1px solid #cbd5e1', borderRadius: 4, padding: '2px 8px', minWidth: 220 }}
                        />
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                        {impact && (
                          <span style={{ fontSize: '0.78rem', background: '#fee2e2', color: '#991b1b', padding: '3px 8px', borderRadius: 12, fontWeight: 600 }}>
                            Removes {impact.fails} ({impact.fail_pct}%)
                          </span>
                        )}
                        <button className="btn btn-secondary" style={{ padding: 4, color: '#dc2626' }} onClick={() => handleRemoveGate(g.id)}>
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </div>

                    {/* Inline Field Editor Row */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr 1.2fr 1.5fr', gap: 10, marginTop: 10 }}>
                      <div>
                        <label style={{ fontSize: '0.75rem', color: '#64748b' }}>Target Field</label>
                        <select
                          value={g.field}
                          onChange={e => handleGateFieldUpdate(g.id, 'field', e.target.value)}
                          style={{ width: '100%', padding: 4, borderRadius: 4, border: '1px solid #cbd5e1', fontSize: '0.82rem' }}
                        >
                          <option value="cgpa_10">cgpa_10 (CGPA / 10)</option>
                          <option value="active_backlogs">active_backlogs</option>
                          <option value="total_backlogs">total_backlogs</option>
                          <option value="graduation_year">graduation_year</option>
                          <option value="pct_10th">pct_10th (10th %)</option>
                          <option value="pct_12th">pct_12th (12th %)</option>
                          <option value="degree">degree</option>
                          <option value="branch_group">branch_group</option>
                        </select>
                      </div>

                      <div>
                        <label style={{ fontSize: '0.75rem', color: '#64748b' }}>Operator</label>
                        <select
                          value={g.op}
                          onChange={e => handleGateFieldUpdate(g.id, 'op', e.target.value)}
                          style={{ width: '100%', padding: 4, borderRadius: 4, border: '1px solid #cbd5e1', fontSize: '0.82rem' }}
                        >
                          <option value=">=">&gt;= (Greater or Equal)</option>
                          <option value="<=">&lt;= (Less or Equal)</option>
                          <option value="==">== (Exact Equals)</option>
                          <option value="in">in (Value List)</option>
                          <option value="not_in">not_in (Not In List)</option>
                        </select>
                      </div>

                      <div>
                        <label style={{ fontSize: '0.75rem', color: '#64748b' }}>Threshold Value</label>
                        <input
                          type="text"
                          value={g.value}
                          onChange={e => handleGateFieldUpdate(g.id, 'value', e.target.value)}
                          style={{ width: '100%', padding: 4, borderRadius: 4, border: '1px solid #cbd5e1', fontSize: '0.82rem' }}
                        />
                      </div>

                      <div>
                        <label style={{ fontSize: '0.75rem', color: '#64748b' }}>On Missing Fact Policy</label>
                        <select
                          value={g.on_missing}
                          onChange={e => handleGateFieldUpdate(g.id, 'on_missing', e.target.value)}
                          style={{ width: '100%', padding: 4, borderRadius: 4, border: '1px solid #cbd5e1', fontSize: '0.82rem' }}
                        >
                          <option value="review">review (Send to Review)</option>
                          <option value="pass">pass (Auto Pass)</option>
                          <option value="fail">fail (Auto Fail)</option>
                        </select>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Add New Gate Form */}
            <div style={{ padding: 14, background: '#eff6ff', border: '1px dashed #93c5fd', borderRadius: 8 }}>
              <div style={{ fontWeight: 600, fontSize: '0.88rem', color: '#1e40af', marginBottom: 10, display: 'flex', alignItems: 'center', gap: 6 }}>
                <Plus size={16} /> Add Custom Gate Rule
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr 1fr 1.2fr auto', gap: 10, alignItems: 'end' }}>
                <div>
                  <label style={{ fontSize: '0.75rem', color: '#1e40af' }}>Field</label>
                  <select
                    value={newGate.field}
                    onChange={e => setNewGate({ ...newGate, field: e.target.value })}
                    style={{ width: '100%', padding: 6, borderRadius: 4, border: '1px solid #bfdbfe', fontSize: '0.82rem' }}
                  >
                    <option value="cgpa_10">cgpa_10</option>
                    <option value="active_backlogs">active_backlogs</option>
                    <option value="graduation_year">graduation_year</option>
                    <option value="degree">degree</option>
                    <option value="branch_group">branch_group</option>
                  </select>
                </div>

                <div>
                  <label style={{ fontSize: '0.75rem', color: '#1e40af' }}>Op</label>
                  <select
                    value={newGate.op}
                    onChange={e => setNewGate({ ...newGate, op: e.target.value })}
                    style={{ width: '100%', padding: 6, borderRadius: 4, border: '1px solid #bfdbfe', fontSize: '0.82rem' }}
                  >
                    <option value=">=">&gt;=</option>
                    <option value="<=">&lt;=</option>
                    <option value="==">==</option>
                    <option value="in">in</option>
                  </select>
                </div>

                <div>
                  <label style={{ fontSize: '0.75rem', color: '#1e40af' }}>Value</label>
                  <input
                    type="text"
                    value={newGate.value}
                    onChange={e => setNewGate({ ...newGate, value: e.target.value })}
                    style={{ width: '100%', padding: 5, borderRadius: 4, border: '1px solid #bfdbfe', fontSize: '0.82rem' }}
                  />
                </div>

                <div>
                  <label style={{ fontSize: '0.75rem', color: '#1e40af' }}>On Missing</label>
                  <select
                    value={newGate.on_missing}
                    onChange={e => setNewGate({ ...newGate, on_missing: e.target.value })}
                    style={{ width: '100%', padding: 6, borderRadius: 4, border: '1px solid #bfdbfe', fontSize: '0.82rem' }}
                  >
                    <option value="review">review</option>
                    <option value="pass">pass</option>
                    <option value="fail">fail</option>
                  </select>
                </div>

                <button className="btn btn-primary" style={{ padding: '6px 14px', fontSize: '0.82rem' }} onClick={handleAddGate}>
                  Add Rule
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: Dimensions */}
        {activeTab === 'dimensions' && (
          <div>
            <p style={{ fontSize: '0.85rem', color: '#64748b', marginBottom: 16 }}>
              Adjust relative weights for match scoring. Weights must sum to 100%.
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div>
                <label style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.9rem', fontWeight: 600 }}>
                  <span>Technical Skills</span>
                  <span>{Math.round(dimensions.skill * 100)}%</span>
                </label>
                <input type="range" min="0" max="1" step="0.05" value={dimensions.skill} onChange={e => handleDimensionChange('skill', e.target.value)} style={{ width: '100%' }} />
              </div>

              <div>
                <label style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.9rem', fontWeight: 600 }}>
                  <span>Experience Fit (YOE)</span>
                  <span>{Math.round(dimensions.experience * 100)}%</span>
                </label>
                <input type="range" min="0" max="1" step="0.05" value={dimensions.experience} onChange={e => handleDimensionChange('experience', e.target.value)} style={{ width: '100%' }} />
              </div>

              <div>
                <label style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.9rem', fontWeight: 600 }}>
                  <span>Education & Certification</span>
                  <span>{Math.round(dimensions.education * 100)}%</span>
                </label>
                <input type="range" min="0" max="1" step="0.05" value={dimensions.education} onChange={e => handleDimensionChange('education', e.target.value)} style={{ width: '100%' }} />
              </div>
            </div>
          </div>
        )}

        {/* Tab 3: Evidence */}
        {activeTab === 'evidence' && (
          <div>
            <p style={{ fontSize: '0.85rem', color: '#64748b', marginBottom: 16 }}>
              Configure context weights depending on WHERE a skill is demonstrated in the resume.
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12, marginBottom: 16 }}>
              <div>
                <label style={{ fontSize: '0.8rem', fontWeight: 600 }}>Listed Skills Section</label>
                <input type="number" step="0.05" min="0" max="1" value={evidence.listed} onChange={e => setEvidence({ ...evidence, listed: parseFloat(e.target.value) })} style={{ width: '100%', padding: 6, borderRadius: 6, border: '1px solid #cbd5e1' }} />
              </div>
              <div>
                <label style={{ fontSize: '0.8rem', fontWeight: 600 }}>Project Description</label>
                <input type="number" step="0.05" min="0" max="1" value={evidence.project} onChange={e => setEvidence({ ...evidence, project: parseFloat(e.target.value) })} style={{ width: '100%', padding: 6, borderRadius: 6, border: '1px solid #cbd5e1' }} />
              </div>
              <div>
                <label style={{ fontSize: '0.8rem', fontWeight: 600 }}>Work Experience / Job</label>
                <input type="number" step="0.05" min="0" max="1" value={evidence.experience} onChange={e => setEvidence({ ...evidence, experience: parseFloat(e.target.value) })} style={{ width: '100%', padding: 6, borderRadius: 6, border: '1px solid #cbd5e1' }} />
              </div>
            </div>
          </div>
        )}

        {/* Tab 4: Recency */}
        {activeTab === 'recency' && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <span style={{ fontSize: '0.9rem', fontWeight: 600 }}>Enable Skill Recency Decay</span>
              <input type="checkbox" checked={recency.enabled} onChange={e => setRecency({ ...recency, enabled: e.target.checked })} style={{ width: 18, height: 18 }} />
            </div>

            <p style={{ fontSize: '0.82rem', color: '#64748b' }}>
              Skills decay over time based on category half-lives (Fast-moving LLM tools decay faster than core SQL/DSA fundamentals).
            </p>
          </div>
        )}

        {/* Modal Actions */}
        <div style={{ marginTop: 24, paddingTop: 16, borderTop: '1px solid #e2e8f0', display: 'flex', justifyContent: 'flex-end', gap: 12 }}>
          <button className="btn btn-secondary" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" onClick={handleApply}>
            <CheckCircle2 size={16} /> Save & Re-Evaluate Pipeline
          </button>
        </div>
      </div>
    </div>
  );
}
