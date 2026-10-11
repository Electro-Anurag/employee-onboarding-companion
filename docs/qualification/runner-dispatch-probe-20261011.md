# Runner assignment probe — 11 October 2026

Run exactly once on commit introducing `.github/workflows/eoc-runner-assignment-probe.yml`. This is an isolated scheduling diagnosis because the original registered Linux ARM64 runner reported online/idle and "Listening for Jobs" at 2026-10-11T15:22:27Z, while pre-reconnect application runs remained unassigned. NTP and GitHub UTC time were in agreement. The probe has no checkout, no secrets, no dependencies, no external services and no product state access; it tests **only job assignment and minimal shell execution**, never application readiness. Its inclusion must not be used as a substitute for M6/M7/Chromium full qualification.

* If probe starts or succeeds and historical runs stay queued: scheduling of older jobs is likely stale; prefer a new **current-HEAD** integrated run after confirming exact source and canceling obsolete pending runs intentionally.
* If probe remains queued while runner is online/idle: investigate GitHub Actions scheduling, per-job runner assignment and broker connectivity through GitHub, do not churn registration or alter task tests.
* If job starts but fails: use exact logged runner failure; do not alter application code to mask it.

Production STOP and J01–J05 0/5 are unchanged.
