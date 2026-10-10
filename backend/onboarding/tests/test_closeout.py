"""J01 closeout qualification: actual typed manager evidence, HR-only and replay."""
from datetime import timedelta
import uuid
import pytest
from django.utils import timezone
from backend.audit.models import AuditEvent
from backend.onboarding.commands import create_case, activate_case, start_task, attest_manager
from backend.onboarding.closeout import closeout_case
from backend.onboarding.models import OnboardingCase, Task
from backend.onboarding.services import CommandFailure
from backend.onboarding.tests.test_m2_workflow import world
from backend.templates.services import create_template, publish_template


@pytest.mark.django_db(transaction=True)
def test_closeout_refuses_missing_evidence_then_completes_exactly_once(world):
    _, users = world
    draft = create_template(
        actor=users['HR'][0], key='synthetic_closeout',
        name='Typed Closeout Demonstration',
        tasks=[{
            'key': 'manager_preparation',
            'kind': 'MANAGER_PREPARATION',
            'owner_role': 'MANAGER', 'title': 'Manager preparation',
            'required': True, 'available_offset_days': -15,
            'due_offset_days': 7,
            'evidence_spec': {'type': 'MANAGER_PREPARATION'},
        }], edges=[],
    )
    published = publish_template(
        actor=users['HR'][0],
        template_id=uuid.UUID(draft['id']), revision=1
    )
    made, _ = create_case(
        actor=users['HR'][0],
        employee_id=users['EMPLOYEE'][1].pk,
        template_version_id=uuid.UUID(published['version_id']),
        joining_date=timezone.localdate() - timedelta(days=1),
        owner_ids={'IT': users['IT'][1].pk,
                   'MANAGER': users['MANAGER'][1].pk},
        key=uuid.uuid4(),
    )
    case = OnboardingCase.objects.get(pk=made['case_id'])
    activate_case(actor=users['HR'][0], case_id=case.pk,
                  key=uuid.uuid4(), expected_version=1)
    case.refresh_from_db()
    assert case.status == 'ACTIVE'
    t = Task.objects.get(case=case, key='manager_preparation')
    assert t.execution_state == 'READY'
    with pytest.raises(CommandFailure, match='CLOSEOUT_MANDATORY_INCOMPLETE'):
        closeout_case(actor=users['HR'][0], case_id=case.pk,
                      key=uuid.uuid4(), expected_version=2)
    with pytest.raises(CommandFailure):
        closeout_case(actor=users['EMPLOYEE'][0], case_id=case.pk,
                      key=uuid.uuid4(), expected_version=2)
    assert not AuditEvent.objects.filter(event_type='CASE_CLOSED').exists()
    start_task(actor=users['MANAGER'][0], case_id=case.pk,
               task_id=t.pk, key=uuid.uuid4(), expected_version=2)
    attest_manager(
        actor=users['MANAGER'][0], case_id=case.pk, task_id=t.pk,
        fields={
            'first_week_plan': 'Pair and deliver synthetic onboarding',
            'buddy_name': 'Synthetic Buddy', 'workstation_ready': True,
        },
        note='Manager preparations are complete',
        key=uuid.uuid4(), expected_version=3,
    )
    key = uuid.uuid4()
    closed, code = closeout_case(
        actor=users['HR'][0], case_id=case.pk, key=key, expected_version=4
    )
    assert code == 200 and closed['result']['status'] == 'COMPLETED'
    assert closed['result']['progress']['mandatory_remaining'] == 0
    assert len(closed['result']['evidence_manifest_sha256']) == 64
    case.refresh_from_db()
    assert case.status == 'COMPLETED' and case.completed_at is not None
    assert case.closeout_snapshot['mandatory_completed'] == 1
    replay, replay_code = closeout_case(
        actor=users['HR'][0], case_id=case.pk, key=key, expected_version=4
    )
    assert replay_code == 200 and replay == closed
    assert AuditEvent.objects.filter(event_type='CASE_CLOSED').count() == 1
    with pytest.raises(CommandFailure):
        closeout_case(actor=users['HR'][0], case_id=case.pk,
                      key=uuid.uuid4(), expected_version=case.version)
