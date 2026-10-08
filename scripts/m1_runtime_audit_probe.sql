-- M1 test-only role: demonstrate SECURITY DEFINER audit insertion succeeds while
-- direct mutation permissions remain denied. Everything rolls back afterward.
BEGIN;
CREATE ROLE m1_application_probe NOLOGIN;
GRANT USAGE ON SCHEMA public TO m1_application_probe;
GRANT EXECUTE ON FUNCTION public.audit_append_event(text,uuid,text,uuid,uuid,jsonb,text) TO m1_application_probe;
SET ROLE m1_application_probe;
DO $$
BEGIN
  IF has_table_privilege('m1_application_probe','public.audit_auditevent','INSERT')
     OR has_table_privilege('m1_application_probe','public.audit_auditevent','UPDATE')
     OR has_table_privilege('m1_application_probe','public.audit_auditevent','DELETE')
     OR has_table_privilege('m1_application_probe','public.audit_auditevent','TRUNCATE') THEN
    RAISE EXCEPTION 'M1 least-privilege audit permissions violated';
  END IF;
END $$;
SELECT event_id,event_hash
FROM public.audit_append_event('org:m1-ci-restricted',NULL::uuid,'M1_ROLE_PROBE',
  NULL::uuid,gen_random_uuid(),'{}'::jsonb,''::text);
DO $$
BEGIN
  BEGIN
    DELETE FROM public.audit_auditevent;
    RAISE EXCEPTION 'Direct audit delete unexpectedly succeeded';
  EXCEPTION WHEN insufficient_privilege THEN NULL;
  END;
  BEGIN
    UPDATE public.audit_auditevent SET event_type='TAMPER';
    RAISE EXCEPTION 'Direct audit update unexpectedly succeeded';
  EXCEPTION WHEN insufficient_privilege THEN NULL;
  END;
  BEGIN
    EXECUTE 'TRUNCATE public.audit_auditevent';
    RAISE EXCEPTION 'Direct audit truncate unexpectedly succeeded';
  EXCEPTION WHEN insufficient_privilege THEN NULL;
  END;
END $$;
RESET ROLE;
ROLLBACK;
