-- M0 feasibility probe only. This is NOT a production grant migration.
-- Run against an isolated PostgreSQL qualification database as its owner.
BEGIN;
CREATE ROLE m0_runtime_limited NOLOGIN;
GRANT USAGE ON SCHEMA public TO m0_runtime_limited;
GRANT SELECT, INSERT ON TABLE foundation_foundationaudit TO m0_runtime_limited;
GRANT USAGE ON SEQUENCE foundation_foundationaudit_id_seq TO m0_runtime_limited;
DO $$
BEGIN
  IF NOT has_table_privilege('m0_runtime_limited','foundation_foundationaudit','SELECT')
     OR NOT has_table_privilege('m0_runtime_limited','foundation_foundationaudit','INSERT')
     OR has_table_privilege('m0_runtime_limited','foundation_foundationaudit','UPDATE')
     OR has_table_privilege('m0_runtime_limited','foundation_foundationaudit','DELETE')
     OR has_table_privilege('m0_runtime_limited','foundation_foundationaudit','TRUNCATE') THEN
    RAISE EXCEPTION 'M0 audit least-privilege requirements are not satisfied';
  END IF;
END $$;
SET ROLE m0_runtime_limited;
SELECT count(*) AS audit_rows_readable FROM foundation_foundationaudit;
RESET ROLE;
ROLLBACK;
