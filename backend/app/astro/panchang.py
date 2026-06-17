"""
Panchang (five limbs) calculations for natal charts.

Tithi, Vaara, Nakshatra, Yoga, and Karana — all sidereal where ephemeris is used.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional, Tuple

import pytz
import swisseph as swe

from .constants import (
    SEFLAGS,
    SYNODIC_MONTH_DAYS,
    TITHI_NAMES,
    YOGA_NAMES,
    YOGA_SPAN_DEG,
    LUNAR_MONTH_NAMES,
    MOVABLE_KARANA_NAMES,
    FIXED_KARANA_BY_SLOT,
    KARANA_TYPE_INDEX,
    VAARA_BY_PYTHON_WEEKDAY,
)
from .engine import compute_sunrise
from .utils import detect_timezone_from_coordinates, norm360


def elongation_at_jd(jd: float) -> Tuple[float, float, float]:
    """Return sidereal (sun_long, moon_long, elongation) at Julian Day."""
    sun_result = swe.calc_ut(jd, swe.SUN, SEFLAGS)
    moon_result = swe.calc_ut(jd, swe.MOON, SEFLAGS)
    sun_long = norm360(sun_result[0][0])
    moon_long = norm360(moon_result[0][0])
    elongation = norm360(moon_long - sun_long)
    return sun_long, moon_long, elongation


def find_new_moon_jd(jd_approx: float) -> float:
    """Refine to exact new moon JD via Newton iteration on sidereal elongation."""
    jd = jd_approx
    for _ in range(40):
        sun_long, moon_long, elong = elongation_at_jd(jd)
        moon_speed = swe.calc_ut(jd, swe.MOON, SEFLAGS)[0][3]
        sun_speed = swe.calc_ut(jd, swe.SUN, SEFLAGS)[0][3]
        elong_dot = moon_speed - sun_speed
        elong_adj = elong - 360.0 if elong > 180.0 else elong
        if abs(elong_adj) < 1e-10 or abs(elong_dot) < 1e-10:
            break
        dt = -elong_adj / elong_dot
        jd += dt
        if abs(dt) < 1e-8:
            break
    return jd


def count_sankrantis(jd_start: float, jd_end: float) -> int:
    """Count Sun sign ingresses between two Julian Days (sidereal)."""
    sun_start = int(swe.calc_ut(jd_start, swe.SUN, SEFLAGS)[0][0] / 30) % 12
    sun_end = int(swe.calc_ut(jd_end, swe.SUN, SEFLAGS)[0][0] / 30) % 12
    return (sun_end - sun_start) % 12


def tithi_gap(a: int, b: int) -> int:
    """Forward distance from tithi a to tithi b in the 1..30 cycle."""
    if b >= a:
        return b - a
    return (30 - a) + b


def tithi_from_elongation(elongation: float) -> Tuple[int, str, str]:
    number = int(elongation // 12) + 1
    paksha = "Shukla" if number <= 15 else "Krishna"
    name = TITHI_NAMES[number - 1]
    return number, name, paksha


def resolve_timezone(
    tz: Optional[str],
    utc_offset_minutes: Optional[int],
    lat: float,
    lon: float,
) -> pytz.BaseTzInfo:
    if tz:
        return pytz.timezone(tz)
    if lat is not None and lon is not None:
        detected = detect_timezone_from_coordinates(lat, lon)
        if detected and detected != "UTC":
            return pytz.timezone(detected)
    if utc_offset_minutes is not None:
        return pytz.FixedOffset(utc_offset_minutes)
    return pytz.UTC


def jd_to_utc_datetime(jd: float) -> datetime:
    year, month, day, hour = swe.revjul(jd, swe.GREG_CAL)
    h = int(hour)
    minute_frac = (hour - h) * 60
    m = int(minute_frac)
    s = int((minute_frac - m) * 60)
    return datetime(year, month, day, h, m, s, tzinfo=timezone.utc)


def local_datetime_at_jd(jd: float, tz_obj: pytz.BaseTzInfo) -> datetime:
    utc_dt = jd_to_utc_datetime(jd)
    return utc_dt.astimezone(tz_obj)


def compute_tithi_tag(
    jd_ut: float,
    lat: float,
    lon: float,
) -> Tuple[Optional[str], Optional[int]]:
    jd_sunrise_before = compute_sunrise(jd_ut, lat, lon, "before")
    jd_sunrise_after = compute_sunrise(jd_ut, lat, lon, "after")
    if jd_sunrise_before is None or jd_sunrise_after is None:
        return None, None

    _, _, elong_before = elongation_at_jd(jd_sunrise_before)
    _, _, elong_after = elongation_at_jd(jd_sunrise_after)
    tithi_before = int(elong_before // 12) + 1
    tithi_after = int(elong_after // 12) + 1

    if tithi_before == tithi_after:
        return "Adhika", None
    if tithi_gap(tithi_before, tithi_after) > 1:
        skipped = (tithi_before % 30) + 1
        return "Kshaya", skipped
    return None, None


def format_month_name(index: int, masa_tag: Optional[str]) -> str:
    base = LUNAR_MONTH_NAMES[index]
    if masa_tag == "Adhika":
        return f"Adhika {base}"
    if masa_tag == "Nija":
        return f"Nija {base}"
    if masa_tag == "Kshaya":
        return f"Kshaya {base}"
    return base


def purnimanta_index(amanta_index: int, paksha: str, masa_tag: Optional[str]) -> int:
    if paksha == "Shukla":
        return amanta_index
    if masa_tag == "Adhika":
        return amanta_index
    return (amanta_index + 1) % 12


def compute_lunar_month(
    jd_ut: float,
    elongation: float,
    paksha: str,
) -> Dict[str, Any]:
    days_since_nm = elongation * (SYNODIC_MONTH_DAYS / 360.0)
    jd_nm_approx = jd_ut - days_since_nm
    jd_this_nm = find_new_moon_jd(jd_nm_approx)
    jd_prev_nm = find_new_moon_jd(jd_this_nm - SYNODIC_MONTH_DAYS)
    jd_prev_prev_nm = find_new_moon_jd(jd_prev_nm - SYNODIC_MONTH_DAYS)

    sun_long_at_nm, _, _ = elongation_at_jd(jd_this_nm)
    amanta_index = int(sun_long_at_nm / 30) % 12

    sankrantis_this = count_sankrantis(jd_prev_nm, jd_this_nm)
    sankrantis_prev = count_sankrantis(jd_prev_prev_nm, jd_prev_nm)

    masa_tag: Optional[str] = None
    is_adhika = False
    is_kshaya = False

    if sankrantis_this == 0:
        masa_tag = "Kshaya"
        is_kshaya = True
    elif sankrantis_this == 2:
        masa_tag = "Adhika"
        is_adhika = True
    elif sankrantis_this == 1 and sankrantis_prev == 2:
        masa_tag = "Nija"

    purn_idx = purnimanta_index(amanta_index, paksha, masa_tag)
    amanta_name = format_month_name(amanta_index, masa_tag)
    purnimanta_name = format_month_name(purn_idx, masa_tag)

    return {
        "amanta": amanta_name,
        "purnimanta": purnimanta_name,
        "masaTag": masa_tag,
        "isAdhika": is_adhika,
        "isKshaya": is_kshaya,
    }


def compute_vaara(
    jd_ut: float,
    lat: float,
    lon: float,
    tz: Optional[str],
    utc_offset_minutes: Optional[int],
) -> Dict[str, Any]:
    tz_obj = resolve_timezone(tz, utc_offset_minutes, lat, lon)
    jd_sunrise_before = compute_sunrise(jd_ut, lat, lon, "before")
    used_fallback = False

    if jd_sunrise_before is not None:
        local_dt = local_datetime_at_jd(jd_sunrise_before, tz_obj)
    else:
        used_fallback = True
        local_dt = local_datetime_at_jd(jd_ut, tz_obj)
        local_dt = local_dt.replace(hour=0, minute=0, second=0, microsecond=0)

    python_weekday = local_dt.weekday()
    name, number = VAARA_BY_PYTHON_WEEKDAY[python_weekday]
    return {
        "number": number,
        "name": name,
        "usedSunriseFallback": used_fallback,
    }


def compute_yoga(jd_for_yoga: float) -> Dict[str, Any]:
    sun_long, moon_long, _ = elongation_at_jd(jd_for_yoga)
    yoga_long = norm360(sun_long + moon_long)
    yoga_number = int(yoga_long / YOGA_SPAN_DEG) + 1
    if yoga_number > 27:
        yoga_number = 27
    return {
        "number": yoga_number,
        "name": YOGA_NAMES[yoga_number - 1],
    }


def compute_karana(elongation: float) -> Dict[str, Any]:
    karana_idx = int(elongation / 6)
    if karana_idx > 59:
        karana_idx = 59

    if karana_idx in FIXED_KARANA_BY_SLOT:
        name = FIXED_KARANA_BY_SLOT[karana_idx]
        is_fixed = True
    else:
        name = MOVABLE_KARANA_NAMES[(karana_idx - 1) % 7]
        is_fixed = False

    return {
        "name": name,
        "typeIndex": KARANA_TYPE_INDEX[name],
        "isFixed": is_fixed,
    }


def compute_panchang(
    jd_ut: float,
    sun_long: float,
    moon_long: float,
    moon_nakshatra: Dict[str, Any],
    moon_charan: int,
    lat: float,
    lon: float,
    tz: Optional[str] = None,
    utc_offset_minutes: Optional[int] = None,
) -> Dict[str, Any]:
    elongation = norm360(moon_long - sun_long)
    number, name, paksha = tithi_from_elongation(elongation)
    tithi_tag, skipped_tithi = compute_tithi_tag(jd_ut, lat, lon)
    lunar_month = compute_lunar_month(jd_ut, elongation, paksha)

    return {
        "tithi": {
            "number": number,
            "name": name,
            "paksha": paksha,
            "elongation": round(elongation, 4),
            "tithiTag": tithi_tag,
            "skippedTithiNumber": skipped_tithi,
            "lunarMonth": lunar_month,
        },
        "vaara": compute_vaara(jd_ut, lat, lon, tz, utc_offset_minutes),
        "nakshatra": {
            "index": moon_nakshatra["index"],
            "name": moon_nakshatra["name"],
            "charan": moon_charan,
        },
        "yoga": compute_yoga(jd_ut),
        "karana": compute_karana(elongation),
    }
