import os
from pathlib import Path

class Config:
    """Application configuration"""
    EPHE_PATH = os.environ.get("EPHE_PATH")
    FLASK_ENV = os.environ.get("FLASK_ENV", "development")
    PORT = int(os.environ.get("PORT", 8080))
    ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "*").split(",")
    DEBUG = os.environ.get("DEBUG", "False").lower() == "true"
    TESTING = os.environ.get("TESTING", "False").lower() == "true"
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        if not cls.EPHE_PATH:
            raise ValueError("EPHE_PATH environment variable is required")
        
        if not Path(cls.EPHE_PATH).is_dir():
            raise ValueError(f"EPHE_PATH {cls.EPHE_PATH} is not a valid directory")
        
        return True
