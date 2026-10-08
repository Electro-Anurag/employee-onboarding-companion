"""Credential lifecycle and authorization admission boundaries for the M1 shell."""
import hashlib
import hmac
import secrets
from datetime import timedelta
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.contrib.auth.password_validation import validate_password
from django.db import connection, transaction
from django.utils import timezone
from backend.accounts.models import LoginThrottle, Membership, OneTimeToken, User

class InvalidActor(PermissionDenied):
    pass

def actor_context(user, *, locked=False):
    """Never silently pick a role/organization when membership is ambiguous."""
    if not user.is_authenticated:
        raise InvalidActor()
    if locked:
        if not connection.in_atomic_block:
            raise RuntimeError("Locked actor must be resolved within a transaction")
        active_user = User.objects.select_for_update().filter(pk=user.pk, is_active=True).first()
        if active_user is None:
            raise InvalidActor()
    elif not user.is_active:
        raise InvalidActor()
    try:
        qs = Membership.objects.select_related('organization')
        if locked:
            qs = qs.select_for_update(of=('self',))
        return qs.get(user_id=user.pk, active=True)
    except (Membership.DoesNotExist, Membership.MultipleObjectsReturned):
        raise InvalidActor()

def digest_token(raw):
    return hashlib.sha256(raw.encode('utf8')).hexdigest()

def _expire_tokens_locked(user, now):
    """Caller owns the User row lock; serialize all issuing/credential-changing flows."""
    OneTimeToken.objects.filter(user=user, used_at__isnull=True).update(used_at=now)

def issue_token(user,purpose,issuer=None):
    if purpose not in (OneTimeToken.INVITE,OneTimeToken.RESET):
        raise InvalidActor()
    raw=secrets.token_urlsafe(36)
    with transaction.atomic():
        # Stable user lock protects the *empty pending-token set* as well.
        current=User.objects.select_for_update().get(pk=user.pk)
        if not current.is_active:
            raise InvalidActor()
        if purpose==OneTimeToken.INVITE and current.has_usable_password():
            raise InvalidActor()  # INVITE cannot become an alternative reset channel.
        now=timezone.now()
        _expire_tokens_locked(current,now)
        ttl=timedelta(hours=24 if purpose==OneTimeToken.INVITE else 1)
        OneTimeToken.objects.create(user=current,purpose=purpose,token_hash=digest_token(raw),
                                    issued_by=issuer,expires_at=now+ttl)
    return raw

def redeem_token(raw,purpose,password):
    if purpose not in (OneTimeToken.INVITE,OneTimeToken.RESET) or not isinstance(raw,str) or not (24<=len(raw)<=256):
        raise InvalidActor()
    if not isinstance(password,str):
        raise InvalidActor()
    with transaction.atomic():
        # Lookup is only a hint to find the stable lock. Re-read token after locking.
        initial=OneTimeToken.objects.filter(token_hash=digest_token(raw),purpose=purpose).values('user_id').first()
        if initial is None:
            raise InvalidActor()
        user=User.objects.select_for_update().filter(pk=initial['user_id'],is_active=True).first()
        if user is None:
            raise InvalidActor()
        token=(OneTimeToken.objects.select_for_update().filter(token_hash=digest_token(raw),
               purpose=purpose,user=user).first())
        if token is None or token.used_at is not None or token.expires_at<=timezone.now():
            raise InvalidActor()
        if purpose==OneTimeToken.INVITE and user.has_usable_password():
            raise InvalidActor()
        try:
            validate_password(password,user)
        except ValidationError:
            raise InvalidActor()
        user.set_password(password)
        user.save(update_fields=['password'])
        _expire_tokens_locked(user,timezone.now())
        # All outstanding invite/reset tokens are revoked in the SAME transaction.
        # Other Django sessions lose access via the changed session auth hash.
    return user

def change_password_locked(user,old_password,new_password):
    """Re-check old password under the credential row lock (reset/change race)."""
    if not isinstance(old_password,str) or not isinstance(new_password,str):
        raise InvalidActor()
    with transaction.atomic():
        current=User.objects.select_for_update().filter(pk=user.pk,is_active=True).first()
        if current is None or not current.check_password(old_password):
            raise InvalidActor()
        validate_password(new_password,current)
        current.set_password(new_password)
        current.save(update_fields=['password'])
        _expire_tokens_locked(current,timezone.now())
    return current

def hmac_identifier(value):
    return hmac.new(settings.SECRET_KEY.encode(),value.encode(),hashlib.sha256).hexdigest()

def admit_attempt(kind,identifier,client_ip):
    """Atomic admission budget; expensive Argon2/redemption happens AFTER commit.

    All attempted logins count, including successful ones: 5/account/15m,
    30/IP/15m. Redemption: 5/token/15m, 10/IP/15m. No per-process state.
    """
    if kind not in ('login','redeem'):
        raise ValueError('Invalid throttle policy')
    if not isinstance(client_ip,str):
        client_ip='unknown'
    buckets=(
        [('login:account:'+hmac_identifier(identifier.casefold()),5),
         ('login:ip:'+hmac_identifier(client_ip),30)]
        if kind=='login' else
        [('redeem:token:'+hmac_identifier(identifier),5),
         ('redeem:ip:'+hmac_identifier(client_ip),10)]
    )
    with transaction.atomic():
        for bucket,limit in sorted(buckets):
            # Serialize even a previously nonexistent counter row.
            lock_key=int.from_bytes(hashlib.sha256(bucket.encode()).digest()[:8],'big',signed=True)
            with connection.cursor() as cur:
                cur.execute('SELECT pg_advisory_xact_lock(%s)',[lock_key])
        now=timezone.now()
        locked=[]
        for bucket,limit in sorted(buckets):
            row,_=LoginThrottle.objects.get_or_create(bucket=bucket)
            row=LoginThrottle.objects.select_for_update().get(pk=bucket)
            if (now-row.window_start).total_seconds()>=900:
                row.window_start=now
                row.failures=0
            if row.failures>=limit:
                return False
            locked.append(row)
        for row in locked:
            row.failures+=1
            row.save(update_fields=['failures','window_start'])
    return True
