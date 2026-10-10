"""M5 HR-only joining date preview and explicit typed confirmation."""
from datetime import date
from django.core.exceptions import PermissionDenied
from django.db import DatabaseError
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET,require_POST
from backend.common.http import error,InputError,json_payload,transient_db_response
from backend.onboarding.api_m2 import command,headers
from backend.onboarding.services import CommandFailure
from backend.onboarding.date_changes import preview_change,commit_change


def _date(raw):
    if type(raw) is not str or len(raw)!=10:
        raise InputError('INVALID_JOINING_DATE',422)
    try: return date.fromisoformat(raw)
    except ValueError:raise InputError('INVALID_JOINING_DATE',422)


def _preview_version(request,case_id):
    value=request.headers.get('If-Match','')
    prefix=f'"case:{case_id}:v'
    if not value.startswith(prefix) or not value.endswith('"'):
        raise InputError('PRECONDITION_REQUIRED',428)
    try: version=int(value[len(prefix):-1])
    except ValueError:raise InputError('INVALID_ETAG',422)
    if version<1:raise InputError('INVALID_ETAG',422)
    return version


@require_GET
def preview(request,case_id):
    try:
        if set(request.GET)!= {'joining_date'}:
            raise InputError('INVALID_DATE_PREVIEW_QUERY',422)
        outcome=preview_change(actor=request.user,case_id=case_id,
            new_date=_date(request.GET['joining_date']),
            expected_version=_preview_version(request,case_id))
        response=JsonResponse(outcome)
        response['Cache-Control']='private, no-store'
        return response
    except (CommandFailure,InputError) as exc:
        return error(exc.code,exc.status)
    except PermissionDenied:return error('NOT_FOUND',404)
    except DatabaseError as exc:return transient_db_response(exc,preflight=True)


@csrf_protect
@require_POST
def commit(request,case_id):
    def run():
        payload=json_payload(request,1500,{'joining_date','preview_digest','reason'})
        if set(payload)!= {'joining_date','preview_digest','reason'}:
            raise InputError('MISSING_FIELD',422)
        key,version=headers(request,case_id)
        return commit_change(actor=request.user,case_id=case_id,
            new_date=_date(payload['joining_date']),
            preview_digest=payload['preview_digest'],reason=payload['reason'],
            key=key,expected_version=version)
    return command(run)
