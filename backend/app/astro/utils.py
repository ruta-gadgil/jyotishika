from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from typing import Optional, Tuple, Dict
import pytz
from timezonefinder import TimezoneFinder

# Vedic astrology constants
from .constants import (
    NAKSHATRA_NAMES,
    NAKSHATRA_SPAN_DEG,
    PADA_SPAN_DEG,
    ZODIAC_SIGNS,
    FIRE_SIGNS,
    EARTH_SIGNS,
    AIR_SIGNS,
    WATER_SIGNS,
)

# Initialize timezone finder (expensive operation, so do it once)
_tf = TimezoneFinder()

def detect_timezone_from_coordinates(latitude: float, longitude: float) -> str:
    """Detect timezone from latitude and longitude coordinates using timezonefinder library"""
    try:
        # Use timezonefinder for accurate timezone detection
        detected_tz = _tf.timezone_at(lat=latitude, lng=longitude)
        
        if detected_tz is not None:
            return detected_tz
        
        # Fallback to simple detection for edge cases
        return _fallback_timezone_detection(latitude, longitude)
        
    except Exception as e:
        # If timezonefinder fails, use fallback
        print(f"Warning: timezonefinder failed ({e}), using fallback detection")
        return _fallback_timezone_detection(latitude, longitude)

def _fallback_timezone_detection(latitude: float, longitude: float) -> str:
    """Fallback timezone detection for edge cases or when timezonefinder fails"""
    # Simple timezone detection based on longitude
    # This is a basic implementation - for production, consider using a more sophisticated library
    
    # India: roughly 68°E to 97°E, latitude 6°N to 37°N
    if 6 <= latitude <= 37 and 68 <= longitude <= 97:
        return "Asia/Kolkata"
    
    # US Eastern: roughly 24°N to 49°N, longitude 66°W to 84°W
    elif 24 <= latitude <= 49 and -84 <= longitude <= -66:
        return "America/New_York"
    
    # US Central: roughly 25°N to 49°N, longitude 84°W to 106°W
    elif 25 <= latitude <= 49 and -106 <= longitude <= -84:
        return "America/Chicago"
    
    # US Mountain: roughly 31°N to 49°N, longitude 102°W to 114°W
    elif 31 <= latitude <= 49 and -114 <= longitude <= -102:
        return "America/Denver"
    
    # US Pacific: roughly 32°N to 49°N, longitude 114°W to 125°W
    elif 32 <= latitude <= 49 and -125 <= longitude <= -114:
        return "America/Los_Angeles"
    
    # UK: roughly 50°N to 60°N, longitude 8°W to 2°E
    elif 50 <= latitude <= 60 and -8 <= longitude <= 2:
        return "Europe/London"
    
    # Australia Eastern: roughly 10°S to 43°S, longitude 113°E to 153°E
    elif -43 <= latitude <= -10 and 113 <= longitude <= 153:
        return "Australia/Sydney"
    
    # Default to UTC if no specific timezone detected
    return "UTC"

def to_utc(dt_iso: str, tz: Optional[str], offset_minutes: Optional[int], latitude: Optional[float] = None, longitude: Optional[float] = None) -> datetime:
    """Convert ISO datetime string to UTC datetime, treating input as local time"""
    naive = datetime.fromisoformat(dt_iso)
    
    # If timezone is explicitly provided, use it
    if tz:
        tz_obj = pytz.timezone(tz)
        return tz_obj.localize(naive).astimezone(pytz.UTC)
    
    # If offset is explicitly provided, use it
    if offset_minutes is not None:
        return naive.replace(tzinfo=timezone(timedelta(minutes=offset_minutes))).astimezone(timezone.utc)
    
    # If coordinates are provided, detect timezone automatically
    if latitude is not None and longitude is not None:
        detected_tz = detect_timezone_from_coordinates(latitude, longitude)
        tz_obj = pytz.timezone(detected_tz)
        return tz_obj.localize(naive).astimezone(pytz.UTC)
    
    # Default: treat as UTC (fallback)
    return naive.replace(tzinfo=timezone.utc)

def norm360(x: float) -> float:
    """Normalize longitude to [0, 360) range"""
    return x % 360.0

def sign_index(longitude: float) -> int:
    """Get zodiac sign index (0-11) from longitude"""
    return int(longitude // 30.0)

def house_from_sign(planet_sign: int, asc_sign: int) -> int:
    """Calculate house number for whole sign system"""
    return ((planet_sign - asc_sign + 12) % 12) + 1

def format_utc_offset(offset_minutes: int) -> str:
    """Format UTC offset as string"""
    hours = abs(offset_minutes) // 60
    minutes = abs(offset_minutes) % 60
    sign = "+" if offset_minutes >= 0 else "-"
    return f"UTC{sign}{hours:02d}:{minutes:02d}"


# ------------------------- Vedic computations -------------------------

def get_nakshatra_and_pada(longitude_sidereal: float) -> Tuple[str, int, int]:
    """Return (nakshatra_name, nakshatra_index_1based, pada_1to4) from sidereal longitude.

    longitude_sidereal: degrees in [0, 360)
    """
    # Normalize explicitly to avoid negatives
    lon = longitude_sidereal % 360.0
    nak_index_0 = int(lon // NAKSHATRA_SPAN_DEG)  # 0..26
    within_nak = lon - nak_index_0 * NAKSHATRA_SPAN_DEG
    pada_1to4 = int(within_nak // PADA_SPAN_DEG) + 1  # 1..4
    return NAKSHATRA_NAMES[nak_index_0], nak_index_0 + 1, pada_1to4


def _navamsha_start_sign_index_for_element(sign_index_0: int) -> int:
    """Return starting navamsha sign index for a base sign's element.

    - Fire (Aries, Leo, Sagittarius): Aries (0)
    - Earth (Taurus, Virgo, Capricorn): Capricorn (9)
    - Air (Gemini, Libra, Aquarius): Libra (6)
    - Water (Cancer, Scorpio, Pisces): Cancer (3)
    """
    if sign_index_0 in FIRE_SIGNS:
        return 0  # Aries
    if sign_index_0 in EARTH_SIGNS:
        return 9  # Capricorn
    if sign_index_0 in AIR_SIGNS:
        return 6  # Libra
    # Water
    return 3  # Cancer


def get_navamsha_info(longitude_sidereal: float) -> Dict[str, object]:
    """Compute navamsha sign and related info from sidereal longitude.

    Returns dict with keys:
      - signIndex: 0..11
      - sign: sign name
      - ordinal: 1..9 (navamsha number within the sign)
      - degreeInNavamsha: float degrees [0, 3.3333..)
    """
    lon = longitude_sidereal % 360.0
    base_sign_index = int(lon // 30.0)
    deg_in_sign = lon - base_sign_index * 30.0
    nav_span = 30.0 / 9.0  # 3°20'
    ordinal_1to9 = int(deg_in_sign // nav_span) + 1
    degree_in_navamsha = deg_in_sign - (ordinal_1to9 - 1) * nav_span

    # Determine navamsha sign by element rule
    start_sign = _navamsha_start_sign_index_for_element(base_sign_index)
    nav_sign_index = (start_sign + (ordinal_1to9 - 1)) % 12
    nav_sign_name = ZODIAC_SIGNS[nav_sign_index]

    return {
        "signIndex": nav_sign_index,
        "sign": nav_sign_name,
        "ordinal": ordinal_1to9,
        "degreeInNavamsha": degree_in_navamsha,
    }
