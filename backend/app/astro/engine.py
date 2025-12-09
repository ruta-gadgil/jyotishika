import swisseph as swe
from datetime import datetime
import logging
from .constants import PLANETS, AYANAMSHA, HOUSE_CODES, SEFLAGS
from .utils import norm360, sign_index, house_from_sign

# Module-level logger
logger = logging.getLogger(__name__)

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
    """
    Calculate ascendant, house cusps, and the four angles in sidereal mode.
    
    Returns:
        tuple: (asc_long, cusps_list, angles_dict)
            - asc_long: Ascendant longitude in degrees
            - cusps_list: List of 12 house cusps (or None for WHOLE_SIGN)
            - angles_dict: Dictionary with keys 'asc', 'mc', 'ic', 'dsc'
    """
    hcode = HOUSE_CODES[houseSystem]
    
    # Use houses_ex with FLG_SIDEREAL - it handles the conversion automatically
    flags = swe.FLG_SIDEREAL | swe.FLG_SPEED | swe.FLG_TRUEPOS
    
    if hcode == "W":
        # For WHOLE_SIGN, we use Placidus to get the angles, but don't use its cusps
        cusps, ascmc = swe.houses_ex(jd_ut, lat, lon, b'P', flags)
        asc = norm360(ascmc[0])
        mc = norm360(ascmc[1])
        # IC and DSC are calculated as opposites
        ic = norm360(mc + 180.0)
        dsc = norm360(asc + 180.0)
        
        if _current_ayanamsha_key == "VEDANJANAM":
            asc = norm360(asc - 0.1)
            mc = norm360(mc - 0.1)
            ic = norm360(ic - 0.1)
            dsc = norm360(dsc - 0.1)
        
        angles = {"asc": asc, "mc": mc, "ic": ic, "dsc": dsc}
        # print(f"📐 Angles calculated: ASC={asc:.2f}°, MC={mc:.2f}°, IC={ic:.2f}°, DSC={dsc:.2f}°")
        logger.debug(f"Angles calculated: ASC={asc:.2f}°, MC={mc:.2f}°, IC={ic:.2f}°, DSC={dsc:.2f}°")
        return asc, None, angles
    else:
        cusps, ascmc = swe.houses_ex(jd_ut, lat, lon, hcode.encode(), flags)
        asc = norm360(ascmc[0])
        mc = norm360(ascmc[1])
        # IC and DSC are calculated as opposites
        ic = norm360(mc + 180.0)
        dsc = norm360(asc + 180.0)
        # Swiss Ephemeris returns cusps as a tuple with 12 elements (0-11)
        cusps_list = [norm360(cusps[i]) for i in range(12)]
        
        if _current_ayanamsha_key == "VEDANJANAM":
            asc = norm360(asc - 0.1)
            mc = norm360(mc - 0.1)
            ic = norm360(ic - 0.1)
            dsc = norm360(dsc - 0.1)
            cusps_list = [norm360(c - 0.1) for c in cusps_list]
        
        angles = {"asc": asc, "mc": mc, "ic": ic, "dsc": dsc}
        logger.debug(f"Angles calculated: ASC={asc:.2f}°, MC={mc:.2f}°, IC={ic:.2f}°, DSC={dsc:.2f}°")
        return asc, cusps_list, angles

def compute_whole_sign_cusps(asc_sign: int):
    """Compute whole sign house cusps"""
    return [norm360(asc_sign * 30 + i * 30) for i in range(12)]

def compute_sripati_cusps(asc: float, ic: float, dsc: float, mc: float):
    """
    Compute Bhav Chalit (Sripati) house cusps using Bhava Madhyas and Sandhis.
    
    In Bhav Chalit (Sripati Padhati), the system works as follows:
    
    1. **Bhava Madhyas** (house centers/midpoints - strongest points):
       - ASC (Ascendant): Madhya of house 1
       - IC (Imum Coeli): Madhya of house 4
       - DSC (Descendant): Madhya of house 7
       - MC (Medium Coeli/Midheaven): Madhya of house 10
    
    2. **Bhava Sandhis** (house boundaries/junctions - weakest points):
       - Calculated as midpoints between consecutive Bhava Madhyas
       - These are the actual cusps/boundaries between houses
    
    The calculation process:
    a) Divide the ecliptic into 4 quadrants using the angles
    b) Trisect each quadrant to get 12 Bhava Madhyas
    c) Calculate Bhava Sandhis as midpoints between consecutive Madhyas
    d) Return Sandhis as cusps (planets assigned based on which Sandhis they fall between)
    
    Quadrants and their houses:
    - Quadrant 1: ASC → IC (houses 1, 2, 3)
    - Quadrant 2: IC → DSC (houses 4, 5, 6)
    - Quadrant 3: DSC → MC (houses 7, 8, 9)
    - Quadrant 4: MC → ASC (houses 10, 11, 12)
    
    Args:
        asc: Ascendant longitude (Madhya of house 1) in degrees (0-360)
        ic: Imum Coeli longitude (Madhya of house 4) in degrees (0-360)
        dsc: Descendant longitude (Madhya of house 7) in degrees (0-360)
        mc: Midheaven longitude (Madhya of house 10) in degrees (0-360)
        
    Returns:
        list: 12 Bhava Sandhis (house boundaries) in degrees, starting from Sandhi 1/2
              Note: Sandhi N marks the boundary between house N and house N+1
    """
    # Step 1: Calculate all 12 Bhava Madhyas (house centers)
    madhyas = []
    
    quadrants = [
        (asc, ic, [1, 2, 3]),    # Quadrant 1: ASC → IC
        (ic, dsc, [4, 5, 6]),    # Quadrant 2: IC → DSC
        (dsc, mc, [7, 8, 9]),    # Quadrant 3: DSC → MC
        (mc, asc, [10, 11, 12])  # Quadrant 4: MC → ASC (wraps around 360°)
    ]
    
    for start_madhya, end_madhya, houses in quadrants:
        # Calculate the arc length between madhyas, handling wraparound at 360°
        if end_madhya >= start_madhya:
            arc = end_madhya - start_madhya
        else:
            arc = (360 - start_madhya) + end_madhya
        
        # Trisect the quadrant - each house gets 1/3 of the arc
        house_span = arc / 3.0
        
        for i, house_num in enumerate(houses):
            if i == 0:
                # First house: madhya is the starting angle
                house_madhya = start_madhya
            else:
                # Subsequent houses: offset madhya by house_span increments
                house_madhya = norm360(start_madhya + i * house_span)
            
            madhyas.append((house_num, house_madhya))
    
    # Sort by house number
    madhyas.sort(key=lambda x: x[0])
    madhya_list = [m[1] for m in madhyas]
    
    # Step 2: Calculate Bhava Sandhis (boundaries) as midpoints between consecutive Madhyas
    sandhis = []
    for i in range(12):
        madhya_current = madhya_list[i]
        madhya_next = madhya_list[(i + 1) % 12]
        
        # Calculate midpoint between consecutive madhyas
        if madhya_next >= madhya_current:
            arc = madhya_next - madhya_current
            sandhi = norm360(madhya_current + arc / 2.0)
        else:
            arc = (360 - madhya_current) + madhya_next
            sandhi = norm360(madhya_current + arc / 2.0)
        
        sandhis.append(sandhi)
    
    
    logger.debug("Bhav Chalit (Sripati) calculated:")
    logger.debug("Bhava Madhyas (house centers):")
    for i, madhya in enumerate(madhya_list, 1):
        logger.debug(f"  House {i:2d} Madhya: {madhya:6.2f}°")
    logger.debug("Bhava Sandhis (house boundaries/cusps):")
    for i, sandhi in enumerate(sandhis, 1):
        next_house = (i % 12) + 1
        logger.debug(f"  Sandhi {i:2d}/{next_house:2d}: {sandhi:6.2f}°")
    
    return sandhis
