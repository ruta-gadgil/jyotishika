from flask import Blueprint, request, jsonify, current_app
from .schemas import ChartRequest, DashaRequest, ProfileUpdateRequest, AnalysisNoteCreate, AnalysisNoteUpdate
from .auth import get_current_user
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
    
    # Log and print request information
    print(f"\n🔵 API Request received - Method: {request.method}, URL: {request.url}")
    # print(f"📋 Request Headers: {dict(request.headers)}")
    print(f"📦 Request Data (raw): {request.data.decode('utf-8') if request.data else 'No data'}")
    
    current_app.logger.info(f"API Request received - Method: {request.method}, URL: {request.url}")
    current_app.logger.info(f"Request Headers: {dict(request.headers)}")
    current_app.logger.info(f"Request Data (raw): {request.data.decode('utf-8') if request.data else 'No data'}")
    
    try:
        payload = ChartRequest.model_validate_json(request.data)
        # Log and print validated payload
        print(f"✅ Validated Payload: {payload.model_dump()}")
        current_app.logger.info(f"Validated Payload: {payload.model_dump()}")
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
            print(f"🎯 Cache hit - returning cached chart for profile: {profile.id}")
            current_app.logger.info(f"Cache hit - returning cached chart for profile: {profile.id}")
            
            response_data = {
                "profile_id": str(profile.id),
                "chart_id": str(cached_chart.id),
                "profile": profile.to_dict(),
                "metadata": cached_chart.chart_metadata,
                "ascendant": cached_chart.ascendant_data,
                "planets": cached_chart.planets_data,
                "bhavChalit": cached_chart.bhav_chalit_data
            }
            
            if cached_chart.house_cusps:
                response_data["houseCusps"] = cached_chart.house_cusps
            
            return jsonify(response_data), 200
        
        # Step 3: Calculate chart (cache miss)
        print(f"💫 Cache miss - calculating chart for profile: {profile.id}")
        current_app.logger.info(f"Cache miss - calculating chart for profile: {profile.id}")
        
        dt_utc = to_utc(payload.datetime, payload.tz, payload.utcOffsetMinutes, payload.latitude, payload.longitude)
        jd_ut = julian_day_utc(dt_utc)

        # initialize (idempotent ok)
        effective_ayanamsha = payload.ayanamsha or current_app.config["AYANAMSHA"]
        effective_house_system = payload.houseSystem or current_app.config["HOUSE_SYSTEM"]
        init_ephemeris(current_app.config["EPHE_PATH"], effective_ayanamsha)

        asc_long, cusps, angles = ascendant_and_houses(jd_ut, payload.latitude, payload.longitude, effective_house_system)
        asc_sign = sign_index(asc_long)
        
        # Calculate nakshatra, charan, and navamsha for ascendant
        asc_nak_name, asc_nak_index_1, asc_charan_1to4 = get_nakshatra_and_charan(asc_long)
        asc_nav_info = get_navamsha_info(asc_long)

        planets = compute_planets(jd_ut, payload.nodeType)
        print(asc_sign, planets)

        # decorate with sign/house if requested and round for frontend
        result_planets = []
        for p in planets:
            rec = dict(p)
            # Round values for frontend display
            rec["longitude"] = round(p["longitude"], 2)  # 2 decimal places for longitude
            rec["speed"] = round(p["speed"], 4)          # 4 decimal places for speed
            
            # Always include nakshatra, charan, and navamsha details (sidereal longitudes)
            nak_name, nak_index_1, charan_1to4 = get_nakshatra_and_charan(p["longitude"])
            nav_info = get_navamsha_info(p["longitude"])  # contains sign/signIndex/ordinal/degreeInNavamsha and mapping
            rec["nakshatra"] = {"name": nak_name, "index": nak_index_1}
            rec["charan"] = charan_1to4
            rec["navamsha"] = {
                "sign": nav_info["sign"],
                "signIndex": nav_info["signIndex"],
                "ordinal": nav_info["ordinal"],
                "degreeInNavamsha": round(nav_info["degreeInNavamsha"], 4),
            }

            if payload.include.signsForEachPlanet:
                rec["signIndex"] = sign_index(p["longitude"])
            if effective_house_system == "WHOLE_SIGN" and payload.include.housesForEachPlanet:
                rec["house"] = house_from_sign(rec.get("signIndex", sign_index(p["longitude"])), asc_sign)
            elif payload.include.housesForEachPlanet and cusps:
                # For Placidus/Equal, we could call swe.house_pos for accuracy
                # For now, we'll use a simple angular separation approach
                planet_long = p["longitude"]  # Use original precision for calculations
                house_num = 1
                for i, cusp in enumerate(cusps):
                    if i < len(cusps) - 1:
                        next_cusp = cusps[i + 1]
                    else:
                        # Last house (12th house) - wrap around to first cusp + 360
                        next_cusp = cusps[0] + 360
                    
                    if cusp <= planet_long < next_cusp or (i == len(cusps) - 1 and planet_long >= cusp):
                        house_num = i + 1
                        break
                rec["house"] = house_num
            result_planets.append(rec)

        out = {
            "metadata": {
                "system": "sidereal",
                "ayanamsha": effective_ayanamsha,
                "houseSystem": effective_house_system,
                "nodeType": payload.nodeType,
                "datetimeInput": payload.datetime,
                "tzApplied": payload.tz if payload.tz else format_utc_offset(payload.utcOffsetMinutes or 0),
                "datetimeUTC": dt_utc.replace(tzinfo=None).isoformat(timespec="seconds") + "Z"
            },
            "ascendant": {
                "longitude": round(asc_long, 2),  # Round ascendant longitude for frontend
                "signIndex": asc_sign,
                "house": 1,
                "nakshatra": {"name": asc_nak_name, "index": asc_nak_index_1},
                "charan": asc_charan_1to4,
                "navamsha": {
                    "sign": asc_nav_info["sign"],
                    "signIndex": asc_nav_info["signIndex"],
                    "ordinal": asc_nav_info["ordinal"],
                    "degreeInNavamsha": round(asc_nav_info["degreeInNavamsha"], 4),
                }
            },
            "planets": result_planets
        }

        if payload.include.houseCusps:
            if effective_house_system == "WHOLE_SIGN":
                # Build whole-sign cusps from asc_sign and round for frontend
                out["houseCusps"] = [round(c, 2) for c in compute_whole_sign_cusps(asc_sign)]
            else:
                # Round house cusps for frontend
                out["houseCusps"] = [round(c, 2) for c in cusps] if cusps else None

        # Always include Bhav Chalit (Sripati Padhati) data
        # Sripati system divides the ecliptic into 4 quadrants using the four angles,
        # then trisects each quadrant to create 12 houses
        sripati_cusps = compute_sripati_cusps(
            angles["asc"], 
            angles["ic"], 
            angles["dsc"], 
            angles["mc"]
        )
        
        # Calculate planet placements in Bhav Chalit houses
        bhav_chalit_planets = []
        # print(f"🌟 Bhav Chalit Planet Placements:")
        current_app.logger.debug("Bhav Chalit Planet Placements:")
        for p in planets:
            planet_house = house_from_cusps(p["longitude"], sripati_cusps)
            bhav_chalit_planets.append({
                "planet": p["planet"],
                "house": planet_house
            })
            # print(f"   {p['planet']:10s} at {p['longitude']:6.2f}° → House {planet_house}")
            current_app.logger.debug(f"  {p['planet']:10s} at {p['longitude']:6.2f}° → House {planet_house}")
        
        out["bhavChalit"] = {
            "system": "SRIPATI",
            "ascendant": {
                "longitude": round(asc_long, 2),
                "house": 1  # Ascendant always defines house 1 in Bhav Chalit
            },
            "houseCusps": [round(c, 2) for c in sripati_cusps],  # Bhava Sandhis (house boundaries)
            "planets": bhav_chalit_planets
        }

        # Step 4: Save calculated chart to database (cache for future requests)
        chart_data = {
            "ascendant": out["ascendant"],
            "planets": out["planets"],
            "houseCusps": out.get("houseCusps"),
            "bhavChalit": out["bhavChalit"],
            "metadata": out["metadata"]
        }
        
        saved_chart = save_chart(profile.id, chart_data)
        print(f"💾 Chart saved to cache for profile: {profile.id}")
        current_app.logger.info(f"Chart saved to cache for profile: {profile.id}")
        
        # Step 5: Return chart data with profile information
        response_data = {
            "profile_id": str(profile.id),
            "chart_id": str(saved_chart.id) if saved_chart else None,
            "profile": profile.to_dict(),
            **out
        }

        # Log and print successful response
        print(f"🎉 Chart calculation successful - Response status: 200")
        current_app.logger.info(f"Chart calculation successful - Response status: 200")
        return jsonify(response_data), 200

    except Exception as e:
        # Log and print the full error for debugging
        print(f"💥 Chart calculation error: {str(e)}")
        current_app.logger.error(f"Chart calculation error: {str(e)}")
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
    
    print(f"\n🔵 GET /chart/{profile_id} - User: {user.email}")
    current_app.logger.info(f"GET /chart/{profile_id} - User: {user.email}")
    
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
            print(f"🎯 Cache hit - returning cached chart for profile: {profile.id}")
            current_app.logger.info(f"Cache hit - returning cached chart for profile: {profile.id}")
            
            response_data = {
                "profile_id": str(profile.id),
                "chart_id": str(cached_chart.id),
                "profile": profile.to_dict(),
                "metadata": cached_chart.chart_metadata,
                "ascendant": cached_chart.ascendant_data,
                "planets": cached_chart.planets_data,
                "bhavChalit": cached_chart.bhav_chalit_data
            }
            
            if cached_chart.house_cusps:
                response_data["houseCusps"] = cached_chart.house_cusps
            
            return jsonify(response_data), 200
        
        # Step 3: Chart not cached - recalculate
        print(f"💫 Cache miss - recalculating chart for profile: {profile.id}")
        current_app.logger.info(f"Cache miss - recalculating chart for profile: {profile.id}")
        
        # Convert profile data to calculation parameters
        dt_utc = to_utc(
            profile.datetime,
            profile.tz,
            profile.utc_offset_minutes,
            profile.latitude,
            profile.longitude
        )
        jd_ut = julian_day_utc(dt_utc)
        
        # Initialize ephemeris
        init_ephemeris(current_app.config["EPHE_PATH"], profile.ayanamsha)
        
        # Calculate ascendant and houses
        asc_long, cusps, angles = ascendant_and_houses(
            jd_ut,
            profile.latitude,
            profile.longitude,
            profile.house_system
        )
        asc_sign = sign_index(asc_long)
        
        # Calculate nakshatra, charan, and navamsha for ascendant
        asc_nak_name, asc_nak_index_1, asc_charan_1to4 = get_nakshatra_and_charan(asc_long)
        asc_nav_info = get_navamsha_info(asc_long)
        
        # Calculate planets
        planets = compute_planets(jd_ut, profile.node_type)
        
        # Decorate planets with additional data
        result_planets = []
        for p in planets:
            rec = dict(p)
            rec["longitude"] = round(p["longitude"], 2)
            rec["speed"] = round(p["speed"], 4)
            
            nak_name, nak_index_1, charan_1to4 = get_nakshatra_and_charan(p["longitude"])
            nav_info = get_navamsha_info(p["longitude"])
            rec["nakshatra"] = {"name": nak_name, "index": nak_index_1}
            rec["charan"] = charan_1to4
            rec["navamsha"] = {
                "sign": nav_info["sign"],
                "signIndex": nav_info["signIndex"],
                "ordinal": nav_info["ordinal"],
                "degreeInNavamsha": round(nav_info["degreeInNavamsha"], 4),
            }
            
            rec["signIndex"] = sign_index(p["longitude"])
            if profile.house_system == "WHOLE_SIGN":
                rec["house"] = house_from_sign(rec["signIndex"], asc_sign)
            elif cusps:
                planet_long = p["longitude"]
                house_num = 1
                for i, cusp in enumerate(cusps):
                    if i < len(cusps) - 1:
                        next_cusp = cusps[i + 1]
                    else:
                        next_cusp = cusps[0] + 360
                    
                    if cusp <= planet_long < next_cusp or (i == len(cusps) - 1 and planet_long >= cusp):
                        house_num = i + 1
                        break
                rec["house"] = house_num
            
            result_planets.append(rec)
        
        # Calculate Bhav Chalit
        sripati_cusps = compute_sripati_cusps(
            angles["asc"],
            angles["ic"],
            angles["dsc"],
            angles["mc"]
        )
        
        bhav_chalit_planets = []
        for p in planets:
            planet_house = house_from_cusps(p["longitude"], sripati_cusps)
            bhav_chalit_planets.append({
                "planet": p["planet"],
                "house": planet_house
            })
        
        # Build response
        ascendant_data = {
            "longitude": round(asc_long, 2),
            "signIndex": asc_sign,
            "house": 1,
            "nakshatra": {"name": asc_nak_name, "index": asc_nak_index_1},
            "charan": asc_charan_1to4,
            "navamsha": {
                "sign": asc_nav_info["sign"],
                "signIndex": asc_nav_info["signIndex"],
                "ordinal": asc_nav_info["ordinal"],
                "degreeInNavamsha": round(asc_nav_info["degreeInNavamsha"], 4),
            }
        }
        
        bhav_chalit_data = {
            "system": "SRIPATI",
            "ascendant": {
                "longitude": round(asc_long, 2),
                "house": 1
            },
            "houseCusps": [round(c, 2) for c in sripati_cusps],
            "planets": bhav_chalit_planets
        }
        
        house_cusps_data = None
        if profile.house_system == "WHOLE_SIGN":
            house_cusps_data = [round(c, 2) for c in compute_whole_sign_cusps(asc_sign)]
        elif cusps:
            house_cusps_data = [round(c, 2) for c in cusps]
        
        metadata = {
            "system": "sidereal",
            "ayanamsha": profile.ayanamsha,
            "houseSystem": profile.house_system,
            "nodeType": profile.node_type,
            "datetimeInput": profile.datetime,
            "tzApplied": profile.tz if profile.tz else format_utc_offset(profile.utc_offset_minutes or 0),
            "datetimeUTC": dt_utc.replace(tzinfo=None).isoformat(timespec="seconds") + "Z"
        }
        
        # Save to cache
        chart_data = {
            "ascendant": ascendant_data,
            "planets": result_planets,
            "houseCusps": house_cusps_data,
            "bhavChalit": bhav_chalit_data,
            "metadata": metadata
        }
        
        saved_chart = save_chart(profile.id, chart_data)
        print(f"💾 Chart recalculated and saved to cache for profile: {profile.id}")
        current_app.logger.info(f"Chart recalculated and saved to cache for profile: {profile.id}")
        
        # Return response
        response_data = {
            "profile_id": str(profile.id),
            "chart_id": str(saved_chart.id) if saved_chart else None,
            "profile": profile.to_dict(),
            "metadata": metadata,
            "ascendant": ascendant_data,
            "planets": result_planets,
            "bhavChalit": bhav_chalit_data
        }
        
        if house_cusps_data:
            response_data["houseCusps"] = house_cusps_data
        
        print(f"🎉 Chart retrieval successful - Response status: 200")
        current_app.logger.info(f"Chart retrieval successful - Response status: 200")
        return jsonify(response_data), 200
        
    except Exception as e:
        print(f"💥 Chart retrieval error: {str(e)}")
        current_app.logger.error(f"Chart retrieval error: {str(e)}")
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
    
    # Log and print request information
    print(f"\n🔵 Dasha API Request received - Method: {request.method}, URL: {request.url}")
    print(f"📦 Request Data (raw): {request.data.decode('utf-8') if request.data else 'No data'}")
    
    current_app.logger.info(f"Dasha API Request received - Method: {request.method}, URL: {request.url}")
    current_app.logger.info(f"Request Headers: {dict(request.headers)}")
    current_app.logger.info(f"Request Data (raw): {request.data.decode('utf-8') if request.data else 'No data'}")
    
    try:
        payload = DashaRequest.model_validate_json(request.data)
        # Log and print validated payload
        print(f"✅ Validated Dasha Payload: {payload.model_dump()}")
        current_app.logger.info(f"Validated Dasha Payload: {payload.model_dump()}")
    except Exception as e:
        # Log and print validation error
        print(f"❌ Dasha request validation error: {str(e)}")
        current_app.logger.error(f"Dasha request validation error: {str(e)}")
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
        
        # Log and print successful response
        print(f"🎉 Dasha calculation successful - Response status: 200")
        current_app.logger.info(f"Dasha calculation successful - Response status: 200")
        return jsonify(result), 200
        
    except Exception as e:
        # Log and print the full error for debugging
        print(f"💥 Dasha calculation error: {str(e)}")
        current_app.logger.error(f"Dasha calculation error: {str(e)}")
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
    
    print(f"\n🔵 GET /profiles - User: {user.email}")
    current_app.logger.info(f"GET /profiles - User: {user.email}")
    
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
        
        print(f"✅ Retrieved {len(profiles_data)} profiles for user: {user.email}")
        current_app.logger.info(f"Retrieved {len(profiles_data)} profiles for user: {user.email}")
        
        # Return JSON array directly (not wrapped in object)
        return jsonify(profiles_data), 200
        
    except Exception as e:
        # Log and print the full error for debugging
        print(f"💥 Profile retrieval error: {str(e)}")
        current_app.logger.error(f"Profile retrieval error: {str(e)}")
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
    
    print(f"\n🔵 PATCH /profiles/{profile_id} - User: {user.email}")
    current_app.logger.info(f"PATCH /profiles/{profile_id} - User: {user.email}")
    
    # Log and print request information
    print(f"📦 Request Data (raw): {request.data.decode('utf-8') if request.data else 'No data'}")
    current_app.logger.info(f"Request Data (raw): {request.data.decode('utf-8') if request.data else 'No data'}")
    
    try:
        # Step 1: Parse and validate request body
        payload = ProfileUpdateRequest.model_validate_json(request.data)
        print(f"✅ Validated Payload: {payload.model_dump(exclude_none=True)}")
        current_app.logger.info(f"Validated Payload: {payload.model_dump(exclude_none=True)}")
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
        print(f"✅ Profile updated successfully: {profile_id}")
        current_app.logger.info(f"Profile updated successfully: {profile_id}")
        
        return jsonify(profile.to_dict()), 200
        
    except Exception as e:
        # Log and print the full error for debugging
        print(f"💥 Profile update error: {str(e)}")
        current_app.logger.error(f"Profile update error: {str(e)}")
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
    
    print(f"\n🔵 DELETE /profiles/{profile_id} - User: {user.email}")
    current_app.logger.info(f"DELETE /profiles/{profile_id} - User: {user.email}")
    
    try:
        # Step 1: Delete profile
        from .db import delete_profile
        
        # Call delete_profile function
        success, error_response = delete_profile(profile_id, user.id)
        
        if error_response:
            # Return error (403, 404, or 500)
            return error_response
        
        # Step 2: Return success response
        print(f"✅ Profile deleted successfully: {profile_id}")
        current_app.logger.info(f"Profile deleted successfully: {profile_id}")
        
        return jsonify({
            "message": "Profile deleted successfully"
        }), 200
        
    except Exception as e:
        # Log and print the full error for debugging
        print(f"💥 Profile deletion error: {str(e)}")
        current_app.logger.error(f"Profile deletion error: {str(e)}")
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
    
    print(f"\n🔵 GET /profiles/{profile_id}/notes - User: {user.email}")
    current_app.logger.info(f"GET /profiles/{profile_id}/notes - User: {user.email}")
    
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
            print(f"⚠️  Profile {profile_id} has no chart yet - returning empty notes array")
            current_app.logger.info(f"Profile {profile_id} has no chart yet")
            return jsonify([]), 200
        
        print(f"✅ Profile found with chart: profile_id={profile_id}, chart_id={chart.id}")
        current_app.logger.info(f"Profile {profile_id} has chart {chart.id}")
        
        # Step 3: Get all notes for the chart
        notes = get_notes_for_chart(chart.id)
        
        # Convert notes to dictionaries
        notes_data = [note.to_dict() for note in notes]
        
        print(f"✅ Retrieved {len(notes_data)} notes for profile: {profile_id}")
        current_app.logger.info(f"Retrieved {len(notes_data)} notes for profile: {profile_id}")
        
        # Return JSON array
        return jsonify(notes_data), 200
        
    except Exception as e:
        # Log and print the full error for debugging
        print(f"💥 Notes retrieval error: {str(e)}")
        current_app.logger.error(f"Notes retrieval error: {str(e)}")
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
    
    print(f"\n🔵 POST /profiles/{profile_id}/notes - User: {user.email}")
    current_app.logger.info(f"POST /profiles/{profile_id}/notes - User: {user.email}")
    
    # Log request data
    print(f"📦 Request Data (raw): {request.data.decode('utf-8') if request.data else 'No data'}")
    current_app.logger.info(f"Request Data (raw): {request.data.decode('utf-8') if request.data else 'No data'}")
    
    try:
        # Step 1: Parse and validate request body
        payload = AnalysisNoteCreate.model_validate_json(request.data)
        print(f"✅ Validated Payload: {payload.model_dump()}")
        current_app.logger.info(f"Validated Payload: {payload.model_dump()}")
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
            print(f"❌ Profile {profile_id} has no chart - cannot create notes")
            current_app.logger.error(f"Profile {profile_id} has no chart")
            return jsonify({
                "error": {
                    "code": "NO_CHART",
                    "message": "Profile has no chart. Calculate the chart first before adding notes."
                }
            }), 400
        
        print(f"✅ Profile found with chart: profile_id={profile_id}, chart_id={chart.id}")
        current_app.logger.info(f"Creating note for profile {profile_id}, chart {chart.id}")
        
        # Step 4: Create the note
        new_note = create_note(
            chart_id=chart.id,
            title=payload.title,
            note=payload.note
        )
        
        print(f"✅ Note created successfully: {new_note.id}")
        current_app.logger.info(f"Note created successfully: {new_note.id}")
        
        # Return created note with 201 status
        return jsonify(new_note.to_dict()), 201
        
    except Exception as e:
        # Log and print the full error for debugging
        print(f"💥 Note creation error: {str(e)}")
        current_app.logger.error(f"Note creation error: {str(e)}")
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
    
    print(f"\n🔵 PATCH /notes/{note_id} - User: {user.email}")
    current_app.logger.info(f"PATCH /notes/{note_id} - User: {user.email}")
    
    # Log request data
    print(f"📦 Request Data (raw): {request.data.decode('utf-8') if request.data else 'No data'}")
    current_app.logger.info(f"Request Data (raw): {request.data.decode('utf-8') if request.data else 'No data'}")
    
    try:
        # Step 1: Parse and validate request body
        payload = AnalysisNoteUpdate.model_validate_json(request.data)
        print(f"✅ Validated Payload: {payload.model_dump(exclude_none=True)}")
        current_app.logger.info(f"Validated Payload: {payload.model_dump(exclude_none=True)}")
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
        
        print(f"✅ Note updated successfully: {note_id}")
        current_app.logger.info(f"Note updated successfully: {note_id}")
        
        # Return updated note
        return jsonify(updated_note.to_dict()), 200
        
    except Exception as e:
        # Log and print the full error for debugging
        print(f"💥 Note update error: {str(e)}")
        current_app.logger.error(f"Note update error: {str(e)}")
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
    
    print(f"\n🔵 DELETE /notes/{note_id} - User: {user.email}")
    current_app.logger.info(f"DELETE /notes/{note_id} - User: {user.email}")
    
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
        
        print(f"✅ Note deleted successfully: {note_id}")
        current_app.logger.info(f"Note deleted successfully: {note_id}")
        
        # Return 204 No Content
        return '', 204
        
    except Exception as e:
        # Log and print the full error for debugging
        print(f"💥 Note deletion error: {str(e)}")
        current_app.logger.error(f"Note deletion error: {str(e)}")
        return jsonify({
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Failed to delete note"
            }
        }), 500
