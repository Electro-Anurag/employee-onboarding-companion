"""Role-authorized current-state guidance; no provider or write authority."""
from django.core.exceptions import PermissionDenied
from django.db import DatabaseError
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from backend.common.http import error,transient_db_response
from backend.onboarding.services import CommandFailure
from backend.ai.guidance import current_guidance


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
