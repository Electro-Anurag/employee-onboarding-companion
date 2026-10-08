"""Real PostgreSQL, separate connections. Never replace this with SQLite/mocks."""
import uuid
import pytest
from django.db import connection
from backend.foundation.models import FoundationOperation, FoundationAudit, FoundationEffect
from backend.foundation.services import create_operation, apply_operation, ProbeRollback
from backend.jobs.atomic import AtomicDeferralRequired, defer_atomic
from backend.jobs.tasks import process_foundation_operation

pytestmark = pytest.mark.django_db(transaction=True)


def _queued(job_id):
    with connection.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM procrastinate_jobs WHERE id = %s", [job_id])
        return cursor.fetchone()[0]


def test_atomic_commit_visible_to_other_connection():
    op_id, job_id = create_operation("commit")
    assert FoundationOperation.objects.get(pk=op_id).status == "CREATED"
    assert FoundationAudit.objects.filter(operation_id=op_id, event="CREATED").count() == 1
    assert _queued(job_id) == 1
    # Close and open a new connection; this cannot observe uncommitted writes.
    connection.close()
    assert FoundationOperation.objects.filter(pk=op_id).exists()
    assert _queued(job_id) == 1


def test_atomic_rollback_removes_every_part():
    op_id = uuid.uuid4()
    with pytest.raises(ProbeRollback):
        create_operation("rollback", command_id=op_id, rollback_after_defer=True)
    connection.close()
    assert not FoundationOperation.objects.filter(pk=op_id).exists()
    assert not FoundationAudit.objects.filter(operation_id=op_id).exists()
    with connection.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM procrastinate_jobs WHERE args->>'operation_id' = %s", [str(op_id)])
        assert cursor.fetchone()[0] == 0


def test_no_nonatomic_enqueue_fallback():
    with pytest.raises(AtomicDeferralRequired):
        defer_atomic(process_foundation_operation, operation_id=str(uuid.uuid4()))


def test_idempotent_effect_on_duplicate_delivery():
    op_id, _ = create_operation("replay")
    assert apply_operation(str(op_id)) is False  # first normal invocation returns crash flag only
    assert apply_operation(str(op_id)) is False
    assert FoundationEffect.objects.filter(operation_id=op_id).count() == 1
    assert FoundationAudit.objects.filter(operation_id=op_id, event="APPLIED").count() == 1
    assert FoundationOperation.objects.get(pk=op_id).status == "APPLIED"
