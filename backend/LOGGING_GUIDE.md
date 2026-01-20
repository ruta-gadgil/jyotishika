# Logging Guide

## Overview

This guide covers logging best practices, security guidelines, and configuration for the Jyotishika API. The application uses structured logging with sensitive data filtering to ensure security and compliance.

## Security Guidelines

### What NOT to Log

**NEVER log the following sensitive information:**

- ❌ Full email addresses (use user IDs or email domains only)
- ❌ Passwords, tokens, secrets, API keys
- ❌ Full session IDs (truncate to 8 characters)
- ❌ OAuth client secrets or authorization codes
- ❌ Full request/response bodies containing PII
- ❌ Database credentials or connection strings
- ❌ Authentication cookies or bearer tokens
- ❌ Personal information (phone numbers, addresses, SSN, etc.)

### What IS Safe to Log

**These are safe to include in logs:**

- ✅ User IDs (UUIDs) - `user.id` instead of `user.email`
- ✅ Email domains - `user@example.com` → `***@example.com`
- ✅ Partial session IDs - First 8 characters only
- ✅ HTTP status codes and response times
- ✅ Operation outcomes (success/failure)
- ✅ Performance metrics and cache hit rates
- ✅ Request paths and methods (not full URLs with params)
- ✅ Content-Type and Content-Length headers
- ✅ Error messages and stack traces (sanitized)

### Log Sanitization

The application includes built-in sanitization functions in `app/logging_utils.py`:

```python
from .logging_utils import sanitize_dict, mask_email, truncate_id

# Sanitize dictionaries before logging
sanitized = sanitize_dict(request_data)
logger.info(f"Request params: {sanitized}")

# Mask email addresses
masked = mask_email("user@example.com")  # Returns: "***@example.com"

# Truncate IDs
truncated = truncate_id("abc123def456", length=8)  # Returns: "abc123de..."
```

## Logging Configuration

### Environment Variables

Control logging behavior with environment variables:

- `FLASK_ENV`: Set to `production` for JSON logs, `development` for colored logs
- `LOG_LEVEL`: Set log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`)
- `GUNICORN_WORKERS`: Number of gunicorn workers
- `GUNICORN_TIMEOUT`: Request timeout in seconds

### Log Levels

Use appropriate log levels for different situations:

- **DEBUG**: Detailed diagnostic information (development only)
  - Function entry/exit, variable values
  - Calculation steps, cache lookups
  - Not shown in production by default

- **INFO**: General informational messages
  - Successful operations, business events
  - Request start/completion, chart calculations
  - User actions (sanitized)

- **WARNING**: Potentially harmful situations
  - Validation errors, missing optional data
  - Deprecated API usage, rate limiting
  - Recoverable errors

- **ERROR**: Error events that might still allow the app to continue
  - Failed database queries, calculation errors
  - External service failures
  - Include `exc_info=True` for stack traces

- **CRITICAL**: Severe errors causing app termination
  - Database unavailable, configuration errors
  - Unrecoverable failures

### Example Usage

```python
from flask import current_app

# Good: Sanitized logging
current_app.logger.info(f"Chart calculated for user: {user.id}")
current_app.logger.debug(f"Cache hit ratio: {hit_ratio:.2%}")

# Bad: Exposes sensitive data
current_app.logger.info(f"User {user.email} logged in")  # ❌ Don't do this
current_app.logger.info(f"Session: {session_id}")  # ❌ Don't log full session ID
```

## Structured Logging

### Production Format (JSON)

In production (`FLASK_ENV=production`), logs are output as JSON for easy parsing:

```json
{
  "timestamp": "2026-01-20T10:30:45.123456Z",
  "level": "INFO",
  "logger": "app.routes",
  "message": "Chart calculation successful",
  "request": {
    "method": "POST",
    "path": "/chart",
    "remote_addr": "192.168.1.1"
  },
  "user_id": "abc123-def456-ghi789"
}
```

### Development Format (Colored)

In development, logs are human-readable with colors:

```
INFO     | 10:30:45 | app.routes          | Chart calculation successful | [POST /chart]
```

## Bhav Chalit Calculation Logs

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

### 2. Bhav Chalit Calculation (Structured Log)
```
DEBUG | app.astro.engine | Bhav Chalit calculated | bhav_chalit={
  "angles": {"asc": 35.46, "ic": 113.81, "dsc": 215.46, "mc": 293.81},
  "madhyas": [
    {"house": 1, "longitude": 35.46},
    {"house": 2, "longitude": 61.58},
    {"house": 3, "longitude": 87.69},
    {"house": 4, "longitude": 113.81},
    {"house": 5, "longitude": 147.69},
    {"house": 6, "longitude": 181.58},
    {"house": 7, "longitude": 215.46},
    {"house": 8, "longitude": 241.58},
    {"house": 9, "longitude": 267.69},
    {"house": 10, "longitude": 293.81},
    {"house": 11, "longitude": 327.69},
    {"house": 12, "longitude": 1.58}
  ],
  "sandhis": [
    {"sandhi": "1/2", "longitude": 48.52},
    {"sandhi": "2/3", "longitude": 74.64},
    {"sandhi": "3/4", "longitude": 100.75},
    {"sandhi": "4/5", "longitude": 130.75},
    {"sandhi": "5/6", "longitude": 164.64},
    {"sandhi": "6/7", "longitude": 198.52},
    {"sandhi": "7/8", "longitude": 228.52},
    {"sandhi": "8/9", "longitude": 254.64},
    {"sandhi": "9/10", "longitude": 280.75},
    {"sandhi": "10/11", "longitude": 310.75},
    {"sandhi": "11/12", "longitude": 344.64},
    {"sandhi": "12/1", "longitude": 18.52}
  ]
}
```

**What it shows:**
- **angles**: The four key angles (ASC, IC, DSC, MC) used for calculation
- **madhyas**: All 12 Bhava Madhyas (house centers) - the strongest points of each house
- **sandhis**: All 12 Bhava Sandhis (house boundaries/cusps) - the boundaries between houses

**Key observations:**
- House 1 Madhya = ASC
- House 4 Madhya = IC
- House 7 Madhya = DSC
- House 10 Madhya = MC
- Sandhis are midpoints between consecutive Madhyas
- Houses are unequal in size (unlike whole sign houses)

### 3. Planet Placements (Structured Log)
```
DEBUG | app.routes | Bhav Chalit planet placements | bhav_chalit_planets=[
  {"planet": "Sun", "longitude": 340.28, "house": 11},
  {"planet": "Moon", "longitude": 95.41, "house": 3},
  {"planet": "Mercury", "longitude": 358.64, "house": 11},
  {"planet": "Venus", "longitude": 13.84, "house": 12},
  {"planet": "Mars", "longitude": 61.64, "house": 2},
  {"planet": "Jupiter", "longitude": 99.86, "house": 3},
  {"planet": "Saturn", "longitude": 280.91, "house": 9},
  {"planet": "Uranus", "longitude": 259.83, "house": 8},
  {"planet": "Neptune", "longitude": 262.86, "house": 8},
  {"planet": "Pluto", "longitude": 206.36, "house": 6},
  {"planet": "Rahu", "longitude": 270.99, "house": 9},
  {"planet": "Ketu", "longitude": 90.99, "house": 3}
]
```

**What it shows:**
- Each planet's name, longitude in degrees, and house placement in Bhav Chalit
- All 12 planets (including Rahu and Ketu) are included

**How it's calculated:**
For each planet, the system checks which house cusp range it falls between:
- If planet longitude >= Sandhi[N-1] AND < Sandhi[N], then planet is in House N
- Handles wraparound at 360°/0° boundary

**Benefits of structured logging:**
- All data in a single log entry (reduced verbosity from 28+ lines to 2 entries)
- Easy to parse and filter programmatically
- JSON structure enables log aggregation and analysis tools
- Maintains all information while improving readability

## Example Analysis

Using the example above:

**Sun at 340.28°:**
- Sandhi 10/11 (House 11 start) at 310.75°
- Sandhi 11/12 (House 12 start) at 344.64°
- 340.28° falls between 310.75° and 344.64°
- Therefore, Sun is in House 11 ✓

**Venus at 13.84°:**
- Sandhi 12/1 (House 12 start) at 18.52° (wraps to 378.52°)
- Sandhi 1/2 (House 1 start) at 48.52°
- 13.84° falls between 18.52° (wrapped) and 48.52°
- Therefore, Venus is in House 12 ✓

**Moon at 95.41°:**
- Sandhi 2/3 (House 3 start) at 74.64°
- Sandhi 3/4 (House 4 start) at 100.75°
- 95.41° falls between 74.64° and 100.75°
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

## Controlling Log Verbosity

### In Development

Set `LOG_LEVEL=DEBUG` to see all calculation steps:

```bash
export LOG_LEVEL=DEBUG
python -m flask run
```

### In Production

Set `LOG_LEVEL=INFO` or `LOG_LEVEL=WARNING` to reduce verbosity:

```bash
export LOG_LEVEL=INFO
gunicorn -c gunicorn.conf.py "app:create_app()"
```

### Filtering Health Checks

Health check requests (`/healthz`) are logged at `DEBUG` level to reduce noise in production.

## Log Symbols

These emoji indicators help quickly identify log entry types:

- 🔵 = API request received
- ✅ = Validation/operation successful
- ⚠️  = Warning or potential issue
- ❌ = Validation error or rejection
- 💥 = Error occurred
- 🎯 = Cache hit
- 💫 = Cache miss
- 💾 = Data saved
- 🎉 = Operation completed successfully
- 📐 = Angles calculation (debug)
- 🏠 = House cusps calculation (debug)
- 🌟 = Planet placements (debug)
- 📦 = Request data information

## Best Practices for New Code

When adding new logging to the codebase:

1. **Use the correct log level**
   - Don't use `ERROR` for validation failures (use `WARNING`)
   - Don't use `INFO` for detailed diagnostic data (use `DEBUG`)

2. **Sanitize before logging**
   ```python
   from .logging_utils import sanitize_dict
   
   # Sanitize user-provided data
   sanitized_data = sanitize_dict(request.get_json())
   logger.debug(f"Request data: {sanitized_data}")
   ```

3. **Include context**
   ```python
   # Good: Includes operation and identifier
   logger.info(f"Profile updated successfully: {profile_id}")
   
   # Bad: Too vague
   logger.info("Updated")
   ```

4. **Use exc_info for errors**
   ```python
   try:
       calculate_chart()
   except Exception as e:
       # Include stack trace for debugging
       logger.error(f"Chart calculation failed: {str(e)}", exc_info=True)
   ```

5. **Avoid logging in loops**
   ```python
   # Good: Log summary
   logger.info(f"Processed {len(items)} items")
   
   # Bad: Log each iteration
   for item in items:
       logger.info(f"Processing {item}")  # Don't do this
   ```

6. **Use lazy string formatting**
   ```python
   # Good: String formatting only happens if log level matches
   logger.debug("Processing user: %s", user_id)
   
   # Acceptable for f-strings with simple variables
   logger.debug(f"Processing user: {user_id}")
   ```

## Monitoring and Alerting

### Log Aggregation

In production, logs should be sent to a centralized logging service:

- **CloudWatch Logs** (AWS)
- **Google Cloud Logging** (GCP)
- **Datadog**, **New Relic**, **Splunk**
- **ELK Stack** (Elasticsearch, Logstash, Kibana)

### Alert Examples

Set up alerts for critical issues:

1. **Error rate spike**: More than 10 errors per minute
2. **Database connection failures**: Any `ERROR` logs containing "Database connection failed"
3. **Authentication failures**: Repeated auth denials from same IP
4. **Performance degradation**: Request duration > 5 seconds

## Compliance

### GDPR and Privacy

The logging configuration ensures GDPR compliance:

- Email addresses are never logged in full
- User IDs (UUIDs) are used instead of PII
- No personal information in logs (names, addresses, etc.)
- Logs can be safely stored and analyzed without PII concerns

### Audit Trail

All authentication events are logged with:

- User ID (not email)
- Event type (login, logout, auth_denied)
- Timestamp (UTC)
- IP address
- Partial session ID (first 8 chars)

This provides a complete audit trail without exposing sensitive data.

## Troubleshooting

### Logs Not Appearing

1. Check `LOG_LEVEL` environment variable
2. Ensure logging is configured before any log statements
3. Check that `configure_logging()` is called in `create_app()`

### Too Verbose

1. Increase `LOG_LEVEL` from `DEBUG` to `INFO`
2. Filter out health check logs (already configured)
3. Reduce third-party library logging in `logging_config.py`

### Sensitive Data in Logs

If you find sensitive data in logs:

1. Identify the log statement
2. Apply sanitization using `sanitize_dict()` or similar
3. Use user IDs instead of emails
4. Truncate session IDs and tokens
5. Add the field to `SENSITIVE_KEYS` in `logging_utils.py`

## Related Documentation

- `app/logging_config.py` - Centralized logging configuration
- `app/logging_utils.py` - Sanitization utilities
- `gunicorn.conf.py` - Production server logging
- `PRODUCTION_AUTH_CHECKLIST.md` - Security checklist







