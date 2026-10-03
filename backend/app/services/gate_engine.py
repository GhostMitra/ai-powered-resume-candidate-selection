import re
from typing import List, Dict, Any, Tuple, Optional
from app.schemas import EligibilityFacts, GateRule, GateResult, GateImpact
from app.services.taxonomy_service import TaxonomyService

CGPA_REGEX = re.compile(r"(?i)\b(?:cgpa|gpa)\s*[:\-–]?\s*(\d{1,2}(?:\.\d{1,2})?)\s*(?:/\s*(10|4|5))?")
PCT_REGEX = re.compile(r"(?i)(\d{2}(?:\.\d{1,2})?)\s*%")
BACKLOG_NONE = re.compile(r"(?i)\bno\s+(?:active\s+)?(?:backlogs?|arrears?)\b")
BACKLOG_N = re.compile(r"(?i)\b(\d+)\s+(?:active\s+)?(?:backlogs?|arrears?)\b")
GRAD_YEAR = re.compile(r"(?i)\b(?:passing|graduat(?:ing|ed|ion))\s*(?:in|year)?\s*[:\-–]?\s*(20\d{2})\b")

class FactExtractorService:
    @classmethod
    def extract_facts(cls, raw_text: str) -> EligibilityFacts:
        facts = EligibilityFacts()
        
        # 1. CGPA Extraction & Normalization
        cgpa_match = CGPA_REGEX.search(raw_text)
        if cgpa_match:
            val = float(cgpa_match.group(1))
            scale = cgpa_match.group(2)
            if scale == "4":
                val = val * 2.5
            elif scale == "5":
                val = val * 2.0
            facts.cgpa_10 = round(min(10.0, max(0.0, val)), 2)

        # 2. Percentage Extraction (10th / 12th)
        pct_matches = PCT_REGEX.findall(raw_text)
        if pct_matches:
            pcts = [float(p) for p in pct_matches if 40.0 <= float(p) <= 100.0]
            if len(pcts) >= 1:
                facts.pct_10th = pcts[0]
            if len(pcts) >= 2:
                facts.pct_12th = pcts[1]
            if not facts.cgpa_10 and pcts:
                # CBSE conversion rule: % / 9.5
                facts.cgpa_10 = round(min(10.0, max(0.0, pcts[0] / 9.5)), 2)

        # 3. Backlogs
        if BACKLOG_NONE.search(raw_text):
            facts.active_backlogs = 0
            facts.total_backlogs = 0
        else:
            backlog_match = BACKLOG_N.search(raw_text)
            if backlog_match:
                facts.active_backlogs = int(backlog_match.group(1))
                facts.total_backlogs = int(backlog_match.group(1))
            else:
                facts.active_backlogs = 0

        # 4. Graduation Year
        grad_match = GRAD_YEAR.search(raw_text)
        if grad_match:
            facts.graduation_year = int(grad_match.group(1))
        else:
            # Fallback search for any 202x year in education section
            years = [int(y) for y in re.findall(r"\b202[0-9]\b", raw_text)]
            if years:
                facts.graduation_year = max(years)

        # 5. Degree & Branch Group
        facts.degree = TaxonomyService.normalize_degree(raw_text)
        facts.branch_group = TaxonomyService.normalize_branch(raw_text)

        return facts

class GateEvaluatorService:
    @classmethod
    def evaluate_rule(cls, rule: GateRule, facts: EligibilityFacts) -> Tuple[bool, bool, bool]:
        """Returns (passed, missing, needs_review)."""
        field_val = getattr(facts, rule.field, None)
        
        if field_val is None:
            # Fact missing
            if rule.on_missing == "pass":
                return True, True, False
            elif rule.on_missing == "fail":
                return False, True, False
            else:  # "review"
                return True, True, True

        op = rule.op
        req_val = rule.value
        
        passed = False
        try:
            if op == ">=":
                passed = float(field_val) >= float(req_val)
            elif op == "<=":
                passed = float(field_val) <= float(req_val)
            elif op == "==":
                passed = str(field_val).lower() == str(req_val).lower()
            elif op == "in":
                if isinstance(req_val, list):
                    passed = any(str(field_val).lower() == str(v).lower() for v in req_val)
                else:
                    passed = str(field_val).lower() in str(req_val).lower()
            elif op == "not_in":
                if isinstance(req_val, list):
                    passed = not any(str(field_val).lower() == str(v).lower() for v in req_val)
                else:
                    passed = str(field_val).lower() not in str(req_val).lower()
        except Exception:
            passed = False

        return passed, False, False

    @classmethod
    def evaluate_candidate_gates(
        cls,
        candidate_id: str,
        jd_id: str,
        gates: List[GateRule],
        facts: EligibilityFacts
    ) -> GateResult:
        
        failed_rules = []
        missing_facts = []
        needs_review = False
        overall_passed = True

        for rule in gates:
            if not rule.enabled:
                continue
            passed, missing, review = cls.evaluate_rule(rule, facts)
            if missing:
                missing_facts.append(rule.label)
            if review:
                needs_review = True
            if not passed:
                overall_passed = False
                failed_rules.append(rule.label)

        return GateResult(
            candidate_id=candidate_id,
            jd_id=jd_id,
            passed=overall_passed,
            needs_review=needs_review,
            failed_rules=failed_rules,
            missing_facts=missing_facts
        )

    @classmethod
    def compute_gate_impact(
        cls,
        gates: List[GateRule],
        all_candidate_facts: List[Dict[str, Any]]
    ) -> List[GateImpact]:
        
        total_candidates = len(all_candidate_facts)
        if total_candidates == 0:
            return []

        impacts: List[GateImpact] = []
        
        for rule in gates:
            if not rule.enabled:
                continue
            fails_count = 0
            unique_fails_count = 0
            missing_count = 0
            
            for cand in all_candidate_facts:
                facts: EligibilityFacts = cand["facts"]
                passed, missing, _ = cls.evaluate_rule(rule, facts)
                if missing:
                    missing_count += 1
                if not passed:
                    fails_count += 1
                    # Check if failed ONLY this rule
                    other_failed = False
                    for r_other in gates:
                        if r_other.id != rule.id and r_other.enabled:
                            p_other, _, _ = cls.evaluate_rule(r_other, facts)
                            if not p_other:
                                other_failed = True
                                break
                    if not other_failed:
                        unique_fails_count += 1

            impacts.append(GateImpact(
                rule_id=rule.id,
                label=rule.label,
                fails=fails_count,
                fail_pct=round((fails_count / total_candidates) * 100.0, 1),
                unique_fails=unique_fails_count,
                missing_data=missing_count
            ))

        return impacts
