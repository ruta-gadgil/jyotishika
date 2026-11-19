"""
Sign placements derived from a calculated chart.

The Saved Profiles filters query these as plain columns on `charts` instead of
scanning chart JSON. They are derived in exactly one place (this module) and
written in exactly one place (`db._apply_chart_data`), so a stored sign can never
disagree with the chart it came from.

Sign indexes are 0-based: 0 = Aries ... 11 = Pisces.
"""
from dataclasses import dataclass
from typing import Any, Mapping, Optional

SIGN_COUNT = 12


@dataclass(frozen=True)
class ChartSigns:
    """Sign index (0-11) for the ascendant, Moon and Sun. None when unknown."""
    asc_sign: Optional[int] = None
    moon_sign: Optional[int] = None
    sun_sign: Optional[int] = None


def _valid_sign(value: Any) -> Optional[int]:
    """Return value as a sign index, or None if it is not an int in 0-11."""
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value if 0 <= value < SIGN_COUNT else None


def _planet_sign(planets: Any, planet_name: str) -> Optional[int]:
    """Sign index of the named planet in a chart's planets list, or None."""
    if not isinstance(planets, (list, tuple)):
        return None
    for planet in planets:
        if isinstance(planet, Mapping) and planet.get("planet") == planet_name:
            return _valid_sign(planet.get("signIndex"))
    return None


def extract_chart_signs(chart_data: Mapping[str, Any]) -> ChartSigns:
    """
    Read the ascendant, Moon and Sun signs from chart data.

    Args:
        chart_data: dict with `ascendant` ({"signIndex": int, ...}) and `planets`
            (list of {"planet": str, "signIndex": int, ...}), as produced by
            `calculate_chart_for_profile`.

    Returns:
        ChartSigns. Any value that is missing or malformed is None, never a guess.
    """
    ascendant = chart_data.get("ascendant")
    asc_sign = _valid_sign(ascendant.get("signIndex")) if isinstance(ascendant, Mapping) else None
    planets = chart_data.get("planets")

    return ChartSigns(
        asc_sign=asc_sign,
        moon_sign=_planet_sign(planets, "Moon"),
        sun_sign=_planet_sign(planets, "Sun"),
    )
