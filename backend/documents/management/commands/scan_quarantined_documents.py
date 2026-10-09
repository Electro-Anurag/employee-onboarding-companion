"""Manual bounded local scanner runner; not an unattended production service."""
from django.core.management.base import BaseCommand,CommandError
from backend.documents.quarantine_models import QuarantinedDocument
from backend.documents.quarantine_commands import enabled,scan_upload
from backend.onboarding.services import CommandFailure

class Command(BaseCommand):
    help='Explicitly scan up to 10 pending local quarantine records through configured ClamAV'

    def add_arguments(self,parser):
        parser.add_argument('--limit',type=int,default=10)

    def handle(self,*args,**options):
        limit=options['limit']
        if not enabled():
            raise CommandError('Quarantine is disabled or ClamAV endpoint not configured')
        if not 1<=limit<=10:
            raise CommandError('Limit must be 1 through 10')
        scanned=0
        errors=0
        for upload in QuarantinedDocument.objects.order_by('uploaded_at')[:100]:
            last=upload.scan_attempts.order_by('-attempt').first()
            if last and (last.outcome in ('CLEAN','MALWARE') or last.attempt>=3):
                continue
            try:
                result=scan_upload(upload.pk)
                scanned+=1
                errors+=result['outcome']=='ERROR'
            except CommandFailure:
                errors+=1
            if scanned>=limit:break
        self.stdout.write(f'SCAN_ATTEMPTS={scanned} ERRORS={errors} (no document releases)')
