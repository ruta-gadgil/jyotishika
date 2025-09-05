# Environment Configuration

This project uses environment variables for configuration. Here's how to set them up:

## Quick Start

1. **Copy the example file:**
   ```bash
   cp env.example .env
   ```

2. **Edit the `.env` file** with your local settings:
   ```bash
   # Flask Configuration
   FLASK_ENV=development
   PORT=8080
   
   # Ephemeris Data Path
   EPHE_PATH=./backend/ephe
   
   # CORS Configuration
   ALLOWED_ORIGINS=*
   ```

3. **Load environment variables** (optional - for development):
   ```bash
   python backend/load_env.py
   ```

## Environment Variables

### Required Variables
- `EPHE_PATH`: Path to the directory containing ephemeris files (e.g., sepl_18.se1)

### Optional Variables
- `FLASK_ENV`: Flask environment (development/production) - Default: development
- `PORT`: Server port - Default: 8080
- `ALLOWED_ORIGINS`: Comma-separated list of allowed CORS origins - Default: *
- `DEBUG`: Enable debug mode (true/false) - Default: false
- `TESTING`: Enable testing mode (true/false) - Default: false
- `LOG_LEVEL`: Logging level (DEBUG/INFO/WARNING/ERROR) - Default: INFO

## Files

- `env.example`: Template file with all available environment variables
- `local.env`: Local development environment file (not tracked in git)
- `.env`: Standard environment file (not tracked in git)
- `backend/load_env.py`: Utility script to load environment variables

## Security Notes

- Never commit `.env` files to version control
- Use different environment files for different environments (dev/staging/prod)
- Keep sensitive data (API keys, secrets) in environment variables, not in code

## Production Deployment

For production, set environment variables directly on your server or use your deployment platform's environment variable configuration.
