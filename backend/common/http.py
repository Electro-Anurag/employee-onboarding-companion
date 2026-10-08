"""Bounded JSON and predictable API failures; no stack traces in responses."""
import json
from django.http import JsonResponse

def error(code, status=400, message=None, **extra):
    return JsonResponse({'error':{'code':code,'message':message or code,**extra}},status=status)

class InputError(Exception):
    def __init__(self, code='INVALID_REQUEST',status=400):
        self.code,self.status=code,status

def json_payload(request, max_bytes=65536, allowed=None):
    if request.content_type != 'application/json': raise InputError('JSON_REQUIRED',415)
    if len(request.body)>max_bytes: raise InputError('REQUEST_TOO_LARGE',413)
    try: value=json.loads(request.body)
    except (UnicodeError,json.JSONDecodeError): raise InputError('INVALID_JSON')
    if not isinstance(value,dict): raise InputError('OBJECT_REQUIRED')
    if allowed is not None and set(value)-set(allowed): raise InputError('UNKNOWN_FIELD',422)
    return value
