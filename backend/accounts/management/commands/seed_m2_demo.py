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
        parser.add_argument('--include-second-hr',action='store_true',
                            help='Also generate a separate synthetic HR for cross-organization browser tests.')

    def handle(self,*args,**options):
        if not settings.DEBUG or not options['confirm_synthetic']:
            raise CommandError('Local DEBUG=1 and --confirm-synthetic required. Never run against production.')
        domain='demo.aster-vale.invalid'
        roles=['HR','EMPLOYEE','IT','MANAGER']
        emails={r:r.lower()+'@'+domain for r in roles}
        if options['include_second_hr']:
            emails['HR_B']='hr_other@demo.other-organization.invalid'
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
            if options['include_second_hr']:
                other_org=Organization.objects.create(name='Other Synthetic Organization',
                                                      timezone='Asia/Kolkata')
                password=secrets.token_urlsafe(20)+'Ab1!'
                other_user=User.objects.create_user(
                    email=emails['HR_B'],password=password,
                    display_name='Synthetic HR Other Organization')
                Membership.objects.create(user=other_user,organization=other_org,role='HR',
                    can_manage_templates=True,can_coordinate_ownership=True)
                secret['HR_B']=password
        self.stdout.write(self.style.SUCCESS('Four synthetic local accounts created'+
            (' with a separate cross-organization HR' if options['include_second_hr'] else '')+'.'))
        self.stdout.write('These one-time displayed credentials are not stored as plaintext. Save securely.')
        for role in roles+(['HR_B'] if options['include_second_hr'] else []):
            self.stdout.write(role+' '+emails[role]+' '+secret[role])
        self.stdout.write('Sign in as HR, create the default template, publish it and create the case.')
