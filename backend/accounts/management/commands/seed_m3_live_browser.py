"""Actual browser/MinIO/ClamAV fixture: synthetic users and one real DOCUMENT task."""
import secrets
import uuid
from datetime import timedelta
from django.conf import settings
from django.core.management.base import BaseCommand,CommandError
from django.db import transaction
from django.utils import timezone
from backend.accounts.models import User,Organization,Membership
from backend.templates.services import create_template,publish_template
from backend.onboarding.commands import create_case,activate_case
from backend.onboarding.models import Task

class Command(BaseCommand):
    help='Create disposable real S3 synthetic browser case without document records'
    def add_arguments(self,parser):
        parser.add_argument('--confirm-synthetic',action='store_true')
    def handle(self,*args,**options):
        if (not options['confirm_synthetic'] or not settings.DEBUG
                or not settings.M3_REAL_DOCUMENT_ENABLED
                or not settings.M3_S3_ALLOW_LOCAL_TEST_ENDPOINT
                or settings.M3_S3_ENDPOINT_URL!='http://127.0.0.1:9000'):
            raise CommandError('Explicit synthetic DEBUG loopback S3 fixture required')
        suffix='@m3-real-browser.invalid'
        roles=('HR','EMPLOYEE','IT','MANAGER')
        if User.objects.filter(email__in=[r.lower()+suffix for r in roles]).exists():
            raise CommandError('M3 real browser fixture already exists')
        with transaction.atomic():
            org=Organization.objects.create(name='M3 Real S3 Synthetic Browser',timezone='UTC')
            people={};members={};credentials={}
            for role in roles:
                password=secrets.token_urlsafe(20)+'Ab1!'
                actor=User.objects.create_user(email=role.lower()+suffix,
                    password=password,display_name='M3 Live '+role.title())
                member=Membership.objects.create(user=actor,organization=org,
                    role=role,can_manage_templates=(role=='HR'),
                    can_coordinate_ownership=(role=='HR'))
                people[role]=actor;members[role]=member;credentials[role]=password
            tasks=[
                dict(key='identity_document',kind='DOCUMENT',owner_role='EMPLOYEE',
                    title='Live Identity PDF',required=True,available_offset_days=-5,
                    due_offset_days=5,evidence_spec={'type':'DOCUMENT'}),
                dict(key='equipment_setup',kind='EQUIPMENT',owner_role='IT',
                    title='Blocked Equipment',required=True,available_offset_days=-5,
                    due_offset_days=5,evidence_spec={'type':'EQUIPMENT'}),
            ]
            draft=create_template(actor=people['HR'],key='m3_real_s3_browser',
                name='Synthetic actual PDF intake',tasks=tasks,
                edges=[{'predecessor':'identity_document','successor':'equipment_setup'}])
            published=publish_template(actor=people['HR'],
                template_id=uuid.UUID(draft['id']),revision=1)
            made,_=create_case(actor=people['HR'],employee_id=members['EMPLOYEE'].pk,
                template_version_id=uuid.UUID(published['version_id']),
                joining_date=timezone.localdate()+timedelta(days=3),
                owner_ids={'IT':members['IT'].pk,'MANAGER':members['MANAGER'].pk},
                key=uuid.uuid4())
            cid=uuid.UUID(made['case_id'])
            activate_case(actor=people['HR'],case_id=cid,key=uuid.uuid4(),
                expected_version=1)
            assert Task.objects.get(case_id=cid,key='equipment_setup').execution_state=='BLOCKED'
        self.stdout.write('CASE '+str(cid))
        for role in roles:
            self.stdout.write(role+' '+people[role].email+' '+credentials[role])
