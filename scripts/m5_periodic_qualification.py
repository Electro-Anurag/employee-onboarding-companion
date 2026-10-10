"""Isolated CI-only periodic Procrastinate worker truth qualification.

This is synthetic test-data creation and read-only verification, never a
production maintenance/bypass command. No clock manipulation or direct
notification insertion substitutes for the actual worker.
"""
import os
import sys
import uuid
from datetime import timedelta

if os.environ.get('M5_CI_PERIODIC_PROBE')!='1':
    raise SystemExit('CI periodic qualification switch required')
os.environ.setdefault('DJANGO_SETTINGS_MODULE','backend.config.settings')
import django
django.setup()
from django.conf import settings
from django.utils import timezone
from backend.accounts.models import User,Membership
from backend.onboarding.models import OnboardingCase,Task
from backend.onboarding.commands import create_case,activate_case
from backend.notifications.models import Notification
from backend.onboarding.state_machine import preview_task_state

if not settings.DEBUG or len(sys.argv) not in (2,3):
    raise SystemExit('Only synthetic DEBUG CI seed/check modes are supported')

mode=sys.argv[1]
if mode=='seed' and len(sys.argv)==2:
    original=OnboardingCase.objects.select_related('organization').get(
        employee__user__email='employee@m5-browser.invalid')
    org=original.organization
    hr=User.objects.get(email='hr@m5-browser.invalid')
    it=Membership.objects.get(user__email='it@m5-browser.invalid')
    manager=Membership.objects.get(user__email='manager@m5-browser.invalid')
    employee=User.objects.create_user(email='m5-periodic-only@synthetic.invalid',
        password='CI-Synthetic-Long-Password!2026',display_name='Synthetic Overdue Employee')
    member=Membership.objects.create(user=employee,organization=org,role='EMPLOYEE')
    made,_=create_case(actor=hr,employee_id=member.pk,
        template_version_id=original.template_version_id,
        joining_date=timezone.localdate()-timedelta(days=7),
        owner_ids={'IT':it.pk,'MANAGER':manager.pk},key=uuid.uuid4())
    cid=uuid.UUID(made['case_id'])
    activate_case(actor=hr,case_id=cid,key=uuid.uuid4(),expected_version=1)
    task=Task.objects.get(case_id=cid,key='m5_manager_preparation')
    assert task.due_at<timezone.now()
    assert preview_task_state(task,task.case)[0]=='READY'
    assert not Notification.objects.filter(case_id=cid).exists()
    print(cid)
elif mode=='check' and len(sys.argv)==3:
    cid=uuid.UUID(sys.argv[2])
    task=Task.objects.get(case_id=cid,key='m5_manager_preparation')
    qs=Notification.objects.filter(case_id=cid,task=task,
        recipient__email='manager@m5-browser.invalid',
        intent__rule_code='OVERDUE_DAILY',status='ACTIVE')
    if qs.count()!=1:
        raise SystemExit(1)
    notice=qs.get()
    assert notice.intent.status=='DELIVERED'
    assert notice.intent.time_bucket==timezone.localdate(
        timezone=__import__('zoneinfo').ZoneInfo(task.case.organization.timezone)).isoformat()
    print('M5_REAL_PERIODIC_WORKER_REMINDER_PASS',notice.pk)
else:
    raise SystemExit('Invalid CI periodic probe mode')
