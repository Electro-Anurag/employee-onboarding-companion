"""Explicitly synthetic document byte fixtures. Never accept general identity files.

This bounded CI/demo-only intake is not an antivirus, object store or a real
employee-document system. Only exact canonical bytes are eligible for review.
"""
import hashlib
from backend.onboarding.services import CommandFailure

FIXTURES={
  'identity_document': b'SYNTHETIC DOCUMENT V1\nIDENTITY EXAMPLE: DEMO-IDENTITY-001\nNO REAL PERSON OR IDENTITY DATA\n',
  'employment_document': b'SYNTHETIC DOCUMENT V1\nEMPLOYMENT EXAMPLE: DEMO-EMPLOYMENT-001\nNO REAL CONTRACT OR EMPLOYER DATA\n',
}
PROFILE='EXACT_SYNTHETIC_FIXTURE_V1'
def sample_for(task):
    content=FIXTURES.get(task.key)
    if task.kind!='DOCUMENT' or content is None:
        raise CommandFailure('DOCUMENT_FIXTURE_NOT_CONFIGURED',422)
    return content

def validate_document(task,raw):
    expected=sample_for(task)
    if (not isinstance(raw,bytes) or len(raw)>4096
            or len(raw)!=len(expected)
            or not __import__('hmac').compare_digest(raw,expected)):
        raise CommandFailure('SYNTHETIC_FIXTURE_ONLY',422)
    return hashlib.sha256(raw).hexdigest()
