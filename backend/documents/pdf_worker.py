"""Isolated, bounded parser subprocess for untrusted synthetic PDF bytes.

This constrains parser CPU and address space, not a complete OS sandbox.
No Django models, database handles, network clients or secrets are loaded.
"""
import io
import resource
import sys

MAX_FILE=10*1024*1024

def inspect(raw):
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
    for page in reader.pages:
        if any(k in page for k in ('/AA','/Annots')):
            raise ValueError('active page annotations')
        if not page.mediabox:
            raise ValueError('invalid page')

if __name__=='__main__':
    try:
        resource.setrlimit(resource.RLIMIT_AS,(512*1024*1024,512*1024*1024))
        resource.setrlimit(resource.RLIMIT_CPU,(4,4))
        content=sys.stdin.buffer.read(MAX_FILE+1)
        if (not content.startswith(b'%PDF-') or len(content)<40
                or len(content)>MAX_FILE or not content.rstrip().endswith(b'%%EOF')):
            raise ValueError('invalid PDF structure')
        inspect(content)
    except BaseException:
        sys.exit(2)
    sys.exit(0)
