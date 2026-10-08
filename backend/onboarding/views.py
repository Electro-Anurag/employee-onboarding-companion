import uuid
from django.http import JsonResponse
from django.views.decorators.http import require_GET,require_POST
from backend.common.http import error,InputError,json_payload
from backend.onboarding.services import CommandFailure,scoped_cases,get_authorized_case,case_summary,reassign_owner
from django.core.exceptions import PermissionDenied
from backend.onboarding.models import OnboardingCase

def _denied(e):
    if isinstance(e,CommandFailure):return error(e.code,e.status)
    return error('UNAUTHENTICATED',401)

@require_GET
def cases(request):
    try:
        qs=scoped_cases(request.user).select_related('employee__user').order_by('id')[:100]
        from backend.accounts.security import actor_context
        member=actor_context(request.user)
        return JsonResponse({'results':[case_summary(member,c) for c in qs]})
    except PermissionDenied as e:return _denied(e)

@require_GET
def case_detail(request,case_id):
    try:
        member,c=get_authorized_case(request.user,case_id)
        return JsonResponse(case_summary(member,c))
    except (PermissionDenied,CommandFailure) as e:return _denied(e)

@require_POST
def assignment(request,case_id):
    try:
        from backend.accounts.security import actor_context
        actor_context(request.user)
        data=json_payload(request,2048,{'role','new_member_id','reason'})
        idem=uuid.UUID(request.headers.get('Idempotency-Key',''))
        match=request.headers.get('If-Match','')
        prefix=f'"case:{case_id}:v'
        if not match.startswith(prefix) or not match.endswith('"'):return error('PRECONDITION_REQUIRED',428)
        expected=int(match[len(prefix):-1])
        response,status=reassign_owner(actor=request.user,case_id=case_id,role=data['role'],
               new_member_id=uuid.UUID(data['new_member_id']),reason=data['reason'],key=idem,expected_version=expected)
        return JsonResponse(response,status=status)
    except (KeyError,ValueError,TypeError,InputError):return error('INVALID_REQUEST',422)
    except (PermissionDenied,CommandFailure) as e:return _denied(e)
    except OnboardingCase.DoesNotExist:
        return error('NOT_FOUND',404)
