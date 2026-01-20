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

from flask import Flask, jsonify
from .routes import bp
from .auth import auth_bp
from .db import init_db, check_db_connection
from .logging_config import configure_logging
import sys

def create_app():
    app = Flask(__name__)
    
    # Configure logging first (before any log statements)
    configure_logging(app)
    
    # Log AGPL compliance information on startup
    try:
        import swisseph as swe
        swe_version = swe.version if hasattr(swe, 'version') else "unknown"
        app.logger.info("=" * 60)
        app.logger.info("AGPL-Licensed Software Notice")
        app.logger.info("=" * 60)
        app.logger.info(f"Swiss Ephemeris version: {swe_version}")
        app.logger.info("Swiss Ephemeris is licensed under AGPL v3")
        app.logger.info("Copyright (C) 1997-2021 Astrodienst AG, Switzerland")
        app.logger.info("Source code: https://github.com/astrorigin/pyswisseph")
        app.logger.info("This application source: [YOUR_GITHUB_REPO_URL]")
        app.logger.info("=" * 60)
    except Exception as e:
        app.logger.warning(f"Could not log Swiss Ephemeris version: {e}")
    
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
        # Wrap in try-catch to prevent startup failures if database is unavailable
        try:
            init_db(app)
            app.logger.info("Database initialized successfully")
        except Exception as e:
            app.logger.error(f"Failed to initialize database: {str(e)}")
            app.logger.warning("Server will start without database - some features may be unavailable")
            # Don't fail startup - allow server to run even if database is unavailable
    else:
        app.logger.warning("DATABASE_URL not set - database features disabled")

    # CORS configuration with credentials support for cookie-based authentication
    # PRODUCTION: Restrict ALLOWED_ORIGINS to specific domains (e.g., "https://yourdomain.com")
    # Never use "*" in production - it allows any origin to make requests
    # Example: ALLOWED_ORIGINS=https://app.yourdomain.com,https://www.yourdomain.com
    # IMPORTANT: When using credentials, cannot use wildcard "*" - must specify explicit origins
    from flask_cors import CORS
    origins_str = os.environ.get("ALLOWED_ORIGINS", "*")
    origins = [origin.strip() for origin in origins_str.split(",")]
    
    # If wildcard is used, convert to explicit origins for development
    # In production, this should never happen (credentials require explicit origins)
    if "*" in origins and len(origins) == 1:
        # For development: use frontend URL from env or default
        frontend_url = os.environ.get("FRONTEND_BASE_URL", "http://localhost:3000")
        origins = [frontend_url]
        app.logger.warning(f"ALLOWED_ORIGINS=* detected - converted to explicit origin: {frontend_url}")
        app.logger.warning("For production, set ALLOWED_ORIGINS to explicit domain(s)")
    
    # Configure CORS with credentials support for HTTP-only cookies
    CORS(app, resources={r"/*": {
        "origins": origins,
        "supports_credentials": True,
        "allow_headers": ["Content-Type", "Authorization"],
        "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    }})

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
        app.logger.debug("Health check requested")
        
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
                app.logger.error(f"Health check failed: {db_message}")
                return health, 503
        
        app.logger.debug("Health check passed")
        return health, 200
    
    @app.get("/license")
    def license_info():
        """
        AGPL compliance endpoint - provides license and source code information.
        
        Required by AGPL v3 for network-accessible software.
        Users must have access to source code.
        
        Returns:
            200: License information and source code links
        """
        try:
            import swisseph as swe
            swe_version = swe.version if hasattr(swe, 'version') else "unknown"
        except Exception:
            swe_version = "unknown"
        
        return jsonify({
            "license": "AGPL-3.0",
            "components": [
                {
                    "name": "Swiss Ephemeris",
                    "version": swe_version,
                    "license": "AGPL-3.0 or Commercial",
                    "copyright": "Copyright (C) 1997-2021 Astrodienst AG, Switzerland",
                    "source": "https://github.com/astrorigin/pyswisseph",
                    "website": "https://www.astro.com/swisseph/"
                },
                {
                    "name": "Jyotishika API",
                    "license": "AGPL-3.0",
                    "source": "[YOUR_GITHUB_REPO_URL]",
                    "note": "Complete source code available under AGPL v3"
                }
            ],
            "agpl_notice": (
                "This software uses Swiss Ephemeris, licensed under AGPL v3. "
                "Under AGPL, users who interact with this software over a network "
                "are entitled to receive the complete source code. "
                "Source code is available at the URLs listed above."
            )
        }), 200
    
    return app
