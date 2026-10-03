import os

class Settings:
    PROJECT_NAME: str = "AI-Powered Resume Screening & Candidate-Job Matching System"
    VERSION: str = "1.0.0"
    
    # LM Studio Configuration
    LM_STUDIO_BASE_URL: str = os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
    LM_STUDIO_MODEL: str = os.getenv("LM_STUDIO_MODEL", "nvidia/nemotron-3-nano-4b")
    
    # Database Settings
    POSTGRES_URI: str = os.getenv("POSTGRES_URI", "sqlite:///./app_screening.db")
    MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DB_NAME: str = os.getenv("MONGO_DB_NAME", "resume_screening")

settings = Settings()
