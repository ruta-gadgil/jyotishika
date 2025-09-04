#!/usr/bin/env python3
"""
Example script demonstrating the Vedic Astrology Backend API
"""

import requests
import json

def test_health_check():
    """Test the health check endpoint"""
    print("Testing health check endpoint...")
    try:
        response = requests.get("http://localhost:8080/healthz")
        if response.status_code == 200:
            print("✓ Health check passed")
            return True
        else:
            print(f"✗ Health check failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("✗ Could not connect to server. Is it running?")
        return False

def test_chart_calculation():
    """Test chart calculation with example data"""
    print("\nTesting chart calculation...")
    
    # Example 1: Birth chart for Mumbai, India
    data1 = {
        "datetime": "1991-03-25T09:46:00",
        "tz": "Asia/Kolkata",
        "latitude": 18.5204,
        "longitude": 73.8567,
        "houseSystem": "WHOLE_SIGN",
        "ayanamsha": "LAHIRI",
        "nodeType": "MEAN",
        "include": {
            "houseCusps": True,
            "housesForEachPlanet": True,
            "signsForEachPlanet": True
        }
    }
    
    try:
        response = requests.post(
            "http://localhost:8080/chart",
            json=data1,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✓ Chart calculation successful")
            print(f"  Ascendant: {result['ascendant']['longitude']:.2f}° (Sign: {result['ascendant']['signIndex']})")
            print(f"  Number of planets: {len(result['planets'])}")
            
            # Show some planet details
            for planet in result['planets'][:3]:  # First 3 planets
                print(f"  {planet['planet']}: {planet['longitude']:.2f}° (Retrograde: {planet['retrograde']})")
            
            return True
        else:
            print(f"✗ Chart calculation failed: {response.status_code}")
            print(f"  Error: {response.json()}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("✗ Could not connect to server")
        return False

def test_validation_errors():
    """Test validation error handling"""
    print("\nTesting validation errors...")
    
    # Test invalid latitude
    data = {
        "datetime": "1991-03-25T09:46:00",
        "tz": "Asia/Kolkata",
        "latitude": 100.0,  # Invalid latitude
        "longitude": 73.8567
    }
    
    try:
        response = requests.post(
            "http://localhost:8080/chart",
            json=data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 400:
            print("✓ Validation error handling works")
            return True
        else:
            print(f"✗ Expected validation error, got: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("✗ Could not connect to server")
        return False

def main():
    print("Vedic Astrology Backend - API Test")
    print("=" * 50)
    
    # Test health check
    if not test_health_check():
        print("\nPlease start the server first:")
        print("  cd backend")
        print("  make run")
        return
    
    # Test chart calculation
    test_chart_calculation()
    
    # Test validation errors
    test_validation_errors()
    
    print("\n" + "=" * 50)
    print("API testing completed!")

if __name__ == "__main__":
    main()
