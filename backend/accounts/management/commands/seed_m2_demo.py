"""Explicit local-only synthetic onboarding accounts (not a production bootstrap)."""
import secrets
from django.conf import settings
from django.core.management.base import BaseCommand,CommandError
from django.db import transaction
from backend.accounts.models import User,Organization,Membership

class Command(BaseCommand):
    help='Create exactly four isolated synthetic login accounts for M2 local demo.'

    def add_arguments(self,parser):
        parser.add_argument('--confirm-synthetic',action='store_true',
                            help='Confirm local synthetic-data-only account creation.')

    def handle(self,*args,**options):
        if not settings.DEBUG or not options['confirm_synthetic']:
            raise CommandError('Local DEBUG=1 and --confirm-synthetic required. Never run against production.')
        domain='demo.aster-vale.invalid'
        roles=['HR','EMPLOYEE','IT','MANAGER']
        emails={r:r.lower()+'@'+domain for r in roles}
        if User.objects.filter(email__in=emails.values()).exists():
            raise CommandError('Demo identities already exist. Never silently overwrite credentials or cases.')
        secret={}
        with transaction.atomic():
            org=Organization.objects.create(name='Aster Vale Labs — Synthetic Local Demo',timezone='Asia/Kolkata')
            for role in roles:
                password=secrets.token_urlsafe(20)+'Ab1!'
                user=User.objects.create_user(email=emails[role],password=password,
                         display_name='Synthetic '+role.title())
                Membership.objects.create(user=user,organization=org,role=role,
                    can_manage_templates=(role=='HR'),can_coordinate_ownership=(role=='HR'))
                secret[role]=password
        self.stdout.write(self.style.SUCCESS('Four synthetic local accounts created.'))
        self.stdout.write('These one-time displayed credentials are not stored as plaintext. Save securely.')
        for role in roles:
            self.stdout.write(role+' '+emails[role]+' '+secret[role])
        self.stdout.write('Sign in as HR, create the default template, publish it and create the case.')
