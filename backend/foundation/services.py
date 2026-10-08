"""Deliberately narrow M0 proof command and idempotent result service."""
import uuid
from django.db import transaction
from django.utils import timezone
from backend.foundation.models import FoundationOperation, FoundationAudit, FoundationEffect
from backend.jobs.atomic import defer_atomic

class ProbeRollback(Exception):
    """Test-only controlled rollback after queuing, before commit."""


def create_operation(label: str, *, command_id: uuid.UUID | None = None,
                     rollback_after_defer: bool = False, crash_after_apply_once: bool = False):
    if not label or len(label) > 128:
        raise ValueError("Invalid probe label")
    command_id = command_id or uuid.uuid4()
    from backend.jobs.tasks import process_foundation_operation
    with transaction.atomic():
        obj = FoundationOperation.objects.create(
            id=command_id, label=label, crash_after_apply_once=crash_after_apply_once,
        )
        FoundationAudit.objects.create(operation=obj, event="CREATED")
        job_id = defer_atomic(process_foundation_operation, operation_id=str(obj.id))
        if rollback_after_defer:
            raise ProbeRollback("Rollback after business, audit and queue writes")
    return obj.id, job_id


def apply_operation(operation_id: str) -> bool:
    """Idempotent effect; hard-killed workers may replay this function."""
    with transaction.atomic():
        obj = FoundationOperation.objects.select_for_update().get(pk=operation_id)
        if obj.status == "APPLIED":
            return False
        FoundationEffect.objects.create(operation=obj)
        FoundationAudit.objects.create(operation=obj, event="APPLIED")
        obj.status = "APPLIED"
        obj.applied_at = timezone.now()
        was_first_crash = obj.crash_after_apply_once and not obj.crash_fired
        if was_first_crash:
            obj.crash_fired = True
        obj.save(update_fields=["status", "applied_at", "crash_fired"])
    return was_first_crash
