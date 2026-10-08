"""Minimal real authentication interface with cookie sessions and CSRF."""
import json
import uuid
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_protect
from django.views.decorators.http import require_GET, require_POST
from backend.accounts.models import Membership, OneTimeToken, User
from backend.accounts.security import actor_context, issue_token, redeem_token, throttle_failure, throttle_check
from backend.common.http import error,json_payload,InputError
from backend.audit.services import append_event
from django.db import transaction

@ensure_csrf_cookie
@require_GET
def csrf(request): return JsonResponse({'csrf_token':get_token(request)})

def safe_context(request):
    try:return actor_context(request.user)
    except PermissionDenied: return None

@require_GET
def me(request):
    member=safe_context(request)
    if member is None:return error('UNAUTHENTICATED',401)
    return JsonResponse({'user_id':str(request.user.pk),'display_name':request.user.display_name,'role':member.role,'organization_id':str(member.organization_id)})

@csrf_protect
@require_POST
def login_view(request):
    try:
        data=json_payload(request,2048,{'email','password'})
        email=data.get('email','');password=data.get('password','')
        if not isinstance(email,str) or not isinstance(password,str) or len(email)>254 or len(password)>256:raise InputError()
        email=email.strip().lower();ip=request.META.get('REMOTE_ADDR','unknown')
        if throttle_check(email,ip):return error('LOGIN_UNAVAILABLE',429)
        user=authenticate(request,username=email,password=password)
        if user is None or not user.is_active or not user.memberships.filter(active=True).exists():
            limited=throttle_failure(email,ip)
            return error('LOGIN_UNAVAILABLE',429 if limited else 401)
        login(request,user);request.session['m1_session_started']=__import__('time').time()
        request.session.set_expiry(1800)
        return JsonResponse({'ok':True})
    except InputError as e:return error(e.code,e.status)

@csrf_protect
@require_POST
def logout_view(request):
    logout(request)
    return JsonResponse({'ok':True})

@csrf_protect
@require_POST
def password_change(request):
    if safe_context(request) is None:return error('UNAUTHENTICATED',401)
    try:
        data=json_payload(request,2048,{'old_password','new_password'})
        if not request.user.check_password(data.get('old_password','')):return error('INVALID_PASSWORD',403)
        validate_password(data['new_password'],request.user)
        with transaction.atomic():
            request.user.set_password(data['new_password']);request.user.save(update_fields=['password'])
            append_event(stream_key=f'org:{safe_context(request).organization_id}',actor=request.user,
                         event_type='PASSWORD_CHANGED',entity_id=request.user.pk,changes={'credential':'changed'})
        update_session_auth_hash(request,request.user)
        return JsonResponse({'ok':True})
    except (KeyError,TypeError,ValidationError,InputError):return error('INVALID_PASSWORD_POLICY',422)

@csrf_protect
@require_POST
def issue_invitation(request):
    member=safe_context(request)
    if member is None:return error('UNAUTHENTICATED',401)
    if member.role!=Membership.HR:return error('FORBIDDEN',403)
    try:
        data=json_payload(request,2048,{'case_id'})
        from backend.onboarding.services import get_authorized_case
        _,case=get_authorized_case(request.user,uuid.UUID(data['case_id']))
        with transaction.atomic():
            token=issue_token(case.employee.user,OneTimeToken.INVITE,request.user)
            append_event(stream_key=f'case:{case.pk}',actor=request.user,event_type='INVITATION_ISSUED',entity_id=case.pk,
                         changes={'target_user_id':str(case.employee.user.pk)})
        # Since no email provider in M1, issue a one-time token to the HR issuer only.
        return JsonResponse({'invitation_token':token,'expires_in_seconds':86400},status=201)
    except (KeyError,ValueError,InputError):return error('INVALID_REQUEST',422)
    except Exception as e:
        from backend.onboarding.services import CommandFailure
        if isinstance(e,CommandFailure):return error(e.code,e.status)
        raise

@csrf_protect
@require_POST
def redeem_invitation(request):
    try:
        data=json_payload(request,2048,{'token','new_password'})
        with transaction.atomic():
            user=redeem_token(data['token'],OneTimeToken.INVITE,data['new_password'])
            member=actor_context(user)
            append_event(stream_key=f'org:{member.organization_id}',actor=user,event_type='INVITATION_REDEEMED',entity_id=user.pk,
                         changes={'credential':'activated'})
        return JsonResponse({'ok':True})
    except (KeyError,ValueError,TypeError,PermissionDenied,InputError):return error('INVALID_OR_EXPIRED_TOKEN',400)

@csrf_protect
@require_POST
def issue_reset(request):
    member=safe_context(request)
    if member is None:return error('UNAUTHENTICATED',401)
    if member.role!=Membership.HR:return error('FORBIDDEN',403)
    try:
        data=json_payload(request,2048,{'case_id'})
        from backend.onboarding.services import get_authorized_case
        _,case=get_authorized_case(request.user,uuid.UUID(data['case_id']))
        with transaction.atomic():
            token=issue_token(case.employee.user,OneTimeToken.RESET,request.user)
            append_event(stream_key=f'case:{case.pk}',actor=request.user,event_type='RESET_ISSUED',entity_id=case.pk,
                         changes={'target_user_id':str(case.employee.user.pk)})
        return JsonResponse({'reset_token':token,'expires_in_seconds':3600},status=201)
    except (KeyError,ValueError,InputError):return error('INVALID_REQUEST',422)
    except Exception as e:
        from backend.onboarding.services import CommandFailure
        if isinstance(e,CommandFailure):return error(e.code,e.status)
        raise

@csrf_protect
@require_POST
def redeem_reset(request):
    try:
        data=json_payload(request,2048,{'token','new_password'})
        with transaction.atomic():
            user=redeem_token(data['token'],OneTimeToken.RESET,data['new_password'])
            member=actor_context(user)
            append_event(stream_key=f'org:{member.organization_id}',actor=user,event_type='PASSWORD_RESET',entity_id=user.pk,
                         changes={'credential':'reset'})
        return JsonResponse({'ok':True})
    except (KeyError,ValueError,TypeError,PermissionDenied,InputError):return error('INVALID_OR_EXPIRED_TOKEN',400)
