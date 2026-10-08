import hashlib
import hmac
import secrets
from datetime import timedelta
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone
from backend.accounts.models import LoginThrottle, Membership, OneTimeToken

class InvalidActor(PermissionDenied): pass

def actor_context(user):
    if not user.is_authenticated or not user.is_active: raise InvalidActor()
    try:
        return Membership.objects.select_related('organization').get(user=user,active=True)
    except (Membership.DoesNotExist,Membership.MultipleObjectsReturned):
        raise InvalidActor()

def digest_token(raw): return hashlib.sha256(raw.encode('utf8')).hexdigest()

def issue_token(user,purpose,issuer=None):
    raw=secrets.token_urlsafe(36)
    now=timezone.now()
    ttl=timedelta(hours=24 if purpose==OneTimeToken.INVITE else 1)
    with transaction.atomic():
        OneTimeToken.objects.select_for_update().filter(user=user,purpose=purpose,used_at__isnull=True).update(used_at=now)
        OneTimeToken.objects.create(user=user,purpose=purpose,token_hash=digest_token(raw),issued_by=issuer,expires_at=now+ttl)
    return raw

def redeem_token(raw,purpose,password):
    if not isinstance(raw,str) or len(raw)>256 or len(raw)<24: raise InvalidActor()
    from django.contrib.auth.password_validation import validate_password
    from django.core.exceptions import ValidationError
    with transaction.atomic():
        token=(OneTimeToken.objects.select_for_update().select_related('user').filter(token_hash=digest_token(raw),purpose=purpose).first())
        if token is None or token.used_at or token.expires_at<=timezone.now() or not token.user.is_active:
            raise InvalidActor()
        try: validate_password(password,token.user)
        except ValidationError: raise InvalidActor()
        user=token.user
        user.set_password(password)
        user.save(update_fields=['password'])
        token.used_at=timezone.now(); token.save(update_fields=['used_at'])
        # Existing sessions become unusable because Django's session auth hash changed.
    return user

def hmac_identifier(text): return hmac.new(settings.SECRET_KEY.encode(),text.encode(),hashlib.sha256).hexdigest()

def throttle_failure(email,client_ip):
    # Account and IP buckets share a 15-minute window. Both must be locked before counts advance.
    names=sorted(['account:'+hmac_identifier(email.casefold()),'ip:'+hmac_identifier(client_ip)])
    now=timezone.now(); denied=False
    with transaction.atomic():
        for name in names:
            entry,_=LoginThrottle.objects.get_or_create(bucket=name)
            entry=LoginThrottle.objects.select_for_update().get(bucket=name)
            if (now-entry.window_start).total_seconds()>=900:
                entry.window_start=now;entry.failures=0
            limit=5 if name.startswith('account:') else 30
            if entry.failures>=limit: denied=True
            if not denied: entry.failures+=1
            entry.save(update_fields=['window_start','failures'])
    return denied

def throttle_check(email,client_ip):
    now=timezone.now()
    for name,limit in [('account:'+hmac_identifier(email.casefold()),5),('ip:'+hmac_identifier(client_ip),30)]:
        r=LoginThrottle.objects.filter(bucket=name).first()
        if r and r.failures>=limit and (now-r.window_start).total_seconds()<900: return True
    return False
