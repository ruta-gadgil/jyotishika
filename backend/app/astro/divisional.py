"""Divisional (varga) charts that split every sign into equal parts.

Each chart is a `DivisionalChart` entry in `DIVISIONAL_CHARTS`: how many parts a sign is
split into, and which sign the first part falls in. To add another equal-division chart
(D7, D12, ...), add one entry here; the chart calculation and API response pick it up.

Charts that do not split signs equally (Hora D2, Trimsamsha D30) need their own functions.
"""

from dataclasses import dataclass
from typing import Callable, Dict, Optional

from .constants import (
    AIR_SIGNS,
    EARTH_SIGNS,
    FIRE_SIGNS,
    WATER_SIGNS,
    ZODIAC_SIGNS,
)

SIGN_SPAN_DEG = 30.0
SIGN_COUNT = 12


def _start_sign_by_element(sign_index_0: int) -> int:
    """Navamsha: the first part starts at a sign set by the base sign's element.

    - Fire (Aries, Leo, Sagittarius): Aries
    - Earth (Taurus, Virgo, Capricorn): Capricorn
    - Air (Gemini, Libra, Aquarius): Libra
    - Water (Cancer, Scorpio, Pisces): Cancer
    """
    if sign_index_0 in FIRE_SIGNS:
        return 0
    if sign_index_0 in EARTH_SIGNS:
        return 9
    if sign_index_0 in AIR_SIGNS:
        return 6
    if sign_index_0 in WATER_SIGNS:
        return 3
    raise ValueError(f"Invalid sign index {sign_index_0}. Must be 0-11 (Aries-Pisces).")


def _start_sign_odd_from_self_even_from_ninth(sign_index_0: int) -> int:
    """Dashamsha (Parashara): odd signs start from themselves, even signs from the 9th sign.

    Sign indices are 0-based, so odd signs (Aries, Gemini, ...) have even indices.
    """
    is_odd_sign = sign_index_0 % 2 == 0
    return sign_index_0 if is_odd_sign else (sign_index_0 + 8) % SIGN_COUNT


@dataclass(frozen=True)
class DivisionalChart:
    key: str                                  # API key and response field, e.g. "navamsha"
    divisions: int                            # parts per sign: 9 for D9, 10 for D10
    start_sign: Callable[[int], int]          # base sign index (0-11) -> sign index of the first part
    legacy_degree_key: Optional[str] = None   # older response field that mirrors degreeInDivision


DIVISIONAL_CHARTS: Dict[str, DivisionalChart] = {
    chart.key: chart
    for chart in (
        DivisionalChart("navamsha", 9, _start_sign_by_element, legacy_degree_key="degreeInNavamsha"),
        DivisionalChart("dashamsha", 10, _start_sign_odd_from_self_even_from_ninth),
    )
}


def divisional_position(longitude_sidereal: float, chart: DivisionalChart) -> Dict[str, object]:
    """Locate a sidereal longitude in a divisional chart.

    Returns a dict with:
      - signIndex: 0..11, sign the longitude falls in within this chart
      - sign: sign name
      - ordinal: 1..chart.divisions, which part of its birth sign the longitude is in
      - degreeInDivision: float degrees from the start of that part, [0, 30 / divisions)
    """
    lon = longitude_sidereal % 360.0
    base_sign_index = int(lon // SIGN_SPAN_DEG)
    degree_in_sign = lon - base_sign_index * SIGN_SPAN_DEG
    span = SIGN_SPAN_DEG / chart.divisions
    # Clamp so a float edge at the very end of a sign cannot produce ordinal divisions + 1
    ordinal = min(int(degree_in_sign // span), chart.divisions - 1) + 1
    sign_index = (chart.start_sign(base_sign_index) + ordinal - 1) % SIGN_COUNT

    return {
        "signIndex": sign_index,
        "sign": ZODIAC_SIGNS[sign_index],
        "ordinal": ordinal,
        "degreeInDivision": degree_in_sign - (ordinal - 1) * span,
    }


def divisional_payload(longitude_sidereal: float, chart: DivisionalChart) -> Dict[str, object]:
    """API-shaped position for one divisional chart (degree rounded to 4 decimals)."""
    position = divisional_position(longitude_sidereal, chart)
    degree = round(position["degreeInDivision"], 4)
    payload = {**position, "degreeInDivision": degree}
    if chart.legacy_degree_key:
        payload[chart.legacy_degree_key] = degree
    return payload


def divisional_payloads(longitude_sidereal: float) -> Dict[str, Dict[str, object]]:
    """API-shaped positions for every registered divisional chart, keyed by chart key."""
    return {
        key: divisional_payload(longitude_sidereal, chart)
        for key, chart in DIVISIONAL_CHARTS.items()
    }
