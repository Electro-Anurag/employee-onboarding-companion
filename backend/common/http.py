"""Small shared request boundary with typed input and sanitized database failures."""
import json
import uuid
from django.http import JsonResponse

def error(code,status=400,message=None,**extra):
    return JsonResponse({'error':{'code':code,'message':message or code,**extra}},status=status)

class InputError(Exception):
    def __init__(self,code='INVALID_REQUEST',status=400):
        self.code,self.status=code,status

def json_payload(request,max_bytes=65536,allowed=None):
    if request.content_type != 'application/json':
        raise InputError('JSON_REQUIRED',415)
    if len(request.body)>max_bytes:
        raise InputError('REQUEST_TOO_LARGE',413)
    try:
        value=json.loads(request.body)
    except (UnicodeError,json.JSONDecodeError):
        raise InputError('INVALID_JSON')
    if not isinstance(value,dict):
        raise InputError('OBJECT_REQUIRED')
    if allowed is not None and set(value)-set(allowed):
        raise InputError('UNKNOWN_FIELD',422)
    return value

def required_uuid(value):
    if not isinstance(value,str):
        raise InputError('INVALID_UUID',422)
    try:
        return uuid.UUID(value)
    except (ValueError,AttributeError):
        raise InputError('INVALID_UUID',422)

def transient_db_response(exc):
    """Call outside transaction.atomic after rollback, never replay uncertain writes."""
    state=getattr(exc,'sqlstate',None) or getattr(getattr(exc,'__cause__',None),'sqlstate',None)
    if state in ('55P03','40P01','40001','57014'):
        return error('TRANSIENT_DATABASE_CONFLICT',409,retryable=True)
    return error('DATABASE_UNAVAILABLE',503,retryable=True)
