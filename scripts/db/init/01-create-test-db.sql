-- Runs once, on first initialisation of the Postgres data volume.
-- Creates a dedicated database for pytest integration tests so tests never touch
-- development data (CODING_STANDARDS.md section 5: a real Postgres, never a mock).
-- The database is owned by the role running this script (POSTGRES_USER).
CREATE DATABASE finance_test;
