"""Pure unit tests for chart sign extraction (no database, no login)."""
import pytest

from app.chart_signs import ChartSigns, extract_chart_signs


def make_chart(asc=7, moon=3, sun=0):
    return {
        "ascendant": {"signIndex": asc, "longitude": 220.5},
        "planets": [
            {"planet": "Sun", "signIndex": sun},
            {"planet": "Moon", "signIndex": moon},
            {"planet": "Mars", "signIndex": 9},
        ],
    }


def test_reads_ascendant_moon_and_sun_signs():
    assert extract_chart_signs(make_chart(asc=7, moon=3, sun=0)) == ChartSigns(
        asc_sign=7, moon_sign=3, sun_sign=0
    )


@pytest.mark.parametrize("sign", [0, 11])
def test_accepts_range_boundaries(sign):
    assert extract_chart_signs(make_chart(asc=sign, moon=sign, sun=sign)) == ChartSigns(sign, sign, sign)


def test_missing_moon_is_none_not_a_guess():
    chart = make_chart()
    chart["planets"] = [p for p in chart["planets"] if p["planet"] != "Moon"]
    assert extract_chart_signs(chart) == ChartSigns(asc_sign=7, moon_sign=None, sun_sign=0)


def test_missing_ascendant_is_none():
    chart = make_chart()
    del chart["ascendant"]
    assert extract_chart_signs(chart).asc_sign is None


def test_empty_chart_is_all_none():
    assert extract_chart_signs({}) == ChartSigns()


@pytest.mark.parametrize("bad", [-1, 12, 3.5, "3", True, None])
def test_out_of_range_or_malformed_signs_are_none(bad):
    assert extract_chart_signs(make_chart(asc=bad, moon=bad, sun=bad)) == ChartSigns()


def test_malformed_planets_do_not_raise():
    assert extract_chart_signs({"ascendant": {"signIndex": 2}, "planets": "oops"}) == ChartSigns(asc_sign=2)
    assert extract_chart_signs({"planets": [None, 5, {"planet": "Moon"}]}) == ChartSigns()
