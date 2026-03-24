from flask import Blueprint, request, jsonify, current_app
from .schemas import ChartRequest, DashaRequest, ProfileUpdateRequest, AnalysisNoteCreate, AnalysisNoteUpdate
from .auth import get_current_user
from .logging_utils import sanitize_request_data, sanitize_dict
from .astro.engine import init_ephemeris, julian_day_utc, ascendant_and_houses, compute_planets, compute_whole_sign_cusps, compute_sripati_cusps
from .astro.utils import (
    to_utc,
    sign_index,
    house_from_sign,
    house_from_cusps,
    norm360,
    format_utc_offset,
    get_nakshatra_and_charan,
    get_navamsha_info,
)
from .astro.constants import PLANET_MEAN_SPEEDS, STATIONARY_THRESHOLDS, COMBUSTION_THRESHOLDS
from .astro.dasha import calculate_vimshottari_timeline
from datetime import datetime
import logging

bp = Blueprint("api", __name__)

@bp.route("/chart", methods=["POST"])
def chart():
    # AUTHENTICATION REQUIRED - Validate session and authorization
    session_data = get_current_user()
    if isinstance(session_data, tuple):  # Error response (401)
        return session_data
    
    # Get authenticated user from Flask g context (set by get_current_user)
    from flask import g
    user = g.current_user
    
    # Log request information
    current_app.logger.info(f"🔵 API Request received - Method: {request.method}, Path: {request.path}")
    # Don't log full headers (contains auth cookies) or full request data (may contain PII)
    current_app.logger.debug(f"📦 Request Content-Type: {request.content_type}, Length: {request.content_length or 0} bytes")
    
    try:
        payload = ChartRequest.model_validate_json(request.data)
        # Log validated payload (sanitized)
        sanitized_payload = sanitize_dict(payload.model_dump())
        current_app.logger.info(f"✅ Validated chart request")
        current_app.logger.debug(f"Chart request params: {sanitized_payload}")
    except Exception as e:
        # Log and print validation error
        print(f"❌ Request validation error: {str(e)}")
        current_app.logger.error(f"Request validation error: {str(e)}")
        return jsonify({
            "error": {
                "code": "VALIDATION_ERROR",
                "message": str(e),
                "details": {"field": "request", "value": "invalid"}
            }
        }), 400

    try:
        # Step 1: Get or create profile for this user + birth details
        from .db import get_or_create_profile, get_cached_chart, save_chart
        
        birth_details = {
            'datetime': payload.datetime,
            'tz': payload.tz,
            'utc_offset_minutes': payload.utcOffsetMinutes,
            'latitude': payload.latitude,
            'longitude': payload.longitude
        }
        
        chart_settings = {
            'house_system': payload.houseSystem or current_app.config["HOUSE_SYSTEM"],
            'ayanamsha': payload.ayanamsha or current_app.config["AYANAMSHA"],
            'node_type': payload.nodeType
        }
        
        profile = get_or_create_profile(
            user_id=user.id,
            birth_details=birth_details,
            chart_settings=chart_settings,
            name=payload.profileName
        )
        
        # Step 2: Check if chart is already cached
        cached_chart = get_cached_chart(profile.id)
        
        if cached_chart:
            # Return cached chart data
            current_app.logger.info(f"🎯 Cache hit - returning cached chart for profile: {profile.id}")
            
            response_data = {
                "profile_id": str(profile.id),
                "chart_id": str(cached_chart.id),
                "profile": profile.to_dict(),
                "metadata": cached_chart.chart_metadata,
                "ascendant": cached_chart.ascendant_data,
                "planets": cached_chart.planets_data,
                "bhavChalit": cached_chart.bhav_chalit_data
            }
            
            return jsonify(response_data), 200
        
        # Step 3: Calculate chart (cache miss)
        current_app.logger.info(f"💫 Cache miss - calculating chart for profile: {profile.id}")

        # Use shared chart calculation helper so POST and lazy paths match
        from .chart_calc import calculate_chart_for_profile
        chart_data = calculate_chart_for_profile(profile)

        # Step 4: Save calculated chart to database (cache for future requests)
        saved_chart = save_chart(profile.id, chart_data)
        current_app.logger.info(f"💾 Chart saved to cache for profile: {profile.id}")

        # Step 5: Return chart data with profile information
        response_data = {
            "profile_id": str(profile.id),
            "chart_id": str(saved_chart.id) if saved_chart else None,
            "profile": profile.to_dict(),
            "metadata": chart_data["metadata"],
            "ascendant": chart_data["ascendant"],
            "planets": chart_data["planets"],
            "bhavChalit": chart_data["bhavChalit"],
        }

        # Log successful response
        current_app.logger.info(f"🎉 Chart calculation successful")
        return jsonify(response_data), 200

    except Exception as e:
        # Log the error for debugging
        current_app.logger.error(f"💥 Chart calculation error: {str(e)}", exc_info=True)
        return jsonify({
            "error": {
                "code": "CALCULATION_ERROR",
                "message": "Failed to calculate chart",
                "details": {"error": str(e)}
            }
        }), 500


@bp.route("/chart/<profile_id>", methods=["GET"])
def get_chart_by_profile(profile_id):
    """
    Get chart by profile ID.
    
    Returns cached chart for the given profile if it exists.
    If chart not cached, recalculates and saves it.
    
    SECURITY:
    - Requires authentication
    - Verifies profile ownership (user can only access their own profiles)
    - Returns 403 if user doesn't own profile
    - Returns 404 if profile doesn't exist
    """
    # AUTHENTICATION REQUIRED - Validate session and authorization
    session_data = get_current_user()
    if isinstance(session_data, tuple):  # Error response (401)
        return session_data
    
    # Get authenticated user from Flask g context
    from flask import g
    user = g.current_user
    
    current_app.logger.info(f"🔵 GET /chart/{profile_id} - User ID: {user.id}")
    
    try:
        # Step 1: Load profile with ownership verification
        from .db import get_user_profile, get_cached_chart, save_chart
        
        profile, error_response = get_user_profile(profile_id, user.id)
        
        if error_response:
            # Return error (403 or 404)
            return error_response
        
        # Step 2: Check if chart is cached
        cached_chart = get_cached_chart(profile.id)
        
        if cached_chart:
            # Return cached chart
            current_app.logger.info(f"🎯 Cache hit - returning cached chart for profile: {profile.id}")
            
            response_data = {
                "profile_id": str(profile.id),
                "chart_id": str(cached_chart.id),
                "profile": profile.to_dict(),
                "metadata": cached_chart.chart_metadata,
                "ascendant": cached_chart.ascendant_data,
                "planets": cached_chart.planets_data,
                "bhavChalit": cached_chart.bhav_chalit_data
            }
            
            return jsonify(response_data), 200
        
        # Step 3: Chart not cached - recalculate
        current_app.logger.info(f"💫 Cache miss - recalculating chart for profile: {profile.id}")
        
        # Use extracted calculation function
        from .chart_calc import calculate_chart_for_profile
        chart_data = calculate_chart_for_profile(profile)
        
        # Save to cache
        saved_chart = save_chart(profile.id, chart_data)
        current_app.logger.info(f"💾 Chart recalculated and saved to cache for profile: {profile.id}")
        
        # Return response
        response_data = {
            "profile_id": str(profile.id),
            "chart_id": str(saved_chart.id) if saved_chart else None,
            "profile": profile.to_dict(),
            "metadata": chart_data["metadata"],
            "ascendant": chart_data["ascendant"],
            "planets": chart_data["planets"],
            "bhavChalit": chart_data["bhavChalit"]
        }
        
        current_app.logger.info(f"🎉 Chart retrieval successful")
        return jsonify(response_data), 200
        
    except Exception as e:
        current_app.logger.error(f"💥 Chart retrieval error: {str(e)}", exc_info=True)
        return jsonify({
            "error": {
                "code": "CALCULATION_ERROR",
                "message": "Failed to retrieve chart",
                "details": {"error": str(e)}
            }
        }), 500


@bp.route("/dasha", methods=["POST"])
def dasha():
    # AUTHENTICATION REQUIRED - Validate session and authorization
    session_data = get_current_user()
    if isinstance(session_data, tuple):  # Error response (401)
        return session_data
    
    # Log request information
    current_app.logger.info(f"🔵 Dasha API Request received - Method: {request.method}, Path: {request.path}")
    # Don't log full headers (contains auth cookies) or full request data (may contain PII)
    current_app.logger.debug(f"📦 Request Content-Type: {request.content_type}, Length: {request.content_length or 0} bytes")
    
    try:
        payload = DashaRequest.model_validate_json(request.data)
        # Log validated payload (sanitized)
        sanitized_payload = sanitize_dict(payload.model_dump())
        current_app.logger.info(f"✅ Validated dasha request")
        current_app.logger.debug(f"Dasha request params: {sanitized_payload}")
    except Exception as e:
        # Log validation error
        current_app.logger.warning(f"❌ Dasha request validation error: {str(e)}")
        return jsonify({
            "error": {
                "code": "VALIDATION_ERROR",
                "message": str(e),
                "details": {"field": "request", "value": "invalid"}
            }
        }), 400

    try:
        # Convert datetime string to datetime object
        birth_dt = datetime.fromisoformat(payload.datetime.replace('Z', '+00:00'))
        
        # Convert optional date strings to datetime objects
        from_date = None
        to_date = None
        at_date = None
        
        if payload.fromDate:
            from_date = datetime.fromisoformat(payload.fromDate.replace('Z', '+00:00'))
        if payload.toDate:
            to_date = datetime.fromisoformat(payload.toDate.replace('Z', '+00:00'))
        if payload.atDate:
            at_date = datetime.fromisoformat(payload.atDate.replace('Z', '+00:00'))
        
        # Calculate birth chart to get Moon's sidereal longitude
        dt_utc = to_utc(payload.datetime, None, None, payload.latitude, payload.longitude)
        jd_ut = julian_day_utc(dt_utc)
        
        # Initialize ephemeris with ayanamsha from request or default
        effective_ayanamsha = payload.ayanamsha or current_app.config["AYANAMSHA"]
        init_ephemeris(current_app.config["EPHE_PATH"], effective_ayanamsha)
        
        # Get Moon's sidereal longitude
        planets = compute_planets(jd_ut, "MEAN")  # Use MEAN nodes for dasha calculation
        moon_longitude_sidereal = None
        
        for planet in planets:
            if planet["planet"] == "Moon":
                moon_longitude_sidereal = planet["longitude"]
                break
        
        if moon_longitude_sidereal is None:
            raise ValueError("Could not calculate Moon's position")
        
        # Calculate Vimshottari timeline
        timeline, metadata = calculate_vimshottari_timeline(
            birth_utc=birth_dt,
            moon_longitude_sidereal=moon_longitude_sidereal,
            depth=payload.depth,
            from_date=from_date,
            to_date=to_date,
            at_date=at_date
        )
        
        result = {
            "timeline": timeline,
            "metadata": metadata
        }
        
        # Log successful response
        current_app.logger.info(f"🎉 Dasha calculation successful")
        return jsonify(result), 200
        
    except Exception as e:
        # Log error for debugging
        current_app.logger.error(f"💥 Dasha calculation error: {str(e)}", exc_info=True)
        return jsonify({
            "error": {
                "code": "CALCULATION_ERROR",
                "message": "Failed to calculate dasha",
                "details": {"error": str(e)}
            }
        }), 500


@bp.route("/profiles", methods=["GET"])
def get_profiles():
    """
    Get all active profiles for the authenticated user.
    
    Returns an array of Profile objects sorted by updated_at descending.
    
    SECURITY:
    - Requires authentication
    - Only returns profiles owned by the authenticated user
    - Only returns active profiles (is_active=True)
    - Returns empty array if user has no profiles
    """
    # AUTHENTICATION REQUIRED - Validate session and authorization
    session_data = get_current_user()
    if isinstance(session_data, tuple):  # Error response (401)
        return session_data
    
    # Get authenticated user from Flask g context (set by get_current_user)
    from flask import g
    user = g.current_user
    
    current_app.logger.info(f"🔵 GET /profiles - User ID: {user.id}")
    
    try:
        # Get all active profiles for the authenticated user
        from .db import get_user_profiles, get_notes_summary_for_charts
        
        profiles = get_user_profiles(user.id)
        
        # Convert profiles to dictionaries
        profiles_data = [profile.to_dict() for profile in profiles]
        
        # Get chart IDs for all profiles
        chart_ids = []
        profile_to_chart = {}  # Map profile_id to chart_id
        for profile in profiles:
            if profile.chart and profile.chart.id:
                chart_ids.append(profile.chart.id)
                profile_to_chart[str(profile.id)] = str(profile.chart.id)
        
        # Get notes summary for all charts
        notes_summary = get_notes_summary_for_charts(chart_ids)
        
        # Add chart_id and notes metadata to each profile
        for profile_dict in profiles_data:
            profile_id = profile_dict['id']
            chart_id = profile_to_chart.get(profile_id)
            
            # Add chart_id to profile response
            profile_dict['chart_id'] = chart_id
            
            if chart_id and chart_id in notes_summary:
                profile_dict['notes_count'] = notes_summary[chart_id]['count']
                profile_dict['note_titles'] = notes_summary[chart_id]['titles']
            else:
                profile_dict['notes_count'] = 0
                profile_dict['note_titles'] = []
        
        current_app.logger.info(f"✅ Retrieved {len(profiles_data)} profiles for user ID: {user.id}")
        
        # Return JSON array directly (not wrapped in object)
        return jsonify(profiles_data), 200
        
    except Exception as e:
        # Log error for debugging
        current_app.logger.error(f"💥 Profile retrieval error: {str(e)}", exc_info=True)
        return jsonify({
            "error": {
                "message": "Failed to retrieve profiles"
            }
        }), 500


@bp.route("/profiles/<profile_id>", methods=["PATCH"])
def update_profile_endpoint(profile_id):
    """
    Update profile details for the authenticated user.
    
    Supports partial updates - only provided fields will be updated.
    
    SECURITY:
    - Requires authentication
    - Verifies profile ownership (user can only update their own profiles)
    - Returns 403 if user doesn't own profile
    - Returns 404 if profile doesn't exist
    - Returns 409 if update would create duplicate profile
    """
    # AUTHENTICATION REQUIRED - Validate session and authorization
    session_data = get_current_user()
    if isinstance(session_data, tuple):  # Error response (401)
        return session_data
    
    # Get authenticated user from Flask g context (set by get_current_user)
    from flask import g
    user = g.current_user
    
    current_app.logger.info(f"🔵 PATCH /profiles/{profile_id} - User ID: {user.id}")
    # Don't log full request data (may contain PII)
    current_app.logger.debug(f"📦 Request Length: {request.content_length or 0} bytes")
    
    try:
        # Step 1: Parse and validate request body
        payload = ProfileUpdateRequest.model_validate_json(request.data)
        sanitized_payload = sanitize_dict(payload.model_dump(exclude_none=True))
        current_app.logger.info(f"✅ Profile update validated")
        current_app.logger.debug(f"Update params: {sanitized_payload}")
    except Exception as e:
        # Log and print validation error
        print(f"❌ Request validation error: {str(e)}")
        current_app.logger.error(f"Request validation error: {str(e)}")
        return jsonify({
            "error": {
                "code": "VALIDATION_ERROR",
                "message": str(e),
                "details": {"field": "request", "value": "invalid"}
            }
        }), 400
    
    try:
        # Step 2: Update profile
        from .db import update_profile
        
        # Convert Pydantic model to dict, excluding None values
        updates = payload.model_dump(exclude_none=True)
        
        # Call update_profile function
        profile, error_response = update_profile(profile_id, user.id, updates)
        
        if error_response:
            # Return error (403, 404, 409, or 500)
            return error_response
        
        # Step 3: Return updated profile
        current_app.logger.info(f"✅ Profile updated successfully: {profile_id}")
        
        return jsonify(profile.to_dict()), 200
        
    except Exception as e:
        # Log error for debugging
        current_app.logger.error(f"💥 Profile update error: {str(e)}", exc_info=True)
        return jsonify({
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Failed to update profile",
                "details": {"error": str(e)}
            }
        }), 500


@bp.route("/profiles/<profile_id>", methods=["DELETE"])
def delete_profile_endpoint(profile_id):
    """
    Delete a profile for the authenticated user.
    
    SECURITY:
    - Requires authentication
    - Verifies profile ownership (user can only delete their own profiles)
    - Returns 403 if user doesn't own profile
    - Returns 404 if profile doesn't exist
    """
    # AUTHENTICATION REQUIRED - Validate session and authorization
    session_data = get_current_user()
    if isinstance(session_data, tuple):  # Error response (401)
        return session_data
    
    # Get authenticated user from Flask g context (set by get_current_user)
    from flask import g
    user = g.current_user
    
    current_app.logger.info(f"🔵 DELETE /profiles/{profile_id} - User ID: {user.id}")
    
    try:
        # Step 1: Delete profile
        from .db import delete_profile
        
        # Call delete_profile function
        success, error_response = delete_profile(profile_id, user.id)
        
        if error_response:
            # Return error (403, 404, or 500)
            return error_response
        
        # Step 2: Return success response
        current_app.logger.info(f"✅ Profile deleted successfully: {profile_id}")
        
        return jsonify({
            "message": "Profile deleted successfully"
        }), 200
        
    except Exception as e:
        # Log error for debugging
        current_app.logger.error(f"💥 Profile deletion error: {str(e)}", exc_info=True)
        return jsonify({
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Failed to delete profile",
                "details": {"error": str(e)}
            }
        }), 500


# ============================================================================
# Analysis Notes Endpoints
# ============================================================================

@bp.route("/profiles/<profile_id>/notes", methods=["GET"])
def get_profile_notes(profile_id):
    """
    Get all analysis notes for a profile's chart.
    
    Returns an array of AnalysisNote objects sorted by updated_at descending.
    
    SECURITY:
    - Requires authentication
    - Verifies profile ownership via user relationship
    - Returns 403 if user doesn't own the profile
    - Returns 404 if profile doesn't exist
    - Returns empty array if profile has no chart yet
    """
    # AUTHENTICATION REQUIRED - Validate session and authorization
    session_data = get_current_user()
    if isinstance(session_data, tuple):  # Error response (401)
        return session_data
    
    # Get authenticated user from Flask g context (set by get_current_user)
    from flask import g
    user = g.current_user
    
    current_app.logger.info(f"🔵 GET /profiles/{profile_id}/notes - User ID: {user.id}")
    
    try:
        from .db import get_user_profile, get_notes_for_chart
        import uuid
        
        # Step 1: Verify profile exists and user owns it
        try:
            profile_uuid = uuid.UUID(profile_id)
        except ValueError:
            return jsonify({
                "error": {
                    "code": "INVALID_ID",
                    "message": "Invalid profile ID format"
                }
            }), 400
        
        profile, error_response = get_user_profile(profile_id, user.id)
        if error_response:
            return error_response
        
        # Step 2: Get the chart for this profile
        chart = profile.chart
        
        if not chart:
            # Profile exists but no chart yet - return empty array
            current_app.logger.info(f"⚠️  Profile {profile_id} has no chart yet - returning empty notes array")
            return jsonify([]), 200
        
        current_app.logger.debug(f"Profile found with chart: profile_id={profile_id}, chart_id={chart.id}")
        
        # Step 3: Get all notes for the chart
        notes = get_notes_for_chart(chart.id)
        
        # Convert notes to dictionaries
        notes_data = [note.to_dict() for note in notes]
        
        current_app.logger.info(f"✅ Retrieved {len(notes_data)} notes for profile: {profile_id}")
        
        # Return JSON array
        return jsonify(notes_data), 200
        
    except Exception as e:
        # Log error for debugging
        current_app.logger.error(f"💥 Notes retrieval error: {str(e)}", exc_info=True)
        return jsonify({
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Failed to retrieve notes"
            }
        }), 500


@bp.route("/profiles/<profile_id>/notes", methods=["POST"])
def create_profile_note(profile_id):
    """
    Create a new analysis note for a profile's chart.
    
    Request body: {"title": "Note title", "note": "Note content"}
    
    SECURITY:
    - Requires authentication
    - Verifies profile ownership via user relationship
    - Returns 403 if user doesn't own the profile
    - Returns 404 if profile doesn't exist
    - Returns 400 if profile has no chart yet
    """
    # AUTHENTICATION REQUIRED - Validate session and authorization
    session_data = get_current_user()
    if isinstance(session_data, tuple):  # Error response (401)
        return session_data
    
    # Get authenticated user from Flask g context (set by get_current_user)
    from flask import g
    user = g.current_user
    
    current_app.logger.info(f"🔵 POST /profiles/{profile_id}/notes - User ID: {user.id}")
    # Don't log full request data (may contain PII)
    current_app.logger.debug(f"📦 Request Length: {request.content_length or 0} bytes")
    
    try:
        # Step 1: Parse and validate request body
        payload = AnalysisNoteCreate.model_validate_json(request.data)
        current_app.logger.info(f"✅ Note creation validated")
        current_app.logger.debug(f"Note title: {payload.title[:50] if len(payload.title) > 50 else payload.title}")
    except Exception as e:
        # Log and print validation error
        print(f"❌ Request validation error: {str(e)}")
        current_app.logger.error(f"Request validation error: {str(e)}")
        return jsonify({
            "error": {
                "code": "VALIDATION_ERROR",
                "message": str(e)
            }
        }), 400
    
    try:
        from .db import get_user_profile, create_note
        import uuid
        
        # Step 2: Verify profile exists and user owns it
        try:
            profile_uuid = uuid.UUID(profile_id)
        except ValueError:
            return jsonify({
                "error": {
                    "code": "INVALID_ID",
                    "message": "Invalid profile ID format"
                }
            }), 400
        
        profile, error_response = get_user_profile(profile_id, user.id)
        if error_response:
            return error_response
        
        # Step 3: Get the chart for this profile
        chart = profile.chart
        
        if not chart:
            # Profile exists but no chart yet
            current_app.logger.warning(f"❌ Profile {profile_id} has no chart - cannot create notes")
            return jsonify({
                "error": {
                    "code": "NO_CHART",
                    "message": "Profile has no chart. Calculate the chart first before adding notes."
                }
            }), 400
        
        current_app.logger.debug(f"Profile found with chart: profile_id={profile_id}, chart_id={chart.id}")
        
        # Step 4: Create the note
        new_note = create_note(
            chart_id=chart.id,
            title=payload.title,
            note=payload.note
        )
        
        current_app.logger.info(f"✅ Note created successfully: {new_note.id}")
        
        # Return created note with 201 status
        return jsonify(new_note.to_dict()), 201
        
    except Exception as e:
        # Log error for debugging
        current_app.logger.error(f"💥 Note creation error: {str(e)}", exc_info=True)
        return jsonify({
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Failed to create note"
            }
        }), 500


@bp.route("/notes/<note_id>", methods=["PATCH"])
def update_note_endpoint(note_id):
    """
    Update an existing analysis note.
    
    Supports partial updates - only provided fields will be updated.
    Request body: {"title"?: "New title", "note"?: "New content"}
    
    SECURITY:
    - Requires authentication
    - Verifies note ownership via chart → profile → user relationship
    - Returns 403 if user doesn't own the note
    - Returns 404 if note doesn't exist
    """
    # AUTHENTICATION REQUIRED - Validate session and authorization
    session_data = get_current_user()
    if isinstance(session_data, tuple):  # Error response (401)
        return session_data
    
    # Get authenticated user from Flask g context (set by get_current_user)
    from flask import g
    user = g.current_user
    
    current_app.logger.info(f"🔵 PATCH /notes/{note_id} - User ID: {user.id}")
    # Don't log full request data (may contain PII)
    current_app.logger.debug(f"📦 Request Length: {request.content_length or 0} bytes")
    
    try:
        # Step 1: Parse and validate request body
        payload = AnalysisNoteUpdate.model_validate_json(request.data)
        current_app.logger.info(f"✅ Note update validated")
        current_app.logger.debug(f"Update fields: {list(payload.model_dump(exclude_none=True).keys())}")
    except Exception as e:
        # Log and print validation error
        print(f"❌ Request validation error: {str(e)}")
        current_app.logger.error(f"Request validation error: {str(e)}")
        return jsonify({
            "error": {
                "code": "VALIDATION_ERROR",
                "message": str(e)
            }
        }), 400
    
    try:
        from .db import get_note_by_id, update_note
        import uuid
        
        # Step 2: Verify note exists
        try:
            note_uuid = uuid.UUID(note_id)
        except ValueError:
            return jsonify({
                "error": {
                    "code": "INVALID_ID",
                    "message": "Invalid note ID format"
                }
            }), 400
        
        existing_note = get_note_by_id(note_uuid)
        
        if not existing_note:
            return jsonify({
                "error": {
                    "code": "NOT_FOUND",
                    "message": "Note not found"
                }
            }), 404
        
        # Step 3: Verify ownership via chart → profile → user
        if existing_note.chart.profile.user_id != user.id:
            return jsonify({
                "error": {
                    "code": "FORBIDDEN",
                    "message": "You don't have permission to update this note"
                }
            }), 403
        
        # Step 4: Update the note
        updated_note = update_note(
            note_id=note_uuid,
            title=payload.title,
            note=payload.note
        )
        
        current_app.logger.info(f"✅ Note updated successfully: {note_id}")
        
        # Return updated note
        return jsonify(updated_note.to_dict()), 200
        
    except Exception as e:
        # Log error for debugging
        current_app.logger.error(f"💥 Note update error: {str(e)}", exc_info=True)
        return jsonify({
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Failed to update note"
            }
        }), 500


@bp.route("/notes/<note_id>", methods=["DELETE"])
def delete_note_endpoint(note_id):
    """
    Delete an analysis note.
    
    SECURITY:
    - Requires authentication
    - Verifies note ownership via chart → profile → user relationship
    - Returns 403 if user doesn't own the note
    - Returns 404 if note doesn't exist
    """
    # AUTHENTICATION REQUIRED - Validate session and authorization
    session_data = get_current_user()
    if isinstance(session_data, tuple):  # Error response (401)
        return session_data
    
    # Get authenticated user from Flask g context (set by get_current_user)
    from flask import g
    user = g.current_user
    
    current_app.logger.info(f"🔵 DELETE /notes/{note_id} - User ID: {user.id}")
    
    try:
        from .db import get_note_by_id, delete_note
        import uuid
        
        # Step 1: Verify note exists
        try:
            note_uuid = uuid.UUID(note_id)
        except ValueError:
            return jsonify({
                "error": {
                    "code": "INVALID_ID",
                    "message": "Invalid note ID format"
                }
            }), 400
        
        existing_note = get_note_by_id(note_uuid)
        
        if not existing_note:
            return jsonify({
                "error": {
                    "code": "NOT_FOUND",
                    "message": "Note not found"
                }
            }), 404
        
        # Step 2: Verify ownership via chart → profile → user
        if existing_note.chart.profile.user_id != user.id:
            return jsonify({
                "error": {
                    "code": "FORBIDDEN",
                    "message": "You don't have permission to delete this note"
                }
            }), 403
        
        # Step 3: Delete the note
        delete_note(note_uuid)
        
        current_app.logger.info(f"✅ Note deleted successfully: {note_id}")
        
        # Return 204 No Content
        return '', 204
        
    except Exception as e:
        # Log error for debugging
        current_app.logger.error(f"💥 Note deletion error: {str(e)}", exc_info=True)
        return jsonify({
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Failed to delete note"
            }
        }), 500
