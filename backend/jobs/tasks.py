"""The crash switch exists only to qualify the M0 recovery contract."""
import os
from procrastinate.contrib.django import app

@app.task(name="m0.foundation_process", queue="control")
def process_foundation_operation(operation_id: str):
    from backend.foundation.services import apply_operation
    crash_now = apply_operation(operation_id)
    if crash_now:
        # An intentional hard exit AFTER DB commit and BEFORE Procrastinate ACK.
        # Used only on isolated M0 test fixtures; no public endpoint accepts it.
        os._exit(77)

class RetriableDocumentScan(RuntimeError):
    """Transient scanner or clean-object promotion needs bounded retry."""


def require_completed_scan_result(result):
    """Do not ACK a persisted scanner failure as a successful queue job."""
    state=result.get('state') if isinstance(result,dict) else None
    if state in ('SCAN_FAILED','PROMOTION_PENDING') or state not in (
            'AWAITING_HR_REVIEW','REJECTED_SECURITY'):
        raise RetriableDocumentScan(state or 'INVALID_SCAN_STATE')


from procrastinate import RetryStrategy

@app.task(name="m3.secure_document_scan",queue="content",
          retry=RetryStrategy(max_attempts=3,wait=30,
                              retry_exceptions={RetriableDocumentScan}))
def scan_secure_document(upload_id: str):
    from backend.documents.real_commands import scan_one
    result=scan_one(upload_id)
    # CI-only hard exit AFTER persisted clean evidence, BEFORE job ACK.
    # No client-supplied field can activate this isolated recovery probe.
    if (os.environ.get('M3_CI_CRASH_AFTER_SCAN')=='1'
            and result.get('state')=='AWAITING_HR_REVIEW'):
        os._exit(77)
    require_completed_scan_result(result)


@app.task(name="m5.reconcile_current_reminders",queue="control")
def reconcile_current_reminders(after: str = ''):
    """Repeatable bounded control job. Not a promise of periodic scheduling."""
    from backend.notifications.services import reconcile_batch
    result=reconcile_batch(after=after or None,limit=100)
    if result['next_cursor']:
        from backend.jobs.atomic import defer_atomic
        from django.db import transaction
        with transaction.atomic():
            defer_atomic(reconcile_current_reminders,after=result['next_cursor'])


@app.periodic(cron="* * * * *")
@app.task(name="m5.reconcile_reminders_periodic",queue="control",
          queueing_lock="m5_reconcile_periodic_singleton")
def reconcile_reminders_periodic(timestamp: int):
    """Worker-scheduled wake: current-state catch-up, no historical tick replay.

    PostgreSQL-backed Procrastinate periodic identity prevents multiple workers
    from deferring the same minute; the queue lock prevents overlap. A worker
    must be running; this is NOT external email delivery or a hosted SLA.
    """
    from backend.notifications.services import reconcile_batch
    from django.utils import timezone
    # Deliberately use actual time rather than timestamp from a delayed tick.
    result=reconcile_batch(now=timezone.now(),limit=100)
    if result['next_cursor']:
        from backend.jobs.atomic import defer_atomic
        from django.db import transaction
        with transaction.atomic():
            defer_atomic(reconcile_current_reminders,after=result['next_cursor'])
