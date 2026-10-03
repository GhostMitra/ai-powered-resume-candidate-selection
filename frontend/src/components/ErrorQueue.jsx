import React from 'react';
import { AlertOctagon, HelpCircle } from 'lucide-react';

export default function ErrorQueue({ failedFiles }) {
  if (!failedFiles || failedFiles.length === 0) return null;

  return (
    <div className="glass-panel error-drawer">
      <h4 style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#f87171', fontSize: '1.05rem' }}>
        <AlertOctagon size={20} /> Could Not Process Queue ({failedFiles.length} file{failedFiles.length !== 1 ? 's' : ''})
      </h4>
      <p style={{ fontSize: '0.82rem', color: '#9ca3af', marginTop: 4 }}>
        The following files were safely isolated due to formatting or readability issues without interrupting batch evaluation.
      </p>

      {failedFiles.map((item, idx) => (
        <div key={idx} className="error-item">
          <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 600 }}>
            <span>📄 {item.filename}</span>
            <span style={{ color: '#f87171', fontSize: '0.78rem', textTransform: 'uppercase' }}>
              [{item.error_code}]
            </span>
          </div>
          <div style={{ color: '#d1d5db', marginTop: 4 }}>{item.user_message}</div>
          <div style={{ fontSize: '0.78rem', color: '#a5b4fc', marginTop: 4, display: 'flex', alignItems: 'center', gap: 4 }}>
            <HelpCircle size={12} /> Suggestion: {item.action_suggested}
          </div>
        </div>
      ))}
    </div>
  );
}
