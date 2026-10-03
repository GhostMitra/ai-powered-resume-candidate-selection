import math
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from app.schemas import (
    ParsedJobDescription,
    ParsedCandidateProfile,
    SkillMatchDetail,
    ScreeningConfig,
    WeightConfig,
    SkillEvidence,
    EvidenceContext
)
from app.services.taxonomy_service import TaxonomyService

class ScoringEngineService:

    @classmethod
    def compute_skill_recency_factor(
        cls,
        context_end: Optional[str],
        category: str,
        config: ScreeningConfig,
        run_year: float = 2026.75
    ) -> float:
        if not config.recency.enabled:
            return 1.0
        if not context_end or context_end.lower() == "undated":
            return config.evidence.undated_recency
        
        # Calculate age in years
        try:
            if context_end.lower() == "present":
                age_years = 0.0
            else:
                end_yr = float(context_end.split("-")[0]) if "-" in context_end else float(context_end)
                age_years = max(0.0, run_year - end_yr)
        except Exception:
            age_years = 1.0

        decay_lambda = TaxonomyService.get_recency_lambda(category, config.recency.half_life_years)
        factor = math.exp(-decay_lambda * age_years)
        return max(config.recency.floor, min(1.0, factor))

    @classmethod
    def calculate_skill_context_credit(
        cls,
        evidences: List[EvidenceContext],
        category: str,
        config: ScreeningConfig
    ) -> float:
        ev_cfg = config.evidence
        w_L = ev_cfg.listed
        w_P = ev_cfg.project
        w_X = ev_cfg.experience
        
        # Track presence & recency per context
        presence = {"listed": 0.0, "project": 0.0, "experience": 0.0}
        recency = {"listed": ev_cfg.undated_recency, "project": 1.0, "experience": 1.0}

        for ev in evidences:
            kind = ev.kind
            presence[kind] = 1.0
            r_factor = cls.compute_skill_recency_factor(ev.end, category, config)
            recency[kind] = max(recency[kind], r_factor)

        if ev_cfg.mode == "strongest":
            max_w = max(w_L, w_P, w_X)
            if max_w <= 0:
                return 0.0
            credits = [
                w_L * presence["listed"] * recency["listed"],
                w_P * presence["project"] * recency["project"],
                w_X * presence["experience"] * recency["experience"],
            ]
            return min(1.0, max(credits) / max_w)
        else:
            # Corroborated mode: normalized weights accumulate
            w_sum = w_L + w_P + w_X
            if w_sum <= 0:
                return 0.0
            hat_w_L = w_L / w_sum
            hat_w_P = w_P / w_sum
            hat_w_X = w_X / w_sum
            
            credit = (
                (hat_w_L * presence["listed"] * recency["listed"]) +
                (hat_w_P * presence["project"] * recency["project"]) +
                (hat_w_X * presence["experience"] * recency["experience"])
            )
            return min(1.0, max(0.0, credit))

    @classmethod
    def calculate_skill_match(
        cls,
        required_skills: List[str],
        parsed_candidate: ParsedCandidateProfile,
        config: ScreeningConfig
    ) -> Tuple[float, SkillMatchDetail]:
        
        if not required_skills:
            return 100.0, SkillMatchDetail()

        candidate_skills = parsed_candidate.skills
        cand_evidence_map: Dict[str, List[EvidenceContext]] = {}
        for ev in parsed_candidate.skill_evidences:
            cand_evidence_map.setdefault(ev.skill.lower(), []).extend(ev.contexts)

        # Build candidate skill credits map
        cand_credits: Dict[str, float] = {}
        cand_evidence_summary: Dict[str, List[str]] = {}

        for cand_s in candidate_skills:
            canon_s = TaxonomyService.get_canonical_skill(cand_s)
            cat = TaxonomyService.get_skill_category(canon_s)
            evs = cand_evidence_map.get(cand_s.lower(), [EvidenceContext(kind="listed")])
            cr = cls.calculate_skill_context_credit(evs, cat, config)
            cand_credits[canon_s.lower()] = cr
            cand_evidence_summary[canon_s] = list(set(e.kind for e in evs))

        matching_skills = []
        missing_skills = []
        substitute_skills = {}
        per_skill_credit = {}
        total_credit_points = 0.0

        for req in required_skills:
            req_canon = TaxonomyService.get_canonical_skill(req)
            req_key = req_canon.lower()

            # 1. Direct match check
            if req_key in cand_credits and cand_credits[req_key] > 0:
                cr = cand_credits[req_key]
                matching_skills.append(req_canon)
                per_skill_credit[req_canon] = round(cr, 2)
                total_credit_points += cr
            else:
                # 2. Substitute check
                best_sub_credit = 0.0
                best_sub_skill = None

                for cand_s, cr in cand_credits.items():
                    sim = TaxonomyService.get_transfer_similarity(req_canon, cand_s)
                    if sim >= config.substitutes.min_similarity:
                        sub_cr = config.substitutes.credit_factor * sim * cr
                        if sub_cr > best_sub_credit:
                            best_sub_credit = sub_cr
                            best_sub_skill = cand_s.title()

                if best_sub_credit > 0 and best_sub_skill:
                    matching_skills.append(f"{req_canon} (via {best_sub_skill})")
                    substitute_skills[req_canon] = best_sub_skill
                    per_skill_credit[req_canon] = round(best_sub_credit, 2)
                    total_credit_points += best_sub_credit
                else:
                    missing_skills.append(req_canon)
                    per_skill_credit[req_canon] = 0.0

        max_possible = float(len(required_skills))
        skill_score_pct = (total_credit_points / max_possible) * 100.0 if max_possible > 0 else 100.0
        skill_score_pct = min(100.0, max(0.0, skill_score_pct))

        return round(skill_score_pct, 1), SkillMatchDetail(
            matching_skills=matching_skills,
            missing_skills=missing_skills,
            substitute_skills=substitute_skills,
            per_skill_credit=per_skill_credit,
            evidence_summary=cand_evidence_summary
        )

    @staticmethod
    def calculate_experience_match(required_yoe: float, candidate_yoe: float) -> float:
        if required_yoe <= 0:
            return 100.0
        if candidate_yoe >= required_yoe:
            return 100.0
        if candidate_yoe <= 0:
            return 20.0
            
        # Log-linear power scaling formula: (cand / req) ^ 0.75 * 100
        score = math.pow((candidate_yoe / required_yoe), 0.75) * 100.0
        return round(min(100.0, max(10.0, score)), 1)

    @staticmethod
    def calculate_education_match(required_edu: Optional[str], candidate_degree: Optional[str]) -> float:
        if not required_edu:
            return 100.0
        if not candidate_degree:
            return 40.0
        
        norm_req = TaxonomyService.normalize_degree(required_edu)
        norm_cand = TaxonomyService.normalize_degree(candidate_degree)
        
        if norm_req == norm_cand and norm_req != "OTHER":
            return 100.0
        if norm_cand != "OTHER":
            return 70.0
        return 40.0

    @classmethod
    def evaluate_candidate(
        cls,
        parsed_jd: ParsedJobDescription,
        parsed_candidate: ParsedCandidateProfile,
        config: Optional[ScreeningConfig] = None
    ) -> Tuple[float, float, float, float, SkillMatchDetail]:
        
        cfg = config or ScreeningConfig()
        
        skill_score, skill_details = cls.calculate_skill_match(
            parsed_jd.required_skills,
            parsed_candidate,
            cfg
        )
        
        experience_score = cls.calculate_experience_match(
            parsed_jd.min_years_experience,
            parsed_candidate.total_years_experience
        )
        
        education_score = cls.calculate_education_match(
            parsed_jd.required_education,
            parsed_candidate.education.degree if parsed_candidate.education else None
        )
        
        w_skill = cfg.dimensions.skill
        w_exp = cfg.dimensions.experience
        w_edu = cfg.dimensions.education
        
        total_score = (w_skill * skill_score) + (w_exp * experience_score) + (w_edu * education_score)
        total_score = round(min(100.0, max(0.0, total_score)), 1)
        
        return total_score, skill_score, experience_score, education_score, skill_details
