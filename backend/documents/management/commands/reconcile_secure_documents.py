"""Bounded operator reconciliation for outstanding private S3 document work.

Select actionable scan/promote work in PostgreSQL, not the oldest 100 intents.
Uploads with no committed quarantine receipt require an authorized client
retry and cannot be silently reconstructed from untrusted object-store HEADs.
No clean object is auto-approved for HR.
"""
from django.core.management.base import BaseCommand,CommandError
from django.db.models import OuterRef,Subquery,Q
from backend.documents import storage
from backend.documents.real_models import SecureUpload,SecureScanAttempt
from backend.documents.real_commands import scan_one
from backend.onboarding.services import CommandFailure

def eligible_uploads(limit):
    """Unreviewable quarantine receipts needing a scan or clean promotion.

    No first-100 cap: SQL filters unreceived, already-clean, malware-terminal,
    and exhausted scans before applying the bounded work limit.
    """
    last=SecureScanAttempt.objects.filter(upload_id=OuterRef('pk')).order_by('-number')
    return (SecureUpload.objects
        .filter(stored__isnull=False,clean__isnull=True)
        .annotate(last_outcome=Subquery(last.values('outcome')[:1]),
                  last_number=Subquery(last.values('number')[:1]))
        .filter(Q(last_outcome__isnull=True)
                | Q(last_outcome='CLEAN')
                | Q(last_outcome='ERROR',last_number__lt=3))
        .order_by('created_at','pk')[:limit])

class Command(BaseCommand):
    help='Reconcile up to 10 pending S3 document scans/promotions.'

    def add_arguments(self,parser):
        parser.add_argument('--limit',type=int,default=10)

    def handle(self,*args,**options):
        if not storage.configured():raise CommandError('M3 real S3 documents are disabled')
        limit=options['limit']
        if not 1<=limit<=10:raise CommandError('limit must be 1 to 10')
        processed=0
        errors=0
        for upload in eligible_uploads(limit):
            processed+=1
            try:
                result=scan_one(upload.pk)
                if result['state'] in ('SCAN_FAILED','PROMOTION_PENDING'):
                    errors+=1
            except CommandFailure:
                errors+=1
        self.stdout.write('PROCESSED='+str(processed)+' ERRORS='+str(errors))
