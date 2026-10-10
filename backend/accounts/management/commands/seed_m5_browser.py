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
            # Separate real HR-only owner recovery. It must not invalidate
            # the existing Manager/HR prerequisite journey.
            original_manager=User.objects.create_user(
                email='unavailable.manager@synthetic.invalid',
                password=secrets.token_urlsafe(20)+'Ab1!',
                display_name='M5 Unavailable Manager')
            original_member=Membership.objects.create(
                user=original_manager,organization=org,role='MANAGER')
            new_password=secrets.token_urlsafe(20)+'Ab1!'
            new_manager=User.objects.create_user(
                email='replacement.manager@synthetic.invalid',
                password=new_password,display_name='M5 Available Replacement')
            Membership.objects.create(user=new_manager,organization=org,role='MANAGER')
            second_employee=User.objects.create_user(
                email='recovery.employee@synthetic.invalid',
                password=secrets.token_urlsafe(20)+'Ab1!',
                display_name='M5 Recovery Employee')
            second_root=Membership.objects.create(user=second_employee,
                organization=org,role='EMPLOYEE')
            recovery,_=create_case(actor=users['HR'],employee_id=second_root.pk,
                template_version_id=uuid.UUID(published['version_id']),
                joining_date=timezone.localdate()+timedelta(days=3),
                owner_ids={'IT':members['IT'].pk,'MANAGER':original_member.pk},
                key=uuid.uuid4())
            recovery_id=uuid.UUID(recovery['case_id'])
            activate_case(actor=users['HR'],case_id=recovery_id,
                key=uuid.uuid4(),expected_version=1)
            original_member.available=False
            original_member.save(update_fields=['available'])

            # Independent HR↔employee review handoff case. It has no effect
            # on the two established manager/exception scenarios.
            handoff_password=secrets.token_urlsafe(20)+'Ab1!'
            handoff_employee=User.objects.create_user(
                email='handoff.employee@synthetic.invalid',
                password=handoff_password,display_name='M5 Handoff Employee')
            handoff_member=Membership.objects.create(user=handoff_employee,
                organization=org,role='EMPLOYEE')
            handoff_tasks=[dict(key='personal_details',kind='FORM',
                owner_role='EMPLOYEE',title='M5 Personal Details',
                required=True,available_offset_days=-10,due_offset_days=5,
                evidence_spec={'type':'FORM',
                               'fields':['preferred_name','contact_email']})]
            handoff_draft=create_template(actor=users['HR'],key='m5_review_handoff',
                name='M5 Real Form Handoff',tasks=handoff_tasks,edges=[])
            handoff_published=publish_template(actor=users['HR'],
                template_id=uuid.UUID(handoff_draft['id']),revision=1)
            handoff_case,_=create_case(actor=users['HR'],employee_id=handoff_member.pk,
                template_version_id=uuid.UUID(handoff_published['version_id']),
                joining_date=timezone.localdate()+timedelta(days=3),
                owner_ids={'IT':members['IT'].pk,'MANAGER':members['MANAGER'].pk},
                key=uuid.uuid4())
            handoff_case_id=uuid.UUID(handoff_case['case_id'])
            activate_case(actor=users['HR'],case_id=handoff_case_id,
                key=uuid.uuid4(),expected_version=1)
            assert Task.objects.get(case_id=handoff_case_id,
                key='personal_details').execution_state=='READY'
        self.stdout.write('HANDOFF_CASE '+str(handoff_case_id))
        self.stdout.write('HANDOFF_EMPLOYEE '+handoff_employee.email+' '+handoff_password)
        self.stdout.write('RECOVERY_CASE '+str(recovery_id))
        self.stdout.write('RECOVERY_MANAGER '+new_manager.email+' '+new_password)
        self.stdout.write('CASE '+str(case_id))
        for role in roles:
            self.stdout.write(role+' '+users[role].email+' '+secrets_by_role[role])
