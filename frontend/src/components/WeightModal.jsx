import React, { useState } from 'react';
import { Sliders, X, Check } from 'lucide-react';

export default function WeightModal({ weights, onSave, onClose }) {
  const [skillW, setSkillW] = useState(Math.round(weights.skill_weight * 100));
  const [expW, setExpW] = useState(Math.round(weights.experience_weight * 100));
  const [eduW, setEduW] = useState(Math.round(weights.education_weight * 100));

  const total = skillW + expW + eduW;

  const handleSave = () => {
    if (total === 0) return;
    onSave({
      skill_weight: parseFloat((skillW / 100).toFixed(2)),
      experience_weight: parseFloat((expW / 100).toFixed(2)),
      education_weight: parseFloat((eduW / 100).toFixed(2))
    });
    onClose();
  };

  return (
    <div className="modal-overlay">
      <div className="glass-panel modal-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <h3 style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '1.2rem' }}>
            <Sliders size={20} color="#6366f1" /> Customize Evaluation Criteria Weights
          </h3>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: '#9ca3af', cursor: 'pointer' }}>
            <X size={20} />
          </button>
        </div>

        <p style={{ fontSize: '0.88rem', color: '#9ca3af', marginBottom: 20 }}>
          Adjust the relative weight sliders for matching logic. Weights dictate the candidate shortlist score calculation.
        </p>

        <div className="slider-group">
          <div className="slider-header">
            <span>Technical & Core Skill Match</span>
            <span style={{ fontWeight: 700, color: '#6366f1' }}>{skillW}%</span>
          </div>
          <input
            type="range"
            min="0"
            max="100"
            value={skillW}
            onChange={(e) => setSkillW(Number(e.target.value))}
            className="custom-range"
          />
        </div>

        <div className="slider-group">
          <div className="slider-header">
            <span>Years of Experience (YOE)</span>
            <span style={{ fontWeight: 700, color: '#10b981' }}>{expW}%</span>
          </div>
          <input
            type="range"
            min="0"
            max="100"
            value={expW}
            onChange={(e) => setExpW(Number(e.target.value))}
            className="custom-range"
          />
        </div>

        <div className="slider-group">
          <div className="slider-header">
            <span>Education & Certifications</span>
            <span style={{ fontWeight: 700, color: '#f59e0b' }}>{eduW}%</span>
          </div>
          <input
            type="range"
            min="0"
            max="100"
            value={eduW}
            onChange={(e) => setEduW(Number(e.target.value))}
            className="custom-range"
          />
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 24 }}>
          <span style={{ fontSize: '0.85rem', color: total === 100 ? '#34d399' : '#f87171' }}>
            Total Sum: <strong>{total}%</strong> {total !== 100 && '(Recommended sum is 100%)'}
          </span>

          <div style={{ display: 'flex', gap: 10 }}>
            <button className="btn btn-secondary" onClick={onClose}>Cancel</button>
            <button className="btn btn-primary" onClick={handleSave}>
              <Check size={16} /> Apply Weights
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
