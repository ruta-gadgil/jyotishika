from flask import Blueprint, request, jsonify, current_app
from .schemas import ChartRequest
from .astro.engine import init_ephemeris, julian_day_utc, ascendant_and_houses, compute_planets, compute_whole_sign_cusps
from .astro.utils import to_utc, sign_index, house_from_sign, norm360, format_utc_offset
import logging

bp = Blueprint("api", __name__)

@bp.route("/chart", methods=["POST"])
def chart():
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
        dt_utc = to_utc(payload.datetime, payload.tz, payload.utcOffsetMinutes)
        jd_ut = julian_day_utc(dt_utc)

        # initialize (idempotent ok)
        init_ephemeris(current_app.config["EPHE_PATH"], payload.ayanamsha)

        asc_long, cusps = ascendant_and_houses(jd_ut, payload.latitude, payload.longitude, payload.houseSystem)
        asc_sign = sign_index(asc_long)

        planets = compute_planets(jd_ut, payload.nodeType)

        # decorate with sign/house if requested
        result_planets = []
        for p in planets:
            rec = dict(p)
            if payload.include.signsForEachPlanet:
                rec["signIndex"] = sign_index(p["longitude"])
            if payload.houseSystem == "WHOLE_SIGN" and payload.include.housesForEachPlanet:
                rec["house"] = house_from_sign(rec.get("signIndex", sign_index(p["longitude"])), asc_sign)
            elif payload.include.housesForEachPlanet and cusps:
                # For Placidus/Equal, we could call swe.house_pos for accuracy
                # For now, we'll use a simple angular separation approach
                planet_long = p["longitude"]
                house_num = 1
                for i, cusp in enumerate(cusps):
                    next_cusp = cusps[(i + 1) % 12] if i < 11 else cusps[0] + 360
                    if cusp <= planet_long < next_cusp or (i == 11 and planet_long >= cusp):
                        house_num = i + 1
                        break
                rec["house"] = house_num
            result_planets.append(rec)

        out = {
            "metadata": {
                "system": "sidereal",
                "ayanamsha": payload.ayanamsha,
                "houseSystem": payload.houseSystem,
                "nodeType": payload.nodeType,
                "datetimeInput": payload.datetime,
                "tzApplied": payload.tz if payload.tz else format_utc_offset(payload.utcOffsetMinutes or 0),
                "datetimeUTC": dt_utc.replace(tzinfo=None).isoformat(timespec="seconds") + "Z"
            },
            "ascendant": {
                "longitude": asc_long,
                "signIndex": asc_sign,
                "house": 1
            },
            "planets": result_planets
        }

        if payload.include.houseCusps:
            if payload.houseSystem == "WHOLE_SIGN":
                # Build whole-sign cusps from asc_sign
                out["houseCusps"] = compute_whole_sign_cusps(asc_sign)
            else:
                out["houseCusps"] = cusps

        # Log and print successful response
        print(f"🎉 Chart calculation successful - Response status: 200")
        current_app.logger.info(f"Chart calculation successful - Response status: 200")
        return jsonify(out), 200

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
