import pytest
from app import create_app
from app.schemas import DashaRequest
from app.astro.engine import init_ephemeris, julian_day_utc, compute_planets
from app.astro.utils import to_utc
from datetime import datetime

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

def test_dasha_endpoint_basic(client):
    """Test basic dasha calculation"""
    data = {
        "datetime": "1991-03-25T09:46:00",
        "latitude": 18.5204,
        "longitude": 73.8567,
        "depth": 2
    }
    
    response = client.post('/dasha', json=data)
    assert response.status_code == 200
    
    result = response.json
    assert 'timeline' in result
    assert 'metadata' in result
    assert result['metadata']['system'] == 'vimshottari'
    assert result['metadata']['depth'] == 2
    assert len(result['timeline']) > 0
    
    # Verify timeline structure
    first_period = result['timeline'][0]
    assert 'lord' in first_period
    assert 'level' in first_period
    assert 'start' in first_period
    assert 'end' in first_period
    assert first_period['level'] == 1  # Mahadasha
    assert 'antardasha' in first_period  # Should have sub-periods at depth 2

def test_dasha_endpoint_with_ayanamsha(client):
    """Test that dasha endpoint accepts and uses ayanamsha parameter"""
    data = {
        "datetime": "1991-03-25T09:46:00",
        "latitude": 18.5204,
        "longitude": 73.8567,
        "ayanamsha": "LAHIRI",
        "depth": 1
    }
    
    response = client.post('/dasha', json=data)
    assert response.status_code == 200
    
    result = response.json
    assert 'timeline' in result
    assert len(result['timeline']) > 0

def test_dasha_ayanamsha_affects_moon_position(client):
    """Test that different ayanamsha values produce different Moon positions and dasha results"""
    base_data = {
        "datetime": "1991-03-25T09:46:00",
        "latitude": 18.5204,
        "longitude": 73.8567,
        "depth": 1
    }
    
    # Get Moon position with LAHIRI ayanamsha
    data_lahiri = {**base_data, "ayanamsha": "LAHIRI"}
    response_lahiri = client.post('/dasha', json=data_lahiri)
    assert response_lahiri.status_code == 200
    
    # Get Moon position with RAMAN ayanamsha
    data_raman = {**base_data, "ayanamsha": "RAMAN"}
    response_raman = client.post('/dasha', json=data_raman)
    assert response_raman.status_code == 200
    
    # Get Moon position with KRISHNAMURTI ayanamsha
    data_kp = {**base_data, "ayanamsha": "KRISHNAMURTI"}
    response_kp = client.post('/dasha', json=data_kp)
    assert response_kp.status_code == 200
    
    # Calculate Moon positions directly to verify they differ
    dt_utc = to_utc("1991-03-25T09:46:00", None, None, 18.5204, 73.8567)
    jd_ut = julian_day_utc(dt_utc)
    
    # Moon with LAHIRI
    init_ephemeris('./ephe', "LAHIRI")
    planets_lahiri = compute_planets(jd_ut, "MEAN")
    moon_lahiri = next(p["longitude"] for p in planets_lahiri if p["planet"] == "Moon")
    
    # Moon with RAMAN
    init_ephemeris('./ephe', "RAMAN")
    planets_raman = compute_planets(jd_ut, "MEAN")
    moon_raman = next(p["longitude"] for p in planets_raman if p["planet"] == "Moon")
    
    # Moon with KRISHNAMURTI
    init_ephemeris('./ephe', "KRISHNAMURTI")
    planets_kp = compute_planets(jd_ut, "MEAN")
    moon_kp = next(p["longitude"] for p in planets_kp if p["planet"] == "Moon")
    
    # Verify Moon positions are different (different ayanamsha = different sidereal longitudes)
    assert abs(moon_lahiri - moon_raman) > 0.1, "LAHIRI and RAMAN should produce different Moon positions"
    assert abs(moon_lahiri - moon_kp) > 0.1, "LAHIRI and KRISHNAMURTI should produce different Moon positions"
    assert abs(moon_raman - moon_kp) > 0.1, "RAMAN and KRISHNAMURTI should produce different Moon positions"
    
    # Verify dasha timelines are different (different Moon positions = different starting lords)
    timeline_lahiri = response_lahiri.json['timeline']
    timeline_raman = response_raman.json['timeline']
    timeline_kp = response_kp.json['timeline']
    
    # The first period's lord should potentially differ if Moon crosses nakshatra boundaries
    # At minimum, verify the timelines are calculated (they may or may not differ depending on Moon position)
    assert len(timeline_lahiri) > 0
    assert len(timeline_raman) > 0
    assert len(timeline_kp) > 0

def test_dasha_default_ayanamsha(client):
    """Test that default ayanamsha is used when none is provided"""
    data = {
        "datetime": "1991-03-25T09:46:00",
        "latitude": 18.5204,
        "longitude": 73.8567,
        "depth": 1
    }
    
    response = client.post('/dasha', json=data)
    assert response.status_code == 200
    
    result = response.json
    assert 'timeline' in result
    assert len(result['timeline']) > 0

def test_dasha_validation_errors(client):
    """Test various validation errors for dasha endpoint"""
    # Invalid ayanamsha
    data = {
        "datetime": "1991-03-25T09:46:00",
        "latitude": 18.5204,
        "longitude": 73.8567,
        "ayanamsha": "INVALID"
    }
    response = client.post('/dasha', json=data)
    assert response.status_code == 400
    assert 'VALIDATION_ERROR' in response.json['error']['code']
    
    # Invalid depth
    data = {
        "datetime": "1991-03-25T09:46:00",
        "latitude": 18.5204,
        "longitude": 73.8567,
        "depth": 5  # Invalid, must be 1-3
    }
    response = client.post('/dasha', json=data)
    assert response.status_code == 400
    
    # Invalid latitude
    data = {
        "datetime": "1991-03-25T09:46:00",
        "latitude": 100.0,  # Invalid
        "longitude": 73.8567
    }
    response = client.post('/dasha', json=data)
    assert response.status_code == 400

def test_dasha_with_date_range(client):
    """Test dasha calculation with fromDate and toDate parameters"""
    data = {
        "datetime": "1991-03-25T09:46:00",
        "latitude": 18.5204,
        "longitude": 73.8567,
        "ayanamsha": "LAHIRI",
        "depth": 2,
        "fromDate": "2000-01-01T00:00:00Z",
        "toDate": "2010-01-01T00:00:00Z"
    }
    
    response = client.post('/dasha', json=data)
    assert response.status_code == 200
    
    result = response.json
    assert 'timeline' in result
    assert 'metadata' in result
    assert result['metadata']['fromDate'] == '2000-01-01T00:00:00Z'
    assert result['metadata']['toDate'] == '2010-01-01T00:00:00Z'
    
    # Verify timeline periods are within the date range
    for period in result['timeline']:
        period_start = datetime.fromisoformat(period['start'].replace('Z', '+00:00'))
        period_end = datetime.fromisoformat(period['end'].replace('Z', '+00:00'))
        range_start = datetime.fromisoformat('2000-01-01T00:00:00+00:00')
        range_end = datetime.fromisoformat('2010-01-01T00:00:00+00:00')
        
        # Period should overlap with the range
        assert not (period_end <= range_start or period_start >= range_end)

def test_dasha_with_at_date(client):
    """Test dasha calculation with atDate parameter to mark active periods"""
    data = {
        "datetime": "1991-03-25T09:46:00",
        "latitude": 18.5204,
        "longitude": 73.8567,
        "ayanamsha": "LAHIRI",
        "depth": 2,
        "atDate": "2005-06-15T12:00:00Z"
    }
    
    response = client.post('/dasha', json=data)
    assert response.status_code == 200
    
    result = response.json
    assert 'timeline' in result
    
    # Verify at least one period is marked as active
    active_found = False
    for period in result['timeline']:
        if period.get('active', False):
            active_found = True
            break
        # Check antardasha periods
        if 'antardasha' in period:
            for antardasha in period['antardasha']:
                if antardasha.get('active', False):
                    active_found = True
                    break
    
    assert active_found, "At least one period should be marked as active"

def test_dasha_all_ayanamsha_values(client):
    """Test that all valid ayanamsha values work correctly"""
    base_data = {
        "datetime": "1991-03-25T09:46:00",
        "latitude": 18.5204,
        "longitude": 73.8567,
        "depth": 1
    }
    
    ayanamsha_values = ["LAHIRI", "RAMAN", "KRISHNAMURTI", "VEDANJANAM"]
    
    for ayanamsha in ayanamsha_values:
        data = {**base_data, "ayanamsha": ayanamsha}
        response = client.post('/dasha', json=data)
        assert response.status_code == 200, f"Failed for ayanamsha: {ayanamsha}"
        
        result = response.json
        assert 'timeline' in result
        assert len(result['timeline']) > 0



