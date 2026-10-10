"""M7 minimal, evidence-gated HR closeout for hosted J01.

All mandatory applicable task completions and all exceptional episodes must
be resolved and HR-closed first. No waiver, bulk completion or bypass exists.
"""
import hashlib
import json
import uuid
from django.db import transaction
from django.utils import timezone
from backend.accounts.models import Membership
from backend.audit.services import append_event
from backend.onboarding.commands import _command_case, _receipt
from backend.onboarding.models import Task, TaskCompletion, CaseException
from backend.onboarding.services import CommandFailure, set_command_timeouts
from backend.onboarding.state_machine import case_progress


def closeout_case(*, actor, case_id, key, expected_version):
    with transaction.atomic():
        set_command_timeouts()
        case, member, prior, digest = _command_case(
            actor, case_id, "m7-closeout", key, {}, expected_version, True
        )
        if prior is not None:
            return prior.response, prior.status_code
        if member.role != Membership.HR or not member.available:
            raise CommandFailure("NOT_FOUND", 404)
        if case.status != "ACTIVE":
            raise CommandFailure("CLOSEOUT_REQUIRES_ACTIVE_CASE", 409)
        tasks = list(Task.objects.select_for_update().filter(case=case).order_by("key"))
        if not tasks or len(tasks) > 60:
            raise CommandFailure("CLOSEOUT_TASK_COUNT_INVALID", 409)
        required = [task for task in tasks if task.required and task.applicable]
        if not required:
            raise CommandFailure("CLOSEOUT_NO_MANDATORY_WORK", 409)
        completed = {
            row["task_id"]: row["evidence_type"]
            for row in TaskCompletion.objects.filter(
                task__case=case, task__required=True, task__applicable=True
            ).values("task_id", "evidence_type")
        }
        missing = [task for task in required
                   if task.execution_state != "COMPLETED" or task.pk not in completed]
        if missing:
            raise CommandFailure("CLOSEOUT_MANDATORY_INCOMPLETE", 409)
        if CaseException.objects.filter(
                case=case, status__in=("OPEN", "ASSIGNED", "RESOLVED")).exists():
            raise CommandFailure("CLOSEOUT_EXCEPTION_NOT_CLOSED", 409)
        evidence = [{
            "task_id": str(task.pk), "evidence_type": completed[task.pk]
        } for task in required]
        manifest = json.dumps(evidence, sort_keys=True, separators=(",", ":"))
        snapshot = {
            "mandatory_completed": len(evidence),
            "evidence_manifest_sha256": hashlib.sha256(manifest.encode()).hexdigest(),
            "case_version_before_closeout": case.version,
        }
        now = timezone.now()
        case.status = "COMPLETED"
        case.completed_at = now
        case.closeout_snapshot = snapshot
        case.version += 1
        case.save(update_fields=[
            "status", "completed_at", "closeout_snapshot", "version"
        ])
        event = append_event(
            stream_key=f"case:{case.pk}", actor=actor, event_type="CASE_CLOSED",
            entity_id=case.pk, changes={
                **snapshot, "case_version": case.version,
                "completed_at": now.isoformat(),
            },
        )
        response = {
            "command_id": str(uuid.uuid4()), "case_id": str(case.pk),
            "case_version": case.version,
            "result": {
                "status": "COMPLETED", "completed_at": now.isoformat(),
                "progress": case_progress(case),
                "evidence_manifest_sha256": snapshot["evidence_manifest_sha256"],
            },
            "affected_task_ids": [],
            "event_ids": [str(event[0])],
        }
        _receipt(actor, "m7-closeout", key, digest, case, response)
    return response, 200
