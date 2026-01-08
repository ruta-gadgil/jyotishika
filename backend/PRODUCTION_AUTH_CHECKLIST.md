# Production Authentication Checklist

This document outlines all the changes needed to productionize the Google OAuth authentication system.

## Critical Security Changes

### 1. Session Storage
**Current:** In-memory dictionary  
**Production:** Use Redis, database, or distributed cache

**Why:** In-memory storage doesn't work with:
- Multiple server instances (load balancing)
- Server restarts (sessions are lost)
- Horizontal scaling

**Implementation Options:**
- Redis (recommended): Fast, supports TTL, works across instances
- PostgreSQL/MySQL: Persistent, supports complex queries
- Memcached: Simple, fast, but no persistence

**Example Redis Implementation:**
```python
import redis
redis_client = redis.Redis(host='localhost', port=6379, db=0)

# Store session
redis_client.setex(f"session:{session_id}", 604800, json.dumps(session_data))

# Retrieve session
session_data = redis_client.get(f"session:{session_id}")
```

### 2. State Token Storage
**Current:** In-memory dictionary  
**Production:** Use Redis or database with TTL

**Why:** Same reasons as session storage - needs to be shared across instances

**Implementation:**
- Use Redis with TTL (e.g., 10 minutes)
- Or database with expiration timestamp

### 3. Cookie Security
**Current:** `secure=False`, `samesite="Lax"`  
**Production:** `secure=True`, appropriate `samesite` value

**Changes Required:**
```python
response.set_cookie(
    "session_id",
    session_id,
    httponly=True,
    secure=True,  # REQUIRED for HTTPS
    samesite="None" if cross_domain else "Lax",  # "None" requires secure=True
    path="/",
    max_age=86400 * 1,  # Consider shorter expiration (1-3 days)
    domain=".yourdomain.com"  # If frontend/backend on different subdomains
)
```

**Notes:**
- `secure=True` requires HTTPS
- `samesite="None"` is needed if frontend and backend are on different domains
- `samesite="None"` requires `secure=True`

### 4. HTTPS Configuration
**Current:** HTTP (http://localhost:8000)  
**Production:** HTTPS required

**Changes:**
- Update `APP_BASE_URL` to use `https://`
- Configure SSL/TLS certificates
- Update Google OAuth redirect URI in Google Cloud Console to HTTPS
- Ensure all cookies use `secure=True`

### 5. Secret Key
**Current:** Auto-generated if not set  
**Production:** MUST be set via environment variable

**Action Required:**
- Generate strong secret: `openssl rand -hex 32`
- Set `SECRET_KEY` environment variable in production
- Remove auto-generation fallback or fail fast if missing

### 6. CORS Configuration
**Current:** `ALLOWED_ORIGINS=*`  
**Production:** Restrict to specific domains

**Changes:**
```bash
# Environment variable
ALLOWED_ORIGINS=https://app.yourdomain.com,https://www.yourdomain.com
```

**Never use `*` in production** - it allows any origin to make requests.

## Performance Optimizations

### 7. JWKs Caching
**Current:** Fetches Google's public keys on every token verification  
**Production:** Cache JWKs with TTL

**Why:** Google rotates keys infrequently, caching reduces API calls

**Implementation:**
```python
from functools import lru_cache
from datetime import datetime, timedelta

_jwks_cache = None
_jwks_cache_time = None
JWKS_CACHE_TTL = 3600  # 1 hour

def get_google_jwks():
    global _jwks_cache, _jwks_cache_time
    
    if _jwks_cache and _jwks_cache_time:
        if datetime.utcnow() - _jwks_cache_time < timedelta(seconds=JWKS_CACHE_TTL):
            return _jwks_cache
    
    # Fetch and cache
    response = requests.get("https://www.googleapis.com/oauth2/v3/certs")
    _jwks_cache = response.json()
    _jwks_cache_time = datetime.utcnow()
    return _jwks_cache
```

**Better:** Use Redis for distributed caching across instances

## Error Handling & Logging

### 8. Error Message Sanitization
**Current:** Exposes internal error details  
**Production:** Return generic messages to users

**Changes:**
```python
# PRODUCTION: Don't expose internal error details
except Exception as e:
    current_app.logger.error(f"Error: {str(e)}", exc_info=True)  # Log full details
    return jsonify({
        "error": {
            "code": "INTERNAL_ERROR",
            "message": "An error occurred. Please try again."  # Generic message
        }
    }), 500
```

### 9. Logging Best Practices
**Current:** Logs user emails  
**Production:** Consider privacy/GDPR requirements

**Changes:**
- Optionally hash emails for logging
- Or log only user_id
- Ensure logs don't contain sensitive data (tokens, secrets)

### 10. Session Expiration
**Current:** No expiration check  
**Production:** Implement session expiration

**Implementation:**
```python
# In /me endpoint
if session:
    # Check if session expired (e.g., 7 days)
    if (datetime.utcnow() - session["created_at"]).days > 7:
        # Delete expired session
        del sessions[session_id]
        return jsonify({"logged_in": False}), 200
```

**Better:** Use TTL in Redis/database

## Environment Variables

### Required Production Environment Variables

```bash
# Security
SECRET_KEY=<strong-random-secret>  # REQUIRED - generate with: openssl rand -hex 32

# OAuth
GOOGLE_CLIENT_ID=<your-client-id>
GOOGLE_CLIENT_SECRET=<your-client-secret>
APP_BASE_URL=https://api.yourdomain.com  # MUST use HTTPS
FRONTEND_BASE_URL=https://app.yourdomain.com  # Production frontend URL

# CORS
ALLOWED_ORIGINS=https://app.yourdomain.com,https://www.yourdomain.com  # No wildcards

# Session Storage (if using Redis)
REDIS_HOST=redis.yourdomain.com
REDIS_PORT=6379
REDIS_PASSWORD=<redis-password>
```

## Google Cloud Console Configuration

### Update OAuth Settings

1. **Authorized JavaScript origins:**
   - `https://api.yourdomain.com`

2. **Authorized redirect URIs:**
   - `https://api.yourdomain.com/auth/google/callback`

3. **Remove localhost URIs** from production OAuth client

## Testing Checklist

Before deploying to production:

- [ ] All environment variables set correctly
- [ ] HTTPS configured and working
- [ ] Cookies use `secure=True`
- [ ] CORS restricted to production domains
- [ ] Session storage using Redis/database
- [ ] JWKs caching implemented
- [ ] Error messages sanitized
- [ ] Session expiration working
- [ ] Google OAuth redirect URI updated
- [ ] Load testing with multiple instances
- [ ] Security audit completed

## Additional Considerations

### Rate Limiting
Consider adding rate limiting to prevent abuse:
- Login attempts per IP
- Token exchange requests
- Session creation

### Monitoring
Set up monitoring for:
- Failed authentication attempts
- Session creation/deletion rates
- Token verification failures
- JWKs cache hit rates

### Backup & Recovery
- Session data backup strategy (if using database)
- Redis persistence configuration
- Disaster recovery plan

## Migration Steps

1. **Set up Redis/database** for session storage
2. **Update environment variables** in production
3. **Deploy code changes** with production comments implemented
4. **Update Google OAuth** redirect URIs
5. **Test authentication flow** in staging environment
6. **Monitor** for errors and performance issues
7. **Gradually roll out** to production users

