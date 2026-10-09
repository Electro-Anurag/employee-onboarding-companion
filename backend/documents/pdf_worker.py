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
    # PDF outline/bookmark actions are not confined to the catalog/page.
    # Walk nested First/Next links with a strict bound, preserving passive
    # bookmarks but rejecting action dictionaries (including JS/Launch/URI).
    if '/Outlines' in root:
        catalog_outline=root['/Outlines'].get_object()
        if not isinstance(catalog_outline,dict) or any(
                k in catalog_outline for k in ('/A','/AA')):
            raise ValueError('invalid or active outline root')
        pending=[catalog_outline.get('/First')]
        seen=set()
        while pending:
            ref=pending.pop()
            if ref is None:
                continue
            marker=(ref.idnum,ref.generation) if hasattr(ref,'idnum') else id(ref)
            if marker in seen or len(seen)>=512:
                raise ValueError('cyclic or excessive PDF outline')
            seen.add(marker)
            item=ref.get_object() if hasattr(ref,'get_object') else ref
            if not isinstance(item,dict) or any(k in item for k in ('/A','/AA')):
                raise ValueError('active outline action')
            pending.extend((item.get('/First'),item.get('/Next')))
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
