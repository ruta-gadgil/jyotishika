"""
SQLAlchemy Database Models

This module defines the ORM models for the email allowlist authorization system.

SECURITY DESIGN:
- ApprovedUser: Email allowlist (manually maintained)
- User: Actual user accounts (created automatically during OAuth)
- Both tables checked on every protected request (defense in depth)

USAGE:
- ApprovedUser entries are added manually via Supabase dashboard or SQL
- User entries are created automatically during OAuth callback
- Both is_active flags must be True for authorization
"""

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from datetime import datetime
import uuid

# SQLAlchemy instance (initialized in __init__.py)
db = SQLAlchemy()


class ApprovedUser(db.Model):
    """
    Email allowlist for authorization.
    
    Manually maintained via Supabase dashboard or direct SQL.
    Only users with approved emails can create accounts and log in.
    
    SECURITY NOTES:
    - Email is primary key (ensures uniqueness, fast lookup)
    - is_active allows temporary deactivation without deletion
    - Checked on every OAuth callback and protected request
    """
    __tablename__ = "approved_users"
    
    # Primary key: email address
    # Must match Google OAuth email exactly (case-sensitive)
    email = db.Column(db.Text, primary_key=True, nullable=False)
    
    # Active flag: if False, user cannot log in
    # Default True so new approvals are immediately active
    is_active = db.Column(db.Boolean, nullable=False, default=True, server_default=db.text("true"))
    
    # Timestamp when email was added to allowlist
    # Uses server timestamp for consistency
    added_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=func.current_timestamp()
    )
    
    # Optional admin note (e.g., "Beta tester", "Team member")
    note = db.Column(db.Text, nullable=True)
    
    def __repr__(self):
        return f"<ApprovedUser {self.email} active={self.is_active}>"


class User(db.Model):
    """
    User accounts created automatically during OAuth.
    
    Only created if email exists in approved_users with is_active=True.
    Records are updated on every successful login.
    
    SECURITY NOTES:
    - UUID primary key prevents enumeration attacks
    - google_sub is the reliable identifier (email can change)
    - Both users.is_active AND approved_users.is_active checked on every request
    - last_login_at updated on every successful OAuth callback
    """
    __tablename__ = "users"
    
    # Primary key: UUID v4
    # Prevents enumeration attacks (can't guess valid user IDs)
    id = db.Column(
        db.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=db.text("uuid_generate_v4()")
    )
    
    # Google's unique user identifier from OAuth "sub" claim
    # This is the authoritative identifier (more reliable than email)
    # Indexed and unique to prevent duplicate accounts
    google_sub = db.Column(db.Text, unique=True, nullable=False, index=True)
    
    # User's email from Google OAuth
    # Stored for convenience but google_sub is the primary identifier
    # Indexed for fast lookup during authorization checks
    email = db.Column(db.Text, unique=True, nullable=False, index=True)
    
    # User's display name from Google profile
    # Optional field (some Google accounts may not have a name)
    name = db.Column(db.Text, nullable=True)
    
    # Timestamp when user record was created (first login)
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=func.current_timestamp()
    )
    
    # Timestamp of most recent successful login
    # Updated on every OAuth callback success
    # Useful for analytics and inactive account cleanup
    last_login_at = db.Column(db.DateTime, nullable=True)
    
    # Active flag: if False, user cannot log in
    # Provides account-level deactivation independent of approved_users
    # Both users.is_active AND approved_users.is_active must be True
    is_active = db.Column(db.Boolean, nullable=False, default=True, server_default=db.text("true"))
    
    def __repr__(self):
        return f"<User {self.email} (google_sub={self.google_sub[:10]}...)>"
    
    def to_dict(self):
        """
        Convert user to dictionary for API responses.
        
        Returns:
            dict: User data (excludes sensitive fields like google_sub)
        """
        return {
            "id": str(self.id),
            "email": self.email,
            "name": self.name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "is_active": self.is_active
        }

