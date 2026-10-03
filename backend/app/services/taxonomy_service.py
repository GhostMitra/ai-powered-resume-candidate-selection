import math
import re
from typing import Dict, List, Optional, Tuple

class TaxonomyService:
    # 1. Skill Categories and Half-Life values (in years)
    CATEGORY_HALF_LIVES: Dict[str, float] = {
        "fundamental": 10.0,   # SQL, DSA, OOP, Linux, Networking
        "language": 6.0,       # Python, Java, C++, TypeScript, Go, Rust
        "framework": 3.0,      # React, Vue, Angular, Django, FastAPI, Spring, PyTorch
        "cloud_devops": 3.0,   # AWS, GCP, Azure, Docker, Kubernetes, Terraform
        "fast_moving": 1.5,    # LLM, LangChain, LlamaIndex, RAG, GenAI
    }

    # Skill -> Category lookup
    SKILL_CATEGORIES: Dict[str, str] = {
        # Fundamentals
        "sql": "fundamental", "dsa": "fundamental", "data structures": "fundamental",
        "algorithms": "fundamental", "oop": "fundamental", "linux": "fundamental",
        "networking": "fundamental", "operating systems": "fundamental", "git": "fundamental",
        
        # Languages
        "python": "language", "java": "language", "c++": "language", "c": "language",
        "javascript": "language", "typescript": "language", "go": "language",
        "golang": "language", "rust": "language", "kotlin": "language", "swift": "language",
        "r": "language", "scala": "language",
        
        # Frameworks
        "react": "framework", "vue": "framework", "angular": "framework", "next.js": "framework",
        "express.js": "framework", "django": "framework", "flask": "framework", "fastapi": "framework",
        "spring": "framework", "spring boot": "framework", "pytorch": "framework",
        "tensorflow": "framework", "keras": "framework", "scikit-learn": "framework",
        
        # Cloud / DevOps
        "aws": "cloud_devops", "gcp": "cloud_devops", "azure": "cloud_devops",
        "docker": "cloud_devops", "kubernetes": "cloud_devops", "k8s": "cloud_devops",
        "terraform": "cloud_devops", "ansible": "cloud_devops", "jenkins": "cloud_devops",
        "ci/cd": "cloud_devops", "postgresql": "cloud_devops", "mysql": "cloud_devops",
        "mongodb": "cloud_devops", "redis": "cloud_devops",
        
        # Fast Moving / GenAI
        "llm": "fast_moving", "langchain": "fast_moving", "llamaindex": "fast_moving",
        "genai": "fast_moving", "generative ai": "fast_moving", "rag": "fast_moving",
        "prompt engineering": "fast_moving", "fine-tuning": "fast_moving", "openai": "fast_moving"
    }

    # 2. Aliases -> Canonical Skill Mapping
    ALIASES: Dict[str, str] = {
        "k8s": "Kubernetes",
        "postgres": "PostgreSQL",
        "postgresql": "PostgreSQL",
        "mysql": "MySQL",
        "mongo": "MongoDB",
        "mongodb": "MongoDB",
        "tf": "TensorFlow",
        "py": "Python",
        "js": "JavaScript",
        "ts": "TypeScript",
        "golang": "Go",
        "aws": "AWS",
        "gcp": "GCP",
        "azure": "Azure",
        "reactjs": "React",
        "react.js": "React",
        "vuejs": "Vue",
        "angularjs": "Angular",
        "nextjs": "Next.js",
        "fast api": "FastAPI",
        "express": "Express.js",
        "docker": "Docker",
        "pytorch": "PyTorch",
        "tensorflow": "TensorFlow",
        "scikit": "Scikit-Learn",
        "sklearn": "Scikit-Learn",
        "llms": "LLM",
        "generative ai": "GenAI"
    }

    # 3. Curated Transferability Table (Similarity Score in [0, 1])
    TRANSFER_TABLE: Dict[Tuple[str, str], float] = {
        ("AWS", "GCP"): 0.85,
        ("AWS", "Azure"): 0.85,
        ("GCP", "Azure"): 0.85,
        ("PyTorch", "TensorFlow"): 0.80,
        ("TensorFlow", "Keras"): 0.85,
        ("React", "Vue"): 0.80,
        ("React", "Angular"): 0.75,
        ("Vue", "Angular"): 0.75,
        ("PostgreSQL", "MySQL"): 0.90,
        ("PostgreSQL", "SQLite"): 0.80,
        ("FastAPI", "Flask"): 0.85,
        ("FastAPI", "Django"): 0.75,
        ("Docker", "Podman"): 0.85,
        ("MongoDB", "Cassandra"): 0.75,
        ("MongoDB", "DynamoDB"): 0.80,
        ("TypeScript", "JavaScript"): 0.90,
        ("Java", "Kotlin"): 0.85,
        ("C++", "C"): 0.85
    }

    # 4. Degree & Branch Group mappings
    DEGREE_MAPPING: Dict[str, str] = {
        "b.tech": "BTECH", "btech": "BTECH", "b.e.": "BTECH", "be": "BTECH",
        "bachelor of technology": "BTECH", "bachelor of engineering": "BTECH", "b.sc": "BSC",
        "bsc": "BSC", "m.tech": "MTECH", "mtech": "MTECH", "m.e.": "MTECH",
        "master of technology": "MTECH", "mca": "MCA", "m.c.a.": "MCA", "m.sc": "MSC"
    }

    BRANCH_MAPPING: Dict[str, str] = {
        "computer science": "CS_IT", "cs": "CS_IT", "cse": "CS_IT", "it": "CS_IT",
        "information technology": "CS_IT", "software engineering": "CS_IT",
        "electronics": "ECE_EE", "ece": "ECE_EE", "electrical": "ECE_EE", "ee": "ECE_EE",
        "mechanical": "MECH", "mech": "MECH", "civil": "CIVIL"
    }

    @classmethod
    def get_canonical_skill(cls, raw_skill: str) -> str:
        s_clean = raw_skill.strip().lower()
        if s_clean in cls.ALIASES:
            return cls.ALIASES[s_clean]
        # Title case default
        return raw_skill.strip().title()

    @classmethod
    def get_skill_category(cls, canonical_skill: str) -> str:
        s_clean = canonical_skill.strip().lower()
        return cls.SKILL_CATEGORIES.get(s_clean, "framework")

    @classmethod
    def get_recency_lambda(cls, category: str, custom_half_lives: Optional[Dict[str, float]] = None) -> float:
        half_lives = custom_half_lives or cls.CATEGORY_HALF_LIVES
        h = half_lives.get(category, 3.0)
        return math.log(2) / max(0.1, h)

    @classmethod
    def get_transfer_similarity(cls, req_skill: str, cand_skill: str) -> float:
        req_canon = cls.get_canonical_skill(req_skill)
        cand_canon = cls.get_canonical_skill(cand_skill)
        
        if req_canon.lower() == cand_canon.lower():
            return 1.0

        pair1 = (req_canon, cand_canon)
        pair2 = (cand_canon, req_canon)
        
        if pair1 in cls.TRANSFER_TABLE:
            return cls.TRANSFER_TABLE[pair1]
        if pair2 in cls.TRANSFER_TABLE:
            return cls.TRANSFER_TABLE[pair2]
            
        return 0.0

    @classmethod
    def normalize_degree(cls, raw_degree: str) -> str:
        if not raw_degree:
            return "OTHER"
        d_lower = raw_degree.lower()
        for key, val in cls.DEGREE_MAPPING.items():
            if key in d_lower:
                return val
        return "OTHER"

    @classmethod
    def normalize_branch(cls, raw_branch: str) -> str:
        if not raw_branch:
            return "OTHER"
        b_lower = raw_branch.lower()
        for key, val in cls.BRANCH_MAPPING.items():
            if key in b_lower:
                return val
        return "OTHER"
