"""
Smoke tests for critical endpoints before deployment.

These tests verify that the most important functionality works:
- Health check endpoint
- Chart calculation (core business logic)
- OAuth endpoints are accessible

Run these before every deployment to catch breaking changes early.
"""
import pytest
from app import create_app


@pytest.fixture
def app():
    """Create test app instance"""
    app = create_app()
    app.config['TESTING'] = True
    app.config['EPHE_PATH'] = './ephe'  # Test ephemeris path
    return app


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


def test_healthz_endpoint(client):
    """Health check must pass - critical for monitoring"""
    response = client.get('/healthz')
    assert response.status_code == 200
    assert response.json['ok'] == True
    
    # If database is configured, it should be healthy
    if 'database' in response.json:
        assert response.json['database']['healthy'] == True


def test_chart_endpoint_basic(client):
    """Chart calculation must work - core business logic"""
    data = {
        "datetime": "2022-03-15T12:36:00",
        "tz": "America/Los_Angeles",
        "latitude": 37.3861,
        "longitude": -122.0839,
        "houseSystem": "WHOLE_SIGN",
        "ayanamsha": "LAHIRI",
        "nodeType": "MEAN"
    }
    
    response = client.post('/chart', json=data)
    assert response.status_code == 200
    assert 'planets' in response.json
    assert 'ascendant' in response.json
    assert len(response.json['planets']) == 12  # All planets calculated


def test_oauth_login_endpoint_accessible(client):
    """OAuth login endpoint must be accessible"""
    response = client.get('/auth/google/login', follow_redirects=False)
    # Should redirect to Google (302) or show config error (500)
    # Both are acceptable for smoke test (just checking endpoint exists)
    assert response.status_code in [302, 500]


def test_oauth_callback_endpoint_accessible(client):
    """OAuth callback endpoint must be accessible"""
    response = client.get('/auth/google/callback')
    # Should redirect with error (no code provided) or show error
    # Just checking the endpoint is routed correctly
    assert response.status_code in [302, 400]


def test_robots_txt_endpoint(client):
    """robots.txt endpoint should exist and return correct format"""
    response = client.get('/robots.txt')
    assert response.status_code == 200
    assert response.content_type == 'text/plain; charset=utf-8'
    assert b'User-agent' in response.data


def test_license_endpoint(client):
    """License endpoint should exist for AGPL compliance"""
    response = client.get('/license')
    assert response.status_code == 200
    assert 'license' in response.json
    assert 'AGPL' in response.json['license']
