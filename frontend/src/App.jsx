import React, { useState, useEffect } from 'react';
import { 
  Sparkles, 
  Eye, 
  EyeOff, 
  Sliders, 
  Play, 
  RefreshCw, 
  AlertTriangle,
  Zap,
  ShieldCheck,
  Cpu
} from 'lucide-react';
import DualUpload from './components/DualUpload';
import CandidateTable from './components/CandidateTable';
import ConfigDrawer from './components/ConfigDrawer';
import ErrorQueue from './components/ErrorQueue';
import AgentProgressBar from './components/AgentProgressBar';

const API_BASE_URL = 'http://127.0.0.1:8000';

export default function App() {
  const [jdFields, setJdFields] = useState({
    role_title: 'Senior Backend Cloud Engineer',
    min_years_experience: 3.0,
    mandatory_skills: ['Python', 'SQL', 'AWS', 'Docker'],
    preferred_skills: ['Kubernetes', 'PostgreSQL', 'Git'],
    required_education: 'Bachelor of Science in Computer Science',
    raw_text: ''
  });

  const [resumeFiles, setResumeFiles] = useState([]);
  const [isBlindMode, setIsBlindMode] = useState(true);
  const [showConfigDrawer, setShowConfigDrawer] = useState(false);
  
  const [screeningConfig, setScreeningConfig] = useState({
    dimensions: { skill: 0.60, experience: 0.25, education: 0.15 },
    evidence: { listed: 0.2, project: 0.4, experience: 0.4, mode: 'strongest', undated_recency: 0.8 },
    recency: { enabled: true, floor: 0.2 },
    shortlist: { top_k: 10, min_score: 60.0, redirect_min_score: 65.0 }
  });

  const [gates, setGates] = useState([
    { id: 'cgpa_min', label: 'CGPA >= 6.5', field: 'cgpa_10', op: '>=', value: 6.5, enabled: true, on_missing: 'review' },
    { id: 'no_backlogs', label: 'No Active Backlogs', field: 'active_backlogs', op: '==', value: 0, enabled: true, on_missing: 'pass' },
    { id: 'grad_year_2027', label: 'Graduating Year == 2027', field: 'graduation_year', op: '==', value: 2027, enabled: false, on_missing: 'pass' }
  ]);

  const [isLoading, setIsLoading] = useState(false);
  const [agentProgress, setAgentProgress] = useState({ stage: 1, percentage: 15, details: '' });
  const [serverStatus, setServerStatus] = useState({ online: false, lm_studio_connected: false, throughput: {} });
  const [samplePresets, setSamplePresets] = useState({ jds: [], resumes: [] });
  const [evaluationResult, setEvaluationResult] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);

  useEffect(() => {
    fetchServerStatus();
    fetchSamplePresets();
  }, []);

  const fetchServerStatus = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/`);
      if (res.ok) {
        const data = await res.json();
        setServerStatus({ 
          online: true, 
          lm_studio_connected: data.lm_studio_connected,
          throughput: data.throughput_metrics || {}
        });
      }
    } catch (e) {
      setServerStatus({ online: false, lm_studio_connected: false, throughput: {} });
    }
  };

  const fetchSamplePresets = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/samples`);
      if (res.ok) {
        const data = await res.json();
        setSamplePresets({ jds: data.sample_jds, resumes: data.sample_resumes });
      }
    } catch (e) {
      console.warn("Could not fetch sample presets:", e);
    }
  };

  const loadSampleData = (sampleJd) => {
    if (sampleJd.id === 'jd_backend') {
      setJdFields({
        role_title: 'Senior Backend Cloud Engineer',
        min_years_experience: 3.0,
        mandatory_skills: ['Python', 'SQL', 'AWS', 'Docker'],
        preferred_skills: ['Kubernetes', 'PostgreSQL', 'Git', 'REST APIs'],
        required_education: 'Bachelor of Science in Computer Science',
        raw_text: sampleJd.content
      });
    } else if (sampleJd.id === 'jd_frontend') {
      setJdFields({
        role_title: 'Frontend React Developer',
        min_years_experience: 2.0,
        mandatory_skills: ['React', 'TypeScript', 'CSS', 'REST APIs'],
        preferred_skills: ['Next.js', 'Redux', 'Tailwind CSS'],
        required_education: 'Bachelor degree in Computer Science',
        raw_text: sampleJd.content
      });
    } else if (sampleJd.id === 'jd_datascientist') {
      setJdFields({
        role_title: 'Data Scientist & ML Engineer',
        min_years_experience: 3.0,
        mandatory_skills: ['Python', 'SQL', 'Machine Learning', 'TensorFlow'],
        preferred_skills: ['PyTorch', 'BigQuery', 'Pandas'],
        required_education: 'Master or Bachelor in Data Science',
        raw_text: sampleJd.content
      });
    } else {
      setJdFields(prev => ({ ...prev, raw_text: sampleJd.content }));
    }

    if (samplePresets.resumes && samplePresets.resumes.length > 0) {
      const sampleFiles = samplePresets.resumes.map(r => {
        const blob = new Blob([r.content], { type: 'text/plain' });
        return new File([blob], r.filename, { type: 'text/plain' });
      });
      setResumeFiles(sampleFiles);
    }
  };

  const handleFileDrop = (newFiles) => {
    setResumeFiles(prev => [...prev, ...newFiles]);
  };

  const getFormattedJdText = () => {
    if (jdFields.mandatory_skills.length > 0 || jdFields.role_title) {
      return `Role Title: ${jdFields.role_title}
Required Experience: ${jdFields.min_years_experience} years
Mandatory Technical Skills: ${jdFields.mandatory_skills.join(', ')}
Preferred Skills: ${jdFields.preferred_skills.join(', ')}
Required Education: ${jdFields.required_education}`;
    }
    return jdFields.raw_text;
  };

  const runCandidateMatching = async () => {
    setErrorMessage(null);

    // Edge Case 1: No Resumes Uploaded
    if (!resumeFiles || resumeFiles.length === 0) {
      setErrorMessage("No resumes uploaded! Please add at least one candidate resume file to evaluate.");
      return;
    }

    // Edge Case 2: Missing Role Title or Required Skills
    if (!jdFields.role_title || jdFields.role_title.trim() === "") {
      setErrorMessage("Job description missing key fields! Please enter a Role Title before ranking.");
      return;
    }

    if (!jdFields.mandatory_skills || jdFields.mandatory_skills.length === 0) {
      setErrorMessage("Job description missing key fields! At least one mandatory required skill is required before ranking.");
      return;
    }

    const formattedJd = getFormattedJdText();

    setIsLoading(true);
    setEvaluationResult(null);

    setAgentProgress({ stage: 1, percentage: 15, details: "Node 1: PDF font/contrast scan & Prompt Injection Shield..." });

    const pTimer1 = setTimeout(() => {
      setAgentProgress({ stage: 2, percentage: 35, details: "Node 2: Fact Extraction & Eligibility Gate evaluation..." });
    }, 400);

    const pTimer2 = setTimeout(() => {
      setAgentProgress({ stage: 3, percentage: 55, details: "Node 3: MinHash LSH deduplication & same-applicant matching..." });
    }, 800);

    const pTimer3 = setTimeout(() => {
      setAgentProgress({ stage: 4, percentage: 75, details: "Node 4: LangGraph Agent structured parsing (with parse_cache)..." });
    }, 1200);

    const pTimer4 = setTimeout(() => {
      setAgentProgress({ stage: 5, percentage: 92, details: "Node 5: Context-weighted scoring & multi-role redirect pool..." });
    }, 1600);

    try {
      const formData = new FormData();
      formData.append('jd_text', formattedJd);
      formData.append('skill_weight', screeningConfig.dimensions.skill);
      formData.append('experience_weight', screeningConfig.dimensions.experience);
      formData.append('education_weight', screeningConfig.dimensions.education);
      
      const rolesPayload = [{
        jd_id: 'PRIMARY',
        jd_text: formattedJd,
        is_primary: true,
        gates: gates
      }];
      formData.append('roles_json', JSON.stringify(rolesPayload));
      formData.append('config_json', JSON.stringify(screeningConfig));

      resumeFiles.forEach(file => {
        formData.append('resumes', file);
      });

      const response = await fetch(`${API_BASE_URL}/api/v1/screen/batch`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || 'Batch screening failed.');
      }

      const data = await response.json();
      setAgentProgress({ stage: 6, percentage: 100, details: "Evaluation Complete! Audit Report generated." });
      
      setTimeout(() => {
        setEvaluationResult(data);
        setIsLoading(false);
        fetchServerStatus();
      }, 300);

    } catch (err) {
      setErrorMessage(err.message || 'Error occurred while running evaluation pipeline.');
      setIsLoading(false);
    } finally {
      clearTimeout(pTimer1);
      clearTimeout(pTimer2);
      clearTimeout(pTimer3);
      clearTimeout(pTimer4);
    }
  };

  const handleSaveConfig = (updatedConfig, updatedGates) => {
    setScreeningConfig(updatedConfig);
    setGates(updatedGates);
  };

  const handleReRunStep = async (batchId, stepName) => {
    try {
      const formData = new FormData();
      formData.append('batch_id', batchId);
      formData.append('step_name', stepName);

      const res = await fetch(`${API_BASE_URL}/api/v1/agent/re-run-step`, {
        method: 'POST',
        body: formData
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Step re-run failed');
      }

      const updatedData = await res.json();
      setEvaluationResult(updatedData);
    } catch (e) {
      setErrorMessage(`Failed to re-run step '${stepName}': ${e.message}`);
    }
  };

  return (
    <div className="app-container">
      {/* Header */}
      <header className="glass-panel app-header">
        <div className="logo-group">
          <div className="logo-icon">
            <Sparkles size={24} />
          </div>
          <div>
            <h1 className="logo-title">TalentMatch AI &bull; Mass-Hiring Edition</h1>
            <p style={{ fontSize: '0.78rem', color: '#64748b', display: 'flex', alignItems: 'center', gap: 6 }}>
              <ShieldCheck size={12} color="#059669" /> Integrity Shield v1.1 Active &bull; <Cpu size={12} color="#2563eb" /> LM Studio (Semaphore: 2)
            </p>
          </div>
        </div>

        <div className="header-controls">
          {/* Server Status Indicator */}
          <div className="status-pill">
            <span className={`status-indicator ${serverStatus.online ? 'active' : ''}`}></span>
            <span>{serverStatus.online ? (serverStatus.lm_studio_connected ? 'LM Studio (Nemotron-3)' : 'Engine Online') : 'Backend Offline'}</span>
          </div>

          {/* Blind Mode Toggle */}
          <label className="toggle-switch-label">
            {isBlindMode ? <EyeOff size={16} color="#059669" /> : <Eye size={16} color="#64748b" />}
            <span>Blind Review</span>
            <div
              className={`toggle-switch ${isBlindMode ? 'checked' : ''}`}
              onClick={() => setIsBlindMode(!isBlindMode)}
            >
              <div className="toggle-slider"></div>
            </div>
          </label>

          {/* Recruiter Configuration Drawer Trigger */}
          <button className="btn btn-secondary" onClick={() => setShowConfigDrawer(true)}>
            <Sliders size={16} /> Pipeline Config
          </button>
        </div>
      </header>

      {/* Preset Demo Bar */}
      <div className="preset-bar">
        <Zap size={16} color="#d97706" />
        <span className="preset-title">Quick Demo Loader:</span>
        {samplePresets.jds.map((jd) => (
          <button key={jd.id} className="btn-sample" onClick={() => loadSampleData(jd)}>
            Load "{jd.title}" + Synthetic Batch
          </button>
        ))}
      </div>

      {/* Error Banner */}
      {errorMessage && (
        <div className="glass-panel" style={{ padding: '14px 20px', marginBottom: 24, border: '1px solid #fecaca', background: '#fef2f2', display: 'flex', alignItems: 'center', gap: 10 }}>
          <AlertTriangle color="#dc2626" size={20} />
          <span style={{ color: '#b91c1c', fontSize: '0.9rem', fontWeight: 500 }}>{errorMessage}</span>
        </div>
      )}

      {/* Dual Upload Area */}
      <DualUpload
        jdFields={jdFields}
        setJdFields={setJdFields}
        resumeFiles={resumeFiles}
        setResumeFiles={setResumeFiles}
        onFileDrop={handleFileDrop}
      />

      {/* Primary Action Button Banner */}
      <div className="glass-panel action-banner">
        <div>
          <div style={{ fontWeight: 600, fontSize: '1.05rem', color: '#0f172a' }}>
            Evaluating Target Role: <span style={{ color: '#2563eb' }}>{jdFields.role_title || 'Software Role'}</span>
          </div>
          <div style={{ fontSize: '0.82rem', color: '#64748b' }}>
            Weights: Skill {Math.round(screeningConfig.dimensions.skill*100)}% | Exp {Math.round(screeningConfig.dimensions.experience*100)}% | Edu {Math.round(screeningConfig.dimensions.education*100)}% &bull; Mode: {screeningConfig.evidence.mode}
          </div>
        </div>

        <button
          className="btn btn-primary"
          style={{ padding: '12px 28px', fontSize: '1rem' }}
          onClick={runCandidateMatching}
          disabled={isLoading}
        >
          {isLoading ? (
            <>
              <RefreshCw size={20} className="spin-icon" style={{ animation: 'spin 1s linear infinite' }} />
              LangGraph Agent Pipeline Running...
            </>
          ) : (
            <>
              <Play size={20} /> Run Candidate Matching & Ranking
            </>
          )}
        </button>
      </div>

      {/* Progress Bar Indicator */}
      {isLoading && (
        <AgentProgressBar
          stage={agentProgress.stage}
          percentage={agentProgress.percentage}
          nodeDetails={agentProgress.details}
        />
      )}

      {/* Results Shortlist Table */}
      {evaluationResult && !isLoading && (
        <>
          <CandidateTable
            shortlist={evaluationResult.shortlist}
            redirects={evaluationResult.redirects}
            duplicates={evaluationResult.duplicates}
            roles={evaluationResult.roles}
            isBlindMode={isBlindMode}
            langgraphTraces={evaluationResult.langgraph_step_traces}
            batchId={evaluationResult.batch_id}
            apiBaseUrl={API_BASE_URL}
            onReRunStep={handleReRunStep}
          />

          <ErrorQueue failedFiles={evaluationResult.could_not_process} />
        </>
      )}

      {/* Configuration Drawer Modal */}
      {showConfigDrawer && (
        <ConfigDrawer
          config={screeningConfig}
          onSave={handleSaveConfig}
          onClose={() => setShowConfigDrawer(false)}
          batchId={evaluationResult?.batch_id}
          apiBaseUrl={API_BASE_URL}
        />
      )}
    </div>
  );
}
