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
    assert cusps[11] == 330.0 # Pisces


# def test_ascendant_calculation_san_francisco(client):
#     """Test ascendant calculation for San Francisco, USA - September 3, 2025, 12:30:00 PDT"""
#     data = {
#         "datetime": "2025-09-03T12:30:00",
#         "tz": "America/Los_Angeles",
#         "latitude": 37.7749,
#         "longitude": -122.4194,
#         "houseSystem": "WHOLE_SIGN",
#         "ayanamsha": "LAHIRI",
#         "nodeType": "MEAN"
#     }
    
#     response = client.post('/chart', json=data)
#     assert response.status_code == 200
    
#     result = response.json
#     ascendant = result['ascendant']
    
#     # Expected: Libra ascendant (Index: 6)
#     assert ascendant['signIndex'] == 6
#     assert ascendant['longitude'] == pytest.approx(206.87, abs=0.1)
#     assert ascendant['house'] == 1

# def test_ascendant_calculation_delhi(client):
#     """Test ascendant calculation for Delhi, India - March 25, 1991, 09:46:00 IST"""
#     data = {
#         "datetime": "1991-03-25T09:46:00",
#         "tz": "Asia/Kolkata",
#         "latitude": 28.6139,
#         "longitude": 77.2090,
#         "houseSystem": "WHOLE_SIGN",
#         "ayanamsha": "LAHIRI",
#         "nodeType": "MEAN"
#     }
    
#     response = client.post('/chart', json=data)
#     assert response.status_code == 200
    
#     result = response.json
#     ascendant = result['ascendant']
    
#     # Expected: Taurus ascendant (Index: 1)
#     assert ascendant['signIndex'] == 1
#     assert ascendant['longitude'] == pytest.approx(43.86, abs=0.1)
#     assert ascendant['house'] == 1

# def test_ascendant_calculation_new_york(client):
#     """Test ascendant calculation for New York, USA - March 25, 1991, 09:46:00 EST"""
#     data = {
#         "datetime": "1991-03-25T09:46:00",
#         "tz": "America/New_York",
#         "latitude": 40.7128,
#         "longitude": -74.0060,
#         "houseSystem": "WHOLE_SIGN",
#         "ayanamsha": "LAHIRI",
#         "nodeType": "MEAN"
#     }
    
#     response = client.post('/chart', json=data)
#     assert response.status_code == 200
    
#     result = response.json
#     ascendant = result['ascendant']
    
#     # Expected: Taurus ascendant (Index: 1)
#     assert ascendant['signIndex'] == 1
#     assert ascendant['longitude'] == pytest.approx(58.66, abs=0.1)
#     assert ascendant['house'] == 1

# def test_ascendant_calculation_london(client):
#     """Test ascendant calculation for London, UK - March 25, 1991, 09:46:00 GMT"""
#     data = {
#         "datetime": "1991-03-25T09:46:00",
#         "tz": "Europe/London",
#         "latitude": 51.5074,
#         "longitude": -0.1278,
#         "houseSystem": "WHOLE_SIGN",
#         "ayanamsha": "LAHIRI",
#         "nodeType": "MEAN"
#     }
    
#     response = client.post('/chart', json=data)
#     assert response.status_code == 200
    
#     result = response.json
#     ascendant = result['ascendant']
    
#     # Expected: Gemini ascendant (Index: 2) - different due to longitude
#     assert ascendant['signIndex'] == 2
#     assert ascendant['longitude'] == pytest.approx(67.87, abs=0.1)
#     assert ascendant['house'] == 1

# def test_ascendant_calculation_sydney(client):
#     """Test ascendant calculation for Sydney, Australia - March 25, 1991, 09:46:00 AEST"""
#     data = {
#         "datetime": "1991-03-25T09:46:00",
#         "tz": "Australia/Sydney",
#         "latitude": -33.8688,
#         "longitude": 151.2093,
#         "houseSystem": "WHOLE_SIGN",
#         "ayanamsha": "LAHIRI",
#         "nodeType": "MEAN"
#     }
    
#     response = client.post('/chart', json=data)
#     assert response.status_code == 200
    
#     result = response.json
#     ascendant = result['ascendant']
    
#     # Expected: Aries ascendant (Index: 0) - different due to longitude and hemisphere
#     assert ascendant['signIndex'] == 0
#     assert ascendant['longitude'] == pytest.approx(26.02, abs=0.1)
#     assert ascendant['house'] == 1

# def test_ascendant_calculation_different_ayanamsha(client):
#     """Test ascendant calculation with different ayanamsha systems"""
#     base_data = {
#         "datetime": "1991-03-25T09:46:00",
#         "tz": "Asia/Kolkata",
#         "latitude": 18.5204,
#         "longitude": 73.8567,
#         "houseSystem": "WHOLE_SIGN",
#         "nodeType": "MEAN"
#     }
    
#     # Test LAHIRI ayanamsha
#     data_lahiri = {**base_data, "ayanamsha": "LAHIRI"}
#     response = client.post('/chart', json=data_lahiri)
#     assert response.status_code == 200
#     result_lahiri = response.json
#     asc_lahiri = result_lahiri['ascendant']['longitude']
    
#     # Test RAMAN ayanamsha
#     data_raman = {**base_data, "ayanamsha": "RAMAN"}
#     response = client.post('/chart', json=data_raman)
#     assert response.status_code == 200
#     result_raman = response.json
#     asc_raman = result_raman['ascendant']['longitude']
    
#     # Test KRISHNAMURTI ayanamsha
#     data_krishnamurti = {**base_data, "ayanamsha": "KRISHNAMURTI"}
#     response = client.post('/chart', json=data_krishnamurti)
#     assert response.status_code == 200
#     result_krishnamurti = response.json
#     asc_krishnamurti = result_krishnamurti['ascendant']['longitude']
    
#     # All should be Taurus ascendant (Index: 1)
#     assert result_lahiri['ascendant']['signIndex'] == 1
#     assert result_raman['ascendant']['signIndex'] == 1
#     assert result_krishnamurti['ascendant']['signIndex'] == 1
    
#     # Check expected differences between ayanamsha systems
#     assert abs(asc_raman - asc_lahiri) == pytest.approx(1.45, abs=0.1)  # ~1.45° difference
#     assert abs(asc_krishnamurti - asc_lahiri) == pytest.approx(0.10, abs=0.1)  # ~0.10° difference

# def test_ascendant_calculation_different_times(client):
#     """Test ascendant calculation with different times"""
#     base_data = {
#         "tz": "Asia/Kolkata",
#         "latitude": 18.5204,
#         "longitude": 73.8567,
#         "houseSystem": "WHOLE_SIGN",
#         "ayanamsha": "LAHIRI",
#         "nodeType": "MEAN"
#     }
    
#     # Test midnight
#     data_midnight = {**base_data, "datetime": "1991-03-25T00:00:00"}
#     response = client.post('/chart', json=data_midnight)
#     assert response.status_code == 200
#     result_midnight = response.json
#     assert result_midnight['ascendant']['signIndex'] == 7  # Scorpio
    
#     # Test noon
#     data_noon = {**base_data, "datetime": "1991-03-25T12:00:00"}
#     response = client.post('/chart', json=data_noon)
#     assert response.status_code == 200
#     result_noon = response.json
#     assert result_noon['ascendant']['signIndex'] == 2  # Gemini

# def test_ascendant_calculation_different_house_systems(client):
#     """Test that different house systems give the same ascendant"""
#     base_data = {
#         "datetime": "1991-03-25T09:46:00",
#         "tz": "Asia/Kolkata",
#         "latitude": 18.5204,
#         "longitude": 73.8567,
#         "ayanamsha": "LAHIRI",
#         "nodeType": "MEAN"
#     }
    
#     house_systems = ["WHOLE_SIGN", "EQUAL", "PLACIDUS"]
#     ascendant_longitudes = []
    
#     for house_system in house_systems:
#         data = {**base_data, "houseSystem": house_system}
#         response = client.post('/chart', json=data)
#         assert response.status_code == 200
#         result = response.json
#         ascendant_longitudes.append(result['ascendant']['longitude'])
    
#     # All house systems should give the same ascendant longitude
#     for i in range(1, len(ascendant_longitudes)):
#         assert ascendant_longitudes[i] == pytest.approx(ascendant_longitudes[0], abs=1e-10)

# def test_ascendant_calculation_edge_cases(client):
#     """Test ascendant calculation edge cases"""
#     # Test with UTC timezone
#     data = {
#         "datetime": "1991-03-25T09:46:00",
#         "tz": "UTC",
#         "latitude": 0.0,  # Equator
#         "longitude": 0.0,
#         "houseSystem": "WHOLE_SIGN",
#         "ayanamsha": "LAHIRI",
#         "nodeType": "MEAN"
#     }
    
#     response = client.post('/chart', json=data)
#     assert response.status_code == 200
#     result = response.json
#     assert 'ascendant' in result
#     assert 'signIndex' in result['ascendant']
#     assert 0 <= result['ascendant']['signIndex'] <= 11

# def test_ascendant_calculation_precision(client):
#     """Test ascendant calculation precision"""
#     data = {
#         "datetime": "1991-03-25T09:46:00",
#         "tz": "Asia/Kolkata",
#         "latitude": 18.5204,
#         "longitude": 73.8567,
#         "houseSystem": "WHOLE_SIGN",
#         "ayanamsha": "LAHIRI",
#         "nodeType": "MEAN"
#     }
    
#     response = client.post('/chart', json=data)
#     assert response.status_code == 200
#     result = response.json
    
#     ascendant = result['ascendant']
    
#     # Test that longitude is properly rounded to 2 decimal places
#     assert isinstance(ascendant['longitude'], (int, float))
#     assert ascendant['longitude'] == round(ascendant['longitude'], 2)
    
#     # Test that sign index is valid
#     assert isinstance(ascendant['signIndex'], int)
#     assert 0 <= ascendant['signIndex'] <= 11
    
#     # Test that house is 1 (ascendant is always in house 1)
#     assert ascendant['house'] == 1
