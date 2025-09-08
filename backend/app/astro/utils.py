from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from typing import Optional
import pytz

def detect_timezone_from_coordinates(latitude: float, longitude: float) -> str:
    """Detect timezone from latitude and longitude coordinates"""
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
    
    # US Mountain: roughly 31°N to 49°N, longitude 102°W to 125°W
    elif 31 <= latitude <= 49 and -125 <= longitude <= -102:
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
