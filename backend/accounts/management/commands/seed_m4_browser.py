"""Disposable M4 browser fixture; real DB commands, no fake UI responses.

Only allowed under DEBUG with explicit synthetic confirmation. Separate org
and accounts prevent coupling with the M2 four-role/browser mutation suite.
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
from backend.training.definitions import default_spec
from backend.onboarding.commands import create_case,activate_case,start_task
from backend.onboarding.models import Task
from backend.activities.models import ActivityOccurrence

class Command(BaseCommand):
    help='Build isolated synthetic M4 training and activity browser case.'

    def add_arguments(self,parser):
        parser.add_argument('--confirm-synthetic',action='store_true')

    def handle(self,*args,**options):
        if not settings.DEBUG or not options['confirm_synthetic']:
            raise CommandError('Explicit synthetic-only DEBUG fixture required')
        suffix='@m4-browser-demo.invalid'
        roles=('HR','EMPLOYEE','IT','MANAGER')
        if User.objects.filter(email__in=[r.lower()+suffix for r in roles]).exists():
            raise CommandError('M4 browser fixture already exists')
        with transaction.atomic():
            org=Organization.objects.create(name='M4 Training and Meetings Browser Synthetic',timezone='UTC')
            users={}
            members={}
            credentials={}
            for role in roles:
                password=secrets.token_urlsafe(20)+'Ab1!'
                user=User.objects.create_user(email=role.lower()+suffix,
                    password=password,display_name='M4 Synthetic '+role.title())
                membership=Membership.objects.create(user=user,organization=org,role=role,
                    can_manage_templates=(role=='HR'),
                    can_coordinate_ownership=(role=='HR'))
                users[role],members[role],credentials[role]=user,membership,password
            def task(key,kind,title,owner,spec):
                return dict(key=key,kind=kind,title=title,owner_role=owner,
                    description='Generated M4 browser qualification only',
                    required=True,available_offset_days=-5,due_offset_days=5,
                    evidence_spec=spec)
            tasks=[
                task('workplace_training','TRAINING','Workplace Training','EMPLOYEE',
                    default_spec('workplace_training')),
                task('scheduled_orientation','ACTIVITY','Scheduled Orientation','HR',
                    {'type':'ACTIVITY'}),
                task('elapsed_orientation','ACTIVITY','Elapsed Orientation','HR',
                    {'type':'ACTIVITY'}),
                task('manager_followup','CHECK_IN','Manager Followup','MANAGER',
                    {'type':'CHECK_IN'}),
            ]
            draft=create_template(actor=users['HR'],key='m4_browser_evidence',
                name='M4 synthetic training and meetings',tasks=tasks,
                edges=[{'predecessor':'elapsed_orientation','successor':'manager_followup'}])
            published=publish_template(actor=users['HR'],
                template_id=uuid.UUID(draft['id']),revision=1)
            joining=timezone.localdate()+timedelta(days=2)
            created,_=create_case(actor=users['HR'],employee_id=members['EMPLOYEE'].pk,
                template_version_id=uuid.UUID(published['version_id']),
                joining_date=joining,
                owner_ids={'IT':members['IT'].pk,'MANAGER':members['MANAGER'].pk},
                key=uuid.uuid4())
            cid=uuid.UUID(created['case_id'])
            activate_case(actor=users['HR'],case_id=cid,key=uuid.uuid4(),expected_version=1)
            elapsed=Task.objects.get(case_id=cid,key='elapsed_orientation')
            start_task(actor=users['HR'],case_id=cid,task_id=elapsed.pk,
                key=uuid.uuid4(),expected_version=2)
            # Only this intentionally generated scenario uses an elapsed time
            # fixture; public schedule API correctly disallows backdating.
            ActivityOccurrence.objects.create(task=elapsed,revision=1,
                begins_at=timezone.now()-timedelta(hours=2),
                ends_at=timezone.now()-timedelta(hours=1),
                medium='IN_PERSON',meeting_reference='Past synthetic session',
                reason='Test-only elapsed occurrence for actual HR browser attendance',
                scheduled_by=users['HR'])
        self.stdout.write('CASE '+str(cid))
        for role in roles:
            self.stdout.write(role+' '+users[role].email+' '+credentials[role])
