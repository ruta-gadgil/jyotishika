from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple

# Core Vimshottari constants
DASHA_LORDS: List[str] = [
    "Ketu",
    "Venus",
    "Sun",
    "Moon",
    "Mars",
    "Rahu",
    "Jupiter",
    "Saturn",
    "Mercury",
]

DASHA_YEARS: Dict[str, int] = {
    "Ketu": 7,
    "Venus": 20,
    "Sun": 6,
    "Moon": 10,
    "Mars": 7,
    "Rahu": 18,
    "Jupiter": 16,
    "Saturn": 19,
    "Mercury": 17,
}

# Astronomical constants
DAYS_PER_YEAR: float = 365.25

# Nakshatra span in degrees (13°20')
NAKSHATRA_SPAN_DEG: float = 13.333333333333334


def _nakshatra_index_and_fraction(longitude_sidereal: float) -> Tuple[int, float]:
    lon = longitude_sidereal % 360.0
    idx0 = int(lon // NAKSHATRA_SPAN_DEG)  # 0..26
    within = lon - idx0 * NAKSHATRA_SPAN_DEG
    fraction = within / NAKSHATRA_SPAN_DEG  # 0..1
    return idx0, fraction


def _add_days(dt: datetime, days: float) -> datetime:
    return dt + timedelta(days=days)


def _seq_from(start_index: int, items: List[str]) -> List[str]:
    return [items[(start_index + i) % len(items)] for i in range(len(items))]


def _overlaps(a_start: datetime, a_end: datetime, window_start: datetime, window_end: datetime) -> bool:
    return not (a_end <= window_start or a_start >= window_end)


def _trim_to_window(start: datetime, end: datetime, window_start: datetime, window_end: datetime) -> Tuple[datetime, datetime]:
    s = start if start >= window_start else window_start
    e = end if end <= window_end else window_end
    return s, e


def _subdivide(parent_start: datetime, parent_end: datetime, parent_lord: str, level: int) -> List[Dict[str, object]]:
    duration_days = (parent_end - parent_start).total_seconds() / 86400.0
    # Antardasha sequence starts from parent lord and follows 9-lord cycle
    start_index = DASHA_LORDS.index(parent_lord)
    sub_lords = _seq_from(start_index, DASHA_LORDS)

    out: List[Dict[str, object]] = []
    cursor = parent_start
    for sub_lord in sub_lords:
        proportion = DASHA_YEARS[sub_lord] / 120.0
        sub_days = duration_days * proportion
        sub_start = cursor
        sub_end = _add_days(cursor, sub_days)
        out.append({
            "lord": sub_lord,
            "level": level,
            "start": sub_start.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z"),
            "end": sub_end.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z"),
            "durationDays": sub_days,
            "yearsShare": DASHA_YEARS[sub_lord],
        })
        cursor = sub_end
    return out


def calculate_vimshottari_timeline(
    birth_utc: datetime,
    moon_longitude_sidereal: float,
    *,
    depth: int = 3,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    at_date: Optional[datetime] = None,
) -> Tuple[List[Dict[str, object]], Dict[str, object]]:
    """
    Compute Vimshottari dasha timeline up to depth 3.

    - birth_utc: naive or aware UTC; will be treated/returned as UTC Z.
    - moon_longitude_sidereal: degrees [0, 360).
    - depth: 1..3 levels.
    - from_date/to_date: UTC window to emit. Defaults: [birth, birth+120y].
    - at_date: mark active periods.
    """
    if depth < 1:
        depth = 1
    if depth > 3:
        depth = 3

    # Normalize datetimes to timezone-aware UTC
    def as_utc(dt: datetime) -> datetime:
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    birth_utc = as_utc(birth_utc)
    if from_date is None:
        window_start = birth_utc
    else:
        window_start = as_utc(from_date)

    if to_date is None:
        window_end = _add_days(birth_utc, 120 * DAYS_PER_YEAR)
    else:
        window_end = as_utc(to_date)

    at_dt = as_utc(at_date) if at_date is not None else None

    nak_idx0, frac = _nakshatra_index_and_fraction(moon_longitude_sidereal)
    start_lord = DASHA_LORDS[nak_idx0 % 9]

    # Remaining portion of the current Mahadasha at birth
    balance_years = (1.0 - frac) * float(DASHA_YEARS[start_lord])
    balance_days = balance_years * DAYS_PER_YEAR

    # Build Mahadasha sequence starting at birth (remaining of current), then full cycles
    timeline: List[Dict[str, object]] = []

    # Helper to attach nested levels
    def attach_children(node: Dict[str, object], start_dt: datetime, end_dt: datetime, lord: str):
        if depth >= 2:
            level2 = _subdivide(start_dt, end_dt, lord, level=2)
            if at_dt is not None:
                for c in level2:
                    s2 = datetime.fromisoformat(c["start"].replace("Z", "+00:00"))
                    e2 = datetime.fromisoformat(c["end"].replace("Z", "+00:00"))
                    c["active"] = bool(s2 <= at_dt < e2)
            node["antardasha"] = level2

            if depth >= 3:
                for c in level2:
                    s2 = datetime.fromisoformat(c["start"].replace("Z", "+00:00"))
                    e2 = datetime.fromisoformat(c["end"].replace("Z", "+00:00"))
                    lord2 = c["lord"]  # type: ignore[index]
                    level3 = _subdivide(s2, e2, lord2, level=3)
                    if at_dt is not None:
                        for cc in level3:
                            s3 = datetime.fromisoformat(cc["start"].replace("Z", "+00:00"))
                            e3 = datetime.fromisoformat(cc["end"].replace("Z", "+00:00"))
                            cc["active"] = bool(s3 <= at_dt < e3)
                    c["pratyantardasha"] = level3

    # First Mahadasha remainder from birth
    cursor = birth_utc
    current_lord = start_lord
    first_end = _add_days(cursor, balance_days)

    # Emit if overlapping window
    if _overlaps(cursor, first_end, window_start, window_end):
        s, e = _trim_to_window(cursor, first_end, window_start, window_end)
        node = {
            "lord": current_lord,
            "level": 1,
            "start": s.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z"),
            "end": e.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z"),
            "durationDays": (e - s).total_seconds() / 86400.0,
            "yearsShare": DASHA_YEARS[current_lord],
        }
        if at_dt is not None:
            node["active"] = bool(s <= at_dt < e)
        attach_children(node, s, e, current_lord)
        timeline.append(node)

    cursor = first_end

    # Continue through subsequent Mahadashas until window_end is reached
    lord_index = DASHA_LORDS.index(start_lord)
    k = 1
    while cursor < window_end:
        lord = DASHA_LORDS[(lord_index + k) % 9]
        years = float(DASHA_YEARS[lord])
        days = years * DAYS_PER_YEAR
        start_dt = cursor
        end_dt = _add_days(start_dt, days)
        if _overlaps(start_dt, end_dt, window_start, window_end):
            s, e = _trim_to_window(start_dt, end_dt, window_start, window_end)
            node = {
                "lord": lord,
                "level": 1,
                "start": s.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z"),
                "end": e.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z"),
                "durationDays": (e - s).total_seconds() / 86400.0,
                "yearsShare": DASHA_YEARS[lord],
            }
            if at_dt is not None:
                node["active"] = bool(s <= at_dt < e)
            attach_children(node, s, e, lord)
            timeline.append(node)
        cursor = end_dt
        k += 1

    metadata = {
        "system": "vimshottari",
        "depth": depth,
        "fromDate": window_start.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z"),
        "toDate": window_end.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    return timeline, metadata



