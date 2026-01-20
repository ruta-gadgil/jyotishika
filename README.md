# Jyotishika

**A Modern Vedic Astrology Platform**

Jyotishika is a Vedic astrology calculation platform built with Flask and Swiss Ephemeris. It provides accurate sidereal astrology calculations, birth chart analysis, and Vimshottari dasha predictions through a REST API.

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

## Features

### Core Calculations
- **Ascendant & Planetary Positions**: Precise sidereal calculations using Swiss Ephemeris
- **Nakshatras & Navamsha**: Traditional Vedic divisional chart calculations with element-based navamsha
- **Vimshottari Dasha System**: Complete 120-year planetary period calculations with mahadasha, antardasha, and pratyantardasha
- **Multiple Ayanamshas**: Support for Lahiri, Raman, and Krishnamurti ayanamshas
- **House Systems**: Whole Sign, Equal House, and Placidus systems
- **Node Types**: Mean and True nodes for Rahu/Ketu calculations

### Platform Features
- **User Authentication**: Secure Google OAuth integration with email allowlist
- **Data Persistence**: PostgreSQL/Supabase backend for user profiles and saved charts
- **RESTful API**: Clean, well-documented API for integration
- **AGPL Compliance**: Full source code transparency and network interaction compliance

## Architecture

This is a full-stack application with:

- **Backend**: Flask REST API powered by Swiss Ephemeris
- **Frontend**: Modern web interface (separate repository)
- **Database**: PostgreSQL (Supabase) for user management and data storage
- **Authentication**: Google OAuth 2.0 with email-based authorization

## Quick Start

### Prerequisites

- Python 3.11+
- Swiss Ephemeris data files
- PostgreSQL database (Supabase recommended)
- Google OAuth credentials

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/ruta-gadgil/jyotishika.git
   cd jyotishika
   ```

2. **Install dependencies**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   # Copy the example environment file
   cp env.example .env
   
   # Edit .env with your configuration:
   # - DATABASE_URL (Supabase connection string)
   # - GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET
   # - SECRET_KEY (generate with: openssl rand -hex 32)
   # - EPHE_PATH (path to Swiss Ephemeris data files)
   ```

4. **Set up the database**
   ```bash
   # Run the schema script in your Supabase SQL Editor
   # Or via command line:
   psql $DATABASE_URL -f backend/sql/schema.sql
   ```

5. **Run the application**
   ```bash
   make run
   # Or directly:
   python -m app
   ```

The API will be available at `http://localhost:8080`

For detailed setup instructions, see the [Backend README](backend/README.md).

## API Examples

### Calculate Birth Chart

```bash
curl -X POST http://localhost:8080/chart \
  -H "Content-Type: application/json" \
  -d '{
    "datetime": "1991-03-25T09:46:00",
    "tz": "Asia/Kolkata",
    "latitude": 18.5204,
    "longitude": 73.8567,
    "houseSystem": "WHOLE_SIGN",
    "ayanamsha": "LAHIRI",
    "nodeType": "MEAN"
  }'
```

### Calculate Vimshottari Dasha

```bash
curl -X POST http://localhost:8080/dasha \
  -H "Content-Type: application/json" \
  -d '{
    "datetime": "1991-03-25T09:46:00",
    "latitude": 18.5204,
    "longitude": 73.8567,
    "ayanamsha": "LAHIRI",
    "depth": 3
  }'
```

For complete API documentation, see the [Backend README](backend/README.md).

## Project Structure

```
jyotishika/
├── backend/
│   ├── app/
│   │   ├── astro/           # Astrology calculation engine
│   │   ├── routes.py        # API endpoints
│   │   ├── auth.py          # Authentication logic
│   │   ├── db.py            # Database operations
│   │   └── models.py        # Data models
│   ├── tests/               # Test suite
│   ├── sql/                 # Database schema
│   ├── requirements.txt     # Python dependencies
│   ├── Dockerfile          # Container configuration
│   └── README.md           # Detailed API documentation
├── LICENSE                 # AGPL-3.0 license
└── README.md              # This file
```

## Documentation

- **[Backend API Documentation](backend/README.md)**: Complete API reference, setup guide, and technical details
- **[Logging Guide](backend/LOGGING_GUIDE.md)**: Logging configuration and best practices
- **[Database RLS Setup](backend/RLS_SETUP.md)**: Row-level security configuration for Supabase
- **[AGPL Compliance](backend/AGPL_COMPLIANCE.md)**: License compliance information

## Development

### Running Tests

```bash
cd backend
make test
```

The test suite includes:
- Nakshatra and navamsha calculation tests
- Ascendant calculation verification
- Planetary position accuracy tests
- Vimshottari dasha timeline validation
- API endpoint integration tests

## License

**GNU Affero General Public License v3.0 (AGPL-3.0)**

This project is licensed under the AGPL-3.0 because it uses [Swiss Ephemeris](https://www.astro.com/swisseph/), which is AGPL-licensed.

### What This Means

**For Users:**
- You have the right to access the complete source code
- This is free and open-source software
- Source code: https://github.com/ruta-gadgil/jyotishika

**For Developers:**
- If you modify this code and run it as a network service, you **must** make your source code available under AGPL-3.0
- You must preserve all copyright notices
- Any derivative works must also be AGPL-3.0 licensed

### Copyright

- **Swiss Ephemeris**: Copyright (C) 1997-2021 Astrodienst AG, Switzerland
- **Jyotishika API**: Copyright (C) 2026 Ruta Gadgil

### License Compliance

This software complies with AGPL v3 Section 13 (Remote Network Interaction). All network users have the right to receive the complete source code.


For the full license text, see the [LICENSE](LICENSE) file or visit https://www.gnu.org/licenses/agpl-3.0.html

### Commercial Licensing

If you need to use this software in a proprietary/closed-source application:
1. **Swiss Ephemeris**: Purchase a commercial license from [Astrodienst AG](https://www.astro.com/swisseph/)
2. **Jyotishika API**: Contact the project maintainer for alternative licensing options

## Support

- **Issues**: Report bugs and request features via [GitHub Issues](https://github.com/ruta-gadgil/jyotishika/issues)
- **Source Code**: https://github.com/ruta-gadgil/jyotishika
- **AGPL Compliance**: Full source code is available to all users under AGPL-3.0

## Acknowledgments

- **Swiss Ephemeris** by Astrodienst AG - High-precision astronomical calculations
- **pyswisseph** by Stanislas Marquis - Python bindings for Swiss Ephemeris
- **Flask** - Web framework
- **Supabase** - PostgreSQL hosting and authentication infrastructure

---

**Note**: This is a Vedic (sidereal) astrology calculation engine. All planetary positions and house cusps are calculated using sidereal zodiac with configurable ayanamsha corrections.
