import React, { useState } from 'react';
import { FileText, UploadCloud, Trash2, FileCheck, Plus, X, SlidersHorizontal, Edit3 } from 'lucide-react';

export default function DualUpload({ 
  jdFields, 
  setJdFields, 
  resumeFiles, 
  setResumeFiles, 
  onFileDrop 
}) {
  const [activeTab, setActiveTab] = useState('fields'); // 'fields' or 'raw'
  const [dragActive, setDragActive] = useState(false);

  const [newMandatorySkill, setNewMandatorySkill] = useState('');
  const [newPreferredSkill, setNewPreferredSkill] = useState('');

  // Add Mandatory Skill Chip
  const addMandatorySkill = () => {
    if (!newMandatorySkill.trim()) return;
    const skillsToAdd = newMandatorySkill.split(',').map(s => s.trim()).filter(Boolean);
    setJdFields(prev => ({
      ...prev,
      mandatory_skills: Array.from(new Set([...prev.mandatory_skills, ...skillsToAdd]))
    }));
    setNewMandatorySkill('');
  };

  const removeMandatorySkill = (skillToRemove) => {
    setJdFields(prev => ({
      ...prev,
      mandatory_skills: prev.mandatory_skills.filter(s => s !== skillToRemove)
    }));
  };

  // Add Preferred Skill Chip
  const addPreferredSkill = () => {
    if (!newPreferredSkill.trim()) return;
    const skillsToAdd = newPreferredSkill.split(',').map(s => s.trim()).filter(Boolean);
    setJdFields(prev => ({
      ...prev,
      preferred_skills: Array.from(new Set([...prev.preferred_skills, ...skillsToAdd]))
    }));
    setNewPreferredSkill('');
  };

  const removePreferredSkill = (skillToRemove) => {
    setJdFields(prev => ({
      ...prev,
      preferred_skills: prev.preferred_skills.filter(s => s !== skillToRemove)
    }));
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      onFileDrop(Array.from(e.dataTransfer.files));
    }
  };

  const handleFileInputChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      onFileDrop(Array.from(e.target.files));
    }
  };

  const removeFile = (idx) => {
    setResumeFiles(resumeFiles.filter((_, i) => i !== idx));
  };

  return (
    <div className="upload-grid">
      {/* Card 1: Editable Job Description Fields */}
      <div className="glass-panel upload-card">
        <div className="card-header">
          <div>
            <div className="card-title">
              <Edit3 color="#6366f1" size={20} /> 1. Job Description Requirements
            </div>
            <div className="card-subtitle">Edit role details, mandatory skills, and YOE</div>
          </div>

          {/* Mode Switch Tabs */}
          <div className="jd-tab-group">
            <button
              className={`jd-tab-btn ${activeTab === 'fields' ? 'active' : ''}`}
              onClick={() => setActiveTab('fields')}
            >
              <SlidersHorizontal size={14} /> Form Fields
            </button>
            <button
              className={`jd-tab-btn ${activeTab === 'raw' ? 'active' : ''}`}
              onClick={() => setActiveTab('raw')}
            >
              <FileText size={14} /> Raw Text
            </button>
          </div>
        </div>

        {activeTab === 'fields' ? (
          <div className="form-fields-container">
            {/* Row 1: Role Title & Min YOE */}
            <div className="form-row-2">
              <div className="form-group">
                <label className="form-label">Target Role Title *</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. Senior Backend Cloud Engineer"
                  value={jdFields.role_title}
                  onChange={(e) => setJdFields({ ...jdFields, role_title: e.target.value })}
                />
              </div>

              <div className="form-group" style={{ maxWidth: '140px' }}>
                <label className="form-label">Min YOE *</label>
                <input
                  type="number"
                  step="0.5"
                  min="0"
                  max="30"
                  className="form-input"
                  value={jdFields.min_years_experience}
                  onChange={(e) => setJdFields({ ...jdFields, min_years_experience: parseFloat(e.target.value) || 0 })}
                />
              </div>
            </div>

            {/* Row 2: Mandatory Technical Skills */}
            <div className="form-group">
              <label className="form-label" style={{ color: '#34d399' }}>
                Mandatory Required Skills *
              </label>
              <div className="skill-input-bar">
                <input
                  type="text"
                  className="form-input-sub"
                  placeholder="Add skill (e.g. Python, SQL, AWS) & press Enter"
                  value={newMandatorySkill}
                  onChange={(e) => setNewMandatorySkill(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addMandatorySkill(); } }}
                />
                <button type="button" className="btn-add-skill" onClick={addMandatorySkill}>
                  <Plus size={16} /> Add
                </button>
              </div>

              <div className="skills-chip-box">
                {jdFields.mandatory_skills.map((skill, i) => (
                  <span key={i} className="chip-item mandatory">
                    {skill}
                    <X size={12} className="chip-remove" onClick={() => removeMandatorySkill(skill)} />
                  </span>
                ))}
                {jdFields.mandatory_skills.length === 0 && (
                  <span className="chip-placeholder">No mandatory skills added yet.</span>
                )}
              </div>
            </div>

            {/* Row 3: Preferred / Secondary Skills */}
            <div className="form-group">
              <label className="form-label" style={{ color: '#a5b4fc' }}>
                Preferred / Nice-to-Have Skills
              </label>
              <div className="skill-input-bar">
                <input
                  type="text"
                  className="form-input-sub"
                  placeholder="Add preferred skill (e.g. Docker, Git) & press Enter"
                  value={newPreferredSkill}
                  onChange={(e) => setNewPreferredSkill(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addPreferredSkill(); } }}
                />
                <button type="button" className="btn-add-skill" onClick={addPreferredSkill}>
                  <Plus size={16} /> Add
                </button>
              </div>

              <div className="skills-chip-box">
                {jdFields.preferred_skills.map((skill, i) => (
                  <span key={i} className="chip-item preferred">
                    {skill}
                    <X size={12} className="chip-remove" onClick={() => removePreferredSkill(skill)} />
                  </span>
                ))}
              </div>
            </div>

            {/* Row 4: Education & Certifications */}
            <div className="form-group">
              <label className="form-label">Required Education / Degree</label>
              <input
                type="text"
                className="form-input"
                placeholder="e.g. Bachelor of Science in Computer Science"
                value={jdFields.required_education}
                onChange={(e) => setJdFields({ ...jdFields, required_education: e.target.value })}
              />
            </div>
          </div>
        ) : (
          <textarea
            className="jd-textarea"
            placeholder="Paste raw Job Description text here..."
            value={jdFields.raw_text}
            onChange={(e) => setJdFields({ ...jdFields, raw_text: e.target.value })}
          />
        )}
      </div>

      {/* Card 2: Batch Resumes */}
      <div className="glass-panel upload-card">
        <div className="card-header">
          <div>
            <div className="card-title">
              <UploadCloud color="#10b981" size={20} /> 2. Upload Batch Resumes
            </div>
            <div className="card-subtitle">Drag & drop candidate resumes (.pdf, .docx, .txt)</div>
          </div>
          <span className="status-pill">
            <span className={`status-indicator ${resumeFiles.length > 0 ? 'active' : ''}`}></span>
            {resumeFiles.length} File{resumeFiles.length !== 1 ? 's' : ''}
          </span>
        </div>

        <div
          className={`dropzone ${dragActive ? 'drag-active' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => document.getElementById('resume-file-input').click()}
        >
          <input
            type="file"
            id="resume-file-input"
            multiple
            accept=".pdf,.docx,.txt"
            style={{ display: 'none' }}
            onChange={handleFileInputChange}
          />
          <UploadCloud size={40} className="dropzone-icon" />
          <p style={{ fontWeight: 600, fontSize: '0.95rem' }}>Drop resumes here or click to browse</p>
          <p style={{ fontSize: '0.78rem', color: '#9ca3af', marginTop: 4 }}>
            Supports PDF, DOCX, and TXT files (Max 50 files)
          </p>
        </div>

        {/* Selected File List */}
        {resumeFiles.length > 0 && (
          <div className="file-list">
            {resumeFiles.map((file, idx) => (
              <div key={idx} className="file-item">
                <span style={{ display: 'flex', alignItems: 'center', gap: 6, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  <FileCheck size={14} color="#34d399" /> {file.name}
                </span>
                <button
                  onClick={(e) => { e.stopPropagation(); removeFile(idx); }}
                  style={{ background: 'none', border: 'none', color: '#f87171', cursor: 'pointer' }}
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
