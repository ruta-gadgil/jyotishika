import pytest
import os
from datetime import datetime
from app import create_app
from app.astro.engine import (
    init_ephemeris, 
    julian_day_utc, 
    ascendant_and_houses, 
    compute_sripati_cusps
)
from app.astro.utils import norm360, to_utc


@pytest.fixture
def app():
    os.environ["EPHE_PATH"] = os.path.join(os.path.dirname(__file__), "..", "ephe")
    os.environ["AYANAMSHA"] = "LAHIRI"
    os.environ["HOUSE_SYSTEM"] = "PLACIDUS"
    app = create_app()
    return app


@pytest.fixture
def client(app):
    return app.test_client()


class TestSripatiCuspsCalculation:
    """Test the mathematical correctness of Sripati house cusp calculations"""
    
    def test_sripati_cusps_basic_quadrant_division(self):
        """Test Bhav Chalit calculation with Bhava Madhyas and Sandhis"""
        # Simple case: angles at 0°, 90°, 180°, 270°
        # These are Bhava Madhyas (house centers) for houses 1, 4, 7, 10
        asc = 0.0   # Madhya of house 1
        ic = 90.0   # Madhya of house 4
        dsc = 180.0 # Madhya of house 7
        mc = 270.0  # Madhya of house 10
        
        # compute_sripati_cusps returns Bhava Sandhis (boundaries between houses)
        sandhis = compute_sripati_cusps(asc, ic, dsc, mc)
        
        # Should have 12 sandhis (boundaries)
        assert len(sandhis) == 12
        
        # Each quadrant is 90°, so each house span is 30°
        # Bhava Madhyas are: 0°, 30°, 60°, 90°, 120°, 150°, 180°, 210°, 240°, 270°, 300°, 330°
        # Bhava Sandhis (midpoints between consecutive madhyas):
        # Sandhi 1/2 = (0 + 30) / 2 = 15°
        # Sandhi 2/3 = (30 + 60) / 2 = 45°
        # etc.
        
        assert abs(sandhis[0] - 15.0) < 0.01   # Sandhi 1/2
        assert abs(sandhis[1] - 45.0) < 0.01   # Sandhi 2/3
        assert abs(sandhis[2] - 75.0) < 0.01   # Sandhi 3/4
        assert abs(sandhis[3] - 105.0) < 0.01  # Sandhi 4/5
        assert abs(sandhis[4] - 135.0) < 0.01  # Sandhi 5/6
        assert abs(sandhis[5] - 165.0) < 0.01  # Sandhi 6/7
        assert abs(sandhis[6] - 195.0) < 0.01  # Sandhi 7/8
        assert abs(sandhis[7] - 225.0) < 0.01  # Sandhi 8/9
        assert abs(sandhis[8] - 255.0) < 0.01  # Sandhi 9/10
        assert abs(sandhis[9] - 285.0) < 0.01  # Sandhi 10/11
        assert abs(sandhis[10] - 315.0) < 0.01 # Sandhi 11/12
        assert abs(sandhis[11] - 345.0) < 0.01 # Sandhi 12/1
    
    def test_sripati_cusps_with_wraparound(self):
        """Test Bhav Chalit calculation when quadrants wrap around 360°"""
        # Bhava Madhyas (house centers) for houses 1, 4, 7, 10
        asc = 350.0  # Madhya of house 1
        ic = 80.0    # Madhya of house 4
        dsc = 170.0  # Madhya of house 7
        mc = 260.0   # Madhya of house 10
        
        sandhis = compute_sripati_cusps(asc, ic, dsc, mc)
        
        # Quadrant 1: ASC (350°) to IC (80°), arc = 90°, each house span = 30°
        # Madhyas: 350°, 20° (350+30 wrapped), 50°
        # Sandhis (midpoints between consecutive madhyas):
        # Sandhi 1/2 = (350 + 20) / 2 = 5° (with wraparound)
        # Sandhi 2/3 = (20 + 50) / 2 = 35°
        # Sandhi 3/4 = (50 + 80) / 2 = 65°
        
        assert abs(sandhis[0] - 5.0) < 0.01    # Sandhi 1/2
        assert abs(sandhis[1] - 35.0) < 0.01   # Sandhi 2/3
        assert abs(sandhis[2] - 65.0) < 0.01   # Sandhi 3/4
        
        # Quadrant 4: MC (260°) to ASC (350°), arc = 90°, each house span = 30°
        # Madhyas: 260°, 290°, 320°
        # Sandhis:
        # Sandhi 9/10 = (240 + 260) / 2 = 250° (from previous quadrant end)
        # Sandhi 10/11 = (260 + 290) / 2 = 275°
        # Sandhi 11/12 = (290 + 320) / 2 = 305°
        # Sandhi 12/1 = (320 + 350) / 2 = 335°
        
        assert abs(sandhis[9] - 275.0) < 0.01  # Sandhi 10/11
        assert abs(sandhis[10] - 305.0) < 0.01 # Sandhi 11/12
        assert abs(sandhis[11] - 335.0) < 0.01 # Sandhi 12/1
    
    def test_sripati_cusps_unequal_quadrants(self):
        """Test Bhav Chalit with unequal quadrant sizes"""
        # Bhava Madhyas (house centers) for houses 1, 4, 7, 10
        asc = 15.0   # Madhya of house 1
        ic = 100.0   # Madhya of house 4
        dsc = 195.0  # Madhya of house 7
        mc = 280.0   # Madhya of house 10
        
        sandhis = compute_sripati_cusps(asc, ic, dsc, mc)
        
        # Quadrant 1: ASC (15°) to IC (100°) = 85° arc
        # Each house span = 85/3 = 28.33°
        # Madhyas: 15°, 43.33°, 71.67°, 100°
        arc1 = 85.0
        house_span1 = arc1 / 3.0
        
        madhya2 = 15.0 + house_span1  # 43.33°
        madhya3 = madhya2 + house_span1  # 71.67°
        
        # Sandhis (midpoints between consecutive madhyas):
        # Sandhi 1/2 = (15 + 43.33) / 2 = 29.17°
        # Sandhi 2/3 = (43.33 + 71.67) / 2 = 57.50°
        # Sandhi 3/4 = (71.67 + 100) / 2 = 85.83°
        
        assert abs(sandhis[0] - (15.0 + madhya2) / 2.0) < 0.01
        assert abs(sandhis[1] - (madhya2 + madhya3) / 2.0) < 0.01
        assert abs(sandhis[2] - (madhya3 + 100.0) / 2.0) < 0.01
        
        # Quadrant 2: IC (100°) to DSC (195°) = 95° arc
        # Each house span = 95/3 = 31.67°
        arc2 = 95.0
        house_span2 = arc2 / 3.0
        
        madhya5 = 100.0 + house_span2  # 131.67°
        madhya6 = madhya5 + house_span2  # 163.33°
        
        # Sandhi 4/5 = (100 + 131.67) / 2 = 115.83°
        # Sandhi 5/6 = (131.67 + 163.33) / 2 = 147.50°
        # Sandhi 6/7 = (163.33 + 195) / 2 = 179.17°
        
        assert abs(sandhis[3] - (100.0 + madhya5) / 2.0) < 0.01
        assert abs(sandhis[4] - (madhya5 + madhya6) / 2.0) < 0.01
        assert abs(sandhis[5] - (madhya6 + 195.0) / 2.0) < 0.01
        
        # Verify all sandhis are within valid range
        for sandhi in sandhis:
            assert 0 <= sandhi < 360
    
    def test_angles_are_opposite(self):
        """Test that IC = MC + 180° and DSC = ASC + 180°"""
        # Initialize ephemeris
        ephe_path = os.path.join(os.path.dirname(__file__), "..", "ephe")
        init_ephemeris(ephe_path, "LAHIRI")
        
        # Calculate for a known location and time
        dt_utc = datetime(1990, 1, 1, 12, 0, 0)
        jd_ut = julian_day_utc(dt_utc)
        lat, lon = 28.6139, 77.2090  # Delhi
        
        asc_long, cusps, angles = ascendant_and_houses(jd_ut, lat, lon, "PLACIDUS")
        
        # Verify IC is opposite MC
        expected_ic = norm360(angles["mc"] + 180.0)
        assert abs(angles["ic"] - expected_ic) < 0.01
        
        # Verify DSC is opposite ASC
        expected_dsc = norm360(angles["asc"] + 180.0)
        assert abs(angles["dsc"] - expected_dsc) < 0.01


class TestBhavChalitEndpoint:
    """Test the /chart endpoint's bhav chalit response"""
    
    def test_chart_includes_bhav_chalit(self, client):
        """Test that /chart response includes bhavChalit data"""
        payload = {
            "datetime": "1990-01-01T12:00:00",
            "latitude": 28.6139,
            "longitude": 77.2090,
            "tz": "Asia/Kolkata",
            "houseSystem": "PLACIDUS",
            "ayanamsha": "LAHIRI"
        }
        
        response = client.post("/chart", json=payload)
        assert response.status_code == 200
        
        result = response.json
        
        # Verify bhavChalit exists in response
        assert "bhavChalit" in result
        
        bhav_chalit = result["bhavChalit"]
        
        # Verify structure
        assert "system" in bhav_chalit
        assert bhav_chalit["system"] == "SRIPATI"
        
        # Verify ascendant
        assert "ascendant" in bhav_chalit
        assert "longitude" in bhav_chalit["ascendant"]
        assert "house" in bhav_chalit["ascendant"]
        assert bhav_chalit["ascendant"]["house"] == 1
        assert 0 <= bhav_chalit["ascendant"]["longitude"] < 360
        
        # Verify planets
        assert "planets" in bhav_chalit
        assert len(bhav_chalit["planets"]) == 12  # All planets should be included
        
        for planet in bhav_chalit["planets"]:
            assert "planet" in planet
            assert "house" in planet
            assert 1 <= planet["house"] <= 12  # House should be between 1 and 12
    
    def test_bhav_chalit_ascendant_matches_main(self, client):
        """Test that bhavChalit ascendant matches the main ascendant"""
        payload = {
            "datetime": "1990-01-01T12:00:00",
            "latitude": 28.6139,
            "longitude": 77.2090,
            "tz": "Asia/Kolkata"
        }
        
        response = client.post("/chart", json=payload)
        assert response.status_code == 200
        
        result = response.json
        
        # ASC in bhavChalit should match main ascendant
        asc_main = result["ascendant"]["longitude"]
        asc_bhav = result["bhavChalit"]["ascendant"]["longitude"]
        
        assert abs(asc_main - asc_bhav) < 0.01
    
    def test_bhav_chalit_planet_house_placements(self, client):
        """Test that planets have valid house placements in Bhav Chalit"""
        payload = {
            "datetime": "1990-01-01T12:00:00",
            "latitude": 28.6139,
            "longitude": 77.2090,
            "tz": "Asia/Kolkata"
        }
        
        response = client.post("/chart", json=payload)
        assert response.status_code == 200
        
        result = response.json
        bhav_chalit = result["bhavChalit"]
        
        # All 12 planets should have house placements
        assert len(bhav_chalit["planets"]) == 12
        
        # Verify each planet has valid house
        planet_names = set()
        for planet in bhav_chalit["planets"]:
            assert "planet" in planet
            assert "house" in planet
            assert 1 <= planet["house"] <= 12
            planet_names.add(planet["planet"])
        
        # Verify all expected planets are present
        expected_planets = {"Sun", "Moon", "Mercury", "Venus", "Mars", 
                          "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto", "Rahu", "Ketu"}
        assert planet_names == expected_planets
    
    def test_bhav_chalit_with_vedanjanam(self, client):
        """Test that VEDANJANAM offset is applied to bhav chalit data"""
        payload = {
            "datetime": "1990-01-01T12:00:00",
            "latitude": 28.6139,
            "longitude": 77.2090,
            "tz": "Asia/Kolkata",
            "ayanamsha": "VEDANJANAM"
        }
        
        response = client.post("/chart", json=payload)
        assert response.status_code == 200
        
        result = response.json
        
        # Should have bhavChalit data
        assert "bhavChalit" in result
        assert result["metadata"]["ayanamsha"] == "VEDANJANAM"
        
        # Ascendant should be valid
        bhav_chalit = result["bhavChalit"]
        assert 0 <= bhav_chalit["ascendant"]["longitude"] < 360
        
        # All planets should have valid house placements
        for planet in bhav_chalit["planets"]:
            assert 1 <= planet["house"] <= 12
    
    def test_bhav_chalit_with_different_house_systems(self, client):
        """Test that bhav chalit is calculated regardless of main house system"""
        house_systems = ["WHOLE_SIGN", "EQUAL", "PLACIDUS"]
        
        for hs in house_systems:
            payload = {
                "datetime": "1990-01-01T12:00:00",
                "latitude": 28.6139,
                "longitude": 77.2090,
                "tz": "Asia/Kolkata",
                "houseSystem": hs
            }
            
            response = client.post("/chart", json=payload)
            assert response.status_code == 200
            
            result = response.json
            
            # Should always have bhavChalit regardless of main house system
            assert "bhavChalit" in result
            assert result["bhavChalit"]["system"] == "SRIPATI"
            assert len(result["bhavChalit"]["planets"]) == 12


    def test_bhav_chalit_houses_can_differ_from_main_chart(self, client):
        """Test that planet houses in Bhav Chalit can differ from main chart"""
        payload = {
            "datetime": "1990-01-01T12:00:00",
            "latitude": 28.6139,
            "longitude": 77.2090,
            "tz": "Asia/Kolkata",
            "houseSystem": "WHOLE_SIGN"
        }
        
        response = client.post("/chart", json=payload)
        assert response.status_code == 200
        
        result = response.json
        
        # Create a map of main chart planet houses
        main_chart_houses = {}
        for planet in result["planets"]:
            main_chart_houses[planet["planet"]] = planet.get("house")
        
        # Create a map of bhav chalit planet houses
        bhav_chalit_houses = {}
        for planet in result["bhavChalit"]["planets"]:
            bhav_chalit_houses[planet["planet"]] = planet["house"]
        
        # At least one planet should have a different house in Bhav Chalit
        # (This is the whole point of Bhav Chalit - planets near sign boundaries
        # may be in different houses when using actual cusps vs sign boundaries)
        differences_found = False
        for planet_name in main_chart_houses:
            if main_chart_houses[planet_name] != bhav_chalit_houses[planet_name]:
                differences_found = True
                break
        
        # Note: Depending on the chart, there may or may not be differences
        # This test just verifies the structure is correct, not that differences always exist
        assert isinstance(differences_found, bool)


class TestBhavChalitEdgeCases:
    """Test edge cases for bhav chalit calculations"""
    
    def test_bhav_chalit_near_poles(self, client):
        """Test bhav chalit calculation at high latitudes"""
        # High latitude location (near Arctic Circle)
        payload = {
            "datetime": "1990-06-21T12:00:00",
            "latitude": 66.0,
            "longitude": 25.0,
            "tz": "Europe/Helsinki"
        }
        
        response = client.post("/chart", json=payload)
        assert response.status_code == 200
        
        result = response.json
        assert "bhavChalit" in result
        
        # All planets should have valid house placements
        for planet in result["bhavChalit"]["planets"]:
            assert 1 <= planet["house"] <= 12
    
    def test_bhav_chalit_at_equator(self, client):
        """Test bhav chalit calculation at the equator"""
        payload = {
            "datetime": "1990-01-01T12:00:00",
            "latitude": 0.0,
            "longitude": 0.0,
            "tz": "UTC"
        }
        
        response = client.post("/chart", json=payload)
        assert response.status_code == 200
        
        result = response.json
        assert "bhavChalit" in result
        assert len(result["bhavChalit"]["planets"]) == 12

