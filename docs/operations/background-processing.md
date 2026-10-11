# M5 dedicated control worker and recovery

**Implementation proposal only. No live worker was deployed, no paid service was enabled.**

Existing Procrastinate one-minute periodic wake reconciles current case state (not historical clock ticks), max 100 cases per batch, transactionally enqueues cursor continuation and enforces current-owner reminder identities and 48-hour HR escalation. Existing current-visibility filters hide obsolete notices after task/owner changes.

New periodic task m5.retry_stalled_control runs once per five minutes while a worker is alive. It queries Procrastinate heartbeat state (120-second stale threshold) and retries only two M5 reconciliation task names, at most 64 per sweep; it never retries M3 scan, M0 foundation, or its own sweep. Durable case locks and unique reminder identities make a committed-before-ACK retry idempotent. Without a running worker, neither reminders nor recovery execute.

Dedicated entrypoint backend/start_control_worker.sh refuses absent EOC_RUN_CONTROL_WORKER=1, DEBUG mode, missing private database URL, or enabled one-time demo control flags. It checks the application and queue schema then execs the control queue worker. The proposed render.full.yaml worker is paid Starter and remains DISABLED/unapplied without explicit owner approval. render.yaml / render.evaluation.yaml Free web and existing Render deployment are unchanged.

Qualification sequence: focused source/unit PostgreSQL CI, real separate-process crash after durable reminder insertion but before job ACK, heartbeat stall recovery, second worker successful ACK and no duplicate, persistent-clock and multi-worker behavior, then optionally an authorized hosted dedicated worker. Current owner approval covers source development, not paid compute or provider cost. Do not claim hosted J03 PASS from CI.

Added an isolated real PostgreSQL subprocess worker crash test. It kills the first worker after durable reminder commit and before its queue ACK, waits for the heartbeat stale threshold, requeues only allowlisted M5 work, starts a second worker and verifies a single active notification. This remains local CI evidence, not hosted always-on worker evidence.

The isolated real-worker qualification also keeps the recovered worker running through a real wall-clock one-minute cron boundary and confirms that m5.reconcile_reminders_periodic reaches succeeded in PostgreSQL without any manual deferral. This is genuine local scheduler evidence, not hosted uptime or delivery SLA.
