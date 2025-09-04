#!/usr/bin/env python3
"""
Simple test script to verify the vedic astrology backend installation
"""

import sys
import os

def test_imports():
    """Test if all required modules can be imported"""
    try:
        import flask
        print("✓ Flask imported successfully")
    except ImportError as e:
        print(f"✗ Flask import failed: {e}")
        return False
    
    try:
        import pyswisseph
        print("✓ Swiss Ephemeris imported successfully")
    except ImportError as e:
        print(f"✗ Swiss Ephemeris import failed: {e}")
        return False
    
    try:
        import pydantic
        print("✓ Pydantic imported successfully")
    except ImportError as e:
        print(f"✗ Pydantic import failed: {e}")
        return False
    
    return True

def test_app_creation():
    """Test if the Flask app can be created"""
    try:
        # Temporarily set EPHE_PATH for testing
        os.environ['EPHE_PATH'] = './ephe'
        
        from app import create_app
        app = create_app()
        print("✓ Flask app created successfully")
        return True
    except Exception as e:
        print(f"✗ Flask app creation failed: {e}")
        return False

def test_ephemeris_path():
    """Test if ephemeris path exists"""
    ephe_path = os.environ.get('EPHE_PATH', './ephe')
    if os.path.isdir(ephe_path):
        print(f"✓ Ephemeris path exists: {ephe_path}")
        return True
    else:
        print(f"⚠ Ephemeris path not found: {ephe_path}")
        print("  You'll need to download Swiss Ephemeris data files")
        return False

def main():
    print("Vedic Astrology Backend - Installation Test")
    print("=" * 50)
    
    success = True
    
    # Test imports
    print("\n1. Testing imports...")
    if not test_imports():
        success = False
    
    # Test app creation
    print("\n2. Testing app creation...")
    if not test_app_creation():
        success = False
    
    # Test ephemeris path
    print("\n3. Testing ephemeris path...")
    test_ephemeris_path()
    
    print("\n" + "=" * 50)
    if success:
        print("✓ All tests passed! The backend is ready to run.")
        print("\nTo start the server:")
        print("  make run")
    else:
        print("✗ Some tests failed. Please check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
