"""Read-only bounded exact-version S3/DB recovery integrity gate."""
from django.core.management.base import BaseCommand, CommandError

from backend.documents.recovery_integrity import verify_referenced_versions
from backend.onboarding.services import CommandFailure


class Command(BaseCommand):
    help = ("Read-only exact S3 VersionId+SHA verification; requires quiesced "
            "document writes to interpret full-scope PASS.")

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100)
        parser.add_argument("--confirm-quiesced", action="store_true")

    def handle(self, *args, **options):
        if not options["confirm_quiesced"]:
            raise CommandError("STOP: document intake must first be quiesced")
        try:
            result = verify_referenced_versions(limit=options["limit"])
        except (ValueError, CommandFailure):
            raise CommandError("RECOVERY_INTEGRITY_PREFLIGHT_STOP") from None
        # Emit only bounded aggregates, never keys, actor names or bytes.
        for key in ("state", "checked", "quarantine_verified", "clean_verified",
                    "incomplete", "integrity_errors", "scope_exceeded"):
            self.stdout.write(key.upper() + "=" + str(result[key]))
        if result["state"] != "PASS":
            raise CommandError("RECOVERY_INTEGRITY_PREFLIGHT_STOP")
        self.stdout.write("EOC_D6_EXACT_VERSION_STORAGE_INTEGRITY_PASS")
