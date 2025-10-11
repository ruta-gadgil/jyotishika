import math

from app.astro.utils import get_nakshatra_and_charan, get_navamsha_info


def approx_equal(a: float, b: float, eps: float = 1e-7) -> bool:
    return abs(a - b) <= eps


def test_nakshatra_charan_boundaries():
    # 0° -> Ashwini, charan 1
    name, index1, charan = get_nakshatra_and_charan(0.0)
    assert name == "Ashwini"
    assert index1 == 1
    assert charan == 1

    # Just before 13°20' (13.333333...) -> Ashwini, charan 4
    edge = 360.0 / 27.0  # 13.3333333...
    name, index1, charan = get_nakshatra_and_charan(edge - 1e-6)
    assert name == "Ashwini"
    assert index1 == 1
    assert charan == 4

    # Just after boundary -> Bharani, charan 1
    name, index1, charan = get_nakshatra_and_charan(edge + 1e-6)
    assert name == "Bharani"
    assert index1 == 2
    assert charan == 1


def test_navamsha_basic_aries():
    # 0° Aries -> ordinal 1, degree 0, navamsha sign Aries
    info = get_navamsha_info(0.0)
    assert info["ordinal"] == 1
    assert approx_equal(info["degreeInNavamsha"], 0.0)
    assert info["sign"] == "Aries"

    # Just over 3°20' -> ordinal 2, navamsha sign advances by one
    nav_span = 30.0 / 9.0
    info2 = get_navamsha_info(nav_span + 1e-6)
    assert info2["ordinal"] == 2
    assert info2["sign"] == "Taurus"


def test_navamsha_sign_mapping_for_elements():
    # Taurus (Earth) starts navamsha at Capricorn
    info_taurus_start = get_navamsha_info(30.0)  # 0° Taurus
    assert info_taurus_start["ordinal"] == 1
    assert info_taurus_start["sign"] == "Capricorn"

    # Gemini (Air) starts navamsha at Libra
    info_gemini_start = get_navamsha_info(60.0)  # 0° Gemini
    assert info_gemini_start["ordinal"] == 1
    assert info_gemini_start["sign"] == "Libra"

    # Cancer (Water) starts navamsha at Cancer
    info_cancer_start = get_navamsha_info(90.0)  # 0° Cancer
    assert info_cancer_start["ordinal"] == 1
    assert info_cancer_start["sign"] == "Cancer"

    # Leo (Fire) starts navamsha at Aries
    info_leo_start = get_navamsha_info(120.0)  # 0° Leo
    assert info_leo_start["ordinal"] == 1
    assert info_leo_start["sign"] == "Aries"


def test_navamsha_calculation_real_birth_data():
    """Test navamsha calculations for real birth data: March 25, 1991, 9:46am IST"""
    import swisseph as swe
    from app.astro.engine import julian_day_utc, compute_planets, init_ephemeris
    from app.astro.utils import to_utc, get_navamsha_info
    
    # Test case: March 25, 1991, 9:46am, lat: 18.5204, long: 73.8567
    iso = '1991-03-25T09:46:00'
    dt_utc = to_utc(iso, 'Asia/Kolkata', None)
    jd = julian_day_utc(dt_utc)
    
    # Initialize ephemeris with Lahiri
    init_ephemeris('./ephe', "LAHIRI")
    
    # Compute planets
    planets = compute_planets(jd, "MEAN")
    
    # Expected navamsha signIndex values (verified with corrected element-based calculation)
    expected_navamsha = {
        'Sun': 6,      # Libra
        'Moon': 4,     # Leo
        'Mercury': 11, # Pisces
        'Venus': 4,    # Leo
        'Mars': 6,     # Libra
        'Jupiter': 5,  # Virgo
        'Saturn': 0,   # Aries
        'Uranus': 5,   # Virgo
        'Neptune': 6,  # Libra
        'Pluto': 1,    # Taurus
        'Rahu': 9,     # Capricorn
        'Ketu': 3,     # Cancer
    }
    
    # Test each planet's navamsha calculation
    for planet in planets:
        name = planet['planet']
        longitude = planet['longitude']
        nav_info = get_navamsha_info(longitude)
        actual_navamsha = nav_info['signIndex']
        expected = expected_navamsha[name]
        
        assert actual_navamsha == expected, (
            f"{name}: Expected navamsha signIndex {expected}, got {actual_navamsha} "
            f"(longitude: {longitude:.1f}°)"
        )
        
        # Verify other navamsha fields are present and valid
        assert 'sign' in nav_info
        assert 'ordinal' in nav_info
        assert 'degreeInNavamsha' in nav_info
        assert 0 <= nav_info['ordinal'] <= 9
        assert 0 <= nav_info['degreeInNavamsha'] < 3.3334  # 3°20'


