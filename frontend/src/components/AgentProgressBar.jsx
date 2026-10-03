import React from 'react';
import { Cpu, CheckCircle, RefreshCw, Layers } from 'lucide-react';

export default function AgentProgressBar({ stage, percentage, nodeDetails }) {
  const steps = [
    { id: 1, name: 'PII Scrubbing', desc: 'File Ingestion & Anonymization' },
    { id: 2, name: 'Structured Parsing', desc: 'LangChain Agent LLM Extraction' },
    { id: 3, name: 'Math Scoring', desc: 'Vector Similarity & Weights' },
    { id: 4, name: 'AI Explanations', desc: 'Narrative Rationale Generation' }
  ];

  return (
    <div className="glass-panel agent-progress-box">
      <div className="progress-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div className="spin-icon-box">
            <RefreshCw size={20} color="#2563eb" style={{ animation: 'spin 1.2s linear infinite' }} />
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: '1.05rem', color: '#0f172a', display: 'flex', alignItems: 'center', gap: 6 }}>
              <Layers size={18} color="#2563eb" /> LangGraph Agent Pipeline Executing...
            </div>
            <div style={{ fontSize: '0.82rem', color: '#64748b' }}>
              {nodeDetails || 'Processing candidate batch through step-by-step agent graph nodes'}
            </div>
          </div>
        </div>

        <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#2563eb', fontFamily: 'var(--font-heading)' }}>
          {percentage}%
        </div>
      </div>

      {/* Progress Bar Track */}
      <div className="progress-bar-track">
        <div
          className="progress-bar-fill"
          style={{ width: `${percentage}%` }}
        />
      </div>

      {/* Step Nodes Badges */}
      <div className="progress-steps-grid">
        {steps.map((s) => {
          const isDone = stage > s.id;
          const isCurrent = stage === s.id;

          return (
            <div
              key={s.id}
              className={`step-badge-card ${isDone ? 'done' : isCurrent ? 'active' : ''}`}
            >
              <div className="step-badge-header">
                {isDone ? (
                  <CheckCircle size={16} color="#059669" />
                ) : isCurrent ? (
                  <Cpu size={16} color="#2563eb" className="pulse-icon" />
                ) : (
                  <span className="step-num">{s.id}</span>
                )}
                <span className="step-name">{s.name}</span>
              </div>
              <div className="step-desc">{s.desc}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
