"""M0 transactional enqueue using Procrastinate's supported sync psycopg connector.

The Django connector drives the worker and migrations, but *does not* support
external connections. The separate sync connector is enqueue-only; task names
are shared with the Django worker registry, not Python callback instances.
"""
from django.db import connection
from procrastinate import App, SyncPsycopgConnector

class AtomicDeferralRequired(RuntimeError):
    pass

# Enqueue-only registry. No external network connection should be needed: the
# connector receives Django's already-open psycopg connection on each defer.
_enqueue_app = App(connector=SyncPsycopgConnector())

@_enqueue_app.task(name="m0.foundation_process", queue="control")
def _foundation_queue_contract(operation_id: str):
    raise RuntimeError("Enqueue-only task definition must never execute in a worker")

@_enqueue_app.task(name="m3.secure_document_scan", queue="content")
def _secure_document_scan_queue_contract(upload_id: str):
    raise RuntimeError("Enqueue-only scan task must never execute in a worker")


@_enqueue_app.task(name="m5.reconcile_current_reminders",queue="control")
def _m5_reconcile_queue_contract(after: str = ''):
    raise RuntimeError("Enqueue-only M5 task definition must never run in a worker")


_ALLOWED = {
    "m0.foundation_process": _foundation_queue_contract,
    "m3.secure_document_scan": _secure_document_scan_queue_contract,
    "m5.reconcile_current_reminders": _m5_reconcile_queue_contract,
}


def defer_atomic(task, **kwargs) -> int:
    """Insert Procrastinate job in exactly the caller's Django DB transaction."""
    if not connection.in_atomic_block:
        raise AtomicDeferralRequired("defer_atomic requires transaction.atomic()")
    connection.ensure_connection()
    raw = connection.connection
    if raw is None or raw.__class__.__module__.split(".")[0] != "psycopg":
        raise AtomicDeferralRequired("Expected Django PostgreSQL psycopg3 connection")
    task_name = task.name
    if task_name not in _ALLOWED:
        raise AtomicDeferralRequired(f"Unregistered transactional task: {task_name}")
    # Never fall back to DjangoConnector.defer or transaction.on_commit() here.
    return _ALLOWED[task_name].configure(connection=raw).defer(**kwargs)
