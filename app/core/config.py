import os
from typing import Optional

class Settings:
    # API Configuration
    API_KEY: str = os.getenv("API_KEY", "honeypot-secret-key-2025-guvi-hackathon")
    
    # GUVI Callback Configuration
    GUVI_CALLBACK_URL: str = "https://hackathon.guvi.in/api/updateHoneyPotFinalResult"
    
    # Agent Configuration
    MAX_TURNS: int = int(os.getenv("MAX_TURNS", "10"))
    SCAM_CONFIDENCE_THRESHOLD: float = 0.75
    
    # LLM Configuration
    LLM_MODEL: str = os.getenv("LLM_MODEL", "llama3")
    LLM_TIMEOUT: int = 40
    
    # Session Configuration
    SESSION_TIMEOUT_MINUTES: int = 30
    
    # Scam Detection
    HEURISTIC_THRESHOLD: int = 6
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()