"""Reject structurally malformed, encrypted or active-content PDFs before promotion."""
import io
from backend.onboarding.services import CommandFailure

def validate_pdf(raw):
    if not raw.startswith(b'%PDF-') or len(raw)<40 or not raw.rstrip().endswith(b'%%EOF'):
        raise CommandFailure('INVALID_PDF_BYTES',422)
    try:
        from pypdf import PdfReader
        reader=PdfReader(io.BytesIO(raw),strict=True)
        if reader.is_encrypted or not 1<=len(reader.pages)<=20:
            raise ValueError('encrypted or oversized page count')
        root=reader.trailer['/Root']
        if any(k in root for k in ('/OpenAction','/AA','/AcroForm')):
            raise ValueError('active catalog')
        names=root.get('/Names')
        if names and any(k in names.get_object() for k in ('/JavaScript','/EmbeddedFiles')):
            raise ValueError('embedded content')
        # Parse every page, not only its page count.
        for page in reader.pages:
            if any(k in page for k in ('/AA','/Annots')):
                raise ValueError('active page annotations')
            if not page.mediabox:raise ValueError('invalid page')
    except Exception as exc:
        raise CommandFailure('INVALID_OR_UNSAFE_PDF',422) from exc
