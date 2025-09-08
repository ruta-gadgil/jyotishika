"""
Comprehensive Ascendant Calculation Tests

This module contains detailed unit tests for ascendant calculation
across different locations, times, ayanamsha systems, and house systems.
"""

import pytest
from app import create_app
from app.astro.utils import to_utc, norm360, sign_index, house_from_sign
from app.astro.engine import julian_day_utc, compute_whole_sign_cusps, ascendant_and_houses
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

class TestAscendantCalculation:
    """Test class for comprehensive ascendant calculation tests"""

    # Comprehensive Ascendant Calculation Tests
    def test_ascendant_calculation_mumbai(self, client):
        """Test ascendant calculation for Pune, India - March 25, 1991, 09:46:00 IST"""
        data = {
            "datetime": "1991-03-25T09:46:00",
            "tz": "Asia/Kolkata",
            "latitude": 18.5246,
            "longitude": 73.8786,
            "houseSystem": "WHOLE_SIGN",
            "ayanamsha": "LAHIRI",
            "nodeType": "MEAN"
        }
        
        response = client.post('/chart', json=data)
        assert response.status_code == 200
        
        result = response.json
        ascendant = result['ascendant']
        
        # Expected: Taurus ascendant (Index: 1)
        assert ascendant['signIndex'] == 1
        # i think it should be 35.92
        assert ascendant['longitude'] == pytest.approx(35.72, abs=0.1)
        assert ascendant['house'] == 1
        
    
    def test_mumbai_standard_case(self, client):
        """Test Mumbai, India - March 25, 1991, 09:46:00 IST"""
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
        ascendant = result['ascendant']
        
        # Expected: Taurus ascendant (Index: 1)
        assert ascendant['signIndex'] == 1
        assert ascendant['longitude'] == pytest.approx(35.46, abs=0.1)
        assert ascendant['house'] == 1
        
        # Verify degrees in sign
        degrees_in_sign = ascendant['longitude'] % 30.0
        assert degrees_in_sign == pytest.approx(5.46, abs=0.1)

    def test_san_francisco_case(self, client):
        """Test San Francisco, USA - September 3, 2025, 12:30:00 PDT"""
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
        ascendant = result['ascendant']
        
        # Expected: Libra ascendant (Index: 6)
        assert ascendant['signIndex'] == 6
        assert ascendant['longitude'] == pytest.approx(206.87, abs=0.1)
        assert ascendant['house'] == 1

    def test_delhi_case(self, client):
        """Test Delhi, India - March 25, 1991, 09:46:00 IST"""
        data = {
            "datetime": "1991-03-25T09:46:00",
            "tz": "Asia/Kolkata",
            "latitude": 28.6139,
            "longitude": 77.2090,
            "houseSystem": "WHOLE_SIGN",
            "ayanamsha": "LAHIRI",
            "nodeType": "MEAN"
        }
        
        response = client.post('/chart', json=data)
        assert response.status_code == 200
        
        result = response.json
        ascendant = result['ascendant']
        
        # Expected: Taurus ascendant (Index: 1)
        assert ascendant['signIndex'] == 1
        assert ascendant['longitude'] == pytest.approx(43.86, abs=0.1)
        assert ascendant['house'] == 1

    def test_new_york_case(self, client):
        """Test New York, USA - March 25, 1991, 09:46:00 EST"""
        data = {
            "datetime": "1991-03-25T09:46:00",
            "tz": "America/New_York",
            "latitude": 40.7128,
            "longitude": -74.0060,
            "houseSystem": "WHOLE_SIGN",
            "ayanamsha": "LAHIRI",
            "nodeType": "MEAN"
        }
        
        response = client.post('/chart', json=data)
        assert response.status_code == 200
        
        result = response.json
        ascendant = result['ascendant']
        
        # Expected: Taurus ascendant (Index: 1)
        assert ascendant['signIndex'] == 1
        assert ascendant['longitude'] == pytest.approx(58.66, abs=0.1)
        assert ascendant['house'] == 1

    def test_london_case(self, client):
        """Test London, UK - March 25, 1991, 09:46:00 GMT"""
        data = {
            "datetime": "1991-03-25T09:46:00",
            "tz": "Europe/London",
            "latitude": 51.5074,
            "longitude": -0.1278,
            "houseSystem": "WHOLE_SIGN",
            "ayanamsha": "LAHIRI",
            "nodeType": "MEAN"
        }
        
        response = client.post('/chart', json=data)
        assert response.status_code == 200
        
        result = response.json
        ascendant = result['ascendant']
        
        # Expected: Gemini ascendant (Index: 2) - different due to longitude
        assert ascendant['signIndex'] == 2
        assert ascendant['longitude'] == pytest.approx(67.87, abs=0.1)
        assert ascendant['house'] == 1

    def test_sydney_case(self, client):
        """Test Sydney, Australia - March 25, 1991, 09:46:00 AEST"""
        data = {
            "datetime": "1991-03-25T09:46:00",
            "tz": "Australia/Sydney",
            "latitude": -33.8688,
            "longitude": 151.2093,
            "houseSystem": "WHOLE_SIGN",
            "ayanamsha": "LAHIRI",
            "nodeType": "MEAN"
        }
        
        response = client.post('/chart', json=data)
        assert response.status_code == 200
        
        result = response.json
        ascendant = result['ascendant']
        
        # Expected: Aries ascendant (Index: 0) - different due to longitude and hemisphere
        assert ascendant['signIndex'] == 0
        assert ascendant['longitude'] == pytest.approx(26.02, abs=0.1)
        assert ascendant['house'] == 1

    def test_different_ayanamsha_systems(self, client):
        """Test different ayanamsha systems for Mumbai case"""
        base_data = {
            "datetime": "1991-03-25T09:46:00",
            "tz": "Asia/Kolkata",
            "latitude": 18.5204,
            "longitude": 73.8567,
            "houseSystem": "WHOLE_SIGN",
            "nodeType": "MEAN"
        }
        
        # Test LAHIRI ayanamsha
        data_lahiri = {**base_data, "ayanamsha": "LAHIRI"}
        response = client.post('/chart', json=data_lahiri)
        assert response.status_code == 200
        result_lahiri = response.json
        asc_lahiri = result_lahiri['ascendant']['longitude']
        
        # Test RAMAN ayanamsha
        data_raman = {**base_data, "ayanamsha": "RAMAN"}
        response = client.post('/chart', json=data_raman)
        assert response.status_code == 200
        result_raman = response.json
        asc_raman = result_raman['ascendant']['longitude']
        
        # Test KRISHNAMURTI ayanamsha
        data_krishnamurti = {**base_data, "ayanamsha": "KRISHNAMURTI"}
        response = client.post('/chart', json=data_krishnamurti)
        assert response.status_code == 200
        result_krishnamurti = response.json
        asc_krishnamurti = result_krishnamurti['ascendant']['longitude']
        
        # All should be Taurus ascendant (Index: 1)
        assert result_lahiri['ascendant']['signIndex'] == 1
        assert result_raman['ascendant']['signIndex'] == 1
        assert result_krishnamurti['ascendant']['signIndex'] == 1
        
        # Check expected differences between ayanamsha systems
        assert abs(asc_raman - asc_lahiri) == pytest.approx(1.45, abs=0.1)  # ~1.45° difference
        assert abs(asc_krishnamurti - asc_lahiri) == pytest.approx(0.10, abs=0.1)  # ~0.10° difference

    def test_different_times(self, client):
        """Test different times for Mumbai case"""
        base_data = {
            "tz": "Asia/Kolkata",
            "latitude": 18.5204,
            "longitude": 73.8567,
            "houseSystem": "WHOLE_SIGN",
            "ayanamsha": "LAHIRI",
            "nodeType": "MEAN"
        }
        
        # Test midnight
        data_midnight = {**base_data, "datetime": "1991-03-25T00:00:00"}
        response = client.post('/chart', json=data_midnight)
        assert response.status_code == 200
        result_midnight = response.json
        assert result_midnight['ascendant']['signIndex'] == 7  # Scorpio
        
        # Test noon
        data_noon = {**base_data, "datetime": "1991-03-25T12:00:00"}
        response = client.post('/chart', json=data_noon)
        assert response.status_code == 200
        result_noon = response.json
        assert result_noon['ascendant']['signIndex'] == 2  # Gemini

    def test_different_house_systems(self, client):
        """Test that different house systems give the same ascendant"""
        base_data = {
            "datetime": "1991-03-25T09:46:00",
            "tz": "Asia/Kolkata",
            "latitude": 18.5204,
            "longitude": 73.8567,
            "ayanamsha": "LAHIRI",
            "nodeType": "MEAN"
        }
        
        house_systems = ["WHOLE_SIGN", "EQUAL", "PLACIDUS"]
        ascendant_longitudes = []
        
        for house_system in house_systems:
            data = {**base_data, "houseSystem": house_system}
            response = client.post('/chart', json=data)
            assert response.status_code == 200
            result = response.json
            ascendant_longitudes.append(result['ascendant']['longitude'])
        
        # All house systems should give the same ascendant longitude
        for i in range(1, len(ascendant_longitudes)):
            assert ascendant_longitudes[i] == pytest.approx(ascendant_longitudes[0], abs=1e-10)

    def test_edge_cases(self, client):
        """Test ascendant calculation edge cases"""
        # Test with UTC timezone
        data = {
            "datetime": "1991-03-25T09:46:00",
            "tz": "UTC",
            "latitude": 0.0,  # Equator
            "longitude": 0.0,
            "houseSystem": "WHOLE_SIGN",
            "ayanamsha": "LAHIRI",
            "nodeType": "MEAN"
        }
        
        response = client.post('/chart', json=data)
        assert response.status_code == 200
        result = response.json
        assert 'ascendant' in result
        assert 'signIndex' in result['ascendant']
        assert 0 <= result['ascendant']['signIndex'] <= 11

    def test_precision(self, client):
        """Test ascendant calculation precision"""
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
        
        ascendant = result['ascendant']
        
        # Test that longitude is properly rounded to 2 decimal places
        assert isinstance(ascendant['longitude'], (int, float))
        assert ascendant['longitude'] == round(ascendant['longitude'], 2)
        
        # Test that sign index is valid
        assert isinstance(ascendant['signIndex'], int)
        assert 0 <= ascendant['signIndex'] <= 11
        
        # Test that house is 1 (ascendant is always in house 1)
        assert ascendant['house'] == 1

    def test_sign_index_edge_cases(self):
        """Test sign_index function edge cases"""
        # Test the current sign_index function behavior
        assert sign_index(0.0) == 0    # Aries
        assert sign_index(29.99) == 0  # Aries
        assert sign_index(30.0) == 1   # Taurus
        assert sign_index(359.99) == 11 # Pisces
        assert sign_index(360.0) == 12  # Current behavior (returns 12 for 360°)
        assert sign_index(390.0) == 13  # Current behavior (390° = 30° + 360°)
        assert sign_index(720.0) == 24  # Current behavior (720° = 0° + 2*360°)
        assert sign_index(-30.0) == -1  # Current behavior (negative values)

    def test_ascendant_calculation_consistency(self):
        """Test ascendant calculation consistency using engine directly"""
        from app.astro.engine import init_ephemeris
        
        # Test case: Mumbai, India - March 25, 1991, 09:46:00 IST
        dt_utc = to_utc("1991-03-25T09:46:00", "Asia/Kolkata", None)
        jd_ut = julian_day_utc(dt_utc)
        
        # Initialize ephemeris
        init_ephemeris('./ephe', "LAHIRI")
        
        # Test different house systems
        house_systems = ["WHOLE_SIGN", "EQUAL", "PLACIDUS"]
        ascendant_longitudes = []
        
        for house_system in house_systems:
            asc_long, cusps = ascendant_and_houses(jd_ut, 18.5204, 73.8567, house_system)
            ascendant_longitudes.append(asc_long)
        
        # All house systems should give the same ascendant longitude
        for i in range(1, len(ascendant_longitudes)):
            assert ascendant_longitudes[i] == pytest.approx(ascendant_longitudes[0], abs=1e-10)
        
        # Verify the ascendant is Taurus (Index: 1)
        asc_sign = sign_index(ascendant_longitudes[0])
        assert asc_sign == 1  # Taurus
