"""Disposable overdue meeting fixture with no backdated occurrence inserts.

All occurrences/attendance must be authored through the real UI/commands.
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
from backend.onboarding.models import Task

class Command(BaseCommand):
    help='Create isolated overdue activity browser scenario with no pre-seeded occurrences'

    def add_arguments(self,parser):
        parser.add_argument('--confirm-synthetic',action='store_true')

    def handle(self,*args,**options):
        if not settings.DEBUG or not options['confirm_synthetic']:
            raise CommandError('DEBUG and explicit synthetic confirmation required')
        suffix='@m4-overdue-browser.invalid'
        roles=('HR','EMPLOYEE','IT','MANAGER')
        if User.objects.filter(email__in=[r.lower()+suffix for r in roles]).exists():
            raise CommandError('Overdue browser fixture already exists')
        with transaction.atomic():
            org=Organization.objects.create(name='M4 Elapsed Overdue Browser Synthetic',
                timezone='UTC')
            users={}
            members={}
            credentials={}
            for role in roles:
                password=secrets.token_urlsafe(20)+'Ab1!'
                user=User.objects.create_user(email=role.lower()+suffix,
                    password=password,display_name='M4 Overdue '+role.title())
                member=Membership.objects.create(user=user,organization=org,role=role,
                    can_manage_templates=(role=='HR'),can_coordinate_ownership=(role=='HR'))
                users[role],members[role],credentials[role]=user,member,password
            tasks=[
                dict(key='overdue_orientation',kind='ACTIVITY',owner_role='HR',
                     title='Overdue Orientation',required=True,
                     available_offset_days=-33,due_offset_days=-30,
                     evidence_spec={'type':'ACTIVITY'}),
                dict(key='overdue_successor',kind='CHECK_IN',owner_role='MANAGER',
                     title='Followup After Overdue',required=True,
                     available_offset_days=-30,due_offset_days=5,
                     evidence_spec={'type':'CHECK_IN'}),
                dict(key='manager_recovery_checkin',kind='CHECK_IN',owner_role='MANAGER',
                     title='Manager Recovery Check-in',required=True,
                     available_offset_days=-30,due_offset_days=5,
                     evidence_spec={'type':'CHECK_IN'}),
                dict(key='hr_after_manager',kind='ACTIVITY',owner_role='HR',
                     title='HR Followup After Manager',required=True,
                     available_offset_days=-30,due_offset_days=7,
                     evidence_spec={'type':'ACTIVITY'}),
            ]
            draft=create_template(actor=users['HR'],key='m4_overdue_browser',
                name='Overdue real elapsed browser qualification',
                tasks=tasks,edges=[
                    {'predecessor':'overdue_orientation','successor':'overdue_successor'},
                    {'predecessor':'manager_recovery_checkin','successor':'hr_after_manager'},
                ])
            published=publish_template(actor=users['HR'],
                template_id=uuid.UUID(draft['id']),revision=1)
            made,_=create_case(actor=users['HR'],
                employee_id=members['EMPLOYEE'].pk,
                template_version_id=uuid.UUID(published['version_id']),
                joining_date=timezone.localdate()+timedelta(days=28),
                owner_ids={'IT':members['IT'].pk,'MANAGER':members['MANAGER'].pk},
                key=uuid.uuid4())
            cid=uuid.UUID(made['case_id'])
            activate_case(actor=users['HR'],case_id=cid,key=uuid.uuid4(),
                expected_version=1)
            task=Task.objects.get(case_id=cid,key='overdue_orientation')
            assert task.due_at<timezone.now()
            assert Task.objects.get(case_id=cid,
                key='overdue_successor').execution_state=='BLOCKED'
            assert Task.objects.get(case_id=cid,
                key='manager_recovery_checkin').execution_state=='READY'
            assert Task.objects.get(case_id=cid,
                key='hr_after_manager').execution_state=='BLOCKED'
        self.stdout.write('CASE '+str(cid))
        for role in roles:
            self.stdout.write(role+' '+users[role].email+' '+credentials[role])
