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

## Configuration

Environment variables:

- `EPHE_PATH` (required): Path to Swiss Ephemeris data files
- `FLASK_ENV` (optional): development | production
- `PORT` (optional): Server port (default: 8080)
- `ALLOWED_ORIGINS` (optional): CORS origins (default: "*")

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

This project uses Swiss Ephemeris which is licensed under the GNU General Public License.
