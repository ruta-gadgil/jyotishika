-- Jyotishika Database Schema
-- 
-- This schema implements:
-- 1. approved_users: Manually maintained allowlist of approved emails
-- 2. users: Actual user records created after successful OAuth + approval
-- 3. profiles: Birth details and chart calculation settings (user-owned)
-- 4. charts: Cached astrological chart calculation results (linked to profiles)
--
-- SECURITY DECISIONS:
-- - Email as primary key in approved_users (ensures uniqueness, fast lookup)
-- - UUID primary keys (prevents enumeration attacks)
-- - google_sub indexed and unique (prevents duplicate Google account reuse)
-- - Foreign keys with CASCADE delete (data cleanup)
-- - Unique constraints prevent duplicate profiles
-- - Timestamps use UTC for consistency across timezones
--
-- DEPLOYMENT:
-- Run this SQL in Supabase SQL Editor or via psql:
--   psql $DATABASE_URL -f backend/sql/schema.sql

-- Enable UUID extension (if not already enabled)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table 1: approved_users
-- Manually maintained allowlist of approved emails
-- Admin adds entries via Supabase dashboard or direct SQL
CREATE TABLE IF NOT EXISTS approved_users (
    -- Email is the primary key (ensures uniqueness, fast lookup during OAuth)
    email TEXT PRIMARY KEY,
    
    -- Active flag allows temporary deactivation without deletion
    -- Default true = new approvals are immediately active
    is_active BOOLEAN NOT NULL DEFAULT true,
    
    -- Timestamp when email was added to allowlist
    added_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Optional note for admin reference (e.g., "Beta tester", "Team member")
    -- Nullable to keep manual inserts simple
    note TEXT
);

-- Index for filtering active approved users (used in authorization checks)
CREATE INDEX IF NOT EXISTS idx_approved_users_active ON approved_users(is_active) WHERE is_active = true;

-- Table 2: users
-- Actual user records created automatically during OAuth callback
-- Only created if email exists in approved_users with is_active=true
CREATE TABLE IF NOT EXISTS users (
    -- UUID primary key prevents enumeration attacks
    -- Generated automatically using uuid_generate_v4()
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Google's unique user identifier (from "sub" claim in ID token)
    -- This is the reliable identifier even if user changes their Google email
    google_sub TEXT NOT NULL UNIQUE,
    
    -- User's email from Google OAuth
    -- Stored for convenience but google_sub is the authoritative identifier
    email TEXT NOT NULL UNIQUE,
    
    -- User's display name from Google profile
    name TEXT,
    
    -- Timestamp when user record was created (first successful login)
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Timestamp of most recent successful login
    -- Updated on every OAuth callback success
    last_login_at TIMESTAMP,
    
    -- Active flag allows account deactivation independent of approved_users
    -- Both users.is_active AND approved_users.is_active must be true for access
    is_active BOOLEAN NOT NULL DEFAULT true
);

-- Index for fast lookup by google_sub (used in every protected request)
CREATE INDEX IF NOT EXISTS idx_users_google_sub ON users(google_sub);

-- Index for fast lookup by email (used for authorization checks)
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Index for filtering active users
CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active) WHERE is_active = true;

-- Index for last_login_at (useful for analytics and cleanup queries)
CREATE INDEX IF NOT EXISTS idx_users_last_login ON users(last_login_at);

-- Comments for documentation
COMMENT ON TABLE approved_users IS 'Email allowlist for authorization. Manually maintained via Supabase dashboard or SQL.';
COMMENT ON TABLE users IS 'User records created automatically during OAuth. Only created if email is approved.';

COMMENT ON COLUMN approved_users.email IS 'Email address to approve. Must match Google OAuth email exactly.';
COMMENT ON COLUMN approved_users.is_active IS 'If false, user cannot log in even if they have an existing account.';
COMMENT ON COLUMN approved_users.note IS 'Optional admin note (e.g., Beta tester, Team member).';

COMMENT ON COLUMN users.google_sub IS 'Google user ID from OAuth sub claim. Primary identifier (email can change).';
COMMENT ON COLUMN users.email IS 'User email from Google. Stored for convenience but google_sub is authoritative.';
COMMENT ON COLUMN users.last_login_at IS 'Updated on every successful login via OAuth callback.';
COMMENT ON COLUMN users.is_active IS 'Account active flag. Both this AND approved_users.is_active must be true.';

-- Enable RLS on approved_users table
ALTER TABLE approved_users ENABLE ROW LEVEL SECURITY;

-- Enable RLS on users table
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- RLS Policies for approved_users
-- Deny all public access via PostgREST (admin-only table, accessed only via direct DB connections)
-- Service role connections bypass RLS, allowing admin operations via Supabase dashboard
DROP POLICY IF EXISTS approved_users_deny_all ON approved_users;
CREATE POLICY approved_users_deny_all ON approved_users
    FOR ALL
    USING (false)
    WITH CHECK (false);

-- RLS Policies for users
-- Deny all public access via PostgREST
-- Application uses direct DB connections which bypass RLS when using service role
DROP POLICY IF EXISTS users_deny_all ON users;
CREATE POLICY users_deny_all ON users
    FOR ALL
    USING (false)
    WITH CHECK (false);

-- Table 3: profiles
-- Birth details and chart calculation settings
-- Each profile belongs to a user and has one associated chart (1:1)
CREATE TABLE IF NOT EXISTS profiles (
    -- UUID primary key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Foreign key to users table
    -- ON DELETE CASCADE: profiles deleted when user deleted
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Optional profile name (e.g., "My Chart", "John's Chart")
    name TEXT,
    
    -- Birth details (PII - sensitive data)
    datetime TEXT NOT NULL,  -- ISO-8601 format (e.g., "1991-03-25T09:46:00")
    tz TEXT,  -- Timezone name (e.g., "Asia/Kolkata")
    utc_offset_minutes INTEGER,  -- UTC offset in minutes
    latitude REAL NOT NULL,  -- -90 to 90
    longitude REAL NOT NULL,  -- -180 to 180
    
    -- Chart calculation settings
    house_system TEXT NOT NULL DEFAULT 'WHOLE_SIGN',  -- WHOLE_SIGN, EQUAL, PLACIDUS
    ayanamsha TEXT NOT NULL DEFAULT 'LAHIRI',  -- LAHIRI, RAMAN, KRISHNAMURTI, VEDANJANAM
    node_type TEXT NOT NULL DEFAULT 'MEAN',  -- MEAN or TRUE
    
    -- Metadata
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT true,
    
    -- Unique constraint: prevent duplicate profiles for same user + birth details + settings
    CONSTRAINT uq_user_profile UNIQUE (user_id, datetime, latitude, longitude, house_system, ayanamsha, node_type)
);

-- Indexes for profiles
CREATE INDEX IF NOT EXISTS idx_profiles_user_id ON profiles(user_id) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_profiles_user_active ON profiles(user_id, is_active);

-- Table 4: charts
-- Cached astrological chart calculation results
-- Each chart belongs to exactly one profile (1:1 relationship)
CREATE TABLE IF NOT EXISTS charts (
    -- UUID primary key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Foreign key to profiles table (1:1 relationship)
    -- UNIQUE constraint enforces one chart per profile
    -- ON DELETE CASCADE: charts deleted when profile deleted
    profile_id UUID NOT NULL UNIQUE REFERENCES profiles(id) ON DELETE CASCADE,
    
    -- Calculated chart data (JSONB for flexibility)
    ascendant_data JSONB NOT NULL,  -- Ascendant position, nakshatra, charan, navamsha
    planets_data JSONB NOT NULL,  -- Array of planet objects with positions
    house_cusps JSONB,  -- House cusp positions (optional)
    bhav_chalit_data JSONB NOT NULL,  -- Bhav Chalit (Sripati) house system data
    chart_metadata JSONB NOT NULL,  -- Calculation metadata (system, ayanamsha, etc.)
    
    -- Metadata
    calculated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Index for charts
CREATE INDEX IF NOT EXISTS idx_charts_profile_id ON charts(profile_id);

-- Table 5: analysis_notes
-- User-created analysis notes for charts
-- Each note belongs to exactly one chart (many-to-one relationship)
CREATE TABLE IF NOT EXISTS analysis_notes (
    -- UUID primary key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Foreign key to charts table (many notes can belong to one chart)
    -- ON DELETE CASCADE: notes deleted when chart deleted
    chart_id UUID NOT NULL REFERENCES charts(id) ON DELETE CASCADE,
    
    -- Note title (max 200 characters)
    title TEXT NOT NULL CHECK (char_length(title) <= 200),
    
    -- Note content (max 5000 characters)
    note TEXT NOT NULL CHECK (char_length(note) <= 5000),
    
    -- Metadata
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Index for analysis_notes (fast retrieval of all notes for a chart)
CREATE INDEX IF NOT EXISTS idx_analysis_notes_chart_id ON analysis_notes(chart_id);

-- Comments for documentation
COMMENT ON TABLE profiles IS 'Birth profiles for astrological chart calculations. Each profile belongs to a user.';
COMMENT ON TABLE charts IS 'Cached chart calculation results. Each chart belongs to one profile (1:1).';
COMMENT ON TABLE analysis_notes IS 'User-created analysis notes for charts. Multiple notes can belong to one chart.';

COMMENT ON COLUMN profiles.user_id IS 'Foreign key to users table. Profiles deleted when user deleted (CASCADE).';
COMMENT ON COLUMN profiles.datetime IS 'Birth datetime in ISO-8601 format (e.g., 1991-03-25T09:46:00).';
COMMENT ON COLUMN profiles.latitude IS 'Birth location latitude (-90 to 90).';
COMMENT ON COLUMN profiles.longitude IS 'Birth location longitude (-180 to 180).';
COMMENT ON COLUMN profiles.house_system IS 'House system for chart calculation (WHOLE_SIGN, EQUAL, PLACIDUS).';
COMMENT ON COLUMN profiles.ayanamsha IS 'Ayanamsha for sidereal calculations (LAHIRI, RAMAN, KRISHNAMURTI, VEDANJANAM).';
COMMENT ON COLUMN profiles.node_type IS 'Node type for Rahu/Ketu (MEAN or TRUE).';

COMMENT ON COLUMN charts.profile_id IS 'Foreign key to profiles table. One chart per profile (UNIQUE constraint).';
COMMENT ON COLUMN charts.ascendant_data IS 'Cached ascendant calculation results (JSONB).';
COMMENT ON COLUMN charts.planets_data IS 'Cached planet positions and details (JSONB array).';
COMMENT ON COLUMN charts.bhav_chalit_data IS 'Cached Bhav Chalit house system data (JSONB).';
COMMENT ON COLUMN charts.chart_metadata IS 'Calculation metadata including system, ayanamsha, timestamps (JSONB).';

COMMENT ON COLUMN analysis_notes.chart_id IS 'Foreign key to charts table. Notes deleted when chart deleted (CASCADE).';
COMMENT ON COLUMN analysis_notes.title IS 'Note title (max 200 characters).';
COMMENT ON COLUMN analysis_notes.note IS 'Note content (max 5000 characters).';

-- ============================================================================
-- Row Level Security (RLS) Policies
-- ============================================================================
-- 
-- RLS provides database-level security enforcement for sensitive data.
-- Even if application code is bypassed (SQL injection, direct DB access),
-- users can only access their own profiles and charts.
--
-- IMPORTANT: This application uses direct PostgreSQL connections (not Supabase Auth).
-- RLS policies use a session variable approach: app.current_user_id
--
-- To use RLS, set the session variable before queries:
--   SET LOCAL app.current_user_id = 'user-uuid-here';
--   (This should be done in your application's database connection setup)
--
-- For now, RLS is enabled but policies are permissive (allow all).
-- Uncomment and configure the policies below when ready to enforce RLS.
-- ============================================================================

-- Enable RLS on profiles table
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

-- Enable RLS on charts table  
ALTER TABLE charts ENABLE ROW LEVEL SECURITY;

-- Enable RLS on analysis_notes table
ALTER TABLE analysis_notes ENABLE ROW LEVEL SECURITY;

-- Create schema for application functions (if it doesn't exist)
CREATE SCHEMA IF NOT EXISTS app;

-- Create a function to get current user ID from session variable
-- This function reads the app.current_user_id session variable
-- SECURITY: Fixed search_path prevents search_path hijacking attacks
CREATE OR REPLACE FUNCTION app.current_user_id()
RETURNS UUID AS $$
BEGIN
    -- Get user ID from session variable (set by application)
    -- Returns NULL if not set (which will deny access in policies)
    RETURN current_setting('app.current_user_id', true)::UUID;
EXCEPTION
    WHEN OTHERS THEN
        -- If variable not set or invalid, return NULL (deny access)
        RETURN NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog;

-- RLS Policy: Users can SELECT their own profiles
-- Uncomment when ready to enforce RLS:
-- CREATE POLICY profiles_select_own ON profiles
--     FOR SELECT
--     USING (user_id = app.current_user_id() AND is_active = true);

-- RLS Policy: Users can INSERT their own profiles
-- Uncomment when ready to enforce RLS:
-- CREATE POLICY profiles_insert_own ON profiles
--     FOR INSERT
--     WITH CHECK (user_id = app.current_user_id());

-- RLS Policy: Users can UPDATE their own profiles
-- Uncomment when ready to enforce RLS:
-- CREATE POLICY profiles_update_own ON profiles
--     FOR UPDATE
--     USING (user_id = app.current_user_id())
--     WITH CHECK (user_id = app.current_user_id());

-- RLS Policy: Users can DELETE their own profiles (soft delete via is_active)
-- Uncomment when ready to enforce RLS:
-- CREATE POLICY profiles_delete_own ON profiles
--     FOR DELETE
--     USING (user_id = app.current_user_id());

-- RLS Policy: Users can SELECT charts for their own profiles
-- Uncomment when ready to enforce RLS:
-- CREATE POLICY charts_select_own ON charts
--     FOR SELECT
--     USING (
--         profile_id IN (
--             SELECT id FROM profiles 
--             WHERE user_id = app.current_user_id() AND is_active = true
--         )
--     );

-- RLS Policy: Users can INSERT charts for their own profiles
-- Uncomment when ready to enforce RLS:
-- CREATE POLICY charts_insert_own ON charts
--     FOR INSERT
--     WITH CHECK (
--         profile_id IN (
--             SELECT id FROM profiles 
--             WHERE user_id = app.current_user_id() AND is_active = true
--         )
--     );

-- RLS Policy: Users can UPDATE charts for their own profiles
-- Uncomment when ready to enforce RLS:
-- CREATE POLICY charts_update_own ON charts
--     FOR UPDATE
--     USING (
--         profile_id IN (
--             SELECT id FROM profiles 
--             WHERE user_id = app.current_user_id() AND is_active = true
--         )
--     )
--     WITH CHECK (
--         profile_id IN (
--             SELECT id FROM profiles 
--             WHERE user_id = app.current_user_id() AND is_active = true
--         )
--     );

-- RLS Policy: Users can DELETE charts for their own profiles
-- Uncomment when ready to enforce RLS:
-- CREATE POLICY charts_delete_own ON charts
--     FOR DELETE
--     USING (
--         profile_id IN (
--             SELECT id FROM profiles 
--             WHERE user_id = app.current_user_id() AND is_active = true
--         )
--     );

-- RLS Policy: Users can SELECT analysis_notes for their own charts
-- Uncomment when ready to enforce RLS:
-- CREATE POLICY analysis_notes_select_own ON analysis_notes
--     FOR SELECT
--     USING (
--         chart_id IN (
--             SELECT c.id FROM charts c
--             INNER JOIN profiles p ON c.profile_id = p.id
--             WHERE p.user_id = app.current_user_id() AND p.is_active = true
--         )
--     );

-- RLS Policy: Users can INSERT analysis_notes for their own charts
-- Uncomment when ready to enforce RLS:
-- CREATE POLICY analysis_notes_insert_own ON analysis_notes
--     FOR INSERT
--     WITH CHECK (
--         chart_id IN (
--             SELECT c.id FROM charts c
--             INNER JOIN profiles p ON c.profile_id = p.id
--             WHERE p.user_id = app.current_user_id() AND p.is_active = true
--         )
--     );

-- RLS Policy: Users can UPDATE analysis_notes for their own charts
-- Uncomment when ready to enforce RLS:
-- CREATE POLICY analysis_notes_update_own ON analysis_notes
--     FOR UPDATE
--     USING (
--         chart_id IN (
--             SELECT c.id FROM charts c
--             INNER JOIN profiles p ON c.profile_id = p.id
--             WHERE p.user_id = app.current_user_id() AND p.is_active = true
--         )
--     )
--     WITH CHECK (
--         chart_id IN (
--             SELECT c.id FROM charts c
--             INNER JOIN profiles p ON c.profile_id = p.id
--             WHERE p.user_id = app.current_user_id() AND p.is_active = true
--         )
--     );

-- RLS Policy: Users can DELETE analysis_notes for their own charts
-- Uncomment when ready to enforce RLS:
-- CREATE POLICY analysis_notes_delete_own ON analysis_notes
--     FOR DELETE
--     USING (
--         chart_id IN (
--             SELECT c.id FROM charts c
--             INNER JOIN profiles p ON c.profile_id = p.id
--             WHERE p.user_id = app.current_user_id() AND p.is_active = true
--         )
--     );

-- NOTE: For now, RLS is enabled but policies are commented out.
-- This means RLS is active but permissive (allows all operations).
-- 
-- To activate RLS enforcement:
-- 1. Uncomment the policies above
-- 2. Modify your application's database connection to set the session variable:
--    SET LOCAL app.current_user_id = 'user-uuid-here';
-- 3. Test thoroughly to ensure all queries work correctly
--
-- Example application code (in db.py init_db or before queries):
--   db.session.execute(db.text("SET LOCAL app.current_user_id = :user_id"), 
--                      {"user_id": str(current_user.id)})
--
-- SECURITY BENEFITS:
-- - Defense in depth: Even if application code is bypassed, DB enforces access
-- - Protection against SQL injection (if attacker can't set session variable)
-- - Protection against direct database access (requires valid user_id)
-- - Automatic enforcement at database level

-- Example data for development/testing
-- Uncomment and modify these INSERT statements to add your test users
-- INSERT INTO approved_users (email, note) VALUES 
--     ('admin@example.com', 'Admin account'),
--     ('user@example.com', 'Test user');