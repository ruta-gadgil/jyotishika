-- Migration 002: Index for paged profile listing
--
-- Run this against your existing Supabase database (SQL Editor or psql):
--   psql $DATABASE_URL -f backend/sql/migrations/002_profiles_user_updated_index.sql
--
-- Backs GET /profiles: active profiles for one user, newest update first,
-- with id as the tie-break so page boundaries are stable.
--
-- This migration is idempotent (safe to run multiple times).

CREATE INDEX IF NOT EXISTS idx_profiles_user_active_updated
    ON profiles (user_id, updated_at DESC, id DESC)
    WHERE is_active;
