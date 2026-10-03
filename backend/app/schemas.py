from pydantic import BaseModel, Field, model_validator
from typing import List, Optional, Literal, Dict, Any, Union

# ----------------------------------------------------
# 1. Config Schemas (§2.1)
# ----------------------------------------------------

class DimensionWeights(BaseModel):
    skill: float = Field(0.60, ge=0, le=1)
    experience: float = Field(0.25, ge=0, le=1)
    education: float = Field(0.15, ge=0, le=1)

    @model_validator(mode="after")
    def must_sum_to_one(self):
        if abs(self.skill + self.experience + self.education - 1.0) > 0.001:
            raise ValueError("Dimension weights must sum to 1.0")
        return self

class EvidenceWeights(BaseModel):
    listed: float = Field(0.2, ge=0, le=1, description="Only named in a skills list")
    project: float = Field(0.4, ge=0, le=1, description="Used in a project")
    experience: float = Field(0.4, ge=0, le=1, description="Used in a job / internship")
    mode: Literal["strongest", "corroborated"] = "strongest"
    undated_recency: float = Field(0.8, ge=0, le=1, description="Recency factor when no dates exist")

    @model_validator(mode="after")
    def at_least_one_positive(self):
        if max(self.listed, self.project, self.experience) <= 0:
            raise ValueError("At least one evidence weight must be > 0")
        return self

class RecencyConfig(BaseModel):
    enabled: bool = True
    half_life_years: Dict[str, float] = Field(default_factory=lambda: {
        "fundamental": 10.0,
        "language": 6.0,
        "framework": 3.0,
        "cloud_devops": 3.0,
        "fast_moving": 1.5,
    })
    floor: float = Field(0.2, ge=0, le=1)

class SubstituteConfig(BaseModel):
    min_similarity: float = 0.75
    credit_factor: float = 0.70

class ShortlistConfig(BaseModel):
    top_k: int = 10
    min_score: float = 60.0
    redirect_min_score: float = 65.0

class IntegrityConfig(BaseModel):
    tiny_font_pt: float = 4.0
    min_contrast_ratio: float = 1.5
    jd_overlap_flag: float = 0.20
    jd_overlap_high: float = 0.40
    stuffing_listed_only_ratio: float = 0.80
    stuffing_min_skills: int = 15
    high_severity_policy: Literal["review", "exclude"] = "review"

class DedupConfig(BaseModel):
    near_dup_jaccard: float = 0.85
    project_plagiarism_jaccard: float = 0.60
    project_min_words: int = 25

class ScreeningConfig(BaseModel):
    dimensions: DimensionWeights = Field(default_factory=DimensionWeights)
    evidence: EvidenceWeights = Field(default_factory=EvidenceWeights)
    recency: RecencyConfig = Field(default_factory=RecencyConfig)
    substitutes: SubstituteConfig = Field(default_factory=SubstituteConfig)
    shortlist: ShortlistConfig = Field(default_factory=ShortlistConfig)
    integrity: IntegrityConfig = Field(default_factory=IntegrityConfig)
    dedup: DedupConfig = Field(default_factory=DedupConfig)

# Legacy alias
class WeightConfig(BaseModel):
    skill_weight: float = Field(default=0.60, ge=0.0, le=1.0)
    experience_weight: float = Field(default=0.25, ge=0.0, le=1.0)
    education_weight: float = Field(default=0.15, ge=0.0, le=1.0)

# ----------------------------------------------------
# 2. Gate & Job Description Schemas (§2.2)
# ----------------------------------------------------

class GateRule(BaseModel):
    id: str
    label: str
    field: Literal["cgpa_10", "active_backlogs", "total_backlogs",
                   "graduation_year", "degree", "branch_group", "pct_10th", "pct_12th"]
    op: Literal[">=", "<=", "==", "in", "not_in"]
    value: Union[float, int, str, List[str], List[int]]
    enabled: bool = True
    on_missing: Literal["fail", "pass", "review"] = "review"

class RoleSpec(BaseModel):
    jd_id: str
    jd_text: str
    is_primary: bool = False
    gates: List[GateRule] = Field(default_factory=list)

class SkillRequirement(BaseModel):
    name: str = Field(description="Canonical skill name, e.g. 'Python'")
    weight: float = Field(default=1.0, ge=0.1, le=2.0)
    is_mandatory: bool = True

class ParsedJobDescription(BaseModel):
    role_title: str = Field(default="Target Role")
    min_years_experience: float = Field(default=0.0)
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    required_education: Optional[str] = None
    certifications: List[str] = Field(default_factory=list)

# ----------------------------------------------------
# 3. Candidate & Evidence Schemas (§2.3)
# ----------------------------------------------------

class EvidenceContext(BaseModel):
    kind: Literal["listed", "project", "experience"]
    snippet: str = Field(default="", max_length=240)
    start: Optional[str] = None
    end: Optional[str] = None
    strength: float = Field(1.0, ge=0, le=1)

class SkillEvidence(BaseModel):
    skill: str
    category: str = "framework"
    contexts: List[EvidenceContext] = Field(default_factory=list)

class ParsedProject(BaseModel):
    title: str = ""
    description: str = ""
    technologies: List[str] = Field(default_factory=list)
    start: Optional[str] = None
    end: Optional[str] = None

class ParsedExperience(BaseModel):
    role: str = ""
    start: Optional[str] = None
    end: Optional[str] = None
    is_internship: bool = False
    summary: str = ""

class EligibilityFacts(BaseModel):
    cgpa_10: Optional[float] = None
    pct_10th: Optional[float] = None
    pct_12th: Optional[float] = None
    active_backlogs: Optional[int] = None
    total_backlogs: Optional[int] = None
    graduation_year: Optional[int] = None
    degree: Optional[str] = None
    branch_group: Optional[str] = None
    extraction_confidence: Dict[str, float] = Field(default_factory=dict)

class CandidateEducation(BaseModel):
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    institution_anonymized: bool = True

class ParsedCandidateProfile(BaseModel):
    candidate_id: str
    original_filename: str
    unique_fingerprint: str = ""
    total_years_experience: float = 0.0
    skills: List[str] = Field(default_factory=list)
    skill_evidences: List[SkillEvidence] = Field(default_factory=list)
    experiences: List[ParsedExperience] = Field(default_factory=list)
    projects: List[ParsedProject] = Field(default_factory=list)
    education: Optional[CandidateEducation] = None
    certifications: List[str] = Field(default_factory=list)
    work_history_summary: List[str] = Field(default_factory=list)
    extracted_name: Optional[str] = None
    extracted_email: Optional[str] = None
    extracted_phone: Optional[str] = None

class ProcessingError(BaseModel):
    filename: str
    error_code: str
    user_message: str
    action_suggested: str

# ----------------------------------------------------
# 4. Integrity, Gate & Duplicate Results (§2.4)
# ----------------------------------------------------

class IntegrityFinding(BaseModel):
    type: Literal["HIDDEN_TEXT", "INSTRUCTION_INJECTION", "INVISIBLE_UNICODE",
                  "JD_COPY_PASTE", "KEYWORD_STUFFING", "OFF_PAGE_TEXT"]
    severity: Literal["LOW", "MEDIUM", "HIGH"]
    detail: str
    location: Optional[str] = None
    evidence_snippet: Optional[str] = Field(None, max_length=160)

class IntegrityReport(BaseModel):
    candidate_id: str
    severity: Literal["NONE", "LOW", "MEDIUM", "HIGH"] = "NONE"
    findings: List[IntegrityFinding] = Field(default_factory=list)
    stripped_char_count: int = 0
    jd_overlap_ratio: float = 0.0

class DuplicateGroup(BaseModel):
    group_id: str
    kind: Literal["EXACT", "NEAR_DUPLICATE", "SAME_APPLICANT", "SHARED_PROJECT_TEXT"]
    similarity: float
    members: List[str]
    canonical: Optional[str] = None
    detail: Optional[str] = None

class GateResult(BaseModel):
    candidate_id: str
    jd_id: str
    passed: bool
    needs_review: bool = False
    failed_rules: List[str] = Field(default_factory=list)
    missing_facts: List[str] = Field(default_factory=list)

class GateImpact(BaseModel):
    rule_id: str
    label: str
    fails: int = 0
    fail_pct: float = 0.0
    unique_fails: int = 0
    missing_data: int = 0

class SkillMatchDetail(BaseModel):
    matching_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    substitute_skills: Dict[str, str] = Field(default_factory=dict)
    per_skill_credit: Dict[str, float] = Field(default_factory=dict)
    evidence_summary: Dict[str, List[str]] = Field(default_factory=dict)

class RoleFit(BaseModel):
    jd_id: str
    role_title: str
    score: float

class RoleRedirect(BaseModel):
    candidate_id: str
    primary_score: Optional[float] = None
    best_alternative: RoleFit
    other_fits: List[RoleFit] = Field(default_factory=list)
    message: str

class CandidateEvaluationResult(BaseModel):
    candidate_id: str
    original_filename: str
    unique_fingerprint: str = ""
    version: int = 1
    is_updated_resume: bool = False
    rank: int = 1
    match_score_percentage: float = 0.0
    skill_score: float = 0.0
    experience_score: float = 0.0
    education_score: float = 0.0
    skill_details: SkillMatchDetail
    llm_explanation_note: str = ""
    raw_parsed_profile: ParsedCandidateProfile
    integrity: IntegrityReport = Field(default_factory=lambda: IntegrityReport(candidate_id=""))
    lane: Literal["SHORTLISTED", "NOT_SELECTED", "NEEDS_REVIEW", "INELIGIBLE", "DUPLICATE"] = "NOT_SELECTED"

class BatchScreeningResponse(BaseModel):
    batch_id: str
    status: str = "COMPLETED"
    total_uploaded: int = 0
    processed_count: int = 0
    failed_count: int = 0
    parsed_jd: ParsedJobDescription
    roles: List[Dict[str, Any]] = Field(default_factory=list)
    shortlist: List[CandidateEvaluationResult] = Field(default_factory=list)
    redirects: List[RoleRedirect] = Field(default_factory=list)
    duplicates: List[DuplicateGroup] = Field(default_factory=list)
    could_not_process: List[ProcessingError] = Field(default_factory=list)
    weights_used: WeightConfig = Field(default_factory=WeightConfig)
    screening_config: ScreeningConfig = Field(default_factory=ScreeningConfig)
    funnel: Dict[str, int] = Field(default_factory=dict)
    throughput_metrics: Dict[str, Any] = Field(default_factory=dict)
    langgraph_step_traces: Dict[str, Any] = Field(default_factory=dict)

class FairnessTestResult(BaseModel):
    sample_size: int
    variants_per_candidate: int
    max_abs_score_delta: float
    rank_changes: int
    failures: List[Dict[str, Any]] = Field(default_factory=list)
    twin_test_passed: bool
    group_rates: Optional[Dict[str, float]] = None
    passed: bool
