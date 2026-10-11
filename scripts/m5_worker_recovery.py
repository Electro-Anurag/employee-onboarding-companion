"""Real PostgreSQL worker kill-after-commit / heartbeat recovery qualification.

Runs only against an isolated localhost CI database with two explicit gates.
Never connects to live Render, never calls external integrations.
"""
import asyncio
import os
import subprocess
import sys
import time
import uuid
from datetime import timedelta
from pathlib import Path

if (os.environ.get("EOC_M5_ISOLATED_RECOVERY_TEST") != "1"
        or os.environ.get("RENDER") == "true"
        or os.environ.get("DATABASE_URL")
        or os.environ.get("POSTGRES_HOST") not in ("localhost", "127.0.0.1")
        or os.environ.get("POSTGRES_DB") != "onboarding_m0"
        or os.environ.get("DJANGO_DEBUG") != "0"):
    raise SystemExit("STOP: M5 crash test requires isolated localhost CI PostgreSQL")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.config.settings")
import django
django.setup()
from django.db import connection, transaction
from django.utils import timezone
from backend.accounts.models import Organization, Membership, User
from backend.templates.services import create_default, publish_template
from backend.onboarding.commands import create_case, activate_case
from backend.onboarding.models import OnboardingCase, Task
from backend.notifications.models import ReminderIntent, Notification
from backend.jobs.tasks import reconcile_current_reminders
from backend.jobs.atomic import defer_atomic
from backend.jobs.recovery import retry_stalled_m5
from procrastinate.contrib.django import app

ROOT = Path(__file__).resolve().parents[1]


def state(job_id):
    connection.close()
    with connection.cursor() as cursor:
        cursor.execute("SELECT status FROM procrastinate_jobs WHERE id=%s", [job_id])
        row = cursor.fetchone()
    return row[0] if row else None


def launch(env):
    return subprocess.Popen(
        [sys.executable, "manage.py", "procrastinate", "worker",
         "--queues", "control"],
        cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
    )


def stop(proc):
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=8)


def synthetic_case():
    org = Organization.objects.create(
        name="Isolated M5 recovery " + uuid.uuid4().hex[:8],
        timezone="Asia/Kolkata")
    actors = {}
    for role in ("HR", "EMPLOYEE", "IT", "MANAGER"):
        user = User.objects.create_user(
            email=f"m5-{role.lower()}-{uuid.uuid4().hex[:8]}@synthetic.invalid",
            password="IsolatedCIWorkerPass!2026", display_name="CI " + role)
        member = Membership.objects.create(
            user=user, organization=org, role=role,
            can_manage_templates=role == "HR",
            can_coordinate_ownership=role == "HR")
        actors[role] = (user, member)
    draft = create_default(actor=actors["HR"][0])
    version = publish_template(
        actor=actors["HR"][0],
        template_id=uuid.UUID(draft["id"]), revision=1)
    created, code = create_case(
        actor=actors["HR"][0],
        employee_id=actors["EMPLOYEE"][1].pk,
        template_version_id=uuid.UUID(version["version_id"]),
        joining_date=timezone.localdate() - timedelta(days=14),
        owner_ids={"IT": actors["IT"][1].pk, "MANAGER": actors["MANAGER"][1].pk},
        key=uuid.uuid4())
    assert code == 201
    case = OnboardingCase.objects.get(pk=created["case_id"])
    _, code = activate_case(actor=actors["HR"][0], case_id=case.pk,
                            key=uuid.uuid4(), expected_version=1)
    assert code == 200
    task = Task.objects.get(case=case, key="manager_preparation")
    assert timezone.now() > task.due_at + timedelta(hours=48)
    return task


async def recover(job_id):
    async with app.open_async():
        result = await retry_stalled_m5(
            app.job_manager, stale_seconds=30)
    assert result["recovered"] >= 1, result


def main():
    task = synthetic_case()
    with transaction.atomic():
        job = defer_atomic(reconcile_current_reminders, after="")
    env = dict(os.environ)
    env["EOC_M5_ISOLATED_RECOVERY_TEST"] = "1"
    env["M5_CI_CRASH_AFTER_RECONCILE"] = "1"
    first = launch(env)
    try:
        first.wait(timeout=45)
        assert first.returncode == 77, (
            f"Crash contract not met: {first.returncode}, "
            f"{first.stderr.read()[:500]!r}")
    finally:
        stop(first)
    assert state(job) == "doing"
    assert ReminderIntent.objects.filter(
        task=task, rule_code="OVERDUE_DAILY", status="DELIVERED").count() == 1
    # The same 30-second minimum is enforced by the implementation.
    time.sleep(33)
    asyncio.run(recover(job))
    assert state(job) == "todo"
    env.pop("M5_CI_CRASH_AFTER_RECONCILE")
    second = launch(env)
    try:
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            if state(job) == "succeeded":
                break
            if second.poll() is not None:
                raise AssertionError(
                    f"Recovery worker exited: {second.returncode}, "
                    f"{second.stderr.read()[:500]!r}")
            time.sleep(.5)
        assert state(job) == "succeeded", state(job)
        print("EOC_M5_REAL_WORKER_CRASH_RECOVERY_PASS", flush=True)
        # Keep the second worker alive across a genuine wall-clock cron tick.
        # This is essential: manually deferring a job does not prove that
        # Procrastinate's periodic scheduler runs automatically.
        deadline = time.monotonic() + 85
        periodic_succeeded = False
        while time.monotonic() < deadline:
            connection.close()
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT COUNT(*) FROM procrastinate_jobs "
                    "WHERE task_name=%s AND status='succeeded'",
                    ["m5.reconcile_reminders_periodic"],
                )
                periodic_succeeded = cursor.fetchone()[0] > 0
            if periodic_succeeded:
                break
            if second.poll() is not None:
                raise AssertionError("Periodic worker terminated unexpectedly")
            time.sleep(.8)
        assert periodic_succeeded, "No real 1-minute M5 periodic job succeeded"
        print("EOC_M5_REAL_PERIODIC_CONTROL_WAKE_PASS", flush=True)
    finally:
        stop(second)
    assert ReminderIntent.objects.filter(
        task=task, rule_code="OVERDUE_DAILY", status="DELIVERED").count() == 1
    assert Notification.objects.filter(
        task=task, intent__rule_code="OVERDUE_DAILY",
        status="ACTIVE").count() == 1
    print("HOSTED_WORKER_UNQUALIFIED_LOCAL_ISOLATED_CI_ONLY")


if __name__ == "__main__":
    main()
