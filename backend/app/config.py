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
    
    # Database configuration
    # PRODUCTION: Set DATABASE_URL via environment variable
    # Format: postgresql://user:password@host:port/database
    # Example: postgresql://user:pass@db.xxxxx.supabase.co:5432/postgres
    DATABASE_URL = os.environ.get("DATABASE_URL")
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        if not cls.EPHE_PATH:
            raise ValueError("EPHE_PATH environment variable is required")
        
        if not Path(cls.EPHE_PATH).is_dir():
            raise ValueError(f"EPHE_PATH {cls.EPHE_PATH} is not a valid directory")
        
        if not cls.DATABASE_URL:
            raise ValueError("DATABASE_URL environment variable is required")
        
        if not cls.DATABASE_URL.startswith("postgresql://"):
            raise ValueError("DATABASE_URL must be a PostgreSQL connection string (postgresql://...)")
        
        return True
