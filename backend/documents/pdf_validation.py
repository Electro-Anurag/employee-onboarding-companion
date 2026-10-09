"""Fail-closed PDF inspection in a bounded child process.

An untrusted PDF is never parsed by a Django web or Procrastinate worker.
Resource limits mitigate hangs/CPU or memory abuse; this is not an OS sandbox.
"""
import subprocess
import sys
from backend.onboarding.services import CommandFailure

def validate_pdf(raw):
    if (not isinstance(raw,bytes) or len(raw)<40 or len(raw)>10*1024*1024
            or not raw.startswith(b'%PDF-') or not raw.rstrip().endswith(b'%%EOF')):
        raise CommandFailure('INVALID_PDF_BYTES',422)
    try:
        result=subprocess.run([sys.executable,'-m','backend.documents.pdf_worker'],
            input=raw,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
            close_fds=True,timeout=6,check=False)
    except subprocess.TimeoutExpired as exc:
        raise CommandFailure('PDF_PARSER_TIMEOUT',422) from exc
    except OSError as exc:
        raise CommandFailure('PDF_PARSER_UNAVAILABLE',503) from exc
    if result.returncode!=0:
        raise CommandFailure('INVALID_OR_UNSAFE_PDF',422)
