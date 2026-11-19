"""Pure unit tests for strict query-parameter parsing (no database, no login)."""
import pytest

from app.query_params import parse_int_param


def test_absent_param_returns_default():
    assert parse_int_param({}, "page", 1, 1) == 1


def test_absent_param_can_default_to_none():
    assert parse_int_param({}, "moon_sign", None, 0, 11) is None


@pytest.mark.parametrize("raw, expected", [("1", 1), ("25", 25), ("0007", 7), ("100", 100)])
def test_parses_digit_strings(raw, expected):
    assert parse_int_param({"n": raw}, "n", 1, 1, 100) == expected


@pytest.mark.parametrize("raw", ["", " ", "abc", "1.5", "-1", "+1", " 2", "2 ", "1e3", "٣"])
def test_rejects_anything_that_is_not_plain_digits(raw):
    with pytest.raises(ValueError, match="n must be"):
        parse_int_param({"n": raw}, "n", 1, 0, 100)


def test_rejects_below_minimum():
    with pytest.raises(ValueError, match="page must be an integer >= 1"):
        parse_int_param({"page": "0"}, "page", 1, 1)


def test_rejects_above_maximum_and_names_the_range():
    with pytest.raises(ValueError, match="page_size must be an integer between 1 and 100"):
        parse_int_param({"page_size": "101"}, "page_size", 25, 1, 100)


def test_boundaries_are_inclusive():
    assert parse_int_param({"s": "0"}, "s", None, 0, 11) == 0
    assert parse_int_param({"s": "11"}, "s", None, 0, 11) == 11
