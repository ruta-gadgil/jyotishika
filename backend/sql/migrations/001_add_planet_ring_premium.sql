-- Migration 001: Add planet_ring_premium flag to users table
--
-- Run this against your existing Supabase database (SQL Editor or psql):
--   psql $DATABASE_URL -f backend/sql/migrations/001_add_planet_ring_premium.sql
--
-- This migration is idempotent (safe to run multiple times).

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS planet_ring_premium BOOLEAN NOT NULL DEFAULT false;

COMMENT ON COLUMN users.planet_ring_premium IS
    'Premium feature flag for planet ring visualization. '
    'Grant via: UPDATE users SET planet_ring_premium = true WHERE email = ''user@example.com'';';

-- Grant premium to specific users (uncomment and edit as needed):
-- UPDATE users SET planet_ring_premium = true WHERE email = 'you@example.com';
