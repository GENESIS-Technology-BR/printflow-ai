-- TALVOA / SupriTech: read-only partner and account discovery.
-- Run in Render's private PostgreSQL connection, NOT against production.
-- This script never prints passwords, hashes, tokens or session secrets.
BEGIN READ ONLY;
SELECT current_database() AS database_name, current_schema() AS schema_name;
SELECT table_schema, table_name
FROM information_schema.tables
WHERE table_schema NOT IN ('pg_catalog','information_schema')
  AND (table_name ILIKE '%partner%' OR table_name ILIKE '%user%' OR table_name ILIKE '%compan%')
ORDER BY table_schema, table_name;
SELECT table_schema, table_name, column_name
FROM information_schema.columns
WHERE table_schema NOT IN ('pg_catalog','information_schema')
  AND (table_name ILIKE '%partner%' OR table_name ILIKE '%user%' OR table_name ILIKE '%compan%')
  AND (column_name ILIKE '%name%' OR column_name ILIKE '%email%' OR column_name ILIKE '%role%' OR column_name ILIKE '%active%' OR column_name IN ('id','partner_id','user_id','company_id'))
ORDER BY table_schema, table_name, ordinal_position;
COMMIT;
-- After inspecting the actual table/column names above, query only
-- safe columns for records matching 'supri' and verify partner membership.
-- Never use SELECT * on authentication tables.
