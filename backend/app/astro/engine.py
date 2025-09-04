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
    """Calculate ascendant and house cusps"""
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
    
    # Extract values safely
    if isinstance(result, tuple) and len(result) >= 2:
        rahu_long = safe_extract_float(result[0])
        rahu_speed = safe_extract_float(result[3]) if len(result) >= 4 else 0.0
    else:
        rahu_long = safe_extract_float(result)
        rahu_speed = 0.0
    
    rahu_long = norm360(rahu_long)

    for name, body in PLANETS:
        if name == "Rahu":
            lng, spd = rahu_long, rahu_speed
        elif name == "Ketu":
            lng = norm360(rahu_long + 180.0)
            spd = -rahu_speed
        else:
            result = swe.calc_ut(jd_ut, body, SEFLAGS)
            if isinstance(result, tuple) and len(result) >= 2:
                lng = safe_extract_float(result[0])
                spd = safe_extract_float(result[3]) if len(result) >= 4 else 0.0
            else:
                lng = safe_extract_float(result)
                spd = 0.0
            
            lng = norm360(lng)
            
        out.append({
            "planet": name,
            "longitude": lng,
            "speed": spd,
            "retrograde": spd < 0
        })
    return out

def compute_whole_sign_cusps(asc_sign: int):
    """Compute whole sign house cusps"""
    return [norm360(asc_sign * 30 + i * 30) for i in range(12)]
