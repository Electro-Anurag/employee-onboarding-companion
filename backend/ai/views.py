"""Role-authorized current-state guidance; no provider or write authority."""
from django.core.exceptions import PermissionDenied
from django.db import DatabaseError
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_protect
from backend.common.http import error,transient_db_response,json_payload,InputError
from backend.onboarding.services import CommandFailure
from backend.ai.guidance import current_guidance
from backend.ai.answers import answer_question


@require_GET
def guidance(request,case_id):
    try:
        response=JsonResponse(current_guidance(request.user,case_id))
        response['Cache-Control']='private, no-store'
        return response
    except (PermissionDenied,CommandFailure):
        return error('NOT_FOUND',404)
    except DatabaseError as exc:
        return transient_db_response(exc,preflight=True)


@csrf_protect
@require_POST
def answer(request, case_id):
    """Explicitly initiated, opt-in model inference; no workflow-write tools."""
    try:
        payload=json_payload(request, 2048, {'question'})
        if set(payload) != {'question'}:
            raise InputError('QUESTION_REQUIRED',422)
        result=answer_question(request.user,case_id,payload['question'])
        response=JsonResponse(result)
        response['Cache-Control']='private, no-store'
        return response
    except InputError as exc:
        return error(exc.code,exc.status)
    except (PermissionDenied,CommandFailure):
        return error('NOT_FOUND',404)
    except ValueError:
        return error('INVALID_QUESTION_OR_CONTEXT',422)
    except DatabaseError as exc:
        return transient_db_response(exc)
