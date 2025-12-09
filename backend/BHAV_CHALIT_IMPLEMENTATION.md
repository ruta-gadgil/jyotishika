# Bhav Chalit (Sripati Padhati) Implementation

## Overview

This document explains the implementation of Bhav Chalit (house cusps) using the Sripati Padhati system in the `/chart` API endpoint.

## What is Bhav Chalit?

**Bhav Chalit** (भाव चलित) is a house division system used in Vedic astrology that calculates actual house cusps based on the birth time and location. Unlike the Rashi chart which uses fixed sign boundaries, Bhav Chalit uses the **Sripati Padhati** (also known as the Porphyry system) to determine where houses actually begin in the sky.

### Key Differences from Rashi Chart

| Aspect | Rashi Chart | Bhav Chalit |
|--------|-------------|-------------|
| House Boundaries | Fixed at sign boundaries (0°, 30°, 60°, etc.) | Calculated based on four angles |
| Dependency | Only depends on Ascendant sign | Depends on birth time, location, and latitude |
| House Sizes | Always 30° each | Unequal sizes based on quadrant division |
| Usage | Sign-based analysis | House-based predictions (bhava phalas) |

## Mathematical Foundation

### The Four Angles (Kendras)

Sripati Padhati (Bhav Chalit) is based on four critical astronomical points. These angles represent the **Bhava Madhyas** (house centers/midpoints - the strongest points of their respective houses):

1. **ASC (Ascendant/Lagna)**: The degree of the zodiac rising on the eastern horizon at birth time
   - **Bhava Madhya** of House 1 (house center - strongest point)
   - Calculated by Swiss Ephemeris based on birth time and location

2. **MC (Midheaven/Medium Coeli)**: The point where the ecliptic crosses the local meridian at its highest point
   - **Bhava Madhya** of House 10 (house center - strongest point)
   - Represents the highest point a planet can reach in the sky
   - Calculated by Swiss Ephemeris: `ascmc[1]`

3. **IC (Imum Coeli)**: The lowest point below the horizon
   - **Bhava Madhya** of House 4 (house center - strongest point)
   - Always opposite to MC: `IC = MC + 180°`

4. **DSC (Descendant)**: The degree setting on the western horizon
   - **Bhava Madhya** of House 7 (house center - strongest point)
   - Always opposite to ASC: `DSC = ASC + 180°`

### Bhava Madhyas vs Bhava Sandhis

In Bhav Chalit, there are two important concepts:

- **Bhava Madhya (भाव मध्य)**: The center/midpoint of a house - the **strongest** point where planetary influence is at its peak
- **Bhava Sandhi (भाव संधि)**: The junction/boundary between two houses - the **weakest** point where planetary influence is transitional

The relationship:
1. Bhava Madhyas are calculated first (using quadrant trisection)
2. Bhava Sandhis are derived as midpoints between consecutive Madhyas
3. Planets are assigned to houses based on which Sandhis they fall between

### Quadrant Division

The four angles divide the ecliptic into 4 quadrants. These angles are the **Bhava Madhyas** (house centers) of their respective houses:

```
Quadrant 1: ASC → IC (contains Houses 1, 2, 3)
            ASC is Bhava Madhya of house 1
Quadrant 2: IC → DSC (contains Houses 4, 5, 6)
            IC is Bhava Madhya of house 4
Quadrant 3: DSC → MC (contains Houses 7, 8, 9)
            DSC is Bhava Madhya of house 7
Quadrant 4: MC → ASC (contains Houses 10, 11, 12)
            MC is Bhava Madhya of house 10
```

### Calculation Process

The Bhav Chalit calculation involves three steps:

**Step 1: Calculate Bhava Madhyas (House Centers)**

For each quadrant with angles M₁ (start madhya) and M₂ (end madhya):

1. Calculate arc length (handling wraparound at 360°):
   ```
   arc = (M₂ - M₁ + 360) % 360
   ```

2. Trisect the quadrant (divide into 3 equal parts):
   ```
   house_span = arc / 3
   ```

3. Calculate all 12 Bhava Madhyas:
   ```
   Bhava Madhya[i] = (M₁ + i × house_span) % 360  for i = 0, 1, 2 in each quadrant
   ```

**Step 2: Calculate Bhava Sandhis (House Boundaries)**

For each pair of consecutive Bhava Madhyas:

```
Bhava Sandhi[i] = midpoint between Madhya[i] and Madhya[i+1]
                = (Madhya[i] + Madhya[i+1]) / 2
```

This creates 12 Bhava Sandhis marking the boundaries between consecutive houses.

**Step 3: Assign Planets to Houses**

A planet is in house N if its longitude falls between:
- Sandhi[N-1] (previous boundary) and
- Sandhi[N] (current boundary)

### Example Calculation

Given:
- ASC = 206.61° (Scorpio) - **MIDPOINT** of house 1
- IC = 304.61° (Aquarius) - **MIDPOINT** of house 4
- DSC = 26.61° (Taurus) - **MIDPOINT** of house 7
- MC = 124.61° (Leo) - **MIDPOINT** of house 10

**Quadrant 1 (ASC → IC):**
- Arc = 304.61° - 206.61° = 98.00°
- House span = 98.00° / 3 = 32.67°
- House 1 midpoint = 206.61° (ASC)
- House 1 cusp = 206.61° - 32.67°/2 = 190.28°
- House 2 midpoint = 206.61° + 32.67° = 239.28°
- House 2 cusp = 239.28° - 32.67°/2 = 222.94°
- House 3 midpoint = 239.28° + 32.67° = 271.94°
- House 3 cusp = 271.94° - 32.67°/2 = 255.61°

**Quadrant 2 (IC → DSC):**
- Arc = (26.61° - 304.61° + 360°) % 360° = 82.00°
- House span = 82.00° / 3 = 27.33°
- House 4 midpoint = 304.61° (IC)
- House 4 cusp = 304.61° - 27.33°/2 = 288.28°
- House 5 midpoint = 304.61° + 27.33° = 331.94°
- House 5 cusp = 331.94° - 27.33°/2 = 318.28°
- House 6 midpoint = 331.94° + 27.33° = 359.28°
- House 6 cusp = 359.28° - 27.33°/2 = 345.61°

And so on for Quadrants 3 and 4.

**Key Point**: Notice how the angles (ASC, IC, DSC, MC) fall at the **center** of their respective houses, not at the starting cusps. This is the defining characteristic of Bhav Chalit.

## Implementation Details

### Files Modified

1. **`backend/app/astro/engine.py`**
   - Added `compute_sripati_cusps()` function to calculate house cusps
   - Modified `ascendant_and_houses()` to return the four angles (ASC, IC, DSC, MC)
   - Fixed cusps indexing (Swiss Ephemeris returns 12 elements starting at index 0)

2. **`backend/app/astro/utils.py`**
   - Added `house_from_cusps()` function to determine which house a planet falls in based on house cusps
   - Handles wraparound at 360°/0° boundary

3. **`backend/app/routes.py`**
   - Updated `/chart` endpoint to calculate and include bhav chalit planet placements
   - Added import for `compute_sripati_cusps` and `house_from_cusps`
   - Updated call to `ascendant_and_houses()` to receive angles
   - Calculates house placement for each planet using Sripati cusps

4. **`backend/tests/test_bhav_chalit.py`**
   - Comprehensive test suite with 12 tests
   - Tests mathematical correctness of Sripati calculations
   - Tests API endpoint integration with planet placements
   - Tests edge cases (poles, equator, wraparound)
   - Tests comparison between Rashi and Bhav Chalit house placements

5. **`backend/tests/test_ascendant_calculation.py`**
   - Updated to handle new return value from `ascendant_and_houses()`

### API Response Structure

The `/chart` endpoint now includes a `bhavChalit` object in the response showing planet placements according to Sripati Padhati:

```json
{
  "bhavChalit": {
    "system": "SRIPATI",
    "ascendant": {
      "longitude": 35.46,
      "house": 1
    },
    "planets": [
      {"planet": "Sun", "house": 11},
      {"planet": "Moon", "house": 3},
      {"planet": "Mercury", "house": 11},
      {"planet": "Venus", "house": 12},
      {"planet": "Mars", "house": 2},
      {"planet": "Jupiter", "house": 3},
      {"planet": "Saturn", "house": 9},
      {"planet": "Uranus", "house": 8},
      {"planet": "Neptune", "house": 8},
      {"planet": "Pluto", "house": 6},
      {"planet": "Rahu", "house": 9},
      {"planet": "Ketu", "house": 3}
    ]
  }
}
```

This format mirrors the main chart's `ascendant` and `planets` structure, making it easy to compare planet house placements between the Rashi chart and Bhav Chalit.

### Key Features

1. **Always Included**: Bhav Chalit data is always included in the `/chart` response, regardless of the main house system selected

2. **Planet Placements**: Shows which house each planet occupies according to Sripati Padhati, making it easy to compare with the main chart

3. **Ayanamsha Support**: Properly applies VEDANJANAM offset (and other ayanamsha systems) to all calculations

4. **Precision**: Ascendant longitude is rounded to 2 decimal places for frontend display

5. **Validation**: Comprehensive tests ensure mathematical accuracy and correct house assignments

## Usage in Astrology

Bhav Chalit is used for:

1. **House-based predictions (Bhava Phalas)**: Determining which house a planet truly occupies for prediction purposes
2. **Planetary strength**: Planets near the angles (ASC, IC, DSC, MC) gain strength, as these represent the **midpoints** (strongest points) of angular houses
3. **Dasha timing**: Some astrologers use Bhav Chalit for timing events during planetary periods
4. **Bhava Madhya**: In Bhav Chalit, the angles (ASC, IC, DSC, MC) ARE the Bhava Madhya (house midpoints) - the strongest points of their respective houses

### When to Use Bhav Chalit vs Rashi Chart

- **Rashi Chart**: Use for sign-based analysis, planetary dignities, aspects, and general chart reading
- **Bhav Chalit**: Use for house-based predictions, timing events, and determining which house truly contains a planet

### Key Difference from Western Systems

While Bhav Chalit shares the quadrant trisection approach with the Western Porphyry system, there are crucial differences:

**Western Porphyry System:**
- Angles (ASC, IC, DSC, MC) are the **starting points/cusps** of houses
- Planets are assigned based on which cusp they fall after
- House boundaries are at the angles

**Bhav Chalit (Sripati Padhati):**
- Angles are the **Bhava Madhyas** (house centers - strongest points)
- Bhava Sandhis (boundaries) are calculated as midpoints between Madhyas
- Planets are assigned based on which Sandhis they fall between
- This reflects the Vedic understanding that angles represent maximum strength, not boundaries

This distinction is critical for accurate Vedic astrological calculations and matches the traditional interpretation used by AstroSage, DrikPanchang, and other Vedic astrology platforms.

## Testing

Run the test suite:

```bash
cd backend
PYTHONPATH=. ../venv/bin/pytest tests/test_bhav_chalit.py -v
```

All 12 tests should pass:
- 4 tests for mathematical correctness of Sripati cusp calculations
- 6 tests for API endpoint integration with planet placements
- 2 tests for edge cases (high latitudes, equator)

## References

- Swiss Ephemeris Documentation: https://www.astro.com/swisseph/
- Sripati/Porphyry House System: Traditional Vedic astrology texts
- Parashari System: Uses Bhav Chalit for house-based predictions

