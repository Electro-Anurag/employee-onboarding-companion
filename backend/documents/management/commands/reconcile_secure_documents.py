"""Case-safe qualification runner to replay durable scans and storage reconciliation.

Production deployments should use Procrastinate content worker plus this bounded
operator fallback. It does not auto-promote or auto-approve an unscanned object.
"""
from django.core.management.base import BaseCommand,CommandError
from backend.documents import storage
from backend.documents.real_models import SecureUpload,StoredQuarantineObject,SecureScanAttempt
from backend.documents.real_commands import scan_one
from backend.onboarding.services import CommandFailure

class Command(BaseCommand):
    help='Reconcile and process at most 10 real S3 document scan jobs.'

    def add_arguments(self,parser):
        parser.add_argument('--limit',type=int,default=10)

    def handle(self,*args,**options):
        if not storage.configured():raise CommandError('M3 real S3 documents are disabled')
        limit=options['limit']
        if not 1<=limit<=10:raise CommandError('limit must be 1 to 10')
        accepted=0
        errors=0
        for upload in SecureUpload.objects.order_by('created_at')[:100]:
            if not StoredQuarantineObject.objects.filter(upload=upload).exists():
                # No raw bytes in PostgreSQL. If storage write had committed and
                # DB finalization crashed, a later storage HEAD may recover it.
                continue
            last=SecureScanAttempt.objects.filter(upload=upload).order_by('-number').first()
            if last and (last.outcome=='MALWARE' or
                (last.outcome=='ERROR' and last.number>=3)):
                continue
            try:
                result=scan_one(upload.pk)
                accepted+=1
                if result['state'] in ('SCAN_FAILED','PROMOTION_PENDING'):errors+=1
            except CommandFailure:
                errors+=1
            if accepted>=limit:break
        self.stdout.write('PROCESSED='+str(accepted)+' ERRORS='+str(errors))
