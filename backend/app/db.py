"""
Database Utilities

This module provides database connection management and utility functions.

SECURITY NOTES:
- Connection pooling configured with reasonable limits
- Graceful error handling for connection failures
- No credentials in code (DATABASE_URL from environment)
"""

from flask import current_app
from sqlalchemy.exc import SQLAlchemyError
from .models import db


def init_db(app):
    """
    Initialize database connection with the Flask app.
    
    Configures SQLAlchemy with connection pooling and error handling.
    
    Args:
        app: Flask application instance
        
    SECURITY NOTES:
    - Connection pool limits prevent resource exhaustion
    - Pool pre-ping validates connections before use
    - Graceful handling of database connection failures
    """
    # SQLAlchemy configuration
    # PRODUCTION: Tune these values based on your traffic and database plan
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False  # Disable event system (saves memory)
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_size": 10,           # Maximum number of permanent connections
        "max_overflow": 20,        # Maximum number of temporary connections
        "pool_timeout": 30,        # Seconds to wait before timing out connection request
        "pool_recycle": 3600,      # Recycle connections after 1 hour (prevents stale connections)
        "pool_pre_ping": True,     # Validate connections before using them
    }
    
    # Initialize SQLAlchemy with app
    db.init_app(app)
    
    # Log database configuration (without exposing credentials)
    database_url = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    # Extract host for logging (don't log password)
    if "@" in database_url:
        host_part = database_url.split("@")[-1].split("/")[0]
        app.logger.info(f"Database configured: {host_part}")
    else:
        app.logger.warning("DATABASE_URL not configured or in unexpected format")


def check_db_connection():
    """
    Check if database connection is healthy.
    
    Returns:
        tuple: (success: bool, message: str)
        
    Used by health check endpoint to verify database connectivity.
    """
    try:
        # Execute a simple query to test connection
        db.session.execute(db.text("SELECT 1"))
        return True, "Database connection healthy"
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database health check failed: {str(e)}")
        return False, f"Database connection failed: {str(e)}"
    except Exception as e:
        current_app.logger.error(f"Unexpected error in database health check: {str(e)}")
        return False, f"Unexpected database error: {str(e)}"


def get_or_create_user(google_sub, email, name):
    """
    Get existing user by google_sub or create new user.
    
    Args:
        google_sub: Google user ID from OAuth sub claim
        email: User's email from Google OAuth
        name: User's display name from Google profile
        
    Returns:
        User: User model instance
        
    SECURITY NOTES:
    - Uses google_sub as primary identifier (reliable even if email changes)
    - Updates last_login_at on every call
    - Wrapped in transaction for atomicity
    """
    from .models import User
    from datetime import datetime
    
    try:
        # Try to find existing user by google_sub
        user = User.query.filter_by(google_sub=google_sub).first()
        
        if user:
            # Update existing user
            user.email = email  # Update in case email changed
            user.name = name    # Update in case name changed
            user.last_login_at = datetime.utcnow()
            current_app.logger.info(f"Existing user logged in: {email}")
        else:
            # Create new user
            user = User(
                google_sub=google_sub,
                email=email,
                name=name,
                last_login_at=datetime.utcnow()
            )
            db.session.add(user)
            current_app.logger.info(f"New user created: {email}")
        
        # Commit transaction
        db.session.commit()
        return user
        
    except SQLAlchemyError as e:
        # Rollback on error
        db.session.rollback()
        current_app.logger.error(f"Database error in get_or_create_user: {str(e)}")
        raise
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Unexpected error in get_or_create_user: {str(e)}")
        raise


def is_email_approved(email):
    """
    Check if email is in approved_users table and is_active=True.
    
    Args:
        email: Email address to check
        
    Returns:
        bool: True if email is approved and active, False otherwise
        
    SECURITY NOTES:
    - Case-sensitive email matching (matches Google OAuth exactly)
    - Must check is_active flag (not just presence in table)
    """
    from .models import ApprovedUser
    
    try:
        # Log the email being checked (for debugging)
        current_app.logger.info(f"Checking authorization for email: {email}")
        
        # Ensure we have a database session
        if not hasattr(current_app, 'extensions') or 'sqlalchemy' not in current_app.extensions:
            current_app.logger.error("Database not initialized - SQLAlchemy extension not found")
            return False
        
        # Query the database
        approved_user = ApprovedUser.query.filter_by(email=email).first()
        
        if not approved_user:
            current_app.logger.warning(f"Authorization denied: email not in allowlist: {email}")
            # Debug: List all approved emails (for troubleshooting)
            try:
                all_approved = ApprovedUser.query.all()
                approved_emails = [au.email for au in all_approved]
                current_app.logger.debug(f"Approved emails in database: {approved_emails}")
            except Exception as debug_e:
                current_app.logger.debug(f"Could not list approved emails: {str(debug_e)}")
            return False
        
        current_app.logger.info(f"Found approved_user: email={approved_user.email}, is_active={approved_user.is_active}")
        
        if not approved_user.is_active:
            current_app.logger.warning(f"Authorization denied: email in allowlist but not active: {email}")
            return False
        
        current_app.logger.info(f"Authorization approved for email: {email}")
        return True
        
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error in is_email_approved: {str(e)}", exc_info=True)
        # Fail closed: deny access on database error
        return False
    except Exception as e:
        current_app.logger.error(f"Unexpected error in is_email_approved: {str(e)}", exc_info=True)
        # Fail closed: deny access on unexpected error
        return False


def is_user_authorized(google_sub, email):
    """
    Check if user is fully authorized (dual-layer check).
    
    Validates:
    1. User exists in users table
    2. users.is_active = True
    3. Email exists in approved_users table
    4. approved_users.is_active = True
    
    Args:
        google_sub: Google user ID from session
        email: User's email from session
        
    Returns:
        tuple: (authorized: bool, user: User or None)
        
    SECURITY NOTES:
    - Checks BOTH tables' is_active flags (defense in depth)
    - Returns generic False for all failure modes (don't leak which check failed)
    - Used on every protected request
    """
    from .models import User, ApprovedUser
    
    try:
        # Check 1: User exists and is active
        user = User.query.filter_by(google_sub=google_sub).first()
        
        if not user:
            current_app.logger.warning(f"Authorization denied: user not found: google_sub={google_sub}")
            return False, None
        
        if not user.is_active:
            current_app.logger.warning(f"Authorization denied: user not active: {email}")
            return False, None
        
        # Check 2: Email is approved and active
        approved_user = ApprovedUser.query.filter_by(email=email).first()
        
        if not approved_user:
            current_app.logger.warning(f"Authorization denied: email not in allowlist: {email}")
            return False, None
        
        if not approved_user.is_active:
            current_app.logger.warning(f"Authorization denied: email in allowlist but not active: {email}")
            return False, None
        
        # Both checks passed
        return True, user
        
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error in is_user_authorized: {str(e)}")
        # Fail closed: deny access on database error
        return False, None
    except Exception as e:
        current_app.logger.error(f"Unexpected error in is_user_authorized: {str(e)}")
        # Fail closed: deny access on unexpected error
        return False, None

