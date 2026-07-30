from app.astro.combustion import (
    apply_combustion_to_planets,
    compute_combustion,
    sun_angular_distance,
)

SUN_LON = 100.0


def test_sun_angular_distance_wraps_at_360():
    assert sun_angular_distance(350.0, 10.0) == 20.0


def test_moon_near_sun_is_not_combust():
    dist, combust = compute_combustion("Moon", SUN_LON + 5, False, SUN_LON)
    assert dist is None
    assert combust is False


def test_mars_within_threshold_is_combust():
    dist, combust = compute_combustion("Mars", SUN_LON + 10, False, SUN_LON)
    assert dist == 10.0
    assert combust is True


def test_mars_outside_threshold_is_not_combust():
    dist, combust = compute_combustion("Mars", SUN_LON + 20, False, SUN_LON)
    assert dist == 20.0
    assert combust is False


def test_rahu_conjunct_sun_is_not_combust():
    dist, combust = compute_combustion("Rahu", SUN_LON, False, SUN_LON)
    assert dist is None
    assert combust is False


def test_ketu_conjunct_sun_is_not_combust():
    dist, combust = compute_combustion("Ketu", SUN_LON, False, SUN_LON)
    assert dist is None
    assert combust is False


def test_sun_is_not_combust():
    dist, combust = compute_combustion("Sun", SUN_LON, False, SUN_LON)
    assert dist is None
    assert combust is False


def test_outer_planets_are_not_combust():
    for planet in ("Uranus", "Neptune", "Pluto"):
        dist, combust = compute_combustion(planet, SUN_LON + 2, False, SUN_LON)
        assert dist is None
        assert combust is False


def test_apply_combustion_to_planets_patches_stale_cache():
    planets = [
        {"planet": "Sun", "longitude": SUN_LON, "retrograde": False},
        {"planet": "Moon", "longitude": SUN_LON + 5, "retrograde": False, "isCombust": True},
        {"planet": "Mars", "longitude": SUN_LON + 10, "retrograde": False, "isCombust": False},
    ]
    result = apply_combustion_to_planets(planets)
    moon = next(p for p in result if p["planet"] == "Moon")
    mars = next(p for p in result if p["planet"] == "Mars")
    assert moon["isCombust"] is False
    assert mars["isCombust"] is True
