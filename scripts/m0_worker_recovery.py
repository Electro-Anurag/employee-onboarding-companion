"""M0 only: kill a real Procrastinate worker post-commit; recover its stalled job.

Run only in isolated test DB with the worker queue otherwise empty. This is not a
production or application endpoint, and the recovery threshold is accelerated
for a CI exercise rather than recommended for real operational use.
"""
import asyncio
import os
import subprocess
import sys
import time

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.config.settings")
import django
django.setup()
from django.db import connection
from backend.foundation.services import create_operation
from backend.foundation.models import FoundationAudit, FoundationEffect, FoundationOperation
from procrastinate.contrib.django import app


def job_status(job_id):
    with connection.cursor() as cursor:
        cursor.execute("SELECT status FROM procrastinate_jobs WHERE id = %s", [job_id])
        row = cursor.fetchone()
        return row[0] if row else None


def start_worker():
    return subprocess.Popen(
        [sys.executable, "manage.py", "procrastinate", "worker"],
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
    )


async def retry_stalled(job_id):
    async with app.open_async():
        stalled = await app.job_manager.get_stalled_jobs(seconds_since_heartbeat=2)
        matching = [job for job in stalled if job.id == job_id and job.task_name == "m0.foundation_process"]
        assert len(matching) == 1, f"Expected one stalled M0 job; observed {len(matching)}"
        await app.job_manager.retry_job(matching[0])


def check_applied_once(op_id):
    assert FoundationOperation.objects.get(pk=op_id).status == "APPLIED"
    assert FoundationEffect.objects.filter(operation_id=op_id).count() == 1
    assert FoundationAudit.objects.filter(operation_id=op_id, event="APPLIED").count() == 1


def main():
    op_id, job_id = create_operation("crash-after-commit", crash_after_apply_once=True)
    first = start_worker()
    try:
        first.wait(timeout=25)
        assert first.returncode == 77, f"Expected hard crash 77, got {first.returncode}; stderr={first.stderr.read()[:800]!r}"
    finally:
        if first.poll() is None:
            first.kill()
            first.wait()
    connection.close()
    check_applied_once(op_id)
    assert job_status(job_id) == "doing", f"Job not stalled: {job_status(job_id)}"
    time.sleep(3)
    asyncio.run(retry_stalled(job_id))
    assert job_status(job_id) == "todo", f"Job not requeued: {job_status(job_id)}"
    second = start_worker()
    try:
        deadline = time.monotonic() + 25
        while time.monotonic() < deadline:
            connection.close()
            if job_status(job_id) == "succeeded":
                break
            if second.poll() is not None:
                raise AssertionError(f"Recovery worker exited unexpectedly: {second.returncode}; stderr={second.stderr.read()[:800]!r}")
            time.sleep(.3)
        assert job_status(job_id) == "succeeded", f"Job not completed after replay: {job_status(job_id)}"
    finally:
        if second.poll() is None:
            second.terminate()
            try: second.wait(timeout=5)
            except subprocess.TimeoutExpired:
                second.kill(); second.wait()
    check_applied_once(op_id)
    print("PASS: real worker hard exit, stale-job retry, single committed effect/audit")


if __name__ == "__main__":
    main()
