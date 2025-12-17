# Bhav Chalit Logging Guide

## Overview

The bhav chalit implementation includes detailed logging to help debug and understand the calculations. The logs show the four angles, Sripati house cusps, and planet placements.

## Log Output Format

When a chart is calculated, you'll see the following logs in sequence:

### 1. Angles Calculation
```
📐 Angles calculated: ASC=35.46°, MC=293.81°, IC=113.81°, DSC=215.46°
```

**What it shows:**
- **ASC (Ascendant)**: The degree rising on the eastern horizon
- **MC (Midheaven)**: The highest point in the sky
- **IC (Imum Coeli)**: The lowest point (opposite MC)
- **DSC (Descendant)**: The setting point on the western horizon (opposite ASC)

**Mathematical relationships:**
- IC = MC + 180°
- DSC = ASC + 180°

### 2. Sripati House Cusps
```
🏠 Sripati Cusps calculated:
   House  1:  35.46°
   House  2:  61.58°
   House  3:  87.69°
   House  4: 113.81°
   House  5: 147.69°
   House  6: 181.58°
   House  7: 215.46°
   House  8: 241.58°
   House  9: 267.69°
   House 10: 293.81°
   House 11: 327.69°
   House 12:   1.58°
```

**What it shows:**
- The starting degree for each of the 12 houses
- Calculated using Sripati Padhati (quadrant trisection method)

**Key observations:**
- House 1 cusp = ASC
- House 4 cusp = IC
- House 7 cusp = DSC
- House 10 cusp = MC
- Houses are unequal in size (unlike whole sign houses)

### 3. Planet Placements
```
🌟 Bhav Chalit Planet Placements:
   Sun        at 340.28° → House 11
   Moon       at  95.41° → House 3
   Mercury    at 358.64° → House 11
   Venus      at  13.84° → House 12
   Mars       at  61.64° → House 2
   Jupiter    at  99.86° → House 3
   Saturn     at 280.91° → House 9
   Uranus     at 259.83° → House 8
   Neptune    at 262.86° → House 8
   Pluto      at 206.36° → House 6
   Rahu       at 270.99° → House 9
   Ketu       at  90.99° → House 3
```

**What it shows:**
- Each planet's longitude in degrees
- Which house the planet occupies according to Bhav Chalit

**How it's calculated:**
For each planet, the system checks which house cusp range it falls between:
- If planet longitude >= House N cusp AND < House N+1 cusp, then planet is in House N
- Handles wraparound at 360°/0° boundary

## Example Analysis

Using the example above:

**Sun at 340.28°:**
- House 11 starts at 327.69°
- House 12 starts at 1.58°
- 340.28° falls between 327.69° and 361.58° (1.58° + 360°)
- Therefore, Sun is in House 11 ✓

**Venus at 13.84°:**
- House 12 starts at 1.58°
- House 1 starts at 35.46°
- 13.84° falls between 1.58° and 35.46°
- Therefore, Venus is in House 12 ✓

**Moon at 95.41°:**
- House 3 starts at 87.69°
- House 4 starts at 113.81°
- 95.41° falls between 87.69° and 113.81°
- Therefore, Moon is in House 3 ✓

## Debugging Tips

### Verify Angle Relationships
Check that:
- IC ≈ MC + 180° (within rounding)
- DSC ≈ ASC + 180° (within rounding)

### Verify Cusp Alignment
Check that:
- House 1 cusp = ASC
- House 4 cusp = IC
- House 7 cusp = DSC
- House 10 cusp = MC

### Verify Planet Placements
For each planet:
1. Note its longitude
2. Find which two consecutive cusps it falls between
3. Confirm the assigned house number matches

### Common Issues

**Issue:** Planet near 360°/0° boundary assigned to wrong house
- **Check:** Wraparound logic in `house_from_cusps()` function
- **Solution:** Ensure the function handles `cusp_start > cusp_end` case

**Issue:** Angles don't match expected values
- **Check:** Ayanamsha being applied correctly
- **Check:** Birth time and location are accurate
- **Solution:** Verify VEDANJANAM offset is applied consistently

## Disabling Logs

If you want to disable these logs in production:

1. Comment out the print statements in:
   - `backend/app/astro/engine.py` (angles and cusps)
   - `backend/app/routes.py` (planet placements)

2. Or redirect them to a logger:
   ```python
   import logging
   logger = logging.getLogger(__name__)
   logger.debug(f"📐 Angles calculated: ASC={asc:.2f}°, ...")
   ```

## Log Symbols

- 📐 = Angles calculation
- 🏠 = House cusps calculation
- 🌟 = Planet placements
- 🔵 = API request received
- ✅ = Validation successful
- 🎉 = Chart calculation successful
- 💥 = Error occurred





