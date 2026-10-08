"""M1 owner access views (authorization is enforced server-side)."""
import uuid
from django.core.exceptions import PermissionDenied
from django.db import DatabaseError
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from backend.common.http import error,InputError,json_payload,required_uuid,transient_db_response
from backend.onboarding.services import CommandFailure,scoped_cases,get_authorized_case,case_summary,reassign_owner
from backend.onboarding.models import OnboardingCase

def _denied(exc):
    if isinstance(exc,CommandFailure):
        return error(exc.code,exc.status)
    return error('UNAUTHENTICATED',401)

@require_GET
def cases(request):
    try:
        from backend.accounts.security import actor_context
        member=actor_context(request.user)
        qs=scoped_cases(request.user).select_related('employee__user').order_by('id')[:100]
        return JsonResponse({'results':[case_summary(member,c) for c in qs]})
    except PermissionDenied as exc:
        return _denied(exc)
    except DatabaseError as exc:
        return transient_db_response(exc)

@require_GET
def case_detail(request,case_id):
    try:
        member,c=get_authorized_case(request.user,case_id)
        return JsonResponse(case_summary(member,c))
    except (PermissionDenied,CommandFailure) as exc:
        return _denied(exc)
    except DatabaseError as exc:
        return transient_db_response(exc,preflight=True)

@require_POST
def assignment(request,case_id):
    try:
        from backend.accounts.security import actor_context
        actor_context(request.user)
        data=json_payload(request,2048,{'role','new_member_id','reason'})
        idem=required_uuid(request.headers.get('Idempotency-Key',''))
        match=request.headers.get('If-Match','')
        prefix=f'"case:{case_id}:v'
        if not match.startswith(prefix) or not match.endswith('"'):
            return error('PRECONDITION_REQUIRED',428)
        try:
            expected=int(match[len(prefix):-1])
        except (ValueError,TypeError):
            raise InputError('INVALID_ETAG',422)
        response,status=reassign_owner(actor=request.user,case_id=case_id,role=data.get('role'),
                    new_member_id=required_uuid(data.get('new_member_id')),
                    reason=data.get('reason'),key=idem,expected_version=expected)
        return JsonResponse(response,status=status)
    except InputError as exc:
        return error(exc.code,exc.status)
    except (PermissionDenied,CommandFailure) as exc:
        return _denied(exc)
    except OnboardingCase.DoesNotExist:
        return error('NOT_FOUND',404)
    except DatabaseError as exc:
        return transient_db_response(exc,idempotent=True)
