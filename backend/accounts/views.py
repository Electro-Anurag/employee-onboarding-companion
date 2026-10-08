"""Minimal credential and session API. All consequential outcomes are persistent."""
import time
import uuid
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction, DatabaseError
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_protect
from django.views.decorators.http import require_GET, require_POST
from backend.accounts.models import Membership, OneTimeToken
from backend.accounts.security import (actor_context,issue_token,redeem_token,
    admit_attempt,change_password_locked,InvalidActor)
from backend.common.http import error, json_payload, InputError, required_uuid, transient_db_response
from backend.audit.services import append_event
from backend.onboarding.services import CommandFailure, issue_credential_for_case

@ensure_csrf_cookie
@require_GET
def csrf(request):
    return JsonResponse({'csrf_token':get_token(request)})

def safe_context(request):
    try:
        return actor_context(request.user)
    except PermissionDenied:
        return None

@require_GET
def me(request):
    try:
        member=safe_context(request)
        if member is None:
            return error('UNAUTHENTICATED',401)
        return JsonResponse({'user_id':str(request.user.pk),'display_name':request.user.display_name,
                             'role':member.role,'organization_id':str(member.organization_id),
                             'capabilities':{'manage_templates':bool(member.can_manage_templates),
                                             'coordinate_ownership':bool(member.can_coordinate_ownership)}})
    except DatabaseError as exc:
        return transient_db_response(exc,preflight=True)

@csrf_protect
@require_POST
def login_view(request):
    try:
        data=json_payload(request,2048,{'email','password'})
        email=data.get('email')
        password=data.get('password')
        if not isinstance(email,str) or not isinstance(password,str) or not (1<=len(email)<=254) or len(password)>256:
            raise InputError()
        email=email.strip().lower()
        if not admit_attempt('login',email,request.META.get('REMOTE_ADDR','unknown')):
            return error('LOGIN_UNAVAILABLE',429)
        user=authenticate(request,username=email,password=password)
        if user is None or not user.is_active:
            return error('LOGIN_UNAVAILABLE',401)
        try:
            actor_context(user)
        except PermissionDenied:
            return error('LOGIN_UNAVAILABLE',401)
        login(request,user)
        request.session['m1_session_started']=time.time()
        request.session.set_expiry(1800)
        return JsonResponse({'ok':True})
    except InputError as exc:
        return error(exc.code,exc.status)
    except DatabaseError as exc:
        return transient_db_response(exc)

@csrf_protect
@require_POST
def logout_view(request):
    try:
        logout(request)
        return JsonResponse({'ok':True})
    except DatabaseError as exc:
        # logout() has already attempted session mutation/flush.
        return transient_db_response(exc,indeterminate=True)

@csrf_protect
@require_POST
def password_change(request):
    try:
        if safe_context(request) is None:
            return error('UNAUTHENTICATED',401)
        data=json_payload(request,2048,{'old_password','new_password'})
        with transaction.atomic():
            user=change_password_locked(request.user,data['old_password'],data['new_password'])
            member=actor_context(user,locked=True)
            append_event(stream_key=f'org:{member.organization_id}',actor=user,
                         event_type='PASSWORD_CHANGED',entity_id=user.pk,changes={'credential':'changed'})
    except InvalidActor:
        return error('INVALID_PASSWORD',403)
    except (KeyError,TypeError,ValidationError,InputError):
        return error('INVALID_PASSWORD_POLICY',422)
    except DatabaseError as exc:
        # The atomic credential/audit block did not return successfully.
        # A lost COMMIT acknowledgement is nevertheless an UNKNOWN outcome.
        return transient_db_response(exc)

    # Transaction.atomic has exited successfully: password, token revocation
    # and audit are COMMITTED. Session rotation is a separate DB operation.
    try:
        request.user=user
        update_session_auth_hash(request,user)
    except DatabaseError:
        return error('SESSION_REFRESH_UNAVAILABLE',503,outcome='COMMAND_COMMITTED',
                     session_state='UNKNOWN',automatic_replay=False)
    return JsonResponse({'ok':True})

def _issue(request,purpose):
    try:
        member=safe_context(request)
        if member is None:
            return error('UNAUTHENTICATED',401)
        if member.role!=Membership.HR:
            return error('FORBIDDEN',403)
        data=json_payload(request,2048,{'case_id'})
        case_id=required_uuid(data.get('case_id'))
        token=issue_credential_for_case(actor=request.user,case_id=case_id,purpose=purpose)
        name='invitation_token' if purpose==OneTimeToken.INVITE else 'reset_token'
        return JsonResponse({name:token,'expires_in_seconds':86400 if purpose==OneTimeToken.INVITE else 3600},status=201)
    except InputError as exc:
        return error(exc.code,exc.status)
    except CommandFailure as exc:
        return error(exc.code,exc.status)
    except PermissionDenied:
        return error('NOT_FOUND',404)
    except DatabaseError as exc:
        return transient_db_response(exc)

@csrf_protect
@require_POST
def issue_invitation(request):
    return _issue(request,OneTimeToken.INVITE)

@csrf_protect
@require_POST
def issue_reset(request):
    return _issue(request,OneTimeToken.RESET)

def _redeem(request,purpose):
    try:
        data=json_payload(request,2048,{'token','new_password'})
        raw=data.get('token')
        if not isinstance(raw,str) or not (24<=len(raw)<=256) or not isinstance(data.get('new_password'),str):
            raise InputError()
        if not admit_attempt('redeem',raw,request.META.get('REMOTE_ADDR','unknown')):
            return error('INVALID_OR_EXPIRED_TOKEN',429)
        with transaction.atomic():
            user=redeem_token(raw,purpose,data['new_password'])
            member=actor_context(user,locked=True)
            append_event(stream_key=f'org:{member.organization_id}',actor=user,
                         event_type='INVITATION_REDEEMED' if purpose==OneTimeToken.INVITE else 'PASSWORD_RESET',
                         entity_id=user.pk,changes={'credential':'activated' if purpose==OneTimeToken.INVITE else 'reset'})
        return JsonResponse({'ok':True})
    except (KeyError,ValueError,TypeError,PermissionDenied,InputError,ValidationError):
        return error('INVALID_OR_EXPIRED_TOKEN',400)
    except DatabaseError as exc:
        return transient_db_response(exc)

@csrf_protect
@require_POST
def redeem_invitation(request):
    return _redeem(request,OneTimeToken.INVITE)

@csrf_protect
@require_POST
def redeem_reset(request):
    return _redeem(request,OneTimeToken.RESET)
