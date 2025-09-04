#!/usr/bin/env python3
"""
Setup script for Vedic Astrology Backend
"""

import os
import sys
import subprocess
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 9):
        print("✗ Python 3.9+ is required")
        print(f"  Current version: {sys.version}")
        return False
    print(f"✓ Python version: {sys.version.split()[0]}")
    return True

def install_dependencies():
    """Install Python dependencies"""
    print("\nInstalling dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✓ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install dependencies: {e}")
        return False

def create_ephe_directory():
    """Create ephemeris directory if it doesn't exist"""
    ephe_dir = Path("ephe")
    if not ephe_dir.exists():
        ephe_dir.mkdir()
        print("✓ Created ephe/ directory")
    else:
        print("✓ ephe/ directory already exists")
    
    # Check if directory is empty
    if not any(ephe_dir.iterdir()):
        print("⚠ ephe/ directory is empty")
        print("  You need to download Swiss Ephemeris data files:")
        print("  - Visit: https://www.astro.com/ftp/swisseph/ephe/")
        print("  - Download files like: sepl_18.se1, semo_18.se1, etc.")
        print("  - Place them in the ephe/ directory")
    else:
        print("✓ ephe/ directory contains files")

def run_tests():
    """Run installation tests"""
    print("\nRunning installation tests...")
    try:
        subprocess.check_call([sys.executable, "test_installation.py"])
        return True
    except subprocess.CalledProcessError:
        print("✗ Installation tests failed")
        return False

def main():
    print("Vedic Astrology Backend - Setup")
    print("=" * 40)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        sys.exit(1)
    
    # Create ephemeris directory
    create_ephe_directory()
    
    # Run tests
    if run_tests():
        print("\n" + "=" * 40)
        print("✓ Setup completed successfully!")
        print("\nNext steps:")
        print("1. Download Swiss Ephemeris data files to ephe/ directory")
        print("2. Start the server: make run")
        print("3. Test the API: python example_api_test.py")
    else:
        print("\n✗ Setup failed. Please check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
