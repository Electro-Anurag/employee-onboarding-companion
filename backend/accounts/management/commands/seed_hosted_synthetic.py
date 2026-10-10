"""One-time production-mode bootstrap for explicitly synthetic hosted demo accounts.

This command is not included in a deploy/startup process. The operator must
run it manually in an authenticated service shell with separately configured
strong secrets. Never enable DEBUG or echo passwords for a hosted demo.
"""
import os
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from backend.accounts.models import User, Organization, Membership


class Command(BaseCommand):
    help = "Manually provision four synthetic demonstration identities on a hosted service"

    def add_arguments(self, parser):
        parser.add_argument("--confirm-synthetic", action="store_true")

    def handle(self, *args, **options):
        if (settings.DEBUG or not options["confirm_synthetic"]
                or os.environ.get("EOC_HOSTED_DEMO_BOOTSTRAP") != "1"):
            raise CommandError(
                "Production mode, EOC_HOSTED_DEMO_BOOTSTRAP=1 and "
                "--confirm-synthetic are all required"
            )
        roles = ("HR", "EMPLOYEE", "IT", "MANAGER")
        # Credential env vars must be configured as *private* service secrets.
        # No password or secret value is printed or persisted as plaintext.
        passwords = {}
        for role in roles:
            value = os.environ.get("EOC_DEMO_" + role + "_PASSWORD", "")
            if not value:
                raise CommandError("Missing hosted demo password for " + role)
            try:
                validate_password(value)
            except Exception as exc:
                raise CommandError("Hosted demo password fails Django policy for " + role) from exc
            passwords[role] = value
        if len(set(passwords.values())) != len(roles):
            raise CommandError("Synthetic roles require distinct passwords")
        emails = {role: role.lower() + "@hosted-onboarding-demo.invalid" for role in roles}
        with transaction.atomic():
            if (Organization.objects.filter(name="Hosted Onboarding Synthetic Demo").exists()
                    or User.objects.filter(email__in=emails.values()).exists()):
                raise CommandError("Hosted synthetic demo already exists; refusing to overwrite")
            org = Organization.objects.create(
                name="Hosted Onboarding Synthetic Demo", timezone="Asia/Kolkata"
            )
            for role in roles:
                user = User.objects.create_user(
                    email=emails[role], password=passwords[role],
                    display_name="Synthetic Hosted " + role.title()
                )
                Membership.objects.create(
                    user=user, organization=org, role=role,
                    can_manage_templates=(role == "HR"),
                    can_coordinate_ownership=(role == "HR"),
                )
        self.stdout.write(
            "Created four synthetic-only demo identities. "
            "Credentials were not printed. Disable EOC_HOSTED_DEMO_BOOTSTRAP now."
        )
        for role in roles:
            self.stdout.write(role + ": " + emails[role])
