# Production Deployment Checklist

**Last Updated:** January 20, 2026

This comprehensive guide outlines all requirements for deploying the Jyotishika Vedic Astrology API to production. It covers infrastructure, security, compliance, monitoring, and operational readiness.

---

## Table of Contents

1. [Pre-Deployment Setup](#pre-deployment-setup)
2. [Code Changes Required](#code-changes-required)
3. [Testing & Quality Assurance](#testing--quality-assurance)
4. [Deployment Process](#deployment-process)
5. [Post-Deployment Operations](#post-deployment-operations)
6. [Final Checklist](#final-checklist)

---

## Pre-Deployment Setup

### Infrastructure & Platform

#### SSL/TLS Certificates
- [ ] Obtain SSL/TLS certificate (Let's Encrypt or managed certificate)
- [ ] Configure certificate auto-renewal
- [ ] Enable HTTPS on all endpoints
- [ ] Set up HTTPS redirect (HTTP → HTTPS)
- [ ] Verify certificate is trusted (A+ rating on SSL Labs)

#### DNS Configuration
- [ ] Configure A/AAAA records pointing to server IP
- [ ] Set up CNAME for `api.yourdomain.com`
- [ ] Configure TTL appropriately (e.g., 300s for production)
- [ ] Set up health check subdomain if needed
- [ ] Verify DNS propagation globally

#### Load Balancer (if applicable)
- [ ] Configure health checks to `/healthz` endpoint
- [ ] Set up SSL termination at load balancer
- [ ] Enable sticky sessions (cookie-based)
- [ ] Configure timeout values (match Gunicorn timeout)
- [ ] Set up connection draining for graceful shutdowns

#### Container Registry & Orchestration
- [ ] Choose container registry (Docker Hub, ECR, GCR, etc.)
- [ ] Set up automated image builds on main branch
- [ ] Tag images with version numbers and `latest`
- [ ] Choose deployment platform:
  - **Docker Compose**: For single-server deployments
  - **Kubernetes**: For multi-server, auto-scaling
  - **Managed Services**: Railway, Render, Fly.io, etc.
- [ ] Configure container resource limits (CPU, memory)
- [ ] Set up container health checks

#### Gunicorn Worker Configuration
**Current:** 2 workers × 4 threads = 8 concurrent requests

**Recommended Formula:** `(2 × CPU cores) + 1` workers

```bash
# For 2 CPU cores
GUNICORN_WORKERS=5
GUNICORN_THREADS=2-4
GUNICORN_TIMEOUT=30  # Adjust based on chart calculation time
```

**Considerations:**
- More workers = better concurrency, more memory usage
- Threads are cheaper than workers but share GIL
- Monitor CPU/memory usage and adjust

#### Ephemeris Files Distribution
**Current:** Baked into Docker image (~500MB)

**Options:**
1. **Baked-in (current)**: Simple, larger image size
2. **Volume mount**: Smaller image, requires external storage
3. **Object storage**: S3/GCS, download on startup

**Recommendation:** Start with baked-in, optimize later if needed

---

### Database Setup

#### PostgreSQL Configuration
- [ ] Choose Supabase tier (Free, Pro, Team, Enterprise)
- [ ] Use **Session Pooler** URL (port 6543) for production, not direct connection
  ```bash
  # Production format
  DATABASE_URL=postgresql://postgres.[PROJECT]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
  ```
- [ ] Enable connection pooling in Supabase dashboard
- [ ] Set appropriate pool size limits

#### Connection Pool Tuning
**Current Settings** (in `backend/app/db.py`):
- Pool size: 10 permanent connections
- Max overflow: 20 additional connections
- Total max: 30 concurrent connections

**Tuning Guide:**
```python
# Adjust based on load testing
pool_size = GUNICORN_WORKERS * 2  # 10 for 5 workers
max_overflow = pool_size * 2      # 20 overflow
```

**Monitor:**
- Connection pool usage (idle vs active)
- Connection wait time
- Pool exhaustion errors

#### Database Schema & Migrations
- [ ] Apply schema from `backend/sql/schema.sql`
- [ ] Verify all tables created: `users`, `approved_users`, `profiles`, `charts`
- [ ] Check indexes on frequently queried columns
- [ ] Document migration procedure for future schema changes
- [ ] Test rollback procedure

#### Row-Level Security (RLS)
**Current Status:** RLS enabled, policies commented out (permissive mode)

**Decision Required:**
- [ ] **Option A:** Enable RLS policies for additional security layer
  - Uncomment policies in `schema.sql`
  - Add `set_rls_user_id()` calls to routes
  - Test thoroughly
- [ ] **Option B:** Keep RLS disabled, rely on application-level checks
  - Simpler implementation
  - Less defense-in-depth

**See:** `backend/RLS_SETUP.md` for detailed guide

#### Database Backups
- [ ] Enable automated daily backups (Supabase has this built-in)
- [ ] Set backup retention period (30+ days recommended)
- [ ] Document and test restore procedure
- [ ] Set up backup monitoring/alerts
- [ ] Consider point-in-time recovery (PITR) for critical data

#### Database Monitoring
- [ ] Monitor query performance (slow query log)
- [ ] Track connection pool usage
- [ ] Set up alerts for:
  - Connection failures
  - Slow queries (> 1 second)
  - Pool exhaustion
  - Disk space usage (> 80%)

#### Data Retention & Privacy
- [ ] Define data retention policy
  - How long to keep inactive user data
  - Chart history retention period
- [ ] Implement automated cleanup for old data
- [ ] Document GDPR compliance for data deletion
- [ ] Consider data anonymization for analytics

---

### Environment Variables

#### Required Variables

```bash
# Application Core
EPHE_PATH=/app/ephe                    # Swiss Ephemeris data files location
FLASK_ENV=production                   # Set to production
PORT=8080                              # Server port

# Database
DATABASE_URL=postgresql://postgres.[PROJECT]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres

# Security
SECRET_KEY=<GENERATE_WITH_openssl_rand_-hex_32>  # MUST be random, persistent

# Google OAuth
GOOGLE_CLIENT_ID=<your-client-id>
GOOGLE_CLIENT_SECRET=<your-client-secret>
APP_BASE_URL=https://api.yourdomain.com         # MUST use HTTPS
FRONTEND_BASE_URL=https://app.yourdomain.com    # Production frontend

# CORS
ALLOWED_ORIGINS=https://app.yourdomain.com,https://www.yourdomain.com  # NO wildcards
```

#### Optional but Recommended

```bash
# Logging
LOG_LEVEL=INFO                         # INFO or WARNING for production

# Gunicorn Configuration
GUNICORN_WORKERS=5                     # (2 × CPU cores) + 1
GUNICORN_THREADS=4                     # Threads per worker
GUNICORN_TIMEOUT=30                    # Request timeout in seconds

# Redis (if implementing session storage)
REDIS_HOST=redis.yourdomain.com
REDIS_PORT=6379
REDIS_PASSWORD=<redis-password>
REDIS_DB=0
REDIS_SSL=true

# Monitoring (optional)
SENTRY_DSN=<your-sentry-dsn>          # Error tracking
```

#### Secret Generation

```bash
# Generate strong SECRET_KEY
openssl rand -hex 32

# Store in environment, NEVER commit to git
echo "SECRET_KEY=$(openssl rand -hex 32)" >> .env.production
```

#### Secrets Management
- [ ] Use platform-specific secrets management:
  - **Railway/Render**: Built-in environment variables
  - **AWS**: Secrets Manager or Parameter Store
  - **GCP**: Secret Manager
  - **Kubernetes**: Secrets or External Secrets Operator
- [ ] Never commit secrets to version control
- [ ] Rotate secrets regularly (every 90 days)
- [ ] Use different secrets for staging vs production

---

### Google Cloud Console Configuration

#### OAuth 2.0 Client Setup

1. **Create Production OAuth Client** (separate from development)
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Navigate to APIs & Services → Credentials
   - Create OAuth 2.0 Client ID

2. **Authorized JavaScript Origins**
   ```
   https://api.yourdomain.com
   https://app.yourdomain.com
   ```

3. **Authorized Redirect URIs**
   ```
   https://api.yourdomain.com/auth/google/callback
   ```

4. **Remove Development URIs**
   - Remove all `http://localhost:*` URIs from production client
   - Keep separate OAuth client for development

5. **Verification Status**
   - [ ] OAuth consent screen configured
   - [ ] App verification completed (if required)
   - [ ] Scopes properly set (openid, email, profile)

---

## Code Changes Required

### Authentication & Session Management

#### 1. Session Storage Migration
**Current:** In-memory dictionary (not production-ready)  
**Required:** Redis or database-backed storage

**Files to modify:**
- `backend/app/auth.py` (lines 25, 31)

**Implementation with Redis:**

```python
import redis
import json
from datetime import timedelta

# Initialize Redis client
redis_client = redis.Redis(
    host=os.environ.get('REDIS_HOST', 'localhost'),
    port=int(os.environ.get('REDIS_PORT', 6379)),
    password=os.environ.get('REDIS_PASSWORD'),
    db=int(os.environ.get('REDIS_DB', 0)),
    ssl=os.environ.get('REDIS_SSL', 'false').lower() == 'true',
    decode_responses=True
)

# Store session with TTL
def store_session(session_id, session_data, ttl_days=7):
    redis_client.setex(
        f"session:{session_id}",
        timedelta(days=ttl_days),
        json.dumps(session_data)
    )

# Retrieve session
def get_session(session_id):
    data = redis_client.get(f"session:{session_id}")
    return json.loads(data) if data else None

# Delete session
def delete_session(session_id):
    redis_client.delete(f"session:{session_id}")
```

**State Token Storage (OAuth CSRF protection):**
```python
# Store with short TTL (10 minutes)
def store_state_token(state, data):
    redis_client.setex(f"state:{state}", timedelta(minutes=10), json.dumps(data))

def get_state_token(state):
    data = redis_client.get(f"state:{state}")
    if data:
        redis_client.delete(f"state:{state}")  # Single use
        return json.loads(data)
    return None
```

#### 2. Cookie Security Hardening
**Current:** `secure=False`, `samesite="Lax"`  
**Required:** `secure=True` for HTTPS

**Files to modify:**
- `backend/app/auth.py` (lines 602-606, 743-744)

**Changes:**

```python
# In /auth/google/callback after successful authentication
response.set_cookie(
    "session_id",
    session_id,
    httponly=True,
    secure=True,  # ✅ REQUIRED for HTTPS
    samesite="Lax" if same_domain else "None",  # "None" requires secure=True
    path="/",
    max_age=86400 * 3,  # ✅ Shorter expiration: 3 days instead of 7
    domain=".yourdomain.com" if multi_subdomain else None
)

# In /auth/logout
response.set_cookie(
    "session_id",
    "",
    httponly=True,
    secure=True,  # ✅ Match login settings
    samesite="Lax" if same_domain else "None",
    path="/",
    max_age=0
)
```

**Notes:**
- `samesite="Lax"`: If frontend and backend on same domain
- `samesite="None"`: If on different domains (requires `secure=True`)
- `domain=".yourdomain.com"`: If frontend/backend on different subdomains

#### 3. JWKs Caching
**Current:** Fetches Google's public keys on every token verification  
**Required:** Cache with TTL to reduce API calls

**File to modify:**
- `backend/app/auth.py` (line 439)

**Implementation:**

```python
from datetime import datetime, timedelta

# In-memory cache (single instance)
_jwks_cache = None
_jwks_cache_time = None
JWKS_CACHE_TTL = 3600  # 1 hour

def get_google_jwks():
    """Get Google's JWKs with caching."""
    global _jwks_cache, _jwks_cache_time
    
    # Check cache
    if _jwks_cache and _jwks_cache_time:
        if datetime.utcnow() - _jwks_cache_time < timedelta(seconds=JWKS_CACHE_TTL):
            return _jwks_cache
    
    # Fetch fresh keys
    response = requests.get("https://www.googleapis.com/oauth2/v3/certs", timeout=5)
    response.raise_for_status()
    _jwks_cache = response.json()
    _jwks_cache_time = datetime.utcnow()
    
    return _jwks_cache

# Redis-based cache (multi-instance)
def get_google_jwks_redis():
    """Get Google's JWKs with Redis caching."""
    cached = redis_client.get("jwks:google")
    if cached:
        return json.loads(cached)
    
    # Fetch and cache
    response = requests.get("https://www.googleapis.com/oauth2/v3/certs", timeout=5)
    response.raise_for_status()
    jwks = response.json()
    redis_client.setex("jwks:google", 3600, json.dumps(jwks))
    
    return jwks
```

#### 4. Error Message Sanitization
**Current:** Exposes internal error details to users  
**Required:** Generic messages to prevent information leakage

**File to modify:**
- `backend/app/auth.py` (line 620, 626)

**Changes:**

```python
# In /auth/google/callback error handling
except Exception as e:
    # ✅ Log full error internally
    current_app.logger.error(f"OAuth callback failed: {str(e)}", exc_info=True)
    
    # ✅ Return generic message to user
    return jsonify({
        "error": {
            "code": "AUTHENTICATION_FAILED",
            "message": "Authentication failed. Please try again."  # Generic
        }
    }), 500

# Also apply to other error handlers
except ValidationError as e:
    current_app.logger.warning(f"Validation error: {str(e)}")
    return jsonify({
        "error": {
            "code": "INVALID_REQUEST",
            "message": "Invalid request parameters."
        }
    }), 400
```

#### 5. Secret Key Validation
**Current:** Auto-generates if not set  
**Required:** Fail fast if missing in production

**File to modify:**
- `backend/app/__init__.py` (lines 45-54)

**Changes:**

```python
# In create_app()
secret_key = os.environ.get("SECRET_KEY")

if flask_env == "production":
    if not secret_key:
        raise ValueError(
            "SECRET_KEY environment variable is required in production. "
            "Generate with: openssl rand -hex 32"
        )
    if len(secret_key) < 32:
        raise ValueError("SECRET_KEY must be at least 32 characters long")
else:
    # Development fallback
    if not secret_key:
        app.logger.warning("SECRET_KEY not set, using development default")
        secret_key = "dev-secret-change-in-production"

app.secret_key = secret_key
```

#### 6. CORS Restriction
**Current:** `ALLOWED_ORIGINS=*` (allows any origin)  
**Required:** Explicit domain list

**File to modify:**
- `backend/app/__init__.py` (lines 94-109)

**Changes:**

```python
allowed_origins = Config.ALLOWED_ORIGINS

# ✅ Fail fast if wildcard in production
if flask_env == "production" and "*" in allowed_origins:
    raise ValueError(
        "ALLOWED_ORIGINS cannot contain '*' in production. "
        "Set explicit domains: ALLOWED_ORIGINS=https://app.yourdomain.com"
    )

# Configure CORS
CORS(
    app,
    origins=allowed_origins,
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization"],
    expose_headers=["Content-Type"],
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
)
```

---

### Security Hardening

#### Security Headers
Add security headers to all responses to protect against common attacks.

**Implementation Options:**

**Option A: Use Flask-Talisman** (recommended)

```bash
# Add to requirements.txt
flask-talisman>=1.0.0
```

```python
# In backend/app/__init__.py
from flask_talisman import Talisman

if flask_env == "production":
    Talisman(
        app,
        force_https=True,
        strict_transport_security=True,
        strict_transport_security_max_age=31536000,  # 1 year
        content_security_policy={
            'default-src': ["'self'"],
            'script-src': ["'self'"],
            'style-src': ["'self'", "'unsafe-inline'"],
            'img-src': ["'self'", 'data:', 'https:'],
        },
        content_security_policy_nonce_in=['script-src'],
        referrer_policy='strict-origin-when-cross-origin',
        feature_policy={
            'geolocation': "'none'",
            'microphone': "'none'",
            'camera': "'none'",
        }
    )
```

**Option B: Manual Headers**

```python
@app.after_request
def add_security_headers(response):
    if Config.FLASK_ENV == "production":
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Content-Security-Policy'] = "default-src 'self'"
    return response
```

#### Rate Limiting
Protect against abuse and DDoS attacks.

**Implementation:**

```bash
# Add to requirements.txt
flask-limiter>=3.0.0
```

```python
# In backend/app/__init__.py
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri=os.environ.get("REDIS_URL", "memory://"),
    strategy="fixed-window"
)

# In routes/auth endpoints
@bp.route("/auth/google/login")
@limiter.limit("10 per minute")
def google_login():
    # ...

@bp.route("/auth/google/callback")
@limiter.limit("10 per minute")
def google_callback():
    # ...

# In chart endpoints
@bp.route("/chart", methods=["POST"])
@limiter.limit("100 per minute")
def chart():
    # ...
```

**Rate Limit Configuration:**
- Login attempts: 10 per minute per IP
- OAuth callback: 10 per minute per IP
- Chart calculations: 100 per minute per user
- Global: 200 requests per day, 50 per hour per IP

#### Input Validation
**Current:** Using Pydantic (already good)

**Verify:**
- [ ] All endpoints validate input with Pydantic models
- [ ] Date/time inputs have range checks (not too far in past/future)
- [ ] Latitude/longitude within valid ranges
- [ ] Enum values validated (houseSystem, ayanamsha, etc.)

#### Dependency Security Scanning
Set up automated vulnerability scanning.

**Option A: GitHub Dependabot**
- Enable in repository settings
- Auto-creates PRs for dependency updates
- Scans for known vulnerabilities

**Option B: Safety CLI**
```bash
# Add to CI/CD pipeline
pip install safety
safety check -r requirements.txt
```

**Option C: Snyk**
- Integrates with GitHub
- Provides detailed vulnerability reports
- Suggests fixes

---

### Additional Code Improvements

#### Session Expiration Implementation

```python
# In backend/app/auth.py - /me endpoint
@bp.route("/me")
def me():
    session_id = request.cookies.get("session_id")
    if not session_id:
        return jsonify({"logged_in": False}), 200
    
    session = get_session(session_id)  # From Redis
    if not session:
        return jsonify({"logged_in": False}), 200
    
    # ✅ Check expiration
    created_at = datetime.fromisoformat(session.get("created_at"))
    if datetime.utcnow() - created_at > timedelta(days=7):
        delete_session(session_id)
        return jsonify({"logged_in": False}), 200
    
    # ✅ Update last accessed time (optional)
    session["last_accessed"] = datetime.utcnow().isoformat()
    store_session(session_id, session, ttl_days=7)
    
    return jsonify({
        "logged_in": True,
        "user": session["user_info"]
    })
```

---

## Testing & Quality Assurance

### Pre-Deployment Testing

#### Unit & Integration Tests
- [ ] All tests passing: `pytest backend/tests/`
- [ ] Currently: 41 tests passing, 12 fixture errors (unrelated to production code)
- [ ] Fix remaining test fixtures before deployment
- [ ] Achieve >80% code coverage (run `pytest --cov`)

#### Load Testing
Test with expected production traffic using Locust, JMeter, or k6.

**Example with k6:**

```javascript
// load-test.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
  stages: [
    { duration: '2m', target: 50 },   // Ramp up to 50 users
    { duration: '5m', target: 50 },   // Stay at 50 users
    { duration: '2m', target: 100 },  // Ramp to 100 users
    { duration: '5m', target: 100 },  // Stay at 100 users
    { duration: '2m', target: 0 },    // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<2000'], // 95% of requests < 2s
    http_req_failed: ['rate<0.05'],    // Error rate < 5%
  },
};

export default function () {
  const payload = JSON.stringify({
    datetime: '1991-03-25T09:46:00',
    latitude: 18.5204,
    longitude: 73.8567,
    houseSystem: 'WHOLE_SIGN',
    ayanamsha: 'LAHIRI',
    nodeType: 'MEAN',
  });

  const params = {
    headers: { 'Content-Type': 'application/json' },
  };

  let res = http.post('https://api.yourdomain.com/chart', payload, params);
  
  check(res, {
    'status is 200': (r) => r.status === 200,
    'response time < 2s': (r) => r.timings.duration < 2000,
  });

  sleep(1);
}
```

Run: `k6 run load-test.js`

**Metrics to Monitor:**
- Response time (p50, p95, p99)
- Error rate
- Requests per second
- CPU/memory usage
- Database connection pool usage

#### Security Testing
- [ ] Run OWASP ZAP scan against staging environment
- [ ] Test for SQL injection (should be prevented by SQLAlchemy)
- [ ] Verify HTTPS configuration (SSL Labs test)
- [ ] Test CORS configuration (only allowed origins work)
- [ ] Verify rate limiting works (exceed limits, get 429 responses)
- [ ] Test authentication bypass attempts
- [ ] Verify sensitive data not in logs (grep for emails, tokens)

#### OAuth End-to-End Testing
- [ ] Complete login flow with Google account
- [ ] Verify session persists across requests
- [ ] Test logout functionality
- [ ] Verify unauthorized access denied (401)
- [ ] Test with multiple users simultaneously
- [ ] Verify session isolation (user A can't access user B's data)

---

### Staging Environment

#### Setup
- [ ] Deploy to staging environment (separate from production)
- [ ] Use staging database (not production)
- [ ] Use separate Google OAuth client (staging redirect URIs)
- [ ] Configure staging environment variables
- [ ] Enable debug logging in staging

#### Testing Checklist
- [ ] All critical user flows work end-to-end
- [ ] Authentication and authorization working
- [ ] Chart calculation endpoints functional
- [ ] Dasha calculation endpoints functional
- [ ] Error handling works correctly
- [ ] Logging outputs correct format (JSON in production mode)
- [ ] Health check endpoint returns 200

---

### Smoke Tests for Production

After deployment, run these critical tests immediately:

```bash
# 1. Health check
curl https://api.yourdomain.com/healthz
# Expected: 200 OK

# 2. License endpoint (AGPL compliance)
curl https://api.yourdomain.com/license
# Expected: 200 with license info

# 3. CORS headers
curl -H "Origin: https://app.yourdomain.com" -I https://api.yourdomain.com/healthz
# Expected: Access-Control-Allow-Origin header present

# 4. Chart endpoint (authenticated)
curl -X POST https://api.yourdomain.com/chart \
  -H "Content-Type: application/json" \
  -H "Cookie: session_id=YOUR_SESSION" \
  -d '{
    "datetime": "1991-03-25T09:46:00",
    "latitude": 18.5204,
    "longitude": 73.8567,
    "houseSystem": "WHOLE_SIGN",
    "ayanamsha": "LAHIRI",
    "nodeType": "MEAN"
  }'
# Expected: 200 with chart data

# 5. OAuth login redirect
curl -I https://api.yourdomain.com/auth/google/login
# Expected: 302 redirect to Google

# 6. Unauthorized access
curl https://api.yourdomain.com/chart
# Expected: 401 Unauthorized
```

---

### Rollback Plan

**Before Deployment:**
- [ ] Document current version/commit hash
- [ ] Tag release in git: `git tag v1.0.0`
- [ ] Keep previous Docker image available
- [ ] Document rollback procedure

**Rollback Procedure:**
1. **Identify issue** - Check logs, metrics, error rates
2. **Decide to rollback** - If critical issue affecting users
3. **Execute rollback:**
   ```bash
   # Docker
   docker pull your-registry/vedic-backend:v0.9.9  # Previous version
   docker stop current-container
   docker run previous-version
   
   # Kubernetes
   kubectl rollout undo deployment/vedic-backend
   
   # Managed platform (Railway, Render)
   # Use platform UI to rollback to previous deployment
   ```
4. **Verify rollback** - Run smoke tests
5. **Investigate issue** - Fix in development, redeploy when ready

**Database Rollback:**
- If schema changed, have migration rollback script ready
- Test rollback procedure in staging first
- Consider blue-green deployment for zero-downtime

---

## Deployment Process

### Pre-Flight Checklist

#### Code & Configuration
- [ ] All PRODUCTION comments in code addressed (20+ in auth.py)
- [ ] SECRET_KEY generated and set in environment
- [ ] ALLOWED_ORIGINS set to production domains (no wildcards)
- [ ] DATABASE_URL uses session pooler (port 6543)
- [ ] Google OAuth redirect URIs updated to HTTPS
- [ ] All environment variables set correctly
- [ ] Docker image built and tagged
- [ ] Code merged to main branch
- [ ] Git tag created for release

#### Infrastructure
- [ ] SSL/TLS certificate installed and valid
- [ ] DNS pointing to correct server/load balancer
- [ ] Database accessible from application server
- [ ] Redis accessible (if using for sessions)
- [ ] Firewall rules configured
- [ ] Health check endpoint working

#### External Services
- [ ] Google OAuth client configured for production
- [ ] Supabase database provisioned and accessible
- [ ] Monitoring services configured (Sentry, etc.)
- [ ] Log aggregation service configured

---

### Deployment Steps

1. **Final Code Review**
   ```bash
   # Review all changes
   git diff main origin/main
   
   # Run tests locally
   cd backend && pytest
   
   # Build Docker image
   docker build -t vedic-backend:v1.0.0 .
   ```

2. **Tag Release**
   ```bash
   git tag -a v1.0.0 -m "Production release v1.0.0"
   git push origin v1.0.0
   ```

3. **Deploy to Staging**
   ```bash
   # Deploy to staging first
   # Run all smoke tests
   # Monitor for 1 hour minimum
   ```

4. **Deploy to Production**
   ```bash
   # Push Docker image
   docker push your-registry/vedic-backend:v1.0.0
   
   # Deploy to platform
   # (Platform-specific commands)
   ```

5. **Run Smoke Tests**
   ```bash
   # Run all smoke tests from "Smoke Tests" section
   # Verify critical functionality working
   ```

6. **Monitor Closely**
   - Watch error rates in monitoring dashboard
   - Check logs for unexpected errors
   - Monitor response times
   - Verify database connections stable

7. **Announce Launch** (if public release)
   - Update documentation with production URLs
   - Announce to users/team
   - Update status page

---

## Post-Deployment Operations

### Monitoring & Observability

#### Application Performance Monitoring (APM)

**Recommended: Sentry for Error Tracking**

```bash
# Add to requirements.txt
sentry-sdk[flask]>=1.40.0
```

```python
# In backend/app/__init__.py
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

if Config.FLASK_ENV == "production":
    sentry_sdk.init(
        dsn=os.environ.get("SENTRY_DSN"),
        integrations=[FlaskIntegration()],
        traces_sample_rate=0.1,  # 10% of requests for performance monitoring
        profiles_sample_rate=0.1,
        environment="production",
        release=os.environ.get("GIT_COMMIT", "unknown"),
    )
```

**Metrics to Track:**
- Error rate and types
- Request latency (p50, p95, p99)
- Throughput (requests per second)
- Chart calculation time
- Database query time
- Memory usage
- CPU usage

#### Log Aggregation

**Current:** Application outputs JSON logs (production mode) ✓

**Options for Centralized Logging:**

1. **CloudWatch Logs** (AWS)
   - Automatic if deploying to ECS/EC2
   - Use CloudWatch agent for Docker

2. **Google Cloud Logging** (GCP)
   - Automatic if deploying to Cloud Run/GKE

3. **Managed Services:**
   - Papertrail, Loggly, Datadog
   - Easy integration, paid

4. **ELK Stack** (self-hosted)
   - Elasticsearch, Logstash, Kibana
   - Full control, more maintenance

**Configuration:**
```bash
# Already configured to output JSON in production
FLASK_ENV=production  # Enables JSON logging
LOG_LEVEL=INFO        # Or WARNING to reduce volume
```

#### Uptime Monitoring

**Options:**
- **UptimeRobot** (free tier available)
- **Pingdom** (paid, comprehensive)
- **StatusCake** (free tier available)
- **Better Uptime** (modern, affordable)

**Configuration:**
- Monitor: `https://api.yourdomain.com/healthz`
- Interval: Every 5 minutes
- Alert: Email/SMS if down for 2 consecutive checks
- Alert: Slack/Discord webhook for team notification

#### Alert Configuration

**Critical Alerts (immediate notification):**
- Application down (health check failing)
- Error rate > 10% for 5 minutes
- Database connection failures
- Response time p95 > 5 seconds
- CPU/Memory > 90% for 5 minutes

**Warning Alerts (investigate soon):**
- Error rate > 5% for 5 minutes
- Response time p95 > 2 seconds
- Failed authentication attempts > 10/minute (possible attack)
- Disk space > 80%
- Database connection pool > 80% usage

**Info Alerts (track trends):**
- Deployment completed
- Daily traffic summary
- Weekly performance report

#### Custom Metrics

**Implement Application-Specific Metrics:**

```python
# In backend/app/routes.py
from datetime import datetime

# Track chart calculations
chart_calculations_total = 0
chart_calculation_times = []

@bp.route("/chart", methods=["POST"])
def chart():
    start_time = datetime.utcnow()
    
    # ... chart calculation logic ...
    
    # Record metrics
    duration = (datetime.utcnow() - start_time).total_seconds()
    chart_calculation_times.append(duration)
    chart_calculations_total += 1
    
    # Log for analysis
    current_app.logger.info(f"Chart calculation completed", extra={
        "duration_seconds": duration,
        "house_system": payload.houseSystem,
        "ayanamsha": payload.ayanamsha,
    })
```

**Metrics to Track:**
- Chart calculations per minute/hour/day
- Average calculation time by house system
- Cache hit ratio (if caching results)
- Session creation/deletion rates
- Active sessions count
- User signup rate (if public)

---

### Performance Optimization

#### Response Caching
Chart results are deterministic - same inputs always produce same outputs.

**Implementation:**

```python
# Simple in-memory cache
from functools import lru_cache
import hashlib

def cache_key(payload):
    """Generate cache key from request parameters."""
    key_data = f"{payload.datetime}:{payload.latitude}:{payload.longitude}:{payload.houseSystem}:{payload.ayanamsha}"
    return hashlib.md5(key_data.encode()).hexdigest()

# Redis-based cache
def get_cached_chart(cache_key):
    cached = redis_client.get(f"chart:{cache_key}")
    return json.loads(cached) if cached else None

def cache_chart(cache_key, result, ttl_days=30):
    # Charts don't change, can cache for long time
    redis_client.setex(f"chart:{cache_key}", timedelta(days=ttl_days), json.dumps(result))
```

**Cache Invalidation:**
- Charts rarely change (only if ephemeris data updated)
- Can use very long TTL (30+ days)
- Clear cache on ephemeris data update

#### Database Indexing
**Verify indexes on frequently queried columns:**

```sql
-- Check existing indexes
SELECT * FROM pg_indexes WHERE tablename IN ('users', 'profiles', 'charts');

-- Add indexes if missing
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_profiles_user_id ON profiles(user_id);
CREATE INDEX idx_profiles_active ON profiles(is_active) WHERE is_active = true;
CREATE INDEX idx_charts_profile_id ON charts(profile_id);
CREATE INDEX idx_charts_created_at ON charts(created_at DESC);
```

#### Compression
Enable gzip compression for API responses.

**Gunicorn configuration** (already supports compression):
```python
# Add to gunicorn.conf.py or use nginx/load balancer
# Most platforms handle this automatically
```

**Or use Flask-Compress:**
```bash
# Add to requirements.txt
flask-compress>=1.14
```

```python
# In backend/app/__init__.py
from flask_compress import Compress

Compress(app)  # Automatically compresses responses
```

#### Connection Pooling
**Already configured** in `backend/app/db.py` ✓

**Monitor and tune based on load:**
```python
# Check pool stats
from sqlalchemy import event

@event.listens_for(db.engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    current_app.logger.debug(f"Database connection opened: {id(dbapi_conn)}")

@event.listens_for(db.engine, "close")
def receive_close(dbapi_conn, connection_record):
    current_app.logger.debug(f"Database connection closed: {id(dbapi_conn)}")
```

---

### Compliance & Legal

#### AGPL v3 Compliance (CRITICAL)

This project uses Swiss Ephemeris, which is AGPL-licensed. Compliance is **legally required**.

**Required Actions:**
- [ ] Publish source code to public GitHub repository
- [ ] Ensure LICENSE file present in repository root ✓
- [ ] Verify `/license` endpoint functional and returning correct info
- [ ] Confirm startup logs show AGPL notice ✓
- [ ] Update `AGPL_COMPLIANCE.md` with actual GitHub repository URL
- [ ] Update `backend/README.md` with source code links

**Verification:**
```bash
# Test /license endpoint
curl https://api.yourdomain.com/license | jq

# Should return:
# {
#   "license": "AGPL-3.0",
#   "source": "https://github.com/yourusername/jyotishika",
#   "components": [...]
# }
```

**Update Required Files:**
1. `backend/AGPL_COMPLIANCE.md` - Replace `[YOUR_GITHUB_REPO_URL]` with actual URL
2. `backend/README.md` - Update source code URLs in license section
3. `backend/app/__init__.py` - Update source URL in startup logs

#### GDPR Compliance (if serving EU users)

**Current Implementation:** Privacy-preserving logging ✓
- Email addresses masked in logs
- User IDs used instead of emails
- No PII in logs

**Additional Requirements:**
- [ ] Create Privacy Policy document
- [ ] Implement data export (user can download their data)
- [ ] Implement data deletion (right to be forgotten)
- [ ] Cookie consent banner (if serving to EU)
- [ ] Data processing agreement (if applicable)

**Data Retention:**
```sql
-- Delete inactive users after 2 years
DELETE FROM users 
WHERE last_login_at < NOW() - INTERVAL '2 years' 
AND is_active = false;

-- Or anonymize instead of delete
UPDATE users 
SET email = 'deleted_' || id || '@example.com',
    name = 'Deleted User',
    picture = NULL
WHERE last_login_at < NOW() - INTERVAL '2 years';
```

#### Privacy Policy
Create `PRIVACY.md` or web page covering:
- What data is collected (email, name, birth chart data)
- How it's used (authentication, chart calculation, storage)
- How long it's retained (define retention policy)
- User rights (access, export, deletion)
- Security measures (encryption, access controls)
- Contact information for privacy concerns

#### Terms of Service
Define acceptable use policy:
- Permitted uses of the API
- Rate limiting and abuse prevention
- Intellectual property rights
- Disclaimer of warranties
- Limitation of liability

---

### Backup & Disaster Recovery

#### Database Backups

**Supabase Built-in Backups:**
- [ ] Verify automated daily backups enabled
- [ ] Set backup retention period (30+ days recommended)
- [ ] Document backup location and access

**Manual Backup Procedure:**
```bash
# Backup entire database
pg_dump "$DATABASE_URL" > backup_$(date +%Y%m%d_%H%M%S).sql

# Backup specific tables
pg_dump "$DATABASE_URL" -t users -t approved_users -t profiles -t charts > backup.sql

# Restore from backup
psql "$DATABASE_URL" < backup.sql
```

**Test Restore Procedure:**
- [ ] Perform test restore to staging environment
- [ ] Verify data integrity after restore
- [ ] Document restore procedure step-by-step
- [ ] Set calendar reminder to test quarterly

#### Configuration Backups
- [ ] Export all environment variables to secure storage
- [ ] Document all infrastructure configuration
- [ ] Store Google OAuth credentials securely
- [ ] Backup any manual database changes (not in schema.sql)

#### Disaster Recovery Plan

**RTO (Recovery Time Objective):** How quickly to recover
- Target: 4 hours from disaster to fully operational

**RPO (Recovery Point Objective):** Maximum acceptable data loss
- Target: 24 hours (daily backups)

**Incident Response Procedure:**

1. **Identify Incident**
   - Alert received (uptime monitor, error spike)
   - Severity assessment (critical, high, medium, low)

2. **Initial Response** (within 15 minutes)
   - Acknowledge incident
   - Notify team/stakeholders
   - Begin investigation

3. **Diagnosis** (within 1 hour)
   - Check application logs
   - Check database connectivity
   - Check infrastructure status
   - Identify root cause

4. **Recovery** (based on severity)
   - **Application crash:** Restart application
   - **Database issue:** Check connections, failover if needed
   - **Infrastructure failure:** Restore from backup or redeploy
   - **Data loss:** Restore from most recent backup

5. **Verification**
   - Run smoke tests
   - Verify data integrity
   - Monitor for recurring issues

6. **Post-Mortem**
   - Document what happened
   - Identify preventive measures
   - Update documentation
   - Implement improvements

#### Session Data Backup (if using Redis)
**Configure Redis Persistence:**

```bash
# RDB (periodic snapshots)
save 900 1      # Save after 900 seconds if at least 1 key changed
save 300 10     # Save after 300 seconds if at least 10 keys changed
save 60 10000   # Save after 60 seconds if at least 10000 keys changed

# AOF (append-only file, more durable)
appendonly yes
appendfsync everysec
```

**Or:** Use managed Redis (AWS ElastiCache, Redis Cloud) with automated backups

---

### CI/CD Pipeline

#### Automated Testing
Set up GitHub Actions, GitLab CI, or similar.

**Example GitHub Actions** (`.github/workflows/test.yml`):

```yaml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
      
      - name: Run linting
        run: |
          cd backend
          ruff check app/ tests/
          black --check app/ tests/
      
      - name: Run tests
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/postgres
          EPHE_PATH: ./ephe
        run: |
          cd backend
          pytest tests/ -v --cov=app --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./backend/coverage.xml
```

#### Security Scanning

```yaml
# .github/workflows/security.yml
name: Security Scan

on: [push]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: './backend'
          format: 'sarif'
          output: 'trivy-results.sarif'
      
      - name: Upload Trivy results
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-results.sarif'
```

#### Docker Image Building

```yaml
# .github/workflows/docker.yml
name: Build Docker Image

on:
  push:
    branches: [main]
    tags: ['v*']

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2
      
      - name: Login to Container Registry
        uses: docker/login-action@v2
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Build and push
        uses: docker/build-push-action@v4
        with:
          context: ./backend
          push: true
          tags: |
            ghcr.io/${{ github.repository }}:latest
            ghcr.io/${{ github.repository }}:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

#### Deployment Automation

**Option A: Automatic to staging, manual to production**
```yaml
# Deploy to staging on every main branch commit
# Deploy to production on git tag (v*)
```

**Option B: Manual approval workflow**
```yaml
jobs:
  deploy-staging:
    # Auto deploy to staging
  
  deploy-production:
    needs: deploy-staging
    environment: production  # Requires manual approval
    # Deploy to production after approval
```

---

### Cost Optimization

#### Resource Sizing Strategy
**Start small, scale as needed:**

1. **Initial Deployment:**
   - 1-2 vCPUs, 1-2 GB RAM
   - Gunicorn: 3-5 workers
   - Supabase: Free tier (500 MB database)
   - Monitor for 1-2 weeks

2. **Monitor Metrics:**
   - CPU usage (target: 50-70% average)
   - Memory usage (target: 60-80% average)
   - Request latency
   - Error rate

3. **Scale Up If:**
   - CPU consistently > 80%
   - Memory consistently > 85%
   - Request latency p95 > 2 seconds
   - Frequent 503 errors (server overload)

4. **Scale Down If:**
   - CPU consistently < 30%
   - Memory consistently < 40%
   - Paying for unused resources

#### Database Plan Selection
**Supabase Pricing Tiers:**

- **Free:** $0/month
  - 500 MB database
  - 50 MB file storage
  - Good for: MVP, testing, small projects

- **Pro:** $25/month
  - 8 GB database
  - 100 GB file storage
  - Daily backups
  - Good for: Production, growing user base

- **Team:** $599/month
  - 50+ GB database
  - Advanced features
  - Good for: Large-scale production

**Recommendation:** Start with Free tier, upgrade to Pro when:
- Database > 400 MB (80% of limit)
- Need daily backups
- Need better support

#### Monitoring Costs
**Balance observability with budget:**

- **Free Tier Services:**
  - Sentry: 5K events/month free
  - UptimeRobot: 50 monitors free
  - Better Stack: Free tier available

- **Paid Services** (consider when scaling):
  - Datadog: ~$15-30/host/month
  - New Relic: ~$25-100/month
  - Papertrail: ~$7-70/month

**Strategy:**
- Start with free tiers
- Upgrade when hitting limits
- Review monthly to optimize

#### Ephemeris Files Optimization
**Current:** Baked into Docker image (~500 MB)

**Alternatives:**
1. **Mount as volume** (reduces image size)
   ```dockerfile
   # Don't COPY ephe files
   # Mount at runtime
   docker run -v /path/to/ephe:/app/ephe ...
   ```

2. **Object storage** (S3/GCS)
   ```python
   # Download on startup
   if not os.path.exists('/app/ephe'):
       download_from_s3('ephe-files', '/app/ephe')
   ```

**Recommendation:** Start with baked-in, optimize later if needed

#### Log Retention
**Balance debugging needs with storage costs:**

- **Hot logs** (searchable): 7-30 days
- **Warm logs** (archived): 30-90 days
- **Cold logs** (backup only): 90-365 days

**Configure in log aggregation service:**
```
7 days:  Full text search enabled
30 days: Compressed, searchable
90 days: Archived, retrievable
>90:     Deleted or deep archive
```

---

## Final Checklist

### Infrastructure ✓
- [ ] SSL/TLS certificate installed and auto-renewing
- [ ] DNS configured and propagated
- [ ] Load balancer configured (if applicable)
- [ ] Container orchestration set up
- [ ] Gunicorn workers configured appropriately
- [ ] Health checks configured

### Database ✓
- [ ] PostgreSQL database provisioned (Supabase)
- [ ] Database URL uses session pooler (port 6543)
- [ ] Schema applied from schema.sql
- [ ] Connection pooling configured
- [ ] Automated backups enabled
- [ ] Restore procedure tested
- [ ] RLS decision made (enabled or disabled)

### Environment Variables ✓
- [ ] All required variables set
- [ ] SECRET_KEY generated (32+ characters)
- [ ] ALLOWED_ORIGINS restricted (no wildcards)
- [ ] DATABASE_URL correct format
- [ ] Google OAuth credentials set
- [ ] APP_BASE_URL uses HTTPS
- [ ] FRONTEND_BASE_URL correct
- [ ] FLASK_ENV=production
- [ ] LOG_LEVEL=INFO or WARNING

### Code Changes ✓
- [ ] Session storage migrated to Redis/database
- [ ] State token storage migrated to Redis/database
- [ ] Cookie security hardened (secure=True, appropriate samesite)
- [ ] JWKs caching implemented
- [ ] Error messages sanitized (no internal details exposed)
- [ ] SECRET_KEY validation (fails fast if missing in production)
- [ ] CORS restricted to production domains
- [ ] All PRODUCTION comments in code addressed

### Security ✓
- [ ] Security headers added (HSTS, CSP, X-Frame-Options, etc.)
- [ ] Rate limiting implemented
- [ ] Input validation verified (Pydantic)
- [ ] Dependency scanning enabled
- [ ] Secrets managed securely (not in code)

### Google OAuth ✓
- [ ] Production OAuth client created
- [ ] Authorized origins set to HTTPS URLs
- [ ] Authorized redirect URIs set to HTTPS
- [ ] Development URIs removed from production client
- [ ] OAuth consent screen configured

### Testing ✓
- [ ] All unit tests passing
- [ ] Load testing completed
- [ ] Security testing completed (OWASP ZAP)
- [ ] OAuth flow tested end-to-end
- [ ] Staging deployment tested
- [ ] Smoke tests prepared

### Monitoring ✓
- [ ] APM/error tracking configured (Sentry)
- [ ] Log aggregation configured
- [ ] Uptime monitoring configured
- [ ] Alerts configured (critical, warning, info)
- [ ] Custom metrics implemented
- [ ] Dashboards created

### Compliance ✓
- [ ] AGPL compliance verified
- [ ] Source code published to public GitHub
- [ ] LICENSE file present
- [ ] /license endpoint functional
- [ ] AGPL_COMPLIANCE.md updated with GitHub URL
- [ ] Startup logs show AGPL notice
- [ ] Privacy policy created (if needed)
- [ ] Terms of service created (if needed)

### Backup & Recovery ✓
- [ ] Database backups automated
- [ ] Backup retention configured (30+ days)
- [ ] Restore procedure documented and tested
- [ ] Configuration backups stored securely
- [ ] Disaster recovery plan documented
- [ ] RTO/RPO defined
- [ ] Redis persistence configured (if applicable)

### CI/CD ✓
- [ ] Automated testing pipeline set up
- [ ] Linting and formatting checks automated
- [ ] Security scanning automated
- [ ] Docker image building automated
- [ ] Deployment automation configured
- [ ] Rollback capability tested

### Documentation ✓
- [ ] README updated with production URLs
- [ ] API documentation updated
- [ ] Deployment guide created
- [ ] Troubleshooting guide created
- [ ] Changelog maintained
- [ ] AGPL_COMPLIANCE.md updated

### Deployment ✓
- [ ] Code merged to main branch
- [ ] Git tag created for release
- [ ] Deployed to staging successfully
- [ ] Deployed to production successfully
- [ ] Smoke tests passed
- [ ] Monitoring dashboard shows healthy

### Post-Deployment ✓
- [ ] Monitored for first 24 hours
- [ ] Performance baseline recorded
- [ ] Users/team notified of launch
- [ ] Support plan in place
- [ ] Incident response plan ready

---

## Support & Troubleshooting

### Common Issues

#### SSL Certificate Issues
**Symptom:** Browser shows "Not Secure" or certificate warnings

**Solutions:**
- Verify certificate installed correctly
- Check certificate expiration date
- Verify domain matches certificate
- Enable auto-renewal
- Check intermediate certificates

#### Database Connection Errors
**Symptom:** "Connection refused" or "Too many connections"

**Solutions:**
- Verify DATABASE_URL correct and accessible
- Check firewall rules allow connection
- Verify using session pooler (port 6543)
- Check connection pool settings
- Monitor active connections

#### OAuth Not Working
**Symptom:** Redirect loops or "redirect_uri_mismatch" errors

**Solutions:**
- Verify Google OAuth redirect URI exactly matches APP_BASE_URL + /auth/google/callback
- Check HTTPS (not HTTP) in production
- Verify correct OAuth client ID and secret
- Clear browser cookies and try again

#### High Response Times
**Symptom:** Requests taking > 2 seconds

**Solutions:**
- Check database query performance
- Verify connection pool not exhausted
- Check CPU/memory usage on server
- Implement caching for chart results
- Consider scaling up resources

#### Session Not Persisting
**Symptom:** Users logged out on every request

**Solutions:**
- Verify cookies being set correctly (check browser DevTools)
- Check secure=True only used with HTTPS
- Verify samesite setting appropriate for your setup
- Check Redis connectivity (if using Redis for sessions)
- Verify session TTL not expired

#### Rate Limit Exceeded
**Symptom:** 429 Too Many Requests errors

**Solutions:**
- Verify rate limits configured appropriately
- Check if legitimate traffic or abuse
- Adjust rate limits if too restrictive
- Implement user-specific limits (not just IP-based)

### Getting Help

**Internal Resources:**
- Check application logs: `docker logs container-name`
- Check monitoring dashboard for error spikes
- Review recent deployments/changes

**External Resources:**
- Swiss Ephemeris documentation: https://www.astro.com/swisseph/
- Flask documentation: https://flask.palletsprojects.com/
- Supabase documentation: https://supabase.com/docs
- Stack Overflow tag: [flask] [google-oauth]

**Emergency Rollback:**
If production is severely impacted and fix not immediately available:
1. Rollback to previous version
2. Investigate issue in staging
3. Deploy fix when ready

---

## Conclusion

This checklist covers all aspects of production deployment:

- ✅ **Infrastructure:** SSL, DNS, load balancing, containers
- ✅ **Database:** PostgreSQL, backups, connection pooling, RLS
- ✅ **Security:** Authentication, authorization, headers, rate limiting
- ✅ **Code:** All production comments addressed, best practices applied
- ✅ **Compliance:** AGPL, GDPR, privacy
- ✅ **Monitoring:** APM, logging, alerts, custom metrics
- ✅ **Operations:** Backups, disaster recovery, CI/CD
- ✅ **Testing:** Unit, load, security, smoke tests

**Before going live:** Review each section, check all boxes, and test thoroughly in staging.

**After deployment:** Monitor closely, respond to issues promptly, and iterate based on real-world usage.

Good luck with your deployment! 🚀
