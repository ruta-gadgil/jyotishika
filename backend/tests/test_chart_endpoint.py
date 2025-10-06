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
    assert len(result['planets']) == 12  # Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn, Uranus, Neptune, Pluto, Rahu, Ketu

    # Verify new fields exist on each planet
    for p in result['planets']:
        assert 'nakshatra' in p and isinstance(p['nakshatra'], dict)
        assert 'name' in p['nakshatra'] and 'index' in p['nakshatra']
        assert 'pada' in p and 1 <= p['pada'] <= 4
        assert 'navamsha' in p and isinstance(p['navamsha'], dict)
        assert 'sign' in p['navamsha'] and 'ordinal' in p['navamsha'] and 'degreeInNavamsha' in p['navamsha']
        assert 'navamshaNakshatraPada' in p and isinstance(p['navamshaNakshatraPada'], dict)
        assert 'nakshatra' in p['navamshaNakshatraPada'] and 'pada' in p['navamshaNakshatraPada']

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

def test_chart_endpoint_mountain_view_dst(client):
    """Test chart calculation for Mountain View, CA during DST - March 15, 2022"""
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
    
    result = response.json
    
    # Verify metadata
    assert result['metadata']['system'] == 'sidereal'
    assert result['metadata']['ayanamsha'] == 'LAHIRI'
    assert result['metadata']['tzApplied'] == 'America/Los_Angeles'
    assert result['metadata']['datetimeUTC'] == '2022-03-15T19:36:00Z'  # PDT -> UTC conversion
    
    # Verify ascendant calculation
    ascendant = result['ascendant']
    assert ascendant['signIndex'] == 2  # Gemini (0=Aries, 1=Taurus, 2=Gemini)
    assert ascendant['longitude'] == pytest.approx(70.04, abs=0.1)  # Gemini 10°04'
    assert ascendant['house'] == 1
    
    # Verify planets are calculated
    assert len(result['planets']) == 12
    assert all('planet' in p for p in result['planets'])
    assert all('longitude' in p for p in result['planets'])

def test_timezone_detection_mountain_view():
    """Test timezone detection for Mountain View coordinates"""
    from app.astro.utils import detect_timezone_from_coordinates
    
    # Mountain View, California coordinates
    lat = 37.3861
    lon = -122.0839
    
    detected_tz = detect_timezone_from_coordinates(lat, lon)
    assert detected_tz == "America/Los_Angeles"  # Should be Pacific Time, not Mountain Time

def test_timezone_detection_international():
    """Test timezone detection for international locations"""
    from app.astro.utils import detect_timezone_from_coordinates
    
    # Test various international locations
    test_cases = [
        (51.5074, -0.1278, "Europe/London"),      # London, UK
        (48.8566, 2.3522, "Europe/Paris"),        # Paris, France
        (35.6762, 139.6503, "Asia/Tokyo"),       # Tokyo, Japan
        (-33.8688, 151.2093, "Australia/Sydney"), # Sydney, Australia
        (19.0760, 72.8777, "Asia/Kolkata"),      # Mumbai, India
        (-23.5505, -46.6333, "America/Sao_Paulo"), # São Paulo, Brazil
    ]
    
    for lat, lon, expected_tz in test_cases:
        detected_tz = detect_timezone_from_coordinates(lat, lon)
        assert detected_tz == expected_tz, f"Expected {expected_tz} for ({lat}, {lon}), got {detected_tz}"

def test_timezone_detection_edge_cases():
    """Test timezone detection for edge cases"""
    from app.astro.utils import detect_timezone_from_coordinates
    
    # Test edge cases that were problematic before
    test_cases = [
        (61.2181, -149.9003, "America/Anchorage"),  # Anchorage, AK
        (21.3099, -157.8581, "Pacific/Honolulu"),   # Honolulu, HI
        (43.6532, -79.3832, "America/New_York"),   # Toronto, Canada
        (49.2827, -123.1207, "America/Los_Angeles"), # Vancouver, Canada
    ]
    
    for lat, lon, expected_tz in test_cases:
        detected_tz = detect_timezone_from_coordinates(lat, lon)
        assert detected_tz == expected_tz, f"Expected {expected_tz} for ({lat}, {lon}), got {detected_tz}"

def test_utc_conversion_mountain_view_dst():
    """Test UTC conversion for Mountain View during DST"""
    from app.astro.utils import to_utc
    
    # Test with explicit timezone
    dt_utc_explicit = to_utc("2022-03-15T12:36:00", "America/Los_Angeles", None, 37.3861, -122.0839)
    assert dt_utc_explicit.hour == 19  # 12:36 PDT -> 19:36 UTC
    assert dt_utc_explicit.minute == 36
    assert dt_utc_explicit.day == 15
    assert dt_utc_explicit.month == 3
    assert dt_utc_explicit.year == 2022
    
    # Test with coordinate detection (should give same result)
    dt_utc_auto = to_utc("2022-03-15T12:36:00", None, None, 37.3861, -122.0839)
    assert dt_utc_auto.hour == 19  # Should be same as explicit
    assert dt_utc_auto.minute == 36
    assert dt_utc_auto.day == 15
    assert dt_utc_auto.month == 3
    assert dt_utc_auto.year == 2022

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
    assert dt_utc.tzinfo.utcoffset(dt_utc).total_seconds() == 0  # UTC offset should be 0
    
    # Test with offset
    dt_utc = to_utc("1991-03-25T09:46:00", None, 330)  # IST offset
    assert dt_utc.tzinfo.utcoffset(dt_utc).total_seconds() == 0  # UTC offset should be 0

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
    assert cusps[11] == 330.0 # Pisces\
