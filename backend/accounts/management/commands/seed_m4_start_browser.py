"""Isolated actual-browser fixture for six typed tasks after generic Start.

Creates only a disposable synthetic case under DEBUG with explicit opt-in.
"""
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

class Command(BaseCommand):
    help='Generate independent Start-to-typed-command browser fixture.'

    def add_arguments(self,parser):
        parser.add_argument('--confirm-synthetic',action='store_true')

    def handle(self,*args,**options):
        if not settings.DEBUG or not options['confirm_synthetic']:
            raise CommandError('DEBUG and explicit synthetic confirmation required')
        suffix='@m4-start-browser.invalid'
        roles=('HR','EMPLOYEE','IT','MANAGER')
        if User.objects.filter(email__in=[r.lower()+suffix for r in roles]).exists():
            raise CommandError('Start browser fixture already exists')
        with transaction.atomic():
            org=Organization.objects.create(name='M4 Start Recovery Browser Synthetic',timezone='UTC')
            users={}
            members={}
            credentials={}
            for role in roles:
                password=secrets.token_urlsafe(22)+'Ab1!'
                user=User.objects.create_user(email=role.lower()+suffix,
                    password=password,display_name='Start Test '+role.title())
                membership=Membership.objects.create(user=user,organization=org,role=role,
                    can_manage_templates=(role=='HR'),can_coordinate_ownership=(role=='HR'))
                users[role],members[role],credentials[role]=user,membership,password
            def task(key,kind,owner,title):
                return dict(key=key,kind=kind,owner_role=owner,title=title,
                    required=True,available_offset_days=-5,due_offset_days=7,
                    evidence_spec={'type':kind})
            tasks=[
                task('started_access','ACCESS','IT','Start Access'),
                task('started_device','EQUIPMENT','IT','Start Device'),
                task('started_receipt','EQUIPMENT_RECEIPT','EMPLOYEE','Start Receipt'),
                task('started_activity','ACTIVITY','HR','Start Activity'),
                task('started_introduction','INTRODUCTION','MANAGER','Start Introduction'),
                task('started_checkin','CHECK_IN','MANAGER','Start Checkin'),
            ]
            draft=create_template(actor=users['HR'],key='m4_start_recovery_browser',
                name='M4 typed Start path synthetic',tasks=tasks,
                edges=[{'predecessor':'started_device','successor':'started_receipt'}])
            published=publish_template(actor=users['HR'],
                template_id=uuid.UUID(draft['id']),revision=1)
            created,_=create_case(actor=users['HR'],employee_id=members['EMPLOYEE'].pk,
                template_version_id=uuid.UUID(published['version_id']),
                joining_date=timezone.localdate()+timedelta(days=2),
                owner_ids={'IT':members['IT'].pk,'MANAGER':members['MANAGER'].pk},
                key=uuid.uuid4())
            cid=uuid.UUID(created['case_id'])
            activate_case(actor=users['HR'],case_id=cid,key=uuid.uuid4(),expected_version=1)
        self.stdout.write('CASE '+str(cid))
        for role in roles:
            self.stdout.write(role+' '+users[role].email+' '+credentials[role])
