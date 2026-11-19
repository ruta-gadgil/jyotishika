"""
Pure unit tests for Saved Profiles filters (no database, no login).

`apply_profile_filters` is checked by compiling the SQL it builds against the
Postgres dialect; nothing is executed.
"""
import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Query

from app.models import Profile
from app.profile_filters import (
    NAME_MAX_LENGTH,
    ProfileFilters,
    apply_profile_filters,
    escape_like,
    parse_profile_filters,
)


# --- parse_profile_filters ---------------------------------------------------


def test_no_params_means_no_filters():
    assert parse_profile_filters({}) == ProfileFilters()


def test_parses_every_filter():
    filters = parse_profile_filters(
        {"name": "ann", "ascendant_sign": "7", "moon_sign": "3", "sun_sign": "0"}
    )
    assert filters == ProfileFilters(name="ann", ascendant_sign=7, moon_sign=3, sun_sign=0)


def test_sign_zero_is_a_real_filter_not_absent():
    filters = parse_profile_filters({"sun_sign": "0"})
    assert filters.sun_sign == 0
    assert filters.has_sign_filter


def test_name_is_trimmed():
    assert parse_profile_filters({"name": "  ann  "}).name == "ann"


@pytest.mark.parametrize("blank", ["", "   "])
def test_blank_name_is_ignored(blank):
    assert parse_profile_filters({"name": blank}).name is None


def test_name_at_the_limit_is_accepted():
    name = "a" * NAME_MAX_LENGTH
    assert parse_profile_filters({"name": name}).name == name


def test_name_over_the_limit_is_rejected():
    with pytest.raises(ValueError, match="name must be at most 80 characters"):
        parse_profile_filters({"name": "a" * (NAME_MAX_LENGTH + 1)})


@pytest.mark.parametrize("bad", ["a\x00b", "\x00", "ann\x00", "line\nbreak", "tab\tinside", "bell\x07", "del\x7f"])
def test_control_characters_in_name_are_rejected(bad):
    with pytest.raises(ValueError, match="name contains invalid characters"):
        parse_profile_filters({"name": bad})


def test_surrounding_whitespace_is_trimmed_not_rejected():
    assert parse_profile_filters({"name": "\tann\n"}).name == "ann"


@pytest.mark.parametrize("name", ["José", "Zoë Müller", "राजनिकांत", "O'Brien", "Anne-Marie", "100% Joy", "a_b"])
def test_ordinary_unicode_and_punctuation_names_are_accepted(name):
    assert parse_profile_filters({"name": name}).name == name


@pytest.mark.parametrize("param", ["ascendant_sign", "moon_sign", "sun_sign"])
@pytest.mark.parametrize("bad", ["12", "-1", "x", "1.5", ""])
def test_invalid_signs_are_rejected_and_name_the_parameter(param, bad):
    with pytest.raises(ValueError, match=f"{param} must be an integer between 0 and 11"):
        parse_profile_filters({param: bad})


def test_has_sign_filter_ignores_name():
    assert not ProfileFilters(name="ann").has_sign_filter
    assert ProfileFilters(moon_sign=3).has_sign_filter


# --- escape_like -------------------------------------------------------------


@pytest.mark.parametrize(
    "raw, escaped",
    [
        ("ann", "ann"),
        ("100%", "100\\%"),
        ("a_b", "a\\_b"),
        ("a\\b", "a\\\\b"),
        ("%_\\", "\\%\\_\\\\"),
    ],
)
def test_escape_like_makes_wildcards_literal(raw, escaped):
    assert escape_like(raw) == escaped


# --- apply_profile_filters (SQL compiled, never executed) ---------------------


def compiled(filters):
    """Compile the filtered query. Values stay bound parameters, as in production."""
    query = apply_profile_filters(Query(Profile), filters)
    return query.statement.compile(dialect=postgresql.dialect())


def test_no_filters_leave_the_query_untouched_and_skip_the_join():
    sql = str(compiled(ProfileFilters()))
    assert "WHERE" not in sql
    assert "JOIN" not in sql


def test_name_filter_is_case_insensitive_substring_with_escape_and_no_join():
    statement = compiled(ProfileFilters(name="50%_off"))
    assert "profiles.name ILIKE" in str(statement)
    assert "ESCAPE" in str(statement)
    assert "JOIN" not in str(statement)
    assert list(statement.params.values()) == ["%50\\%\\_off%"]


def test_each_sign_filter_adds_its_own_condition_and_one_join():
    statement = compiled(ProfileFilters(ascendant_sign=7, moon_sign=3, sun_sign=0))
    sql = str(statement)
    assert sql.count("JOIN charts") == 1
    assert "charts.asc_sign =" in sql
    assert "charts.moon_sign =" in sql
    assert "charts.sun_sign =" in sql
    assert sorted(statement.params.values()) == [0, 3, 7]


def test_only_set_signs_are_filtered():
    statement = compiled(ProfileFilters(moon_sign=3))
    sql = str(statement)
    assert "charts.moon_sign =" in sql
    assert "asc_sign =" not in sql
    assert "sun_sign =" not in sql
    assert list(statement.params.values()) == [3]


def test_all_filters_combine_with_and():
    sql = str(compiled(ProfileFilters(name="ann", moon_sign=3)))
    assert "ILIKE" in sql
    assert "charts.moon_sign =" in sql
    assert " AND " in sql
    assert " OR " not in sql
