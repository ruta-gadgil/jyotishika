"""
Database Utilities

This module provides database connection management and utility functions.

SECURITY NOTES:
- Connection pooling configured with reasonable limits
- Graceful error handling for connection failures
- No credentials in code (DATABASE_URL from environment)
- Profile operations verify user ownership
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


def set_rls_user_id(user_id):
    """
    Set the current user ID for Row Level Security (RLS) policies.
    
    This function sets a session variable that RLS policies use to determine
    which user is making the request. Call this before executing queries
    that should be filtered by RLS.
    
    Args:
        user_id: UUID of the current user (from authenticated session)
        
    NOTES:
    - Only needed if RLS policies are enabled in the database
    - Should be called at the start of each request handler
    - Session variable is scoped to the current transaction
    - Safe to call even if RLS is not enabled (no-op)
    
    Example usage in route:
        from flask import g
        from .db import set_rls_user_id
        
        user = g.current_user
        set_rls_user_id(user.id)
        # Now all queries will be filtered by RLS policies
    """
    try:
        # Set session variable for RLS policies
        # This is used by the app.current_user_id() function in RLS policies
        db.session.execute(
            db.text("SET LOCAL app.current_user_id = :user_id"),
            {"user_id": str(user_id)}
        )
        current_app.logger.debug(f"RLS user_id set: {user_id}")
    except Exception as e:
        # Don't fail if RLS is not configured or variable can't be set
        # This allows the app to work with or without RLS enabled
        current_app.logger.debug(f"Could not set RLS user_id (RLS may not be enabled): {str(e)}")


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
            current_app.logger.info(f"Existing user logged in: {google_sub[:12]}...")
        else:
            # Create new user
            user = User(
                google_sub=google_sub,
                email=email,
                name=name,
                last_login_at=datetime.utcnow()
            )
            db.session.add(user)
            email_domain = email.split("@")[1] if "@" in email else "unknown"
            current_app.logger.info(f"New user created from domain: {email_domain}")
        
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
        # Log the email domain being checked (for debugging)
        email_domain = email.split("@")[1] if "@" in email else "unknown"
        current_app.logger.info(f"Checking authorization for domain: {email_domain}")
        
        # Ensure we have a database session
        if not hasattr(current_app, 'extensions') or 'sqlalchemy' not in current_app.extensions:
            current_app.logger.error("Database not initialized - SQLAlchemy extension not found")
            return False
        
        # Query the database
        approved_user = ApprovedUser.query.filter_by(email=email).first()
        
        if not approved_user:
            current_app.logger.warning(f"Authorization denied: domain not in allowlist: {email_domain}")
            # Debug: List count of approved users (for troubleshooting)
            try:
                approved_count = ApprovedUser.query.filter_by(is_active=True).count()
                current_app.logger.debug(f"Active approved users in database: {approved_count}")
            except Exception as debug_e:
                current_app.logger.debug(f"Could not count approved users: {str(debug_e)}")
            return False
        
        current_app.logger.info(f"Found approved_user for domain: {email_domain}, is_active={approved_user.is_active}")
        
        if not approved_user.is_active:
            current_app.logger.warning(f"Authorization denied: user in allowlist but not active (domain: {email_domain})")
            return False
        
        current_app.logger.info(f"Authorization approved for domain: {email_domain}")
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
            current_app.logger.warning(f"Authorization denied: user not active (google_sub: {google_sub[:12]}...)")
            return False, None
        
        # Check 2: Email is approved and active
        approved_user = ApprovedUser.query.filter_by(email=email).first()
        email_domain = email.split("@")[1] if "@" in email else "unknown"
        
        if not approved_user:
            current_app.logger.warning(f"Authorization denied: domain not in allowlist: {email_domain}")
            return False, None
        
        if not approved_user.is_active:
            current_app.logger.warning(f"Authorization denied: user in allowlist but not active (domain: {email_domain})")
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


# ============================================================================
# Profile and Chart Management Functions
# ============================================================================


def get_or_create_profile(user_id, birth_details, chart_settings, name=None):
    """
    Get existing profile or create new one for the given user and birth details.
    
    Automatically deduplicates profiles based on unique constraint:
    (user_id, datetime, latitude, longitude, house_system, ayanamsha, node_type)
    
    Args:
        user_id: UUID of the user (from authenticated session)
        birth_details: dict with keys: datetime, tz, utc_offset_minutes, latitude, longitude
        chart_settings: dict with keys: house_system, ayanamsha, node_type
        name: Optional profile name (e.g., "My Chart")
        
    Returns:
        Profile: Profile model instance (existing or newly created)
        
    Raises:
        SQLAlchemyError: On database errors
        
    SECURITY NOTES:
    - user_id must come from authenticated session (never from request)
    - Unique constraint prevents duplicate profiles
    - Wrapped in transaction for atomicity
    - Handles floating-point precision issues with lat/lng
    """
    from .models import Profile
    from sqlalchemy.exc import IntegrityError
    from sqlalchemy import and_, func
    
    # Round lat/lng to match PostgreSQL REAL precision (4 decimal places is safe)
    # This prevents precision mismatches between Python floats and database storage
    lat_rounded = round(birth_details['latitude'], 4)
    lng_rounded = round(birth_details['longitude'], 4)
    
    try:
        # Try to find existing profile using range query for lat/lng to handle precision
        # Use a small tolerance (0.0001 degrees ≈ 11 meters) for floating-point comparison
        tolerance = 0.0001
        profile = Profile.query.filter(
            and_(
                Profile.user_id == user_id,
                Profile.datetime == birth_details['datetime'],
                Profile.latitude.between(lat_rounded - tolerance, lat_rounded + tolerance),
                Profile.longitude.between(lng_rounded - tolerance, lng_rounded + tolerance),
                Profile.house_system == chart_settings['house_system'],
                Profile.ayanamsha == chart_settings['ayanamsha'],
                Profile.node_type == chart_settings['node_type']
            )
        ).first()
        
        if profile:
            current_app.logger.info(f"Reusing existing profile: {profile.id}")
            # Update name if provided and different
            if name and profile.name != name:
                profile.name = name
                db.session.commit()
            return profile
        
        # Create new profile with rounded coordinates
        profile = Profile(
            user_id=user_id,
            name=name,
            datetime=birth_details['datetime'],
            tz=birth_details.get('tz'),
            utc_offset_minutes=birth_details.get('utc_offset_minutes'),
            latitude=lat_rounded,  # Use rounded value
            longitude=lng_rounded,  # Use rounded value
            house_system=chart_settings['house_system'],
            ayanamsha=chart_settings['ayanamsha'],
            node_type=chart_settings['node_type']
        )
        
        db.session.add(profile)
        
        try:
            db.session.commit()
            current_app.logger.info(f"Created new profile: {profile.id} for user: {user_id}")
            return profile
        except IntegrityError as ie:
            # Race condition or precision issue: profile exists but our query missed it
            db.session.rollback()
            current_app.logger.info(f"Profile already exists (caught by unique constraint), fetching existing profile")
            
            # Query again with broader range to catch any precision variations
            profile = Profile.query.filter(
                and_(
                    Profile.user_id == user_id,
                    Profile.datetime == birth_details['datetime'],
                    Profile.latitude.between(lat_rounded - tolerance, lat_rounded + tolerance),
                    Profile.longitude.between(lng_rounded - tolerance, lng_rounded + tolerance),
                    Profile.house_system == chart_settings['house_system'],
                    Profile.ayanamsha == chart_settings['ayanamsha'],
                    Profile.node_type == chart_settings['node_type']
                )
            ).first()
            
            if profile:
                current_app.logger.info(f"Retrieved existing profile after IntegrityError: {profile.id}")
                # Update name if provided and different
                if name and profile.name != name:
                    profile.name = name
                    db.session.commit()
                return profile
            else:
                # Last resort: query by all other fields and pick the closest lat/lng match
                # This handles extreme precision edge cases
                current_app.logger.warning(f"Could not find profile with tolerance, trying broader search")
                candidates = Profile.query.filter_by(
                    user_id=user_id,
                    datetime=birth_details['datetime'],
                    house_system=chart_settings['house_system'],
                    ayanamsha=chart_settings['ayanamsha'],
                    node_type=chart_settings['node_type']
                ).all()
                
                # Find closest match by lat/lng
                for candidate in candidates:
                    lat_diff = abs(candidate.latitude - lat_rounded)
                    lng_diff = abs(candidate.longitude - lng_rounded)
                    if lat_diff < 0.001 and lng_diff < 0.001:  # Within ~100 meters
                        current_app.logger.info(f"Found matching profile via broader search: {candidate.id}")
                        if name and candidate.name != name:
                            candidate.name = name
                            db.session.commit()
                        return candidate
                
                # Still couldn't find it - this shouldn't happen
                current_app.logger.error(f"IntegrityError occurred but could not find existing profile: {str(ie)}")
                raise
        
    except IntegrityError as e:
        # This should have been caught above, but just in case
        db.session.rollback()
        current_app.logger.error(f"IntegrityError in get_or_create_profile: {str(e)}")
        raise
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error in get_or_create_profile: {str(e)}")
        raise
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Unexpected error in get_or_create_profile: {str(e)}")
        raise


def get_user_profile(profile_id, user_id):
    """
    Load profile by ID with ownership verification.
    
    Args:
        profile_id: UUID of the profile to load
        user_id: UUID of the authenticated user (from session)
        
    Returns:
        tuple: (profile: Profile or None, error_response: tuple or None)
        - On success: (profile, None)
        - On not found: (None, (error_dict, 404))
        - On unauthorized: (None, (error_dict, 403))
        
    SECURITY NOTES:
    - Always verifies profile.user_id == user_id
    - Returns 403 if user doesn't own profile
    - Returns 404 if profile doesn't exist
    - Generic error messages (don't leak existence)
    """
    from .models import Profile
    from flask import jsonify
    
    try:
        # Load profile by ID
        profile = Profile.query.filter_by(id=profile_id, is_active=True).first()
        
        if not profile:
            current_app.logger.warning(f"Profile not found: {profile_id}")
            return None, (jsonify({
                "error": {
                    "code": "NOT_FOUND",
                    "message": "Profile not found"
                }
            }), 404)
        
        # Verify ownership
        if str(profile.user_id) != str(user_id):
            current_app.logger.warning(
                f"Unauthorized profile access attempt: profile={profile_id}, "
                f"owner={profile.user_id}, requester={user_id}"
            )
            return None, (jsonify({
                "error": {
                    "code": "FORBIDDEN",
                    "message": "Access denied"
                }
            }), 403)
        
        current_app.logger.info(f"Profile loaded: {profile_id} for user: {user_id}")
        return profile, None
        
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error in get_user_profile: {str(e)}")
        return None, (jsonify({
            "error": {
                "code": "DATABASE_ERROR",
                "message": "Failed to load profile"
            }
        }), 500)
    except Exception as e:
        current_app.logger.error(f"Unexpected error in get_user_profile: {str(e)}")
        return None, (jsonify({
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred"
            }
        }), 500)


def get_cached_chart(profile_id):
    """
    Retrieve cached chart for the given profile.
    
    Args:
        profile_id: UUID of the profile
        
    Returns:
        Chart: Chart model instance or None if not cached
        
    NOTES:
    - Returns None if chart doesn't exist (not an error)
    - Caller should recalculate and save if None
    """
    from .models import Chart
    
    try:
        chart = Chart.query.filter_by(profile_id=profile_id).first()
        
        if chart:
            current_app.logger.info(f"Cache hit: chart found for profile {profile_id}")
        else:
            current_app.logger.info(f"Cache miss: no chart for profile {profile_id}")
        
        return chart
        
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error in get_cached_chart: {str(e)}")
        # Return None on error (caller will recalculate)
        return None
    except Exception as e:
        current_app.logger.error(f"Unexpected error in get_cached_chart: {str(e)}")
        return None


def save_chart(profile_id, chart_data):
    """
    Save calculated chart results to database.
    
    Creates new chart or updates existing chart for the profile.
    
    Args:
        profile_id: UUID of the profile
        chart_data: dict with keys: ascendant, planets, houseCusps, bhavChalit, metadata
        
    Returns:
        Chart: Chart model instance
        
    Raises:
        SQLAlchemyError: On database errors
        
    NOTES:
    - Uses upsert pattern (create or update)
    - Wrapped in transaction for atomicity
    """
    from .models import Chart
    
    try:
        # Check if chart already exists
        chart = Chart.query.filter_by(profile_id=profile_id).first()
        
        if chart:
            # Update existing chart
            chart.ascendant_data = chart_data['ascendant']
            chart.planets_data = chart_data['planets']
            chart.house_cusps = chart_data.get('houseCusps')
            chart.bhav_chalit_data = chart_data['bhavChalit']
            chart.chart_metadata = chart_data['metadata']
            current_app.logger.info(f"Updated cached chart for profile: {profile_id}")
        else:
            # Create new chart
            chart = Chart(
                profile_id=profile_id,
                ascendant_data=chart_data['ascendant'],
                planets_data=chart_data['planets'],
                house_cusps=chart_data.get('houseCusps'),
                bhav_chalit_data=chart_data['bhavChalit'],
                chart_metadata=chart_data['metadata']
            )
            db.session.add(chart)
            current_app.logger.info(f"Created new cached chart for profile: {profile_id}")
        
        db.session.commit()
        return chart
        
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error in save_chart: {str(e)}")
        raise
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Unexpected error in save_chart: {str(e)}")
        raise


def get_user_profiles(user_id, limit=100):
    """
    Get all active profiles for a user.
    
    Args:
        user_id: UUID of the user
        limit: Maximum number of profiles to return (default 100)
        
    Returns:
        list: List of Profile model instances
        
    NOTES:
    - Only returns active profiles (is_active=True)
    - Ordered by updated_at descending (most recently updated first)
    - Limited to prevent excessive data transfer
    """
    from .models import Profile
    
    try:
        profiles = Profile.query.filter_by(
            user_id=user_id,
            is_active=True
        ).order_by(
            Profile.updated_at.desc()
        ).limit(limit).all()
        
        current_app.logger.info(f"Retrieved {len(profiles)} profiles for user: {user_id}")
        return profiles
        
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error in get_user_profiles: {str(e)}")
        return []
    except Exception as e:
        current_app.logger.error(f"Unexpected error in get_user_profiles: {str(e)}")
        return []


def update_profile(profile_id, user_id, updates):
    """
    Update profile with provided fields.
    
    Args:
        profile_id: UUID of the profile to update
        user_id: UUID of the authenticated user (from session)
        updates: dict with fields to update (camelCase keys from frontend)
                 Keys: name, datetime, tz, utcOffsetMinutes, latitude, longitude,
                       houseSystem, ayanamsha, nodeType
                 
    Returns:
        tuple: (profile: Profile or None, error_response: tuple or None)
        - On success: (profile, None)
        - On not found: (None, (error_dict, 404))
        - On unauthorized: (None, (error_dict, 403))
        - On duplicate: (None, (error_dict, 409))
        
    SECURITY NOTES:
    - Verifies profile ownership before updating
    - Rounds coordinates to 4 decimal places for precision
    - Checks unique constraint before committing
    - Invalidates chart cache if chart-affecting fields change
    - Wrapped in transaction for atomicity
    
    Chart-affecting fields (will invalidate cache):
    - datetime, latitude, longitude, house_system, ayanamsha, node_type
    """
    from .models import Profile, Chart
    from sqlalchemy.exc import IntegrityError
    from sqlalchemy import and_
    from flask import jsonify
    
    # Map camelCase frontend keys to snake_case database keys
    field_mapping = {
        'name': 'name',
        'datetime': 'datetime',
        'tz': 'tz',
        'utcOffsetMinutes': 'utc_offset_minutes',
        'latitude': 'latitude',
        'longitude': 'longitude',
        'houseSystem': 'house_system',
        'ayanamsha': 'ayanamsha',
        'nodeType': 'node_type'
    }
    
    # Chart-affecting fields (if any of these change, invalidate cache)
    chart_affecting_fields = {'datetime', 'latitude', 'longitude', 'house_system', 'ayanamsha', 'node_type'}
    
    try:
        # Step 1: Verify ownership
        profile, error_response = get_user_profile(profile_id, user_id)
        if error_response:
            return None, error_response
        
        # Step 2: Check if there are any updates
        if not updates:
            current_app.logger.info(f"No updates provided for profile: {profile_id}")
            return profile, None
        
        # Step 3: Build update dict with snake_case keys and handle special cases
        db_updates = {}
        chart_invalidation_needed = False
        
        for frontend_key, value in updates.items():
            if value is None:  # Skip None values (frontend can send null to clear optional fields)
                # Only allow None for optional fields
                if frontend_key in ['name', 'tz', 'utcOffsetMinutes']:
                    db_key = field_mapping[frontend_key]
                    db_updates[db_key] = None
                continue
            
            db_key = field_mapping.get(frontend_key)
            if db_key is None:
                current_app.logger.warning(f"Unknown update field: {frontend_key}")
                continue
            
            # Round coordinates to 4 decimal places
            if db_key in ['latitude', 'longitude']:
                value = round(float(value), 4)
            
            db_updates[db_key] = value
            
            # Track if chart cache needs invalidation
            if db_key in chart_affecting_fields:
                chart_invalidation_needed = True
        
        # Step 4: Check unique constraint before updating
        # Build the "new" profile values (current + updates)
        new_datetime = db_updates.get('datetime', profile.datetime)
        new_latitude = db_updates.get('latitude', profile.latitude)
        new_longitude = db_updates.get('longitude', profile.longitude)
        new_house_system = db_updates.get('house_system', profile.house_system)
        new_ayanamsha = db_updates.get('ayanamsha', profile.ayanamsha)
        new_node_type = db_updates.get('node_type', profile.node_type)
        
        # Round lat/lng for comparison
        lat_rounded = round(new_latitude, 4)
        lng_rounded = round(new_longitude, 4)
        
        # Check if another profile exists with same unique constraint values
        # Use tolerance-based comparison for lat/lng (0.0001 degrees ≈ 11 meters)
        tolerance = 0.0001
        conflicting_profile = Profile.query.filter(
            and_(
                Profile.user_id == user_id,
                Profile.id != profile_id,  # Exclude current profile
                Profile.datetime == new_datetime,
                Profile.latitude.between(lat_rounded - tolerance, lat_rounded + tolerance),
                Profile.longitude.between(lng_rounded - tolerance, lng_rounded + tolerance),
                Profile.house_system == new_house_system,
                Profile.ayanamsha == new_ayanamsha,
                Profile.node_type == new_node_type
            )
        ).first()
        
        if conflicting_profile:
            current_app.logger.warning(
                f"Unique constraint violation: profile update would create duplicate "
                f"profile_id={profile_id}, conflicting_id={conflicting_profile.id}"
            )
            return None, (jsonify({
                "error": {
                    "code": "DUPLICATE_PROFILE",
                    "message": "A profile with these details already exists"
                }
            }), 409)
        
        # Step 5: Apply updates to profile object
        for db_key, value in db_updates.items():
            setattr(profile, db_key, value)
        
        # Step 6: Invalidate chart cache if chart-affecting fields changed
        if chart_invalidation_needed:
            chart = Chart.query.filter_by(profile_id=profile_id).first()
            if chart:
                db.session.delete(chart)
                current_app.logger.info(f"Deleted cached chart for profile: {profile_id} (chart-affecting fields updated)")
        
        # Step 7: Commit transaction
        try:
            db.session.commit()
            current_app.logger.info(f"Profile updated: {profile_id} for user: {user_id}")
            return profile, None
        except IntegrityError as ie:
            # Race condition: another request created duplicate profile
            db.session.rollback()
            current_app.logger.warning(f"IntegrityError on profile update (race condition): {str(ie)}")
            return None, (jsonify({
                "error": {
                    "code": "DUPLICATE_PROFILE",
                    "message": "A profile with these details already exists"
                }
            }), 409)
        
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error in update_profile: {str(e)}")
        return None, (jsonify({
            "error": {
                "code": "DATABASE_ERROR",
                "message": "Failed to update profile"
            }
        }), 500)
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Unexpected error in update_profile: {str(e)}")
        return None, (jsonify({
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred"
            }
        }), 500)


def delete_profile(profile_id, user_id):
    """
    Delete profile and associated chart.
    
    Args:
        profile_id: UUID of the profile to delete
        user_id: UUID of the authenticated user (from session)
        
    Returns:
        tuple: (success: bool, error_response: tuple or None)
        - On success: (True, None)
        - On error: (False, (error_dict, status_code))
        
    SECURITY NOTES:
    - Verifies profile ownership before deletion
    - Charts automatically deleted via CASCADE constraint
    - Wrapped in transaction for atomicity
    - Generic error messages (don't leak existence)
    """
    from .models import Profile
    from flask import jsonify
    
    try:
        # Step 1: Verify ownership
        profile, error_response = get_user_profile(profile_id, user_id)
        if error_response:
            # Return (False, error_response) to indicate failure
            return False, error_response
        
        # Step 2: Delete profile (hard delete)
        # Charts will be automatically deleted via CASCADE constraint
        db.session.delete(profile)
        
        # Step 3: Commit transaction
        db.session.commit()
        
        current_app.logger.info(f"Profile deleted: {profile_id} for user: {user_id}")
        return True, None
        
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error in delete_profile: {str(e)}")
        return False, (jsonify({
            "error": {
                "code": "DATABASE_ERROR",
                "message": "Failed to delete profile"
            }
        }), 500)
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Unexpected error in delete_profile: {str(e)}")
        return False, (jsonify({
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred"
            }
        }), 500)


# ============================================================================
# Analysis Notes Functions
# ============================================================================

def get_notes_for_chart(chart_id):
    """
    Get all analysis notes for a specific chart.
    
    Args:
        chart_id: UUID of the chart
        
    Returns:
        list: List of AnalysisNote objects, ordered by updated_at DESC
        
    Raises:
        SQLAlchemyError: If database query fails
    """
    from .models import AnalysisNote
    
    try:
        notes = AnalysisNote.query.filter_by(chart_id=chart_id)\
            .order_by(AnalysisNote.updated_at.desc())\
            .all()
        return notes
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error in get_notes_for_chart: {str(e)}")
        raise


def create_note(chart_id, title, note):
    """
    Create a new analysis note for a chart.
    
    Args:
        chart_id: UUID of the chart
        title: Note title (max 200 chars)
        note: Note content (max 5000 chars)
        
    Returns:
        AnalysisNote: The created note object
        
    Raises:
        SQLAlchemyError: If database operation fails
    """
    from .models import AnalysisNote
    
    try:
        # Create new note
        new_note = AnalysisNote(
            chart_id=chart_id,
            title=title,
            note=note
        )
        
        db.session.add(new_note)
        db.session.commit()
        
        current_app.logger.info(f"Note created: {new_note.id} for chart: {chart_id}")
        return new_note
        
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error in create_note: {str(e)}")
        raise


def get_note_by_id(note_id):
    """
    Get a single analysis note by ID.
    
    Args:
        note_id: UUID of the note
        
    Returns:
        AnalysisNote or None: The note object if found, None otherwise
        
    Raises:
        SQLAlchemyError: If database query fails
    """
    from .models import AnalysisNote
    
    try:
        note = AnalysisNote.query.filter_by(id=note_id).first()
        return note
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error in get_note_by_id: {str(e)}")
        raise


def update_note(note_id, title=None, note=None):
    """
    Update an existing analysis note.
    
    Args:
        note_id: UUID of the note
        title: Optional new title (max 200 chars)
        note: Optional new note content (max 5000 chars)
        
    Returns:
        AnalysisNote or None: The updated note object if found, None otherwise
        
    Raises:
        SQLAlchemyError: If database operation fails
    """
    from .models import AnalysisNote
    from datetime import datetime as dt
    
    try:
        existing_note = AnalysisNote.query.filter_by(id=note_id).first()
        
        if not existing_note:
            return None
        
        # Update fields if provided
        if title is not None:
            existing_note.title = title
        if note is not None:
            existing_note.note = note
        
        # Update timestamp
        existing_note.updated_at = dt.utcnow()
        
        db.session.commit()
        
        current_app.logger.info(f"Note updated: {note_id}")
        return existing_note
        
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error in update_note: {str(e)}")
        raise


def delete_note(note_id):
    """
    Delete an analysis note.
    
    Args:
        note_id: UUID of the note
        
    Returns:
        bool: True if deleted, False if note not found
        
    Raises:
        SQLAlchemyError: If database operation fails
    """
    from .models import AnalysisNote
    
    try:
        note = AnalysisNote.query.filter_by(id=note_id).first()
        
        if not note:
            return False
        
        db.session.delete(note)
        db.session.commit()
        
        current_app.logger.info(f"Note deleted: {note_id}")
        return True
        
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error in delete_note: {str(e)}")
        raise


def get_notes_summary_for_charts(chart_ids):
    """
    Get notes summary (count and titles) for multiple charts.
    
    Used to enhance the profiles list with notes metadata.
    
    Args:
        chart_ids: List of chart UUIDs
        
    Returns:
        dict: Dictionary mapping chart_id to {count, titles}
              Example: {
                  'chart-uuid-1': {'count': 3, 'titles': ['Title 1', 'Title 2', 'Title 3']},
                  'chart-uuid-2': {'count': 1, 'titles': ['Title A']}
              }
        
    Raises:
        SQLAlchemyError: If database query fails
    """
    from .models import AnalysisNote
    from sqlalchemy import func
    
    try:
        if not chart_ids:
            return {}
        
        # Query to get all notes for the specified charts
        notes = AnalysisNote.query.filter(AnalysisNote.chart_id.in_(chart_ids))\
            .order_by(AnalysisNote.chart_id, AnalysisNote.updated_at.desc())\
            .all()
        
        # Group notes by chart_id
        summary = {}
        for note in notes:
            chart_id_str = str(note.chart_id)
            if chart_id_str not in summary:
                summary[chart_id_str] = {'count': 0, 'titles': []}
            summary[chart_id_str]['count'] += 1
            summary[chart_id_str]['titles'].append(note.title)
        
        return summary
        
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error in get_notes_summary_for_charts: {str(e)}")
        raise

