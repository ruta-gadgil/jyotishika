import pytest
from app import create_app
from app.schemas import ChartRequest
from app.astro.utils import to_utc, norm360, sign_index, house_from_sign
from app.astro.engine import julian_day_utc, compute_whole_sign_cusps
from datetime import datetime, timezone

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
    """Test health check endpoint"""
    response = client.get('/healthz')
    assert response.status_code == 200
    assert response.json['ok'] == True

def test_chart_endpoint_basic(client):
    """Test basic chart calculation"""
    data = {
        "datetime": "1991-03-25T09:46:00",
        "tz": "Asia/Kolkata",
        "latitude": 18.5204,
        "longitude": 73.8567,
        "houseSystem": "WHOLE_SIGN",
        "ayanamsha": "LAHIRI",
        "nodeType": "MEAN"
    }
    
    response = client.post('/chart', json=data)
    assert response.status_code == 200
    
    result = response.json
    assert 'metadata' in result
    assert 'ascendant' in result
    assert 'planets' in result
    assert len(result['planets']) == 9  # Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn, Rahu, Ketu

def test_chart_endpoint_sf(client):
    """Test chart calculation for San Francisco"""
    data = {
        "datetime": "2025-09-03T12:30:00",
        "tz": "America/Los_Angeles",
        "latitude": 37.7749,
        "longitude": -122.4194,
        "houseSystem": "WHOLE_SIGN",
        "ayanamsha": "LAHIRI",
        "nodeType": "MEAN"
    }
    
    response = client.post('/chart', json=data)
    assert response.status_code == 200
    
    result = response.json
    assert result['metadata']['system'] == 'sidereal'
    assert result['metadata']['ayanamsha'] == 'LAHIRI'

def test_validation_errors(client):
    """Test various validation errors"""
    # Invalid latitude
    data = {
        "datetime": "1991-03-25T09:46:00",
        "tz": "Asia/Kolkata",
        "latitude": 100.0,  # Invalid
        "longitude": 73.8567
    }
    response = client.post('/chart', json=data)
    assert response.status_code == 400
    assert 'VALIDATION_ERROR' in response.json['error']['code']

    # Invalid timezone
    data = {
        "datetime": "1991-03-25T09:46:00",
        "tz": "Invalid/Timezone",
        "latitude": 18.5204,
        "longitude": 73.8567
    }
    response = client.post('/chart', json=data)
    assert response.status_code == 400

def test_utc_conversion():
    """Test UTC conversion utility"""
    # Test with timezone
    dt_utc = to_utc("1991-03-25T09:46:00", "Asia/Kolkata", None)
    assert dt_utc.tzinfo == timezone.utc
    
    # Test with offset
    dt_utc = to_utc("1991-03-25T09:46:00", None, 330)  # IST offset
    assert dt_utc.tzinfo == timezone.utc

def test_longitude_normalization():
    """Test longitude normalization"""
    assert norm360(370.0) == 10.0
    assert norm360(-10.0) == 350.0
    assert norm360(360.0) == 0.0

def test_sign_index():
    """Test zodiac sign index calculation"""
    assert sign_index(0.0) == 0    # Aries
    assert sign_index(30.0) == 1   # Taurus
    assert sign_index(359.9) == 11 # Pisces

def test_house_from_sign():
    """Test whole sign house calculation"""
    # If ascendant is in Aries (0), Sun in Leo (4) should be in house 5
    assert house_from_sign(4, 0) == 5
    
    # If ascendant is in Pisces (11), Sun in Aries (0) should be in house 2
    assert house_from_sign(0, 11) == 2

def test_whole_sign_cusps():
    """Test whole sign cusp calculation"""
    cusps = compute_whole_sign_cusps(0)  # Aries ascendant
    assert len(cusps) == 12
    assert cusps[0] == 0.0   # Aries
    assert cusps[1] == 30.0  # Taurus
    assert cusps[11] == 330.0 # Pisces
