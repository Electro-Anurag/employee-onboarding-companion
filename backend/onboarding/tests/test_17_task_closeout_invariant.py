"""Full default 17-task closeout invariant over the real database.

This protects the real template from an accidental "ready" shortcut.
It deliberately does NOT claim that a complete 17-task journey passed;
that is a separate, still-open end-to-end acceptance gate.
"""
import uuid

import pytest

from backend.audit.models import AuditEvent
from backend.onboarding.closeout import closeout_case, preview_closeout
from backend.onboarding.commands import activate_case, attest_manager
from backend.onboarding.models import OnboardingCase, Task, TaskCompletion
from backend.onboarding.services import CommandFailure
from backend.onboarding.tests.test_m2_workflow import create, published, world


@pytest.mark.django_db(transaction=True)
def test_all_17_real_mandatory_tasks_remain_necessary_for_hr_closeout(world):
    _, people = world
    created, _ = create(world, published(world), offset=-1)
    case = OnboardingCase.objects.get(pk=created["case_id"])
    hr = people["HR"][0]
    activate_case(actor=hr, case_id=case.pk, key=uuid.uuid4(), expected_version=1)
    case.refresh_from_db()
    assert case.status == "ACTIVE"
    assert Task.objects.filter(case=case).count() == 17

    before = preview_closeout(hr, case.pk)
    assert before["mandatory_total"] == 17
    assert before["mandatory_completed"] == 0
    assert before["ready"] is False
    assert before["reason_codes"] == ["CLOSEOUT_MANDATORY_INCOMPLETE"]
    assert len(before["missing_tasks"]) == 17
    assert TaskCompletion.objects.filter(task__case=case).count() == 0

    with pytest.raises(CommandFailure) as denied:
        closeout_case(actor=hr, case_id=case.pk,
                      key=uuid.uuid4(), expected_version=case.version)
    assert denied.value.code == "CLOSEOUT_MANDATORY_INCOMPLETE"
    assert not AuditEvent.objects.filter(event_type="CASE_CLOSED").exists()

    with pytest.raises(CommandFailure):
        preview_closeout(people["EMPLOYEE"][0], case.pk)
    with pytest.raises(CommandFailure):
        preview_closeout(people["MANAGER"][0], case.pk)

    manager_task = Task.objects.get(case=case, key="manager_preparation")
    attest_manager(
        actor=people["MANAGER"][0], case_id=case.pk, task_id=manager_task.pk,
        fields={
            "first_week_plan": "Pair on synthetic first-week projects",
            "buddy_name": "Synthetic Buddy",
            "workstation_ready": True,
        },
        note="Typed manager evidence",
        key=uuid.uuid4(), expected_version=case.version,
    )
    case.refresh_from_db()
    after = preview_closeout(hr, case.pk)
    assert after["mandatory_total"] == 17
    assert after["mandatory_completed"] == 1
    assert len(after["missing_tasks"]) == 16
    assert all(row["task_id"] != str(manager_task.pk)
               for row in after["missing_tasks"])
    assert after["ready"] is False
    assert "CLOSEOUT_MANDATORY_INCOMPLETE" in after["reason_codes"]
    assert TaskCompletion.objects.filter(task__case=case).count() == 1

    introduction = Task.objects.get(case=case, key="team_introduction")
    workspace_access = Task.objects.get(case=case, key="workspace_access")
    assert introduction.execution_state in ("READY", "NOT_STARTED")
    assert workspace_access.execution_state == "BLOCKED"

    with pytest.raises(CommandFailure) as still_denied:
        closeout_case(actor=hr, case_id=case.pk,
                      key=uuid.uuid4(), expected_version=case.version)
    assert still_denied.value.code == "CLOSEOUT_MANDATORY_INCOMPLETE"
    case.refresh_from_db()
    assert case.status == "ACTIVE"
    assert case.completed_at is None
    assert AuditEvent.objects.filter(event_type="CASE_CLOSED").count() == 0
