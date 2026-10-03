import re

class PIIAnonymizerService:
    EMAIL_REGEX = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    PHONE_REGEX = r'(?:\+?91[\-\s]?)?[6-9]\d{9}|\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
    YEAR_REGEX = r'\b(19|20)\d{2}\b'
    URL_REGEX = r'https?://\S+|www\.\S+|(?:linkedin|github)\.com/\S+'
    
    INSTITUTION_KEYWORDS = [
        "University", "College", "Institute of Technology", "Polytechnic", "School of Business", "Academy", "IIT", "NIT"
    ]

    @classmethod
    def anonymize_text(cls, raw_text: str, candidate_idx: int = 0) -> str:
        if not raw_text:
            return ""
            
        text = re.sub(cls.EMAIL_REGEX, "[EMAIL_MASKED]", raw_text)
        text = re.sub(cls.PHONE_REGEX, "[PHONE_MASKED]", text)
        text = re.sub(cls.URL_REGEX, "[LINK_MASKED]", text)
        
        # Anonymize Institution names
        for kw in cls.INSTITUTION_KEYWORDS:
            text = re.sub(rf'\b[A-Z][a-zA-Z\s]+\s{kw}\b', "[INSTITUTION_MASKED]", text)
            
        # Scrub top 2 lines (Candidate Header usually containing Name, Address)
        lines = text.split('\n')
        anonymized_candidate_id = f"Candidate #{candidate_idx + 101}"
        
        if len(lines) > 0:
            lines[0] = f"APPLICANT ID: {anonymized_candidate_id}"
        if len(lines) > 1 and ("Email:" in lines[1] or "Phone:" in lines[1] or "Address" in lines[1] or "@" in lines[1]):
            lines[1] = "[CONTACT_INFO_MASKED]"
            
        return '\n'.join(lines)
