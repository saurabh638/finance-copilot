-- Every base table in the public schema, with its exact row count.
--
-- Exact rather than estimated: pg_stat_user_tables lags right after a restore,
-- which is the moment this matters most. Used by the backup scripts and by the
-- restore check, so both always measure the same thing.
SELECT table_name,
       (xpath('/row/c/text()',
              query_to_xml(format('SELECT count(*) AS c FROM %I.%I', table_schema, table_name),
                           false, true, '')))[1]::text::bigint AS rows
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_type = 'BASE TABLE'
ORDER BY table_name;
