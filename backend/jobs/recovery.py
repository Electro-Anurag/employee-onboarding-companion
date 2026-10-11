"""Bounded recovery of genuinely stalled M5 control work.

Procrastinate heartbeat checks identify abandoned 'doing' jobs. Only existing
reminder reconciliation jobs are retried, never content scanning, foundation
crash probes, arbitrary commands, or the recovery sweep itself.
"""
RECOVERABLE = frozenset({
    "m5.reconcile_current_reminders",
    "m5.reconcile_reminders_periodic",
})


async def retry_stalled_m5(job_manager, *, stale_seconds=120, limit=64):
    """No job args, IDs, personal data or credential material are logged."""
    if (type(stale_seconds) is not int or stale_seconds < 30
            or type(limit) is not int or not 1 <= limit <= 100):
        raise ValueError("INVALID_M5_RECOVERY_BOUNDS")
    stalled = await job_manager.get_stalled_jobs(
        seconds_since_heartbeat=stale_seconds
    )
    recovered = 0
    unrelated = 0
    for job in stalled:
        if job.task_name not in RECOVERABLE:
            unrelated += 1
            continue
        if recovered >= limit:
            break
        await job_manager.retry_job(job)
        recovered += 1
    return {"recovered": recovered, "unrelated_skipped": unrelated}
