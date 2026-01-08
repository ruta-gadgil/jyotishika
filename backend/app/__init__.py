import os
from pathlib import Path
# Load environment variables BEFORE importing modules that depend on them
from dotenv import load_dotenv

# Find the project root (parent of backend directory)
backend_dir = Path(__file__).parent.parent
project_root = backend_dir.parent

# Try local.env first (for local development), then .env
# Look in project root directory
load_dotenv(project_root / "local.env")  # Try local.env first
load_dotenv(project_root / ".env")  # Then try .env (won't override if already set)

from flask import Flask
from .routes import bp
from .auth import auth_bp
from .db import init_db, check_db_connection

def create_app():
    app = Flask(__name__)
    
    # Set secret key for session management
    # PRODUCTION: SECRET_KEY MUST be set via environment variable
    # Use a strong, random secret (e.g., openssl rand -hex 32)
    # Never commit SECRET_KEY to version control
    secret_key = os.environ.get("SECRET_KEY")
    if secret_key:
        app.config["SECRET_KEY"] = secret_key
    else:
        # Generate a random secret key for development if not set
        # PRODUCTION: This fallback should NOT be used in production
        # Fail fast if SECRET_KEY is missing in production
        app.config["SECRET_KEY"] = os.urandom(32).hex()
    
    ephe = os.environ.get("EPHE_PATH")
    if not ephe or not os.path.isdir(ephe):
        raise RuntimeError("EPHE_PATH not set or not a directory")
    app.config["EPHE_PATH"] = ephe

    # Ayanamsha configuration
    ayanamsha = os.environ.get("AYANAMSHA", "VEDANJANAM")
    allowed_ayanamsha = {"LAHIRI", "RAMAN", "KRISHNAMURTI", "VEDANJANAM"}
    if ayanamsha not in allowed_ayanamsha:
        raise RuntimeError(f"Invalid AYANAMSHA value: {ayanamsha}. Must be one of {allowed_ayanamsha}")
    app.config["AYANAMSHA"] = ayanamsha

    # House system configuration (server-wide default; can be overridden per request)
    house_system = os.environ.get("HOUSE_SYSTEM", "WHOLE_SIGN")
    allowed_house_systems = {"WHOLE_SIGN", "EQUAL", "PLACIDUS"}
    if house_system not in allowed_house_systems:
        raise RuntimeError(f"Invalid HOUSE_SYSTEM value: {house_system}. Must be one of {allowed_house_systems}")
    app.config["HOUSE_SYSTEM"] = house_system

    # Database configuration
    # PRODUCTION: DATABASE_URL must be set via environment variable
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        app.config["SQLALCHEMY_DATABASE_URI"] = database_url
        # Initialize database with connection pooling
        init_db(app)
        app.logger.info("Database initialized successfully")
    else:
        app.logger.warning("DATABASE_URL not set - database features disabled")

    # CORS (simple)
    # PRODUCTION: Restrict ALLOWED_ORIGINS to specific domains (e.g., "https://yourdomain.com")
    # Never use "*" in production - it allows any origin to make requests
    # Example: ALLOWED_ORIGINS=https://app.yourdomain.com,https://www.yourdomain.com
    from flask_cors import CORS
    origins = os.environ.get("ALLOWED_ORIGINS", "*").split(",")
    CORS(app, resources={r"/*": {"origins": origins}})

    app.register_blueprint(bp)
    app.register_blueprint(auth_bp)

    @app.get("/healthz")
    def healthz():
        """
        Health check endpoint.
        
        Checks:
        - Basic app health (always returns ok: true)
        - Database connection (if DATABASE_URL configured)
        
        Returns:
            200: Service healthy
            503: Service unhealthy (database connection failed)
        """
        health = {"ok": True}
        
        # Check database connection if configured
        if app.config.get("SQLALCHEMY_DATABASE_URI"):
            db_healthy, db_message = check_db_connection()
            health["database"] = {
                "healthy": db_healthy,
                "message": db_message
            }
            
            # Return 503 if database is unhealthy
            if not db_healthy:
                health["ok"] = False
                return health, 503
        
        return health, 200
    
    return app
