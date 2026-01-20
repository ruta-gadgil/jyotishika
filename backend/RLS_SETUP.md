# Row Level Security (RLS) Setup Guide

## Overview

Row Level Security (RLS) provides **database-level protection** for sensitive profile data. Even if application code is bypassed (SQL injection, direct database access, compromised credentials), users can only access their own profiles and charts.

## Security Benefits

### Defense in Depth
- **Application-level**: Python code verifies ownership (current implementation)
- **Database-level**: RLS policies enforce access at the database level (additional layer)

### Protection Scenarios
1. **SQL Injection**: If an attacker injects SQL, RLS still filters results
2. **Direct Database Access**: Even with database credentials, users can only see their data
3. **Application Bugs**: If application code has a bug, RLS provides backup protection
4. **Compromised Application**: If the application server is compromised, RLS limits data exposure

## Current Status

**RLS is enabled on all tables** with different enforcement levels:

- ✅ **RLS active and enforced** on `approved_users` and `users` tables (denies all PostgREST access)
- ✅ **RLS active** on `profiles`, `charts`, and `analysis_notes` tables
- ⚠️ **Policies commented out** for `profiles`, `charts`, and `analysis_notes` (permissive mode - ready for future use)
- 🔒 **Decision**: User-scoped RLS policies remain commented out. Application-level security checks provide sufficient protection for current needs.
- 📝 **Future**: To activate enforcement for user data tables, uncomment policies in `schema.sql` and add `set_rls_user_id()` calls to routes

## Setup Instructions

> **Note**: The following instructions are for **future use** when you decide to enable user-scoped RLS policies. Currently, these policies remain commented out and application-level security is used instead.

### Step 1: Enable RLS Policies (Future)

1. Open `backend/sql/schema.sql`
2. Find the RLS policy section (near the end)
3. Uncomment the policies you want to enforce:
   ```sql
   -- Change from:
   -- CREATE POLICY profiles_select_own ON profiles...
   
   -- To:
   CREATE POLICY profiles_select_own ON profiles...
   ```

4. Run the SQL migration:
   ```bash
   psql $DATABASE_URL -f backend/sql/schema.sql
   ```

### Step 2: Update Application Code (Future)

Add RLS session variable setting to your route handlers:

**Option A: Set in each route (recommended)**
```python
from flask import g
from .db import set_rls_user_id

@bp.route("/chart", methods=["POST"])
def chart():
    session_data = get_current_user()
    if isinstance(session_data, tuple):
        return session_data
    
    user = g.current_user
    set_rls_user_id(user.id)  # Set RLS user ID
    
    # Rest of your route code...
```

**Option B: Set in middleware (cleaner)**
```python
# In app/__init__.py or a middleware file
@app.before_request
def set_rls_context():
    if hasattr(g, 'current_user') and g.current_user:
        from .db import set_rls_user_id
        set_rls_user_id(g.current_user.id)
```

### Step 3: Test Thoroughly

1. **Test as user A**: Create profiles, verify you can access them
2. **Test as user B**: Try to access user A's profiles (should fail with RLS)
3. **Test all endpoints**: Ensure all profile/chart operations work correctly

## How It Works

### Session Variable Approach

Since this application uses **direct PostgreSQL connections** (not Supabase Auth), RLS uses a session variable:

1. **Application sets variable**: `SET LOCAL app.current_user_id = 'user-uuid'`
2. **RLS policies read variable**: `app.current_user_id()` function
3. **Policies filter queries**: Only return rows where `user_id` matches

### Example Flow

```python
# 1. User authenticates
user = g.current_user  # UUID: 550e8400-...

# 2. Set RLS context
set_rls_user_id(user.id)  # Sets session variable

# 3. Query profiles
profiles = Profile.query.filter_by(is_active=True).all()
# RLS automatically filters to only this user's profiles

# 4. Try to access another user's profile
other_profile = Profile.query.filter_by(id=other_user_profile_id).first()
# Returns None (RLS blocks it)
```

## RLS Policies Explained

### Authorization Tables (approved_users, users)

These tables have **restrictive policies** that deny all public access via PostgREST:

- **approved_users**: Denies all PostgREST access (admin-only table)
- **users**: Denies all PostgREST access (user account data)

**Why these policies?**
- These tables are exposed via Supabase's PostgREST API (auto-generated REST endpoints)
- The application uses direct PostgreSQL connections (not PostgREST), so these policies don't affect application functionality
- Service role connections bypass RLS, allowing admin operations via Supabase dashboard
- This addresses Supabase Security Advisor warnings about RLS being disabled

**Important Notes:**
- Direct database connections from the application continue to work unchanged
- Admin operations via Supabase dashboard continue to work (service role bypasses RLS)
- These policies only block unauthorized access via PostgREST endpoints

### User Data Tables (profiles, charts, analysis_notes)

These tables have **user-scoped policies** (currently commented out):

**Profiles Table Policies:**
- **SELECT**: Users can only read their own active profiles
- **INSERT**: Users can only create profiles with their own `user_id`
- **UPDATE**: Users can only update their own profiles
- **DELETE**: Users can only delete their own profiles

**Charts Table Policies:**
- **SELECT**: Users can only read charts for their own profiles
- **INSERT**: Users can only create charts for their own profiles
- **UPDATE**: Users can only update charts for their own profiles
- **DELETE**: Users can only delete charts for their own profiles

**Analysis Notes Table Policies:**
- Similar user-scoped policies based on chart ownership

## Troubleshooting

### Issue: Queries return no results

**Cause**: RLS is enforcing but session variable not set

**Solution**: Ensure `set_rls_user_id()` is called before queries

### Issue: "permission denied" errors

**Cause**: RLS policies are blocking access

**Solution**: 
1. Verify `user_id` in session variable matches profile owner
2. Check that `is_active = true` for profiles
3. Review policy conditions in `schema.sql`

### Issue: Policies not working

**Cause**: Policies might not be created or RLS not enabled

**Solution**:
```sql
-- Check if RLS is enabled on all tables
SELECT tablename, rowsecurity FROM pg_tables 
WHERE tablename IN ('approved_users', 'users', 'profiles', 'charts', 'analysis_notes');

-- Check if policies exist
SELECT * FROM pg_policies 
WHERE tablename IN ('approved_users', 'users', 'profiles', 'charts', 'analysis_notes');
```

### Issue: PostgREST access blocked for approved_users/users

**Cause**: This is expected behavior - these tables deny all PostgREST access for security

**Solution**: 
- If you need to access these tables, use direct database connections (as the application does)
- Admin operations via Supabase dashboard continue to work (service role bypasses RLS)
- This is a security feature, not a bug

## Migration Strategy

### Phase 1: Enable RLS on Authorization Tables (Completed)
- ✅ RLS enabled on `approved_users` and `users` tables
- ✅ Restrictive policies active (deny all PostgREST access)
- ✅ Application code works normally (direct DB connections unaffected)
- ✅ Addresses Supabase Security Advisor warnings
- ✅ Function `app.current_user_id()` has fixed `search_path` for security

### Phase 2: Enable RLS on User Data Tables (Current - Policies Commented)
- ✅ RLS enabled on `profiles`, `charts`, and `analysis_notes` tables
- ⚠️ Policies commented out (permissive mode - ready for future use)
- ✅ Application code works normally with application-level security checks
- 📝 **Decision**: Keeping policies commented for now. Application-level security provides sufficient protection.

### Phase 3: Enable User Data Policies (Future - Optional)
- Uncomment policies for `profiles`, `charts`, and `analysis_notes` in development environment
- Add `set_rls_user_id()` calls to routes
- Test all functionality thoroughly
- Fix any issues
- Deploy to production with monitoring

## Best Practices

1. **Always set RLS context**: Call `set_rls_user_id()` at the start of protected routes
2. **Keep application checks**: Don't remove Python-level ownership verification
3. **Test thoroughly**: RLS can break queries if not configured correctly
4. **Monitor logs**: Watch for RLS-related errors in production
5. **Document exceptions**: If you need to bypass RLS (admin operations), document why

## Security Notes

- **RLS is not a replacement** for application-level security
- **Use both layers**: Application checks + RLS = defense in depth
- **Session variables are transaction-scoped**: Reset for each request
- **Function is SECURITY DEFINER**: `app.current_user_id()` runs with elevated privileges (safe, reads session variable only)
- **Fixed search_path**: The function uses `SET search_path = pg_catalog` to prevent search_path hijacking attacks

## References

- [PostgreSQL RLS Documentation](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [Supabase RLS Guide](https://supabase.com/docs/guides/auth/row-level-security)
