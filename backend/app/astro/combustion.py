"""Combustion (astangata) rules and calculations for Vedic charts."""

from typing import List, Optional, Tuple

# Grahas that are never combust in Vedic astrology.
# Moon: new moon proximity is a lunar phase, not combustion (astangata).
# Rahu/Ketu: shadow nodes, not grahas subject to combustion.
# Uranus/Neptune/Pluto: modern planets with no combustion degrees.
NON_COMBUSTIBLE_PLANETS = frozenset({
    "Sun", "Moon", "Rahu", "Ketu",
    "Uranus", "Neptune", "Pluto",
})

# Combustion thresholds (angular distance from Sun in degrees) per Laghu Parashari / BPHS.
# Mercury and Venus have tighter thresholds when retrograde (they face the Sun directly).
# Only Mars, Mercury, Jupiter, Venus, and Saturn can be combust.
COMBUSTION_THRESHOLDS = {
    "Mars":    {"direct": 17.0, "retrograde": 17.0},
    "Mercury": {"direct": 14.0, "retrograde": 12.0},
    "Jupiter": {"direct": 11.0, "retrograde": 11.0},
    "Venus":   {"direct": 10.0, "retrograde":  8.0},
    "Saturn":  {"direct": 15.0, "retrograde": 15.0},
}


def sun_angular_distance(lon1: float, lon2: float) -> float:
    """Shortest angular separation between two ecliptic longitudes (degrees)."""
    diff = abs(lon1 - lon2)
    return round(min(diff, 360.0 - diff), 4)


def compute_combustion(
    planet_name: str,
    planet_longitude: float,
    retrograde: bool,
    sun_longitude: Optional[float],
) -> Tuple[Optional[float], bool]:
    """Return (sun_distance, is_combust) for a planet relative to the Sun."""
    if planet_name in NON_COMBUSTIBLE_PLANETS or sun_longitude is None:
        return None, False

    thresholds = COMBUSTION_THRESHOLDS.get(planet_name)
    if thresholds is None:
        return None, False

    sun_distance = sun_angular_distance(planet_longitude, sun_longitude)
    direction = "retrograde" if retrograde else "direct"
    is_combust = sun_distance <= thresholds[direction]
    return sun_distance, is_combust


def apply_combustion_to_planets(planets: List[dict]) -> List[dict]:
    """Recompute sunDistance and isCombust for a stored or cached planet list."""
    sun_longitude = next(
        (p["longitude"] for p in planets if p.get("planet") == "Sun"),
        None,
    )
    result = []
    for p in planets:
        rec = dict(p)
        sun_distance, is_combust = compute_combustion(
            rec["planet"],
            rec["longitude"],
            rec.get("retrograde", False),
            sun_longitude,
        )
        rec["sunDistance"] = sun_distance
        rec["isCombust"] = is_combust
        result.append(rec)
    return result
