import swisseph as swe
from datetime import datetime
from .constants import PLANETS, AYANAMSHA, HOUSE_CODES, SEFLAGS
from .utils import norm360, sign_index, house_from_sign

# Module-level variable to track current ayanamsha
_current_ayanamsha_key = None

def init_ephemeris(ephe_path: str, ayanamsha_key: str):
    """Initialize Swiss Ephemeris with path and ayanamsha"""
    global _current_ayanamsha_key
    swe.set_ephe_path(ephe_path)
    _current_ayanamsha_key = ayanamsha_key
    # For VEDANJANAM, use Lahiri mode internally (we'll apply offset manually)
    sid_mode = AYANAMSHA[ayanamsha_key]
    swe.set_sid_mode(sid_mode)

def julian_day_utc(dt_utc: datetime) -> float:
    """Convert UTC datetime to Julian Day"""
    ut = dt_utc.hour + dt_utc.minute/60 + dt_utc.second/3600 + dt_utc.microsecond/3.6e9
    return swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, ut)

def get_ayanamsa_value(jd_ut: float) -> float:
    """Get ayanamsha value with custom offsets applied (e.g., VEDANJANAM = Lahiri + 6 arc minutes)"""
    base_ayanamsa = swe.get_ayanamsa_ut(jd_ut)
    if _current_ayanamsha_key == "VEDANJANAM":
        # Add 6 arc minutes (0.1 degrees) to Lahiri ayanamsha
        return base_ayanamsa + 0.1
    return base_ayanamsa

def compute_planets(jd_ut: float, nodeType: str = "MEAN"):
    """
    Compute planetary positions and speeds using sidereal mode (ayanamsha set by init_ephemeris).
    
    Configuration:
    - Geocentric positions (Earth-centered, not observer-location based)
    - Apparent positions (includes light-time correction and aberration - standard for astrology)
    - Sidereal zodiac (ayanamsha-corrected)
    - Mean nodes by default (traditional Vedic astrology standard)
    
    Args:
        jd_ut: Julian Day in Universal Time
        nodeType: "MEAN" for mean node (traditional Vedic), "TRUE" for true node (oscillating)
        
    Returns:
        list: List of dictionaries with planetary data:
            - planet: Planet name
            - longitude: Sidereal longitude in degrees (0-360)
            - speed: Daily motion in degrees per day
            - retrograde: Boolean indicating retrograde motion
            
    Raises:
        ValueError: If nodeType is not "MEAN" or "TRUE"
        RuntimeError: If Swiss Ephemeris calculation fails
    """
    # Validate nodeType parameter
    if nodeType not in ["MEAN", "TRUE"]:
        raise ValueError(f"nodeType must be 'MEAN' or 'TRUE', got: {nodeType}")
    
    out = []
    
    # Calculate Rahu (North Node)
    node_body = swe.MEAN_NODE if nodeType == "MEAN" else swe.TRUE_NODE
    
    try:
        result = swe.calc_ut(jd_ut, node_body, SEFLAGS)
        # Swiss Ephemeris with FLG_SPEED returns:
        # result[0] = (longitude, latitude, distance, speed_long, speed_lat, speed_dist)
        # result[1] = return flag
        rahu_long = float(result[0][0])  # longitude in degrees
        rahu_speed = float(result[0][3])  # speed in degrees per day
        rahu_long = norm360(rahu_long)
    except Exception as e:
        raise RuntimeError(f"Failed to calculate Rahu/Ketu position: {e}")

    # Calculate all planets
    for name, body in PLANETS:
        try:
            if name == "Rahu":
                lng, spd = rahu_long, rahu_speed
                
            elif name == "Ketu":
                # Ketu is always 180° opposite to Rahu
                lng = norm360(rahu_long + 180.0)
                spd = rahu_speed  # Ketu has same speed as Rahu
                
            else:
                # Calculate regular planet
                result = swe.calc_ut(jd_ut, body, SEFLAGS)
                lng = float(result[0][0])  # longitude in degrees
                spd = float(result[0][3])  # speed in degrees per day
                lng = norm360(lng)
            
            # Apply VEDANJANAM offset if needed
            # When VEDANJANAM is used, planets are computed in Lahiri sidereal mode
            # To convert to Vedanjanam (Lahiri + 6 arc minutes), we subtract 0.1 degrees
            # because: sidereal = tropical - ayanamsha, so increasing ayanamsha by 0.1 
            # means decreasing sidereal by 0.1
            if _current_ayanamsha_key == "VEDANJANAM":
                lng = norm360(lng - 0.1)
            
            # Determine retrograde status
            # Rahu and Ketu are ALWAYS retrograde in Vedic astrology (moving backwards through zodiac)
            # Other planets are retrograde when speed < 0
            is_retrograde = spd < 0 if name not in ["Rahu", "Ketu"] else True
            
            out.append({
                "planet": name,
                "longitude": lng,
                "speed": spd,
                "retrograde": is_retrograde
            })
            
        except Exception as e:
            raise RuntimeError(f"Failed to calculate position for {name}: {e}")
    
    return out

def ascendant_and_houses(jd_ut: float, lat: float, lon: float, houseSystem: str):
    """Calculate ascendant and house cusps in sidereal mode."""
    hcode = HOUSE_CODES[houseSystem]
    
    # Use houses_ex with FLG_SIDEREAL - it handles the conversion automatically
    flags = swe.FLG_SIDEREAL | swe.FLG_SPEED | swe.FLG_TRUEPOS
    
    if hcode == "W":
        cusps, ascmc = swe.houses_ex(jd_ut, lat, lon, b'P', flags)
        asc = norm360(ascmc[0])
        if _current_ayanamsha_key == "VEDANJANAM":
            asc = norm360(asc - 0.1)
        return asc, None
    else:
        cusps, ascmc = swe.houses_ex(jd_ut, lat, lon, hcode.encode(), flags)
        asc = norm360(ascmc[0])
        cusps_list = [norm360(cusps[i]) for i in range(1, 13)]
        
        if _current_ayanamsha_key == "VEDANJANAM":
            asc = norm360(asc - 0.1)
            cusps_list = [norm360(c - 0.1) for c in cusps_list]
        
        return asc, cusps_list

def compute_whole_sign_cusps(asc_sign: int):
    """Compute whole sign house cusps"""
    return [norm360(asc_sign * 30 + i * 30) for i in range(12)]
