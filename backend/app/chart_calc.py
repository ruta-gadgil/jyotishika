"""
Chart calculation logic extracted for reuse.

Used by:
- routes.py: when user requests a chart
- db.py: when update_profile needs to recalculate chart due to profile changes
"""

from flask import current_app
from .astro.engine import (
    init_ephemeris,
    julian_day_utc,
    ascendant_and_houses,
    compute_planets,
    compute_whole_sign_cusps,
    compute_sripati_cusps,
)
from .astro.utils import (
    to_utc,
    sign_index,
    house_from_sign,
    house_from_cusps,
    format_utc_offset,
    get_nakshatra_and_charan,
    get_navamsha_info,
)
from .astro.constants import PLANET_MEAN_SPEEDS, STATIONARY_THRESHOLDS, COMBUSTION_THRESHOLDS


def calculate_chart_for_profile(profile):
    """
    Calculate chart data for a given profile.
    
    Args:
        profile: Profile model instance with birth details and chart settings
        
    Returns:
        dict: Chart data with keys: ascendant, planets, houseCusps, bhavChalit, metadata
        
    Raises:
        Exception: If chart calculation fails
        
    NOTES:
    - Initializes ephemeris with profile's ayanamsha
    - Calculates ascendant, planets, houses, bhav chalit
    - Returns data structure ready for save_chart()
    """
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

    # Extract Sun's longitude once for combustion calculations
    sun_longitude = next((p["longitude"] for p in planets if p["planet"] == "Sun"), None)

    # Decorate planets with additional data (mirror /chart POST logic)
    result_planets = []
    for p in planets:
        rec = dict(p)

        # Round core kinematics
        rec["longitude"] = round(p["longitude"], 2)
        rec["speed"] = round(p["speed"], 4)
        if "latitude" in p:
            rec["latitude"] = round(p["latitude"], 4)

        # prevSpeed is internal-only; keep for derived metrics, then drop
        prev_speed = rec.pop("prevSpeed", None)

        # Derived motion metrics
        mean_speed = PLANET_MEAN_SPEEDS.get(p["planet"])
        if mean_speed is not None:
            rec["meanSpeed"] = round(mean_speed, 4)

        if prev_speed is not None:
            acceleration = p["speed"] - prev_speed
            rec["acceleration"] = round(acceleration, 6)
            rec["isAccelerating"] = abs(p["speed"]) > abs(prev_speed)

        threshold = STATIONARY_THRESHOLDS.get(p["planet"])
        if threshold is not None:
            rec["isStationary"] = abs(p["speed"]) <= threshold
        else:
            rec["isStationary"] = False

        # Combustion metrics relative to Sun
        combust_thresholds = COMBUSTION_THRESHOLDS.get(p["planet"])
        if combust_thresholds is not None and sun_longitude is not None and p["planet"] != "Sun":
            diff = abs(p["longitude"] - sun_longitude)
            sun_distance = round(min(diff, 360.0 - diff), 4)
            direction = "retrograde" if p["retrograde"] else "direct"
            rec["sunDistance"] = sun_distance
            rec["isCombust"] = sun_distance <= combust_thresholds[direction]
        else:
            rec["sunDistance"] = None
            rec["isCombust"] = False

        # Always include nakshatra, charan, and navamsha details (sidereal longitudes)
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

        # Sign and house placement
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
    
    # Build chart data structures
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
    
    # Return chart data dict ready for save_chart()
    chart_data = {
        "ascendant": ascendant_data,
        "planets": result_planets,
        "houseCusps": house_cusps_data,
        "bhavChalit": bhav_chalit_data,
        "metadata": metadata
    }
    
    return chart_data
