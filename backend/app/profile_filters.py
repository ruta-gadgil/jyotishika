"""
Filters for the Saved Profiles list.

Three jobs, kept separate:
- `parse_profile_filters`: validate query-string input into a `ProfileFilters`.
- `escape_like`: make user text literal inside a LIKE/ILIKE pattern.
- `apply_profile_filters`: add the matching SQL conditions to a profiles query.

Different filters combine with AND. Adding a filter means one dataclass field,
one line in the parser, and one condition in `apply_profile_filters`.
"""
from dataclasses import dataclass
from typing import Mapping, Optional

from .chart_signs import SIGN_COUNT
from .models import Chart, Profile
from .query_params import parse_int_param

NAME_MAX_LENGTH = 80
LIKE_ESCAPE_CHAR = "\\"


@dataclass(frozen=True)
class ProfileFilters:
    """Validated filters. None means "no filter" for that field."""
    name: Optional[str] = None  # case-insensitive substring, already trimmed
    ascendant_sign: Optional[int] = None  # 0 (Aries) to 11 (Pisces)
    moon_sign: Optional[int] = None
    sun_sign: Optional[int] = None

    @property
    def has_sign_filter(self) -> bool:
        return any(
            sign is not None
            for sign in (self.ascendant_sign, self.moon_sign, self.sun_sign)
        )


def parse_profile_filters(args: Mapping[str, str]) -> ProfileFilters:
    """
    Build ProfileFilters from query parameters.

    Query parameters (all optional):
        name: trimmed, at most NAME_MAX_LENGTH characters, no control characters,
            blank is ignored
        ascendant_sign, moon_sign, sun_sign: integer 0-11

    Raises:
        ValueError: naming the offending parameter.
    """
    return ProfileFilters(
        name=_parse_name(args),
        ascendant_sign=parse_int_param(args, "ascendant_sign", None, 0, SIGN_COUNT - 1),
        moon_sign=parse_int_param(args, "moon_sign", None, 0, SIGN_COUNT - 1),
        sun_sign=parse_int_param(args, "sun_sign", None, 0, SIGN_COUNT - 1),
    )


def _parse_name(args: Mapping[str, str]) -> Optional[str]:
    name = (args.get("name") or "").strip()
    if not name:
        return None
    if len(name) > NAME_MAX_LENGTH:
        raise ValueError(f"name must be at most {NAME_MAX_LENGTH} characters")
    # Postgres rejects NUL in text parameters (would surface as a 500); other control
    # characters are never part of a real name. Reject rather than silently rewrite.
    if any(ord(char) < 32 or ord(char) == 127 for char in name):
        raise ValueError("name contains invalid characters")
    return name


def escape_like(text: str, escape_char: str = LIKE_ESCAPE_CHAR) -> str:
    """Escape LIKE wildcards so `text` always matches literally."""
    return (
        text.replace(escape_char, escape_char * 2)
        .replace("%", escape_char + "%")
        .replace("_", escape_char + "_")
    )


def apply_profile_filters(query, filters: ProfileFilters):
    """
    Narrow a Profile query by the given filters.

    Charts are joined only when a sign filter is set, so a profile without a chart
    (or with an unknown sign) still appears in the unfiltered list and drops out
    once a sign filter is applied. The join is on the unique `charts.profile_id`,
    so it never duplicates profiles and counts stay correct.
    """
    if filters.name is not None:
        pattern = f"%{escape_like(filters.name)}%"
        query = query.filter(Profile.name.ilike(pattern, escape=LIKE_ESCAPE_CHAR))

    if filters.has_sign_filter:
        query = query.join(Chart, Chart.profile_id == Profile.id)
        if filters.ascendant_sign is not None:
            query = query.filter(Chart.asc_sign == filters.ascendant_sign)
        if filters.moon_sign is not None:
            query = query.filter(Chart.moon_sign == filters.moon_sign)
        if filters.sun_sign is not None:
            query = query.filter(Chart.sun_sign == filters.sun_sign)

    return query
