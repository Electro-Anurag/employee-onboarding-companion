"""Database-owned append interface. Models can read history but cannot update it."""
import uuid
from django.db import connection

class UnsafeAuditContent(ValueError): pass

def append_event(*,stream_key,actor,event_type,entity_id=None,command_id=None,changes=None,reason=''):
    if not isinstance(changes,dict) or len(str(changes))>4096: raise UnsafeAuditContent('Sanitized change object required')
    if not stream_key or len(stream_key)>110 or len(event_type)>80: raise UnsafeAuditContent('Invalid audit key/type')
    if len(reason)>256: raise UnsafeAuditContent('Reason too long')
    command_id=command_id or uuid.uuid4()
    # jsonb parameter uses Django's JSON adaptation via psycopg Jsonb.
    from psycopg.types.json import Jsonb
    with connection.cursor() as cursor:
        cursor.execute('SELECT event_id,event_hash FROM public.audit_append_event(%s,%s,%s,%s,%s,%s,%s)',
            [stream_key,actor.pk if actor else None,event_type,entity_id,command_id,Jsonb(changes),reason])
        return cursor.fetchone()
