# D6 quiesced PostgreSQL and full MinIO filesystem restoration (synthetic only)

**This is an implementation candidate pending isolated CI, not a production recovery method.**

The qualification uses a disposable PostgreSQL 17 service and a disposable filesystem-backed MinIO, with real ClamAV signature qualification. One synthetic employee sends a generated PDF through the actual prepare, private-quarantine upload, scanner, exact clean-object promotion and HR acceptance code. Both S3 buckets have enabled versioning; PostgreSQL contains the recorded immutable VersionIds, completions, HR review, audit and command receipts.

The test performs a coordinated offline recovery point: **no web process or worker is running**, the MinIO source is stopped, PostgreSQL is dumped, the entire stopped MinIO data filesystem is archived, the archive is extracted to a second directory, and a new MinIO process starts exclusively from that copy. A separate PostgreSQL database is restored from the dump. The check compares a SHA-256 fingerprint of all relevant durable database rows and applied migrations and independently re-reads both exact historical S3 versions and their hashes from the restored MinIO.

Unlike ordinary S3 object CopyObject replication, full filesystem snapshot restoration *may* preserve MinIO's internal identifiers; the exact proof must run before it can be claimed. This is intentionally a **same-engine/same-image, localhost-only** test with disposable synthetic data and cleanup, not a claim of compatibility with a different S3 provider, a new S3 bucket, arbitrary cloud snapshots, or independent asynchronous disaster recovery.

**Never run this workflow against real accounts, populated or hosted databases, shared MinIO services or live employee documents.** Guards in the test program refuse anything outside two allowlisted CI database names, localhost endpoint and explicit workflow environment marker. No credentials or document bytes should enter CI output or artifacts.

Even if this test succeeds, production release needs an authorized durable backup design, isolation/encryption, secret and key restoration, immutable audit security assessment, consistency and retention guarantees, operational RPO/RTO measurements, ClamAV/worker restart, and hosted J01–J05 acceptance. Do not enable paid hosting or live real documents from this proof.
