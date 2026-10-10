"""A single fully synthetic M5 exception dependency journey for Chromium."""
import secrets
import uuid
from datetime import timedelta
from django.conf import settings
from django.core.management.base import BaseCommand,CommandError
from django.db import transaction
from django.utils import timezone
from backend.accounts.models import User,Membership,Organization
from backend.onboarding.commands import create_case,activate_case
from backend.onboarding.models import Task
from backend.templates.services import create_template,publish_template


class Command(BaseCommand):
    help='Create isolated synthetic M5 manager/HR exception workflow'
    def add_arguments(self,parser):
        parser.add_argument('--confirm-synthetic',action='store_true')
    def handle(self,*args,**kwargs):
        if not (settings.DEBUG and kwargs['confirm_synthetic']):
            raise CommandError('Local DEBUG=1 with --confirm-synthetic is required')
        suffix='@m5-browser.invalid'
        roles=['HR','EMPLOYEE','IT','MANAGER']
        if User.objects.filter(email__in=[r.lower()+suffix for r in roles]).exists():
            raise CommandError('M5 test fixture already exists')
        with transaction.atomic():
            org=Organization.objects.create(name='M5 Synthetic Exception Workflow',timezone='UTC')
            users={};members={};secrets_by_role={}
            for role in roles:
                password=secrets.token_urlsafe(20)+'Ab1!'
                user=User.objects.create_user(email=role.lower()+suffix,
                    password=password,display_name='M5 Synthetic '+role.title())
                member=Membership.objects.create(user=user,organization=org,role=role,
                    can_manage_templates=(role=='HR'),
                    can_coordinate_ownership=(role=='HR'))
                users[role]=user;members[role]=member
                secrets_by_role[role]=password
            tasks=[
                dict(key='m5_manager_preparation',kind='MANAGER_PREPARATION',
                    owner_role='MANAGER',title='M5 Manager Preparation',
                    required=True,available_offset_days=-5,due_offset_days=5,
                    evidence_spec={'type':'MANAGER_PREPARATION'}),
                dict(key='m5_team_introduction',kind='INTRODUCTION',
                    owner_role='MANAGER',title='M5 Team Introduction',
                    required=True,available_offset_days=-5,due_offset_days=6,
                    evidence_spec={'type':'INTRODUCTION'}),
            ]
            draft=create_template(actor=users['HR'],key='m5_exception_browser',
                name='M5 Actual Exception Recovery',tasks=tasks,
                edges=[{'predecessor':'m5_manager_preparation',
                        'successor':'m5_team_introduction'}])
            published=publish_template(actor=users['HR'],
                template_id=uuid.UUID(draft['id']),revision=1)
            made,_=create_case(actor=users['HR'],employee_id=members['EMPLOYEE'].pk,
                template_version_id=uuid.UUID(published['version_id']),
                joining_date=timezone.localdate()+timedelta(days=3),
                owner_ids={'IT':members['IT'].pk,'MANAGER':members['MANAGER'].pk},
                key=uuid.uuid4())
            case_id=uuid.UUID(made['case_id'])
            activate_case(actor=users['HR'],case_id=case_id,
                key=uuid.uuid4(),expected_version=1)
            assert Task.objects.get(case_id=case_id,
                key='m5_team_introduction').execution_state=='BLOCKED'
        self.stdout.write('CASE '+str(case_id))
        for role in roles:
            self.stdout.write(role+' '+users[role].email+' '+secrets_by_role[role])
