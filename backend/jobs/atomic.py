"""Only permitted M0 enqueue path: same psycopg connection as Django transaction."""
from django.db import connection, transaction

class AtomicDeferralRequired(RuntimeError):
    pass


def defer_atomic(task, **kwargs) -> int:
    """Enqueue within the enclosing transaction; caller owns commit/rollback.

    Intentionally never falls back to Task.defer() / on_commit(): both would
    split domain state and queued work across transaction boundaries.
    """
    if not connection.in_atomic_block:
        raise AtomicDeferralRequired("defer_atomic requires transaction.atomic()")
    connection.ensure_connection()
    raw = connection.connection
    if raw is None or raw.__class__.__module__.split(".")[0] != "psycopg":
        raise AtomicDeferralRequired("Expected Django PostgreSQL psycopg3 connection")
    return task.configure(connection=raw).defer(**kwargs)
