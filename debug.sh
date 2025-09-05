#!/bin/bash

# Debug launch script for Jyotishika Flask app
# This script sets up the environment and launches the Flask app in debug mode

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔧 Setting up Jyotishika Flask app in debug mode...${NC}"

# Check if we're in the right directory
if [ ! -f "backend/app/__init__.py" ]; then
    echo -e "${RED}❌ Error: Please run this script from the project root directory${NC}"
    exit 1
fi

# Set environment variables for debug mode
export FLASK_ENV=development
export FLASK_DEBUG=1
export DEBUG=True
export LOG_LEVEL=DEBUG
export EPHE_PATH=./backend/ephe
export PORT=8080
export ALLOWED_ORIGINS=*

echo -e "${GREEN}✅ Environment variables set:${NC}"
echo -e "  FLASK_ENV: $FLASK_ENV"
echo -e "  FLASK_DEBUG: $FLASK_DEBUG"
echo -e "  DEBUG: $DEBUG"
echo -e "  LOG_LEVEL: $LOG_LEVEL"
echo -e "  EPHE_PATH: $EPHE_PATH"
echo -e "  PORT: $PORT"

# Check if ephemeris data exists
if [ ! -d "$EPHE_PATH" ]; then
    echo -e "${RED}❌ Error: Ephemeris data directory not found at $EPHE_PATH${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Ephemeris data directory found${NC}"

# Change to backend directory
cd backend

echo -e "${BLUE}🚀 Starting Flask app in debug mode...${NC}"
echo -e "${YELLOW}💡 You can now set breakpoints in your code and they will be hit!${NC}"
echo -e "${YELLOW}💡 The app will be available at: http://localhost:8080${NC}"
echo -e "${YELLOW}💡 Health check endpoint: http://localhost:8080/healthz${NC}"
echo ""

# Activate virtual environment and launch Flask app with debug mode
source venv/bin/activate
cd backend
FLASK_APP=app python -m flask run --host=0.0.0.0 --port=8080 --debug
