# Vedic Astrology Backend API

A Flask-based backend API for computing vedic astrology charts using Swiss Ephemeris.

## Features

- **Ascendant Calculation**: Sidereal (Lahiri) ascendant computation
- **Planetary Positions**: Longitudes, speeds, and retrograde motion
- **Nakshatra & Navamsha**: For ascendant and every planet, response includes
  - `nakshatra`: `{ name, index }` (1–27)
  - `charan`: integer 1–4
  - `navamsha`: `{ sign, signIndex, ordinal, degreeInNavamsha }`
    - Uses element-based calculation: Fire→Aries, Earth→Capricorn, Air→Libra, Water→Cancer
- **Vimshottari Dasha System**: Complete 120-year planetary periods calculation
  - Mahadasha, Antardasha, and Pratyantardasha periods
  - Configurable depth (1-3 levels)
  - Date range filtering and active period marking
  - Defaults to full 120-year cycle from birth for prediction
  - Based on Moon's nakshatra position at birth
- **House Systems**: Support for Whole Sign, Equal, and Placidus
- **Ayanamsha**: Lahiri, Raman, and Krishnamurti
- **Node Types**: Mean and True nodes (Rahu/Ketu)

## Quick Start

### Prerequisites

- Python 3.11+
- Swiss Ephemeris data files (place in `ephe/` directory)

### Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up Swiss Ephemeris data:
   ```bash
   # Download Swiss Ephemeris files and place in ephe/ directory
   # Files should include: sepl_18.se1, semo_18.se1, etc.
   ```

4. Run the application:
   ```bash
   make run
   ```

### API Usage

#### POST /chart

Calculate a vedic astrology chart:

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
    "nodeType": "MEAN",
    "include": {"housesForEachPlanet": true, "signsForEachPlanet": true}
  }'
```

Example response (truncated):

```json
{
  "metadata": {
    "system": "sidereal",
    "ayanamsha": "LAHIRI"
  },
  "ascendant": { 
    "longitude": 70.04, 
    "signIndex": 2, 
    "house": 1,
    "nakshatra": { "name": "Punarvasu", "index": 7 },
    "charan": 2,
    "navamsha": { "sign": "Leo", "signIndex": 4, "ordinal": 3, "degreeInNavamsha": 1.2345 }
  },
  "planets": [
    {
      "planet": "Sun",
      "longitude": 340.28,
      "speed": 0.9909,
      "retrograde": false,
      "signIndex": 11,
      "nakshatra": { "name": "Shatabhisha", "index": 24 },
      "charan": 2,
      "navamsha": { "sign": "Capricorn", "signIndex": 9, "ordinal": 6, "degreeInNavamsha": 1.2345 },
      "house": 10
    }
  ]
}
```

#### POST /dasha

Calculate Vimshottari dasha periods:

```bash
curl -X POST http://localhost:8080/dasha \
  -H "Content-Type: application/json" \
  -d '{
    "datetime": "1991-03-25T09:46:00",
    "latitude": 18.5204,
    "longitude": 73.8567,
    "ayanamsha": "LAHIRI",
    "depth": 3,
    "fromDate": "1991-03-25T00:00:00Z",
    "toDate": "2025-12-31T23:59:59Z",
    "atDate": "2024-01-15T12:00:00Z"
  }'
```

**Note**: `fromDate`, `toDate`, and `atDate` are optional parameters. If `toDate` is not provided, it defaults to 120 years from birth for complete Vimshottari cycle prediction.

Example response (truncated):

```json
{
  "timeline": [
    {
      "lord": "Moon",
      "level": 1,
      "start": "1991-03-25T09:46:00Z",
      "end": "2001-03-25T09:46:00Z",
      "durationDays": 3652.5,
      "yearsShare": 10,
      "active": false,
      "antardasha": [
        {
          "lord": "Moon",
          "level": 2,
          "start": "1991-03-25T09:46:00Z",
          "end": "1992-01-25T09:46:00Z",
          "durationDays": 304.375,
          "yearsShare": 10,
          "active": false,
          "pratyantardasha": [...]
        }
      ]
    }
  ],
  "metadata": {
    "system": "vimshottari",
    "depth": 3,
    "fromDate": "1991-03-25T00:00:00Z",
    "toDate": "2025-12-31T23:59:59Z"
  }
}
```

#### GET /healthz

Health check endpoint:

```bash
curl http://localhost:8080/healthz
```

## Setup & Configuration

### Environment Variables

Create a `.env` or `local.env` file (see `env.example` for template):

**Required:**
```bash
# Swiss Ephemeris data files directory
EPHE_PATH=./ephe

# PostgreSQL database (Supabase)
DATABASE_URL=postgresql://postgres.[PROJECT]:[PASSWORD]@db.[REGION].supabase.co:5432/postgres

# Google OAuth (get from Google Cloud Console)
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
APP_BASE_URL=http://localhost:8000
FRONTEND_BASE_URL=http://localhost:3000

# Security (generate with: openssl rand -hex 32)
SECRET_KEY=your-secret-key-here
```

**Optional:**
```bash
FLASK_ENV=development              # development | production
PORT=8080                          # Server port
ALLOWED_ORIGINS=*                  # CORS origins (comma-separated)
LOG_LEVEL=INFO                     # DEBUG | INFO | WARNING | ERROR
```

**Production Notes:**
- Use **Session Pooler** URL (port 6543) for `DATABASE_URL` in production
- Set `ALLOWED_ORIGINS` to specific domains (no wildcards)
- Set `FLASK_ENV=production` for production deployments
- Generate a strong `SECRET_KEY` and keep it secure

### Database Setup

This application uses PostgreSQL (Supabase) for user authentication and data storage.

**1. Create Supabase Project:**
- Go to [Supabase](https://supabase.com/)
- Create a new project
- Get your connection string from Project Settings > Database

**2. Apply Database Schema:**

```bash
# Option A: Supabase Dashboard
# - Go to SQL Editor
# - Copy contents of backend/sql/schema.sql
# - Run the query

# Option B: Command Line
psql $DATABASE_URL -f backend/sql/schema.sql
```

This creates the following tables:
- `users` - User accounts (auto-created on first login)
- `approved_users` - Email allowlist for authorization
- `profiles` - User birth chart profiles
- `charts` - Saved birth charts

**3. Add Approved Users:**

Users must be added to the `approved_users` table before they can log in:

```sql
-- Add users to allowlist
INSERT INTO approved_users (email, note) VALUES
    ('your-email@example.com', 'Admin'),
    ('user@example.com', 'Beta tester');
```

### Google OAuth Setup

**1. Create OAuth Client:**
- Go to [Google Cloud Console](https://console.cloud.google.com/)
- Navigate to APIs & Services > Credentials
- Create OAuth 2.0 Client ID (Web application)

**2. Configure Authorized URIs:**
- **Authorized JavaScript origins:** `http://localhost:8000`
- **Authorized redirect URIs:** `http://localhost:8000/auth/google/callback`

**3. Update Environment Variables:**
- Set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in your `.env` file

### Authentication Flow

```
1. User visits /auth/google/login
2. Redirected to Google for authentication
3. Google redirects back to /auth/google/callback
4. Backend checks if email is in approved_users table
   - If approved: Create session, redirect to frontend
   - If not approved: Redirect to /auth/denied
5. User can access protected endpoints with session cookie
```

**Protected Endpoints:**
- `/me` - Get current user info
- `/chart` - Calculate birth charts (requires authentication)
- `/dasha` - Calculate dasha periods (requires authentication)

**User Management:**
```sql
-- Approve new user
INSERT INTO approved_users (email, note) VALUES ('user@example.com', 'Approved');

-- Deactivate user
UPDATE approved_users SET is_active = false WHERE email = 'user@example.com';

-- Reactivate user
UPDATE approved_users SET is_active = true WHERE email = 'user@example.com';
```

For detailed deployment instructions, see [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md).

## Development

### Running Tests

```bash
make test
```

**Test Coverage:**
- **Nakshatra & Navamsha**: Comprehensive tests for element-based navamsha calculations
- **Ascendant Calculation**: Multiple locations, times, and ayanamsha systems
- **Planetary Positions**: Sidereal calculations with Lahiri ayanamsha
- **Vimshottari Dasha**: Complete timeline calculation with nested periods
- **API Endpoints**: Full request/response validation

**Navamsha Calculation Method:**
The API uses traditional Vedic element-based navamsha calculation:
- Each sign (30°) is divided into 9 navamshas of 3°20' each
- Starting navamsha sign depends on the element of the base sign:
  - **Fire** (Aries, Leo, Sagittarius) → Start at Aries
  - **Earth** (Taurus, Virgo, Capricorn) → Start at Capricorn  
  - **Air** (Gemini, Libra, Aquarius) → Start at Libra
  - **Water** (Cancer, Scorpio, Pisces) → Start at Cancer
- Each subsequent navamsha progresses sign by sign in zodiacal order

**Vimshottari Dasha System:**
The API implements the traditional 120-year Vimshottari dasha system:
- **Mahadasha**: 9 planetary periods totaling 120 years (Ketu: 7, Venus: 20, Sun: 6, Moon: 10, Mars: 7, Rahu: 18, Jupiter: 16, Saturn: 19, Mercury: 17)
- **Antardasha**: Each Mahadasha is subdivided into 9 sub-periods following the same planetary sequence
- **Pratyantardasha**: Each Antardasha is further subdivided into 9 micro-periods
- **Starting Lord**: Determined by Moon's nakshatra position at birth
- **Balance Calculation**: Accounts for the remaining portion of the birth nakshatra
- **Default Timeline**: When `toDate` is not specified, defaults to full 120-year cycle from birth for complete prediction
- **Active Period Marking**: Optional `atDate` parameter marks which periods are currently active

**Known Test Issue:**
- `backend/tests/test_ascendant_calculation.py::TestAscendantCalculation::test_ascendant_calculation_mumbai`
  - Expected ascendant longitude: 35.72 ± 0.1
  - Actual ascendant longitude: 35.49
  - Input: 1991-03-25T09:46:00 Asia/Kolkata, lat 18.5246, lon 73.8786, WHOLE_SIGN, LAHIRI, MEAN

### Code Formatting

```bash
make format
```

### Linting

```bash
make lint
```

## Docker Deployment

```bash
make docker-build
make docker-run
```

## Project Structure

```
backend/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── config.py            # Configuration
│   ├── routes.py            # API routes
│   ├── schemas.py           # Pydantic models
│   └── astro/
│       ├── __init__.py
│       ├── constants.py     # Astro constants
│       ├── dasha.py         # Vimshottari dasha calculations
│       ├── engine.py        # Swiss Ephemeris engine
│       └── utils.py         # Utility functions
├── tests/
│   └── test_chart_endpoint.py
├── ephe/                    # Swiss Ephemeris data files
├── requirements.txt
├── Dockerfile
├── gunicorn.conf.py
├── Makefile
└── README.md
```

## License

**AGPL-3.0 License**

This project is licensed under the GNU Affero General Public License v3 (AGPL-3.0) because it uses Swiss Ephemeris, which is AGPL-licensed.

### What This Means

**For Users:**
- You have the right to access the complete source code
- The source code is available at: [YOUR_GITHUB_REPO_URL]
- This is free and open-source software

**For Developers:**
- If you modify this code and run it as a network service, you **must** make your source code available under AGPL-3.0
- You must preserve all copyright notices
- Any derivative works must also be AGPL-3.0 licensed

### Components

**Swiss Ephemeris:**
- Version: pyswisseph >= 2.10.3
- License: AGPL-3.0 or Commercial License
- Copyright: (C) 1997-2021 Astrodienst AG, Switzerland
- Source: https://github.com/astrorigin/pyswisseph
- Website: https://www.astro.com/swisseph/

**Jyotishika API:**
- License: AGPL-3.0
- Source: [YOUR_GITHUB_REPO_URL]

### AGPL Compliance

This software complies with AGPL v3 Section 13 (Remote Network Interaction):

1. **Source Code Access**: Available via `/license` endpoint and GitHub repository
2. **Copyright Notices**: Preserved in code and documentation
3. **License Information**: Logged on application startup
4. **User Rights**: Complete source code provided to all network users

### API Endpoints for Compliance

```bash
# Get license and source code information
curl http://localhost:8080/license
```

Returns JSON with:
- License details for all components
- Source code repository URLs
- Copyright information
- AGPL compliance notice

### Commercial Licensing

If you need to use this software in a proprietary/closed-source application:

1. **Swiss Ephemeris**: Purchase a commercial license from Astrodienst AG
   - Contact: https://www.astro.com/swisseph/
   
2. **Jyotishika API**: Contact the project maintainer for alternative licensing

For the full license text, see [LICENSE](../LICENSE) file.

For the full AGPL v3 text: https://www.gnu.org/licenses/agpl-3.0.html
