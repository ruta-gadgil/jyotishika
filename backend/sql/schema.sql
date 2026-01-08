-- Email Allowlist Authorization Schema
-- 
-- This schema implements a two-table authorization system:
-- 1. approved_users: Manually maintained allowlist of approved emails
-- 2. users: Actual user records created after successful OAuth + approval
--
-- SECURITY DECISIONS:
-- - Email as primary key in approved_users (ensures uniqueness, fast lookup)
-- - UUID primary key for users (prevents enumeration attacks)
-- - google_sub indexed and unique (prevents duplicate Google account reuse)
-- - Both tables have is_active flags (dual-layer deactivation control)
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

-- Example data for development/testing
-- Uncomment and modify these INSERT statements to add your test users
-- INSERT INTO approved_users (email, note) VALUES 
--     ('admin@example.com', 'Admin account'),
--     ('user@example.com', 'Test user');