from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from typing import Optional

def to_utc(dt_iso: str, tz: Optional[str], offset_minutes: Optional[int]) -> datetime:
    """Convert ISO datetime string to UTC datetime"""
    naive = datetime.fromisoformat(dt_iso)
    if tz:
        return naive.replace(tzinfo=ZoneInfo(tz)).astimezone(timezone.utc)
    if offset_minutes is not None:
        return naive.replace(tzinfo=timezone(timedelta(minutes=offset_minutes))).astimezone(timezone.utc)
    # default: treat as UTC
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
