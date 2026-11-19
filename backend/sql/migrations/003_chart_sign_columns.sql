-- Migration 003: Sign columns on charts (for Saved Profiles filters)
--
-- Run this against your existing Supabase database (SQL Editor or psql):
--   psql $DATABASE_URL -f backend/sql/migrations/003_chart_sign_columns.sql
--
-- IMPORTANT: run this BEFORE deploying the backend that selects these columns.
--
-- Adds the ascendant, Moon and Sun sign (0 = Aries ... 11 = Pisces) as plain
-- columns so profile filters do not scan chart JSON. The application keeps them
-- in sync: every chart write goes through db.save_chart.
--
-- This migration is idempotent (safe to run multiple times).

ALTER TABLE charts
    ADD COLUMN IF NOT EXISTS asc_sign  SMALLINT CHECK (asc_sign  BETWEEN 0 AND 11),
    ADD COLUMN IF NOT EXISTS moon_sign SMALLINT CHECK (moon_sign BETWEEN 0 AND 11),
    ADD COLUMN IF NOT EXISTS sun_sign  SMALLINT CHECK (sun_sign  BETWEEN 0 AND 11);

-- Backfill existing charts from the stored JSON. Only touches rows where all three
-- are still NULL, so re-running never overwrites values the application wrote.
UPDATE charts
SET
    asc_sign = (ascendant_data::jsonb ->> 'signIndex')::smallint,
    moon_sign = (
        SELECT (planet ->> 'signIndex')::smallint
        FROM jsonb_array_elements(planets_data::jsonb) AS planet
        WHERE planet ->> 'planet' = 'Moon'
        LIMIT 1
    ),
    sun_sign = (
        SELECT (planet ->> 'signIndex')::smallint
        FROM jsonb_array_elements(planets_data::jsonb) AS planet
        WHERE planet ->> 'planet' = 'Sun'
        LIMIT 1
    )
WHERE asc_sign IS NULL
  AND moon_sign IS NULL
  AND sun_sign IS NULL;

COMMENT ON COLUMN charts.asc_sign IS 'Ascendant sign, 0 (Aries) to 11 (Pisces). Derived from ascendant_data.';
COMMENT ON COLUMN charts.moon_sign IS 'Moon sign, 0 (Aries) to 11 (Pisces). Derived from planets_data.';
COMMENT ON COLUMN charts.sun_sign IS 'Sun sign, 0 (Aries) to 11 (Pisces). Derived from planets_data.';
