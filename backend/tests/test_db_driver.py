"""
Database driver / dependency guard tests.

These exist because an unpinned transitive upgrade (SQLAlchemy 2.1 switching the
default Postgres driver from psycopg2 to psycopg v3) took production down while every
other test stayed green: tests ran without DATABASE_URL, so the database setup path
was never exercised.

None of these tests open a network connection. They only verify that the configured
driver can be loaded and that startup failures are reported honestly.
"""
from importlib.metadata import version
from pathlib import Path

import pytest
from packaging.requirements import Requirement
from sqlalchemy import create_engine

from app import create_app
from app.db import DB_INIT_ERROR_KEY, POSTGRES_DRIVERNAME, normalize_database_url

BACKEND_DIR = Path(__file__).resolve().parent.parent


@pytest.fixture
def app_env(monkeypatch):
    """Environment required by create_app, without touching a real database."""
    monkeypatch.setenv("EPHE_PATH", str(BACKEND_DIR / "ephe"))
    monkeypatch.setenv("TESTING", "true")
    return monkeypatch


# --- URL normalization -------------------------------------------------------


@pytest.mark.parametrize(
    "raw",
    [
        "postgresql://user:pass@host:5432/db",
        "postgres://user:pass@host:5432/db",
    ],
)
def test_driverless_postgres_urls_get_explicit_driver(raw):
    assert normalize_database_url(raw).startswith(f"{POSTGRES_DRIVERNAME}://")


@pytest.mark.parametrize(
    "raw",
    [
        "postgresql+psycopg://user:pass@host/db",
        "postgresql+psycopg2://user:pass@host/db",
        "sqlite:///local.db",
    ],
)
def test_explicit_drivers_are_left_alone(raw):
    assert normalize_database_url(raw) == raw


def test_special_characters_in_credentials_survive_normalization():
    raw = "postgresql://postgres.ref:p%40ss%2Fw%3Ard@aws-0.pooler.supabase.com:6543/postgres?sslmode=require"
    normalized = normalize_database_url(raw)

    assert normalized == raw.replace("postgresql://", f"{POSTGRES_DRIVERNAME}://", 1)


# --- Driver availability -----------------------------------------------------


def test_postgres_driver_is_installed():
    """Fails if the driver we name in POSTGRES_DRIVERNAME is not in the environment."""
    url = normalize_database_url("postgresql://user:pass@localhost:5432/db")
    engine = create_engine(url)  # imports the DBAPI; does not connect

    assert engine.dialect.driver == POSTGRES_DRIVERNAME.split("+", 1)[1]
    engine.dispose()


def test_driverless_url_in_environment_still_initializes_database(app_env):
    """The exact production shape: plain postgresql:// DATABASE_URL."""
    app_env.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")

    app = create_app()

    assert DB_INIT_ERROR_KEY not in app.config
    assert app.config["SQLALCHEMY_DATABASE_URI"].startswith(f"{POSTGRES_DRIVERNAME}://")
    with app.app_context():
        from app.models import db

        assert db.engine.dialect.driver == POSTGRES_DRIVERNAME.split("+", 1)[1]


# --- Failure reporting -------------------------------------------------------


def test_database_init_failure_is_reported_by_healthz(app_env):
    """A broken driver must fail /healthz with the real cause, not a generic bind error."""
    app_env.setenv("DATABASE_URL", "postgresql+nonexistentdriver://user:pass@localhost/db")

    app = create_app()
    response = app.test_client().get("/healthz")

    assert response.status_code == 503
    assert response.json["ok"] is False
    assert "failed to initialize" in response.json["database"]["message"]
    assert "nonexistentdriver" in response.json["database"]["message"]


# --- Dependency pinning ------------------------------------------------------


def test_sqlalchemy_is_pinned_with_an_upper_bound():
    """
    SQLAlchemy is only a transitive dependency of Flask-SQLAlchemy. Without our own
    bounded pin, every image rebuild silently takes the newest release.
    """
    requirements = (BACKEND_DIR / "requirements.txt").read_text().splitlines()
    pins = [
        Requirement(line.strip())
        for line in requirements
        if line.strip() and not line.startswith("#")
    ]
    sqlalchemy_pins = [r for r in pins if r.name.lower() == "sqlalchemy"]

    assert sqlalchemy_pins, "requirements.txt must pin sqlalchemy directly"
    specifiers = {spec.operator for spec in sqlalchemy_pins[0].specifier}
    assert specifiers & {"<", "<=", "==", "~="}, "sqlalchemy pin needs an upper bound"


def test_installed_sqlalchemy_satisfies_requirements_pin():
    requirements = (BACKEND_DIR / "requirements.txt").read_text().splitlines()
    pin = next(
        Requirement(line.strip())
        for line in requirements
        if line.strip().lower().startswith("sqlalchemy")
    )

    assert pin.specifier.contains(version("sqlalchemy")), (
        f"installed sqlalchemy {version('sqlalchemy')} is outside requirements.txt pin {pin.specifier}"
    )
