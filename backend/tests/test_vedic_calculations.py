import math

from app.astro.utils import get_nakshatra_and_pada, get_navamsha_info


def approx_equal(a: float, b: float, eps: float = 1e-7) -> bool:
    return abs(a - b) <= eps


def test_nakshatra_pada_boundaries():
    # 0° -> Ashwini, pada 1
    name, index1, pada = get_nakshatra_and_pada(0.0)
    assert name == "Ashwini"
    assert index1 == 1
    assert pada == 1

    # Just before 13°20' (13.333333...) -> Ashwini, pada 4
    edge = 360.0 / 27.0  # 13.3333333...
    name, index1, pada = get_nakshatra_and_pada(edge - 1e-6)
    assert name == "Ashwini"
    assert index1 == 1
    assert pada == 4

    # Just after boundary -> Bharani, pada 1
    name, index1, pada = get_nakshatra_and_pada(edge + 1e-6)
    assert name == "Bharani"
    assert index1 == 2
    assert pada == 1


def test_navamsha_basic_aries():
    # 0° Aries -> ordinal 1, degree 0, navamsha sign Aries, Ashwini pada 1
    info = get_navamsha_info(0.0)
    assert info["ordinal"] == 1
    assert approx_equal(info["degreeInNavamsha"], 0.0)
    assert info["sign"] == "Aries"
    assert info["navamshaNakshatra"] == "Ashwini"
    assert info["navamshaPada"] == 1

    # Just over 3°20' -> ordinal 2, navamsha sign advances by one
    nav_span = 30.0 / 9.0
    info2 = get_navamsha_info(nav_span + 1e-6)
    assert info2["ordinal"] == 2
    assert info2["sign"] == "Taurus"


def test_navamsha_sign_mapping_for_modalities():
    # Taurus (fixed) starts navamsha at Capricorn
    info_taurus_start = get_navamsha_info(30.0)  # 0° Taurus
    assert info_taurus_start["ordinal"] == 1
    assert info_taurus_start["sign"] == "Capricorn"

    # Gemini (dual) starts navamsha at Sagittarius
    info_gemini_start = get_navamsha_info(60.0)  # 0° Gemini
    assert info_gemini_start["ordinal"] == 1
    assert info_gemini_start["sign"] == "Sagittarius"


