# Vedic Astrology Backend API

A Flask-based backend API for computing vedic astrology charts using Swiss Ephemeris.

## Features

- **Ascendant Calculation**: Sidereal (Lahiri) ascendant computation
- **Planetary Positions**: Longitudes, speeds, and retrograde motion
- **Nakshatra & Navamsha (NEW)**: For every planet, response includes
  - `nakshatra`: `{ name, index }` (1–27)
  - `pada`: integer 1–4
  - `navamsha`: `{ sign, signIndex, ordinal, degreeInNavamsha }`
  - `navamshaNakshatraPada`: `{ nakshatra, pada }`
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
  "ascendant": { "longitude": 70.04, "signIndex": 2, "house": 1 },
  "planets": [
    {
      "planet": "Sun",
      "longitude": 340.28,
      "speed": 0.9909,
      "retrograde": false,
      "signIndex": 11,
      "nakshatra": { "name": "Shatabhisha", "index": 24 },
      "pada": 2,
      "navamsha": { "sign": "Capricorn", "signIndex": 9, "ordinal": 6, "degreeInNavamsha": 1.2345 },
      "navamshaNakshatraPada": { "nakshatra": "Shatabhisha", "pada": 2 },
      "house": 10
    }
  ]
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

Current known failing test (subject to verification):

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
