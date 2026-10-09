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

@app.task(name="m3.secure_document_scan",queue="content")
def scan_secure_document(upload_id: str):
    from backend.documents.real_commands import scan_one
    scan_one(upload_id)
