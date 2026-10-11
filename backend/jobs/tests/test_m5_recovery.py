"""M5 periodic stalled-job recovery is bounded and allowlisted."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from backend.jobs.recovery import retry_stalled_m5


def test_only_reminder_jobs_retried_and_bounded():
    jobs = [
        SimpleNamespace(task_name="m3.secure_document_scan", id=1),
        SimpleNamespace(task_name="m5.reconcile_current_reminders", id=2),
        SimpleNamespace(task_name="m0.foundation_process", id=3),
        SimpleNamespace(task_name="m5.reconcile_reminders_periodic", id=4),
        SimpleNamespace(task_name="m5.retry_stalled_control", id=5),
        SimpleNamespace(task_name="m5.reconcile_current_reminders", id=6),
    ]
    manager = SimpleNamespace(get_stalled_jobs=AsyncMock(return_value=jobs),
                              retry_job=AsyncMock())
    result = asyncio.run(retry_stalled_m5(manager, limit=2))
    assert result == {"recovered": 2, "unrelated_skipped": 3}
    assert [c.args[0].id for c in manager.retry_job.call_args_list] == [2, 4]
    manager.get_stalled_jobs.assert_awaited_once_with(seconds_since_heartbeat=120)


def test_no_unbounded_heartbeat_window_or_batch():
    for opts in ({"limit": 0}, {"limit": 101}, {"limit": True},
                 {"stale_seconds": 0}, {"stale_seconds": 29},
                 {"stale_seconds": True}):
        with pytest.raises(ValueError, match="INVALID_M5_RECOVERY_BOUNDS"):
            asyncio.run(retry_stalled_m5(object(), **opts))
