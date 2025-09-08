import swisseph as swe
from datetime import datetime
from .constants import PLANETS, AYANAMSHA, HOUSE_CODES, SEFLAGS
from .utils import norm360, sign_index, house_from_sign

def init_ephemeris(ephe_path: str, ayanamsha_key: str):
    """Initialize Swiss Ephemeris with path and ayanamsha"""
    swe.set_ephe_path(ephe_path)
    swe.set_sid_mode(AYANAMSHA[ayanamsha_key])

def julian_day_utc(dt_utc: datetime) -> float:
    """Convert UTC datetime to Julian Day"""
    ut = dt_utc.hour + dt_utc.minute/60 + dt_utc.second/3600 + dt_utc.microsecond/3.6e9
    return swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, ut)

def safe_extract_float(value):
    """Safely extract float value from Swiss Ephemeris result"""
    if isinstance(value, tuple):
        return safe_extract_float(value[0])
    elif isinstance(value, (list, dict)):
        return 0.0
    else:
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0

def ascendant_and_houses(jd_ut: float, lat: float, lon: float, houseSystem: str):
    """Calculate ascendant and house cusps for Vedic astrology using sidereal conversion"""
    try:
        # Calculate houses using Swiss Ephemeris
        # swe.houses() returns (cusps, ascmc) where:
        # cusps[1-12] are the house cusps (cusps[0] is unused)
        # ascmc[0] = Ascendant, ascmc[1] = MC, ascmc[2] = ARMC, ascmc[3] = Vertex
        cusps, ascmc = swe.houses(jd_ut, lat, lon, b'P')
        
        # Extract the ascendant (in tropical longitude)
        ascendant_tropical = ascmc[0]
        
        # Convert to sidereal (Vedic) using Lahiri Ayanamsa
        # Set ayanamsa to Lahiri (most commonly used in Vedic astrology)
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        ayanamsa = swe.get_ayanamsa(jd_ut)
        
        # Convert ascendant to sidereal
        ascendant_sidereal = (ascendant_tropical - ayanamsa) % 360
        
        # Handle different house systems
        hcode = HOUSE_CODES[houseSystem]
        if hcode == "W":
            # For whole sign houses, return ascendant and None for cusps
            return ascendant_sidereal, None
        else:
            # Convert house cusps to sidereal
            houses_sidereal = []
            for i in range(1, 13):  # Houses 1-12
                cusp_sidereal = (cusps[i] - ayanamsa) % 360
                houses_sidereal.append(cusp_sidereal)
            
            return ascendant_sidereal, houses_sidereal
            
    except Exception as e:
        print(f"Error calculating houses: {e}")
        # Fallback to original logic if sidereal conversion fails
        hcode = HOUSE_CODES[houseSystem]
        
        if hcode == "W":
            # Use Placidus internally just to get ASC, then replace cusps with whole sign bins.
            result = swe.houses_ex(jd_ut, lat, lon, b'P', SEFLAGS)
            if len(result) == 3:
                _, ascmc, _ = result
            else:
                ascmc = result[1]  # Handle case where only 2 values returned
            asc = norm360(safe_extract_float(ascmc[0]))  # Ascendant is at index 0
            return asc, None  # cusps computed later if asked
        else:
            result = swe.houses_ex(jd_ut, lat, lon, hcode.encode(), SEFLAGS)
            if len(result) == 3:
                cusps, ascmc, _ = result
            else:
                cusps, ascmc = result  # Handle case where only 2 values returned
            asc = norm360(safe_extract_float(ascmc[0]))  # Ascendant is at index 0
            return asc, [norm360(safe_extract_float(c)) for c in cusps[1:13]]

def compute_planets(jd_ut: float, nodeType: str):
    """Compute planetary positions and speeds"""
    out = []
    # Rahu (node)
    node_body = swe.MEAN_NODE if nodeType == "MEAN" else swe.TRUE_NODE
    # Precompute node
    result = swe.calc_ut(jd_ut, node_body, SEFLAGS)
    
    # Extract values safely - with FLG_SPEED, result[0] is tuple of 6 values:
    # (longitude, latitude, distance, speed_longitude, speed_latitude, speed_distance)
    if isinstance(result, tuple) and len(result) >= 2 and isinstance(result[0], tuple) and len(result[0]) >= 4:
        rahu_long = safe_extract_float(result[0][0])  # longitude
        rahu_speed = safe_extract_float(result[0][3])  # speed in longitude
    else:
        rahu_long = safe_extract_float(result[0]) if isinstance(result, tuple) else safe_extract_float(result)
        rahu_speed = 0.0
    
    rahu_long = norm360(rahu_long)

    for name, body in PLANETS:
        if name == "Rahu":
            lng, spd = rahu_long, rahu_speed
        elif name == "Ketu":
            lng = norm360(rahu_long + 180.0)
            spd = rahu_speed  # Ketu has same speed as Rahu
        else:
            result = swe.calc_ut(jd_ut, body, SEFLAGS)
            # With FLG_SPEED flag: result[0] is tuple of 6 values
            if isinstance(result, tuple) and len(result) >= 2 and isinstance(result[0], tuple) and len(result[0]) >= 4:
                lng = safe_extract_float(result[0][0])  # longitude
                spd = safe_extract_float(result[0][3])  # speed in longitude
            else:
                lng = safe_extract_float(result[0]) if isinstance(result, tuple) else safe_extract_float(result)
                spd = 0.0
            
            lng = norm360(lng)
            
        # Both Rahu and Ketu are always retrograde in Vedic astrology
        is_retrograde = spd < 0 if name not in ["Rahu", "Ketu"] else True
        
        out.append({
            "planet": name,
            "longitude": lng,
            "speed": spd,
            "retrograde": is_retrograde
        })
    return out

def compute_whole_sign_cusps(asc_sign: int):
    """Compute whole sign house cusps"""
    return [norm360(asc_sign * 30 + i * 30) for i in range(12)]
