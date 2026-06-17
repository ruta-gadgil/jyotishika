"""Unit tests for Panchang (five-limb) calculations."""

from unittest.mock import patch

import pytest

from app.astro.constants import YOGA_NAMES
from app.astro.engine import init_ephemeris, julian_day_utc, compute_planets
from app.astro.panchang import (
    tithi_from_elongation,
    compute_karana,
    compute_yoga,
    compute_vaara,
    compute_panchang,
    compute_lunar_month,
    purnimanta_index,
    tithi_gap,
)
from app.astro.utils import to_utc


@pytest.fixture(scope="module", autouse=True)
def _init_ephe():
    init_ephemeris("./ephe", "LAHIRI")


def test_tithi_elongation_boundaries():
    number, name, paksha = tithi_from_elongation(0.0)
    assert number == 1
    assert name == "Pratipada"
    assert paksha == "Shukla"

    number, name, paksha = tithi_from_elongation(180.0)
    assert number == 16
    assert name == "Pratipada"
    assert paksha == "Krishna"

    number, name, paksha = tithi_from_elongation(348.0)
    assert number == 30
    assert name == "Amavasya"
    assert paksha == "Krishna"


def test_tithi_gap_cycle():
    assert tithi_gap(29, 30) == 1
    assert tithi_gap(30, 2) == 2
    assert tithi_gap(10, 12) == 2


def test_karana_fixed_and_movable_slots():
    assert compute_karana(0.0)["name"] == "Kimstughna"
    assert compute_karana(0.0)["typeIndex"] == 1
    assert compute_karana(0.0)["isFixed"] is True

    assert compute_karana(57 * 6)["name"] == "Shakuni"
    assert compute_karana(57 * 6)["typeIndex"] == 9

    assert compute_karana(58 * 6)["name"] == "Chatushpada"
    assert compute_karana(58 * 6)["typeIndex"] == 10

    assert compute_karana(59 * 6)["name"] == "Naga"
    assert compute_karana(59 * 6)["typeIndex"] == 11

    assert compute_karana(7 * 6)["name"] == "Vishti"
    assert compute_karana(7 * 6)["typeIndex"] == 8
    assert compute_karana(7 * 6)["isFixed"] is False

    assert compute_karana(1 * 6)["name"] == "Bava"


def test_yoga_names_siddhi_not_siddha():
    assert YOGA_NAMES[15] == "Siddhi"
    assert YOGA_NAMES[20] == "Siddha"
    assert YOGA_NAMES[15] != YOGA_NAMES[20]


def test_yoga_boundary_math():
    jd = julian_day_utc(to_utc("1991-03-25T09:46:00", "Asia/Kolkata", None))
    yoga = compute_yoga(jd)
    assert 1 <= yoga["number"] <= 27
    assert yoga["name"] == YOGA_NAMES[yoga["number"] - 1]


def test_yoga_at_birth_time_mumbai_1970():
    """Yoga is computed at birth moment, not sunrise (natal panchang)."""
    jd = julian_day_utc(to_utc("1970-06-05T04:52:00", "Asia/Kolkata", None))
    yoga = compute_yoga(jd)
    assert yoga["number"] == 9
    assert yoga["name"] == "Shula"


def test_yoga_at_birth_time_indore_1962():
    jd = julian_day_utc(to_utc("1962-02-03T20:00:00", "Asia/Kolkata", None))
    yoga = compute_yoga(jd)
    assert yoga["number"] == 16
    assert yoga["name"] == "Siddhi"


def test_purnimanta_index_rules():
    assert purnimanta_index(5, "Shukla", None) == 5
    assert purnimanta_index(5, "Krishna", None) == 6
    assert purnimanta_index(5, "Krishna", "Adhika") == 5


def test_lunar_month_shukla_purnimanta_equals_amanta():
    jd = julian_day_utc(to_utc("1991-03-25T09:46:00", "Asia/Kolkata", None))
    planets = compute_planets(jd, "MEAN")
    moon = next(p for p in planets if p["planet"] == "Moon")
    sun = next(p for p in planets if p["planet"] == "Sun")
    elongation = (moon["longitude"] - sun["longitude"]) % 360
    month = compute_lunar_month(jd, elongation, "Shukla")
    assert month["amanta"] == month["purnimanta"]


def test_vaara_pune_birth_datetime():
    jd = julian_day_utc(to_utc("1991-03-25T09:46:00", "Asia/Kolkata", None))
    vaara = compute_vaara(jd, 18.5204, 73.8567, "Asia/Kolkata", None)
    assert vaara["name"] == "Somavaara"
    assert vaara["number"] == 2
    assert vaara["usedSunriseFallback"] is False


def test_vaara_polar_sunrise_fallback():
    jd = julian_day_utc(to_utc("1991-03-25T09:46:00", "Asia/Kolkata", None))
    with patch("app.astro.panchang.compute_sunrise", return_value=None):
        vaara = compute_vaara(jd, 70.0, 70.0, "Asia/Kolkata", None)
    assert vaara["usedSunriseFallback"] is True
    assert 1 <= vaara["number"] <= 7


def test_compute_panchang_reference_birth():
    from app.astro.utils import get_nakshatra_and_charan

    jd = julian_day_utc(to_utc("1991-03-25T09:46:00", "Asia/Kolkata", None))
    planets = compute_planets(jd, "MEAN")
    sun = next(p for p in planets if p["planet"] == "Sun")
    moon = next(p for p in planets if p["planet"] == "Moon")
    nak_name, nak_idx, charan = get_nakshatra_and_charan(moon["longitude"])

    panchang = compute_panchang(
        jd,
        sun["longitude"],
        moon["longitude"],
        {"name": nak_name, "index": nak_idx},
        charan,
        18.5204,
        73.8567,
        "Asia/Kolkata",
        None,
    )

    assert panchang["tithi"]["number"] == 10
    assert panchang["tithi"]["name"] == "Dashami"
    assert panchang["tithi"]["paksha"] == "Shukla"
    assert "lunarMonth" in panchang["tithi"]
    assert panchang["vaara"]["name"] == "Somavaara"
    assert panchang["yoga"]["number"] == 6
    assert panchang["karana"]["typeIndex"] == 6
    assert 1 <= panchang["nakshatra"]["index"] <= 27
    assert 1 <= panchang["nakshatra"]["charan"] <= 4
