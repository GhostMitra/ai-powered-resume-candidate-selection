import re
import fitz  # PyMuPDF
import docx
import io
from collections import Counter
from typing import Tuple, List, Dict, Any, Optional
from app.schemas import IntegrityFinding, IntegrityReport, IntegrityConfig

INJECTION_PATTERNS = [
    r"ignore (all |any )?(the )?(previous|prior|above|earlier) (instructions|prompts?|rules)",
    r"disregard (the )?(previous|prior|above|system)",
    r"(rank|score|rate|shortlist|recommend)\s+(this|me|the)\s*(candidate|resume|applicant)?.{0,20}(#?1\b|first|top|highest|100|perfect)",
    r"\b(you are|act as|pretend to be)\b.{0,40}\b(assistant|recruiter|model|hr)\b",
    r"(system prompt|developer message|assistant:|###\s*instruction)",
    r"(give|assign)\s+(this|me).{0,30}(maximum|full|perfect|100)",
    r"always\s+recommend\s+hire",
    r"jailbreak",
]

INVISIBLE_MAP = dict.fromkeys(map(ord, "\u200b\u200c\u200d\u2060\ufeff\u180e"), None)

def _lum(rgb):  # rgb: (r, g, b) 0-255 -> WCAG relative luminance
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (x / 255 for x in rgb)
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)

def _contrast(a, b):
    hi, lo = max(_lum(a), _lum(b)), min(_lum(a), _lum(b))
    return (hi + 0.05) / (lo + 0.05)

def _bg_rgb(page, bbox):
    try:
        clip = fitz.Rect(bbox) + (-4, -4, 4, 4)
        pix = page.get_pixmap(clip=clip & page.rect, dpi=72)
        if pix and pix.n > 0:
            px = zip(*[iter(pix.samples)] * pix.n)
            return Counter(px).most_common(1)[0][0][:3]
    except Exception:
        pass
    return (255, 255, 255)

def shingles(text: str, n: int = 5) -> set:
    t = re.findall(r"\w+", text.lower())
    if len(t) < n:
        return set()
    return {" ".join(t[i:i + n]) for i in range(len(t) - n + 1)}

def jd_containment(jd_text: str, resume_text: str) -> float:
    if not jd_text or not resume_text:
        return 0.0
    jd = shingles(jd_text)
    if not jd:
        return 0.0
    res = shingles(resume_text)
    return len(jd & res) / max(1, len(jd))

class IntegrityShieldService:
    @classmethod
    def scan_and_sanitize(
        cls,
        filename: str,
        file_bytes: bytes,
        raw_text: str,
        candidate_id: str,
        jd_text: Optional[str] = None,
        config: Optional[IntegrityConfig] = None
    ) -> Tuple[str, IntegrityReport, List[Dict[str, Any]]]:
        
        cfg = config or IntegrityConfig()
        findings: List[IntegrityFinding] = []
        stripped_spans: List[Dict[str, Any]] = []
        visible_text_parts: List[str] = []
        ext = filename.split('.')[-1].lower() if '.' in filename else ''

        # 1. PDF Deep Scan (font size, contrast, off-page text)
        if ext == 'pdf' and file_bytes:
            try:
                doc = fitz.open(stream=file_bytes, filetype="pdf")
                for pno, page in enumerate(doc, start=1):
                    page_dict = page.get_text("dict")
                    for block in page_dict.get("blocks", []):
                        for line in block.get("lines", []):
                            for sp in line.get("spans", []):
                                txt = sp.get("text", "").strip()
                                if not txt:
                                    continue
                                color_int = sp.get("color", 0)
                                fg = ((color_int >> 16) & 255, (color_int >> 8) & 255, color_int & 255)
                                font_size = sp.get("size", 10)
                                bbox = sp.get("bbox", [0, 0, 0, 0])
                                
                                reasons = []
                                if font_size < cfg.tiny_font_pt:
                                    reasons.append("TINY_FONT")
                                bg = _bg_rgb(page, bbox)
                                if _contrast(fg, bg) < cfg.min_contrast_ratio:
                                    reasons.append("LOW_CONTRAST")
                                if not fitz.Rect(bbox).intersects(page.rect):
                                    reasons.append("OFF_PAGE")

                                if reasons:
                                    stripped_spans.append({
                                        "page": pno,
                                        "reasons": reasons,
                                        "text": txt,
                                        "location": f"Page {pno}"
                                    })
                                    findings.append(IntegrityFinding(
                                        type="HIDDEN_TEXT",
                                        severity="HIGH" if "LOW_CONTRAST" in reasons or "TINY_FONT" in reasons else "MEDIUM",
                                        detail=f"Hidden text ({', '.join(reasons)}) on page {pno}: '{txt[:50]}...'",
                                        location=f"Page {pno}",
                                        evidence_snippet=txt[:160]
                                    ))
                                else:
                                    visible_text_parts.append(txt)
            except Exception:
                visible_text_parts = [raw_text]
        elif ext == 'docx' and file_bytes:
            # DOCX XML scan
            try:
                doc = docx.Document(io.BytesIO(file_bytes))
                for p in doc.paragraphs:
                    for run in p.runs:
                        txt = run.text.strip()
                        if not txt:
                            continue
                        is_hidden = False
                        if run.font.hidden or (run.font.size and run.font.size.pt < cfg.tiny_font_pt):
                            is_hidden = True
                        if is_hidden:
                            stripped_spans.append({"page": 1, "reasons": ["DOCX_HIDDEN_RUN"], "text": txt})
                            findings.append(IntegrityFinding(
                                type="HIDDEN_TEXT",
                                severity="HIGH",
                                detail=f"Hidden DOCX text: '{txt[:50]}...'",
                                evidence_snippet=txt[:160]
                            ))
                        else:
                            visible_text_parts.append(txt)
            except Exception:
                visible_text_parts = [raw_text]
        else:
            visible_text_parts = [raw_text]

        working_text = " ".join(visible_text_parts) if visible_text_parts else raw_text

        # 2. Check for Invisible Unicode characters
        unicode_stripped = working_text.translate(INVISIBLE_MAP)
        invisible_chars_count = len(working_text) - len(unicode_stripped)
        if invisible_chars_count > 0:
            findings.append(IntegrityFinding(
                type="INVISIBLE_UNICODE",
                severity="LOW",
                detail=f"Stripped {invisible_chars_count} zero-width invisible Unicode characters.",
                evidence_snippet=None
            ))
            working_text = unicode_stripped

        # 3. Check for Prompt Instruction Injection patterns
        norm_text = working_text.lower()
        injection_hits = []
        for p in INJECTION_PATTERNS:
            for m in re.finditer(p, norm_text, re.IGNORECASE):
                hit_str = m.group(0)
                injection_hits.append(hit_str)
                working_text = re.sub(re.escape(hit_str), "[PROMPT_INJECTION_STRIPPED]", working_text, flags=re.IGNORECASE)

        if injection_hits:
            findings.append(IntegrityFinding(
                type="INSTRUCTION_INJECTION",
                severity="HIGH",
                detail=f"Detected adversarial prompt injection command: '{injection_hits[0]}'",
                evidence_snippet=injection_hits[0][:160]
            ))

        # 4. Check for JD Copy-Paste Shingles Overlap
        jd_overlap = 0.0
        if jd_text:
            jd_overlap = jd_containment(jd_text, working_text)
            if jd_overlap >= cfg.jd_overlap_high:
                findings.append(IntegrityFinding(
                    type="JD_COPY_PASTE",
                    severity="HIGH",
                    detail=f"High verbatim JD overlap ({jd_overlap*100:.1f}%) detected in candidate resume text.",
                    evidence_snippet=None
                ))
            elif jd_overlap >= cfg.jd_overlap_flag:
                findings.append(IntegrityFinding(
                    type="JD_COPY_PASTE",
                    severity="MEDIUM",
                    detail=f"Moderate JD overlap ({jd_overlap*100:.1f}%) detected.",
                    evidence_snippet=None
                ))

        # Overall severity roll-up
        overall_severity = "NONE"
        if any(f.severity == "HIGH" for f in findings):
            overall_severity = "HIGH"
        elif any(f.severity == "MEDIUM" for f in findings):
            overall_severity = "MEDIUM"
        elif findings:
            overall_severity = "LOW"

        stripped_char_count = sum(len(s.get("text", "")) for s in stripped_spans) + invisible_chars_count

        report = IntegrityReport(
            candidate_id=candidate_id,
            severity=overall_severity,
            findings=findings,
            stripped_char_count=stripped_char_count,
            jd_overlap_ratio=round(jd_overlap, 3)
        )

        return working_text, report, stripped_spans
