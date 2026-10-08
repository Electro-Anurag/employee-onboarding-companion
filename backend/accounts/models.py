"""Persistent identities, organization roles and one-time credential flows."""
import uuid
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

class UserManager(BaseUserManager):
    use_in_migrations = True
    def create_user(self, email, password=None, **extra):
        if not email: raise ValueError('Email is required')
        email = self.normalize_email(email).strip().lower()
        user = self.model(email=email, **extra)
        if password: user.set_password(password)
        else: user.set_unusable_password()
        user.save(using=self._db)
        return user
    def create_superuser(self, email, password=None, **extra):
        extra.setdefault('is_staff', True); extra.setdefault('is_superuser', True)
        if not extra['is_staff'] or not extra['is_superuser']: raise ValueError('Superuser flags required')
        return self.create_user(email, password, **extra)

class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, max_length=254)
    display_name = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    objects = UserManager()
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    class Meta:
        constraints = [models.UniqueConstraint(Lower('email'),name='accounts_email_case_insensitive')]
    def save(self,*args,**kwargs):
        self.email = self.email.strip().lower()
        super().save(*args,**kwargs)
    def __str__(self): return self.email

class Organization(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=160)
    timezone = models.CharField(max_length=80, default='Asia/Kolkata')

class Membership(models.Model):
    EMPLOYEE='EMPLOYEE'; HR='HR'; IT='IT'; MANAGER='MANAGER'
    ROLE_CHOICES = [(x,x) for x in [EMPLOYEE,HR,IT,MANAGER]]
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    user = models.ForeignKey(User,on_delete=models.PROTECT,related_name='memberships')
    organization = models.ForeignKey(Organization,on_delete=models.PROTECT)
    role = models.CharField(max_length=16,choices=ROLE_CHOICES)
    active = models.BooleanField(default=True)
    available = models.BooleanField(default=True)
    can_manage_templates = models.BooleanField(default=False)
    can_coordinate_ownership = models.BooleanField(default=False)
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['organization','user'],name='one_org_membership_per_user'),
            models.UniqueConstraint(fields=['user'],condition=models.Q(active=True),name='one_active_membership_per_user'),
            models.CheckConstraint(condition=models.Q(role__in=['EMPLOYEE','HR','IT','MANAGER']),name='membership_known_role'),
        ]

class OneTimeToken(models.Model):
    INVITE='INVITE'; RESET='RESET'
    PURPOSE_CHOICES=[(INVITE,INVITE),(RESET,RESET)]
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    user=models.ForeignKey(User,on_delete=models.PROTECT)
    purpose=models.CharField(max_length=12,choices=PURPOSE_CHOICES)
    token_hash=models.CharField(max_length=64,unique=True)
    issued_by=models.ForeignKey(User,on_delete=models.PROTECT,related_name='issued_tokens',null=True)
    created_at=models.DateTimeField(default=timezone.now)
    expires_at=models.DateTimeField()
    used_at=models.DateTimeField(null=True)
    class Meta:
        indexes=[models.Index(fields=['user','purpose','used_at'])]
        constraints=[
            models.UniqueConstraint(fields=['user','purpose'],condition=models.Q(used_at__isnull=True),name='one_pending_token_per_purpose'),
            models.CheckConstraint(condition=models.Q(purpose__in=['INVITE','RESET']),name='credential_known_purpose'),
        ]

class LoginThrottle(models.Model):
    bucket=models.CharField(primary_key=True,max_length=96)
    failures=models.PositiveSmallIntegerField(default=0)
    window_start=models.DateTimeField(default=timezone.now)
