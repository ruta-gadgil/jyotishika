# Email Allowlist Authorization - Deployment Guide

This guide explains how to deploy and use the email allowlist authorization system.

## Overview

The authorization system uses a two-table design with defense-in-depth security:

1. **`approved_users`** - Manually maintained email allowlist
2. **`users`** - Automatically created user records

**Both tables must have `is_active=true` for a user to access protected routes.**

## Architecture

```
OAuth Flow:
1. User clicks "Login with Google"
2. Google OAuth redirects to /auth/google/callback
3. Backend verifies Google ID token ✓
4. Backend checks if email is in approved_users with is_active=true
5a. If NOT approved → redirect to /auth/denied (no session)
5b. If approved → create/update user record in users table
6. Create session cookie and redirect to frontend

Protected Route Access:
1. User makes request to /me or other protected route
2. Backend validates session cookie
3. Backend checks users.is_active = true
4. Backend checks approved_users.is_active = true
5a. If any check fails → return 401 Unauthorized
5b. If all checks pass → return user data
```

## Setup Instructions

### 1. Database Setup

#### Option A: Supabase Dashboard (Recommended for Quick Setup)

1. Go to your Supabase project
2. Click **SQL Editor** in the sidebar
3. Create a new query
4. Copy and paste the contents of `backend/sql/schema.sql`
5. Click **Run** to create the tables

#### Option B: Command Line (Using psql)

```bash
# Get your DATABASE_URL from Supabase Project Settings > Database > Connection String
psql "postgresql://user:password@db.xxxxx.supabase.co:5432/postgres" -f backend/sql/schema.sql
```

### 2. Environment Configuration

1. Get your Supabase connection string:
   - Go to **Supabase Project Settings > Database**
   - Copy the **Connection String** (URI format)
   - Use the **Session Pooler** URL for production (port 6543)
   - Use the **Direct Connection** URL for development (port 5432)

2. Update `local.env` (for local development):

```bash
DATABASE_URL=postgresql://postgres.[PROJECT-REF]:[PASSWORD]@db.[REGION].supabase.co:5432/postgres
```

3. Set production environment variable:

```bash
# Railway, Heroku, etc.
export DATABASE_URL="postgresql://..."

# Or add to your deployment platform's environment variables
```

### 3. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 4. Add Approved Users

Users must be added to the `approved_users` table BEFORE they can log in.

#### Option A: Supabase Dashboard

1. Go to **Table Editor** in Supabase
2. Select `approved_users` table
3. Click **Insert row**
4. Fill in:
   - `email`: The exact email from Google OAuth (case-sensitive)
   - `is_active`: ✓ (checked)
   - `note`: Optional (e.g., "Admin", "Beta tester")
5. Click **Save**

#### Option B: SQL Insert

```sql
-- Add single user
INSERT INTO approved_users (email, note)
VALUES ('user@example.com', 'Admin account');

-- Add multiple users
INSERT INTO approved_users (email, note) VALUES
    ('admin@example.com', 'Admin'),
    ('user1@example.com', 'Beta tester'),
    ('user2@example.com', 'Team member');
```

#### Option C: psql Command Line

```bash
psql $DATABASE_URL -c "INSERT INTO approved_users (email, note) VALUES ('user@example.com', 'Admin');"
```

### 5. Test the Authorization Flow

1. Start your backend server:

```bash
cd backend
gunicorn -c gunicorn.conf.py "app:create_app()"
```

2. Test authentication flow:

```bash
# Open browser to login
open http://localhost:8000/auth/google/login

# After successful login, check your user info
curl -b cookies.txt http://localhost:8000/me
```

3. Test authorization denial:
   - Try logging in with an email NOT in `approved_users`
   - Should redirect to `/auth/denied`
   - No session should be created

## User Management

### Approving a New User

```sql
-- Add to allowlist
INSERT INTO approved_users (email, note)
VALUES ('newuser@example.com', 'Reason for approval');
```

User can now log in. A record will be automatically created in the `users` table.

### Deactivating a User (Two Options)

**Option 1: Deactivate in `approved_users` (recommended)**
```sql
UPDATE approved_users
SET is_active = false
WHERE email = 'user@example.com';
```

**Option 2: Deactivate in `users` table**
```sql
UPDATE users
SET is_active = false
WHERE email = 'user@example.com';
```

**Both checks are enforced** - either deactivation will prevent access.

### Reactivating a User

```sql
-- Reactivate in approved_users
UPDATE approved_users
SET is_active = true
WHERE email = 'user@example.com';

-- Or reactivate in users
UPDATE users
SET is_active = true
WHERE email = 'user@example.com';
```

### Removing a User Completely

```sql
-- Remove from allowlist (user can't log in anymore)
DELETE FROM approved_users WHERE email = 'user@example.com';

-- Optionally, delete user record (keeps data if you want audit trail)
DELETE FROM users WHERE email = 'user@example.com';
```

## Querying Users

### List All Approved Emails

```sql
SELECT email, is_active, added_at, note
FROM approved_users
ORDER BY added_at DESC;
```

### List All Active Users

```sql
SELECT id, email, name, created_at, last_login_at
FROM users
WHERE is_active = true
ORDER BY last_login_at DESC;
```

### Check User Authorization Status

```sql
SELECT
    u.email,
    u.is_active AS user_active,
    a.is_active AS approved_active,
    u.last_login_at,
    a.note
FROM users u
JOIN approved_users a ON u.email = a.email
WHERE u.email = 'user@example.com';
```

### Find Inactive Users

```sql
-- Users who haven't logged in for 30+ days
SELECT email, name, last_login_at
FROM users
WHERE last_login_at < NOW() - INTERVAL '30 days'
  AND is_active = true
ORDER BY last_login_at ASC;
```

## Protecting New Routes

To protect a new Flask route, use the `get_current_user()` dependency:

```python
from .auth import get_current_user

@bp.route("/protected-endpoint", methods=["GET"])
def protected_endpoint():
    # Validate authorization
    session_data = get_current_user()
    if isinstance(session_data, tuple):  # Error response
        return session_data
    
    # User is authorized
    from flask import g
    user = g.current_user  # Database user object
    
    return jsonify({
        "message": "Protected data",
        "user_email": user.email
    })
```

## Security Notes

### Defense in Depth

The system checks authorization at multiple points:

1. **OAuth Callback** - Email must be in `approved_users` to create session
2. **Protected Routes** - Both `users.is_active` AND `approved_users.is_active` checked
3. **Dual Tables** - Can deactivate at either level

### Session Storage

- **Current**: In-memory dictionary (sessions lost on restart)
- **Production**: Use Redis for persistence across restarts/instances

### Database Connection

- Connection pooling configured (10 permanent, 20 overflow)
- Pool pre-ping validates connections before use
- Automatic connection recycling every hour

### Error Handling

- Generic 401 responses (don't leak which check failed)
- Detailed logs for security monitoring
- Fail-closed on database errors (deny access)

## Troubleshooting

### User Can't Log In

1. Check if email is in `approved_users`:
```sql
SELECT * FROM approved_users WHERE email = 'user@example.com';
```

2. Check if `is_active` is true:
```sql
SELECT email, is_active FROM approved_users WHERE email = 'user@example.com';
```

3. Check backend logs for authorization denial messages

### Database Connection Errors

1. Verify `DATABASE_URL` is set:
```bash
echo $DATABASE_URL
```

2. Test connection:
```bash
psql $DATABASE_URL -c "SELECT 1;"
```

3. Check health endpoint:
```bash
curl http://localhost:8000/healthz
```

### User Gets 401 After Logging In

1. Check both tables' `is_active` flags:
```sql
SELECT u.email, u.is_active AS user_active, a.is_active AS approved_active
FROM users u
JOIN approved_users a ON u.email = a.email
WHERE u.email = 'user@example.com';
```

2. Check session cookie is being sent:
```bash
# In browser console
document.cookie
```

## Production Checklist

- [ ] `DATABASE_URL` set via environment variable (not in code)
- [ ] Use Supabase Session Pooler URL (port 6543) for production
- [ ] `SECRET_KEY` set to strong random value (not default)
- [ ] `ALLOWED_ORIGINS` restricted to your frontend domain (not `*`)
- [ ] OAuth cookies use `secure=True` and `samesite="None"` for HTTPS
- [ ] Consider migrating sessions from in-memory to Redis
- [ ] Monitor failed authorization attempts in logs
- [ ] Set up backup for `approved_users` table
- [ ] Document admin process for approving new users

## Files Created/Modified

### New Files
- `backend/sql/schema.sql` - Database schema
- `backend/app/models.py` - SQLAlchemy ORM models
- `backend/app/db.py` - Database utilities
- `backend/AUTHORIZATION_GUIDE.md` - This file

### Modified Files
- `backend/app/config.py` - Added DATABASE_URL
- `backend/app/__init__.py` - Initialize SQLAlchemy
- `backend/app/auth.py` - Added authorization checks, `/auth/denied`, `get_current_user()`
- `backend/requirements.txt` - Added Flask-SQLAlchemy, psycopg2-binary
- `env.example` - Added DATABASE_URL example
- `local.env` - Added DATABASE_URL for development

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review logs for detailed error messages
3. Verify database schema matches `backend/sql/schema.sql`
4. Test with `curl` to isolate frontend vs backend issues


