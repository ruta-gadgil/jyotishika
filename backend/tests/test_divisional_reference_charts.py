"""Divisional chart correctness against two reference natal charts (Pune, Vedanjanam ayanamsha).

Reference values are (degree in sign, Navamsha sign, Dashamsha sign) per planet, taken from an
independent chart report (its Sun Dashamsha for case 2 is corrected to Cancer: 2°54' Scorpio is in the
first 3° part, which starts at Cancer). The report's degrees match our engine within ~30 arc-seconds.
"""

from pathlib import Path

import pytest

from app.astro.constants import ZODIAC_SIGNS
from app.astro.divisional import DIVISIONAL_CHARTS, divisional_position
from app.astro.engine import (
    ascendant_and_houses,
    compute_planets,
    init_ephemeris,
    julian_day_utc,
)
from app.astro.utils import to_utc

EPHE_DIR = str(Path(__file__).resolve().parents[1] / "ephe")
PUNE_LAT, PUNE_LON = 18.5204, 73.8567
DEGREE_TOLERANCE = 0.01  # reference degrees are rounded to whole arc-seconds, engine drifts slightly


def dms(degrees: int, minutes: int, seconds: int) -> float:
    return degrees + minutes / 60 + seconds / 3600


# Case 1: March 25, 1991, 9:47am Pune. Reference lists the sign too.
CASE_1 = {
    "iso": "1991-03-25T09:47:00",
    "planets": {
        # name: (sign, degree in sign, navamsha, dashamsha)
        "Ascendant": ("Taurus", dms(5, 37, 12), "Aquarius", "Aquarius"),
        "Sun": ("Pisces", dms(10, 10, 48), "Libra", "Aquarius"),
        "Moon": ("Cancer", dms(5, 19, 12), "Leo", "Aries"),
        "Mars": ("Gemini", dms(1, 33, 0), "Libra", "Gemini"),
        "Mercury": ("Pisces", dms(28, 32, 24), "Pisces", "Leo"),
        "Jupiter": ("Cancer", dms(9, 45, 36), "Virgo", "Gemini"),
        "Venus": ("Aries", dms(13, 44, 24), "Leo", "Leo"),
        "Saturn": ("Capricorn", dms(10, 48, 36), "Aries", "Sagittarius"),
        "Rahu": ("Capricorn", dms(0, 53, 24), "Capricorn", "Virgo"),
        "Ketu": ("Cancer", dms(0, 53, 24), "Cancer", "Pisces"),
    },
}

# Case 2: Nov 19, 1995, 8:29pm Pune. Reference does not list the birth sign.
CASE_2 = {
    "iso": "1995-11-19T20:29:00",
    "planets": {
        # name: (sign, degree in sign, navamsha, dashamsha); sign is checked against our engine
        "Ascendant": ("Gemini", dms(10, 46, 48), "Capricorn", "Virgo"),
        "Sun": ("Scorpio", dms(2, 54, 0), "Cancer", "Cancer"),
        "Moon": ("Virgo", dms(22, 16, 12), "Cancer", "Sagittarius"),
        "Mars": ("Scorpio", dms(27, 51, 36), "Pisces", "Aries"),
        "Mercury": ("Scorpio", dms(0, 49, 12), "Cancer", "Cancer"),
        "Jupiter": ("Scorpio", dms(26, 1, 12), "Aquarius", "Pisces"),
        "Venus": ("Scorpio", dms(26, 14, 24), "Aquarius", "Pisces"),
        "Saturn": ("Aquarius", dms(24, 6, 0), "Taurus", "Libra"),
        "Rahu": ("Libra", dms(0, 46, 48), "Libra", "Libra"),
        "Ketu": ("Aries", dms(0, 46, 48), "Aries", "Aries"),
    },
}


def natal_longitudes(iso: str) -> dict:
    init_ephemeris(EPHE_DIR, "VEDANJANAM")
    jd = julian_day_utc(to_utc(iso, "Asia/Kolkata", None))
    asc, _, _ = ascendant_and_houses(jd, PUNE_LAT, PUNE_LON, "WHOLE_SIGN")
    longitudes = {"Ascendant": asc}
    longitudes.update({p["planet"]: p["longitude"] for p in compute_planets(jd, "MEAN")})
    return longitudes


@pytest.mark.parametrize("case", [CASE_1, CASE_2], ids=["1991-03-25", "1995-11-19"])
def test_divisional_charts_match_reference(case):
    longitudes = natal_longitudes(case["iso"])

    for name, (sign, degree, navamsha, dashamsha) in case["planets"].items():
        longitude = longitudes[name]
        assert ZODIAC_SIGNS[int(longitude // 30)] == sign, f"{name} sign"
        assert abs(longitude % 30 - degree) < DEGREE_TOLERANCE, f"{name} degree in sign"

        for key, expected in (("navamsha", navamsha), ("dashamsha", dashamsha)):
            actual = divisional_position(longitude, DIVISIONAL_CHARTS[key])["sign"]
            assert actual == expected, f"{name} {key}: expected {expected}, got {actual}"
