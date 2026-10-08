from django.db import migrations

AUDIT_SQL = r"""
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE OR REPLACE FUNCTION public.audit_deny_changes()
RETURNS trigger LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
BEGIN
  RAISE EXCEPTION 'Audit events are append only';
END; $$;
CREATE TRIGGER audit_no_modify BEFORE UPDATE OR DELETE ON public.audit_auditevent
FOR EACH ROW EXECUTE FUNCTION public.audit_deny_changes();

CREATE OR REPLACE FUNCTION public.audit_append_event(
 p_stream text,p_actor uuid,p_type text,p_entity uuid,p_command uuid,p_change jsonb,p_reason text)
RETURNS TABLE(event_id uuid,event_hash text)
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE v_seq bigint; v_prior text; v_hash text; v_id uuid := gen_random_uuid();
BEGIN
 IF length(p_stream)>110 OR length(p_stream)<3 OR length(p_type)>80 OR length(p_type)<3
    OR p_change IS NULL OR jsonb_typeof(p_change)<>'object'
    OR octet_length(p_change::text)>4096 OR length(p_reason)>256 THEN
   RAISE EXCEPTION 'Invalid audit payload';
 END IF;
 INSERT INTO public.audit_auditstream (key,next_sequence,last_hash)
 VALUES (p_stream,1,repeat('0',64)) ON CONFLICT (key) DO NOTHING;
 SELECT s.next_sequence,s.last_hash INTO v_seq,v_prior
 FROM public.audit_auditstream AS s WHERE s.key=p_stream FOR UPDATE;
 v_hash := encode(public.digest(convert_to(
   v_prior||'|'||p_stream||'|'||v_seq::text||'|'||coalesce(p_actor::text,'system')||'|'||
   p_type||'|'||coalesce(p_entity::text,'none')||'|'||p_command::text||'|'||p_change::text||'|'||p_reason,
   'UTF8'),'sha256'),'hex');
 INSERT INTO public.audit_auditevent
 (id,stream_id,sequence,actor_id,event_type,entity_id,command_id,sanitized_change,reason,created_at,previous_hash,event_hash)
 VALUES (v_id,p_stream,v_seq,p_actor,p_type,p_entity,p_command,p_change,p_reason,now(),v_prior,v_hash);
 UPDATE public.audit_auditstream SET next_sequence=v_seq+1,last_hash=v_hash WHERE key=p_stream;
 RETURN QUERY SELECT v_id,v_hash;
END; $$;
REVOKE ALL ON FUNCTION public.audit_append_event(text,uuid,text,uuid,uuid,jsonb,text) FROM PUBLIC;
"""
REVERSE_SQL = r"""
DROP FUNCTION IF EXISTS public.audit_append_event(text,uuid,text,uuid,uuid,jsonb,text);
DROP TRIGGER IF EXISTS audit_no_modify ON public.audit_auditevent;
DROP TRIGGER IF EXISTS audit_no_truncate ON public.audit_auditevent;
DROP FUNCTION IF EXISTS public.audit_deny_changes();
"""
class Migration(migrations.Migration):
    dependencies=[('audit','0001_initial')]
    operations=[migrations.RunSQL(AUDIT_SQL,REVERSE_SQL)]
