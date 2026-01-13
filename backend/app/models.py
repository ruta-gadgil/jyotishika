"""
SQLAlchemy Database Models

This module defines the ORM models for the authorization and chart storage system.

SECURITY DESIGN:
- ApprovedUser: Email allowlist (manually maintained)
- User: Actual user accounts (created automatically during OAuth)
- Profile: Birth details and chart settings (user-owned, PII)
- Chart: Cached chart calculation results (linked to profiles)
- Both authorization tables checked on every protected request (defense in depth)

USAGE:
- ApprovedUser entries are added manually via Supabase dashboard or SQL
- User entries are created automatically during OAuth callback
- Profile entries created automatically when users calculate charts
- Chart entries cache expensive Swiss Ephemeris calculations
- Both is_active flags must be True for authorization
"""

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from datetime import datetime as dt
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
        default=dt.utcnow,
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
        default=dt.utcnow,
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


class Profile(db.Model):
    """
    Birth profiles for astrological chart calculations.
    
    Stores birth details and chart calculation settings.
    Each profile belongs to a user and has one associated chart (1:1).
    
    SECURITY NOTES:
    - Contains PII (birth datetime, location coordinates)
    - user_id foreign key enforces ownership
    - ON DELETE CASCADE removes profiles when user deleted
    - Unique constraint prevents duplicate profiles
    - Only accessible to owning user (verified in routes)
    
    FEATURES:
    - Automatic deduplication via unique constraint
    - Soft delete support via is_active flag
    - Optional profile names for user organization
    """
    __tablename__ = "profiles"
    
    # Primary key: UUID v4
    id = db.Column(
        db.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=db.text("uuid_generate_v4()")
    )
    
    # Foreign key to users table
    # ON DELETE CASCADE: profiles deleted when user deleted
    user_id = db.Column(
        db.UUID(as_uuid=True),
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    
    # Optional profile name (e.g., "My Chart", "John's Chart")
    name = db.Column(db.Text, nullable=True)
    
    # Birth details (PII - sensitive data)
    datetime = db.Column(db.Text, nullable=False)  # ISO-8601 format
    tz = db.Column(db.Text, nullable=True)  # Timezone name (e.g., "Asia/Kolkata")
    utc_offset_minutes = db.Column(db.Integer, nullable=True)  # UTC offset in minutes
    latitude = db.Column(db.Float, nullable=False)  # -90 to 90
    longitude = db.Column(db.Float, nullable=False)  # -180 to 180
    
    # Chart calculation settings
    house_system = db.Column(db.Text, nullable=False, default='WHOLE_SIGN')
    ayanamsha = db.Column(db.Text, nullable=False, default='LAHIRI')
    node_type = db.Column(db.Text, nullable=False, default='MEAN')
    
    # Metadata
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=dt.utcnow,
        server_default=func.current_timestamp()
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=dt.utcnow,
        onupdate=dt.utcnow,
        server_default=func.current_timestamp()
    )
    is_active = db.Column(db.Boolean, nullable=False, default=True, server_default=db.text("true"))
    
    # Relationships
    user = db.relationship('User', backref=db.backref('profiles', lazy=True))
    chart = db.relationship('Chart', uselist=False, back_populates='profile', cascade='all, delete-orphan')
    
    # Unique constraint: prevent duplicate profiles for same user + birth details + settings
    __table_args__ = (
        db.UniqueConstraint(
            'user_id', 'datetime', 'latitude', 'longitude',
            'house_system', 'ayanamsha', 'node_type',
            name='uq_user_profile'
        ),
    )
    
    def __repr__(self):
        return f"<Profile {self.id} user={self.user_id} name={self.name}>"
    
    def to_dict(self):
        """
        Convert profile to dictionary for API responses.
        
        Returns:
            dict: Profile data including birth details (only returned to owner)
        """
        return {
            "id": str(self.id),
            "name": self.name,
            "datetime": self.datetime,
            "tz": self.tz,
            "utc_offset_minutes": self.utc_offset_minutes,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "house_system": self.house_system,
            "ayanamsha": self.ayanamsha,
            "node_type": self.node_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_active": self.is_active
        }


class Chart(db.Model):
    """
    Cached astrological chart calculation results.
    
    Stores pre-calculated chart data to avoid expensive Swiss Ephemeris recomputation.
    Each chart belongs to exactly one profile (1:1 relationship).
    
    DESIGN NOTES:
    - JSONB columns store flexible calculation results
    - ON DELETE CASCADE removes charts when profile deleted
    - Unique constraint on profile_id enforces 1:1 relationship
    - Immutable data (astrological calculations don't change)
    
    PERFORMANCE:
    - Caching reduces chart calculation from ~100-500ms to ~5-10ms
    - JSONB enables efficient querying if needed in future
    """
    __tablename__ = "charts"
    
    # Primary key: UUID v4
    id = db.Column(
        db.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=db.text("uuid_generate_v4()")
    )
    
    # Foreign key to profiles table (1:1 relationship)
    # UNIQUE constraint enforces one chart per profile
    # ON DELETE CASCADE: charts deleted when profile deleted
    profile_id = db.Column(
        db.UUID(as_uuid=True),
        db.ForeignKey('profiles.id', ondelete='CASCADE'),
        nullable=False,
        unique=True,
        index=True
    )
    
    # Calculated chart data (JSONB for flexibility)
    ascendant_data = db.Column(db.JSON, nullable=False)  # Ascendant position, nakshatra, etc.
    planets_data = db.Column(db.JSON, nullable=False)  # Array of planet objects
    house_cusps = db.Column(db.JSON, nullable=True)  # House cusp positions
    bhav_chalit_data = db.Column(db.JSON, nullable=False)  # Bhav Chalit house system
    chart_metadata = db.Column(db.JSON, nullable=False)  # Calculation metadata
    
    # Metadata
    calculated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=dt.utcnow,
        server_default=func.current_timestamp()
    )
    
    # Relationships
    profile = db.relationship('Profile', back_populates='chart')
    
    def __repr__(self):
        return f"<Chart {self.id} profile={self.profile_id}>"
    
    def to_dict(self):
        """
        Convert chart to dictionary for API responses.
        
        Returns:
            dict: Chart calculation results
        """
        return {
            "ascendant": self.ascendant_data,
            "planets": self.planets_data,
            "houseCusps": self.house_cusps,
            "bhavChalit": self.bhav_chalit_data,
            "metadata": self.chart_metadata,
            "calculated_at": self.calculated_at.isoformat() if self.calculated_at else None
        }

