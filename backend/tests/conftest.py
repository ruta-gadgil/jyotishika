from types import SimpleNamespace
from uuid import uuid4

import pytest
from flask import g


class TestProfile:
    """Minimal profile model substitute for endpoint calculation tests."""

    def __init__(self, birth_details, chart_settings, name=None):
        self.id = uuid4()
        self.name = name
        self.datetime = birth_details["datetime"]
        self.tz = birth_details["tz"]
        self.utc_offset_minutes = birth_details["utc_offset_minutes"]
        self.latitude = birth_details["latitude"]
        self.longitude = birth_details["longitude"]
        self.house_system = chart_settings["house_system"]
        self.ayanamsha = chart_settings["ayanamsha"]
        self.node_type = chart_settings["node_type"]

    def to_dict(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "datetime": self.datetime,
            "tz": self.tz,
            "utc_offset_minutes": self.utc_offset_minutes,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "house_system": self.house_system,
            "ayanamsha": self.ayanamsha,
            "node_type": self.node_type,
            "created_at": None,
            "updated_at": None,
            "is_active": True,
        }


@pytest.fixture
def authed_client(client, monkeypatch):
    """Return a client with authenticated, database-free endpoint dependencies."""
    import app.db
    import app.routes

    user = SimpleNamespace(id=uuid4(), email="test@example.com")

    def get_current_user():
        g.current_user = user
        return {"user_id": "test-user", "email": user.email}

    def get_or_create_profile(user_id, birth_details, chart_settings, name=None):
        assert user_id == user.id
        return TestProfile(birth_details, chart_settings, name)

    monkeypatch.setattr(app.routes, "get_current_user", get_current_user)
    monkeypatch.setattr(app.db, "get_or_create_profile", get_or_create_profile)
    monkeypatch.setattr(app.db, "get_cached_chart", lambda profile_id: None)
    monkeypatch.setattr(app.db, "save_chart", lambda profile_id, chart_data: SimpleNamespace(id=uuid4()))

    return client
