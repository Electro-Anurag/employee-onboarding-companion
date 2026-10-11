"""Owner-gated *read-only* synthetic hosted credential admission diagnostic.

Checks four allowlisted .invalid accounts against four private service env
secrets without attempting an HTTP login or writing accounts, sessions, audit
events, throttles, or credentials. Prints status categories only: no personal
data, submitted passwords, salt, hash, session keys, user IDs, or org IDs.
"""
import os
from django.conf import settings
from django.contrib.auth import authenticate
from django.core.management.base import BaseCommand, CommandError

from backend.accounts.models import User, Organization, Membership
from backend.accounts.security import actor_context
from backend.accounts.management.commands.rotate_hosted_synthetic import (
    DEMO_ORG_NAME, DEMO_DOMAIN, ROLES,
)


class Command(BaseCommand):
    help = "Read-only hosted synthetic account and private secret diagnostic"

    def add_arguments(self, parser):
        parser.add_argument("--confirm-synthetic-diagnostic", action="store_true")

    def handle(self, *args, **options):
        if (settings.DEBUG
                or not options["confirm_synthetic_diagnostic"]
                or os.environ.get("EOC_HOSTED_DEMO_CREDENTIAL_DIAGNOSE") != "1"
                or os.environ.get("EOC_HOSTED_DEMO_BOOTSTRAP", "0") == "1"
                or os.environ.get("EOC_HOSTED_DEMO_CREDENTIAL_ROTATE", "0") == "1"):
            raise CommandError(
                "Read-only diagnostic requires DEBUG=0, exact confirmation, "
                "diagnostic flag and both mutation flags disabled"
            )
        orgs = list(Organization.objects.filter(name=DEMO_ORG_NAME)[:2])
        if len(orgs) != 1:
            self.stdout.write("EOC_SYNTHETIC_AUTH_DIAG=UNQUALIFIED_ORGANIZATION")
            return
        org = orgs[0]

        for role in ROLES:
            email = role.lower() + DEMO_DOMAIN
            users = list(User.objects.filter(email=email)[:2])
            if len(users) != 1:
                self.stdout.write("EOC_SYNTHETIC_AUTH_DIAG_ROLE=" + role +
                                  " STATUS=IDENTITY_MISSING_OR_AMBIGUOUS")
                continue
            user = users[0]
            memberships = list(Membership.objects.filter(user=user)[:3])
            matching = (
                len(memberships) == 1
                and memberships[0].organization_id == org.pk
                and memberships[0].role == role
                and memberships[0].active and memberships[0].available
                and user.is_active and not user.is_staff and not user.is_superuser
                and bool(memberships[0].can_manage_templates) == (role == "HR")
                and bool(memberships[0].can_coordinate_ownership) == (role == "HR")
            )
            if not matching:
                self.stdout.write("EOC_SYNTHETIC_AUTH_DIAG_ROLE=" + role +
                                  " STATUS=IDENTITY_OR_MEMBERSHIP_INVALID")
                continue
            password = os.environ.get("EOC_DEMO_" + role + "_PASSWORD")
            if not password:
                self.stdout.write("EOC_SYNTHETIC_AUTH_DIAG_ROLE=" + role +
                                  " STATUS=PRIVATE_ENV_SECRET_MISSING")
                continue
            if not user.check_password(password):
                self.stdout.write("EOC_SYNTHETIC_AUTH_DIAG_ROLE=" + role +
                                  " STATUS=PRIVATE_ENV_SECRET_HASH_MISMATCH")
                continue
            admitted = authenticate(username=email, password=password)
            if admitted is None or admitted.pk != user.pk:
                self.stdout.write("EOC_SYNTHETIC_AUTH_DIAG_ROLE=" + role +
                                  " STATUS=DJANGO_AUTH_BACKEND_REJECTED")
                continue
            try:
                actor = actor_context(admitted)
                if actor.organization_id != org.pk or actor.role != role:
                    self.stdout.write("EOC_SYNTHETIC_AUTH_DIAG_ROLE=" + role +
                                      " STATUS=AUTH_CONTEXT_MISMATCH")
                    continue
            except Exception:
                self.stdout.write("EOC_SYNTHETIC_AUTH_DIAG_ROLE=" + role +
                                  " STATUS=AUTH_CONTEXT_REJECTED")
                continue
            self.stdout.write("EOC_SYNTHETIC_AUTH_DIAG_ROLE=" + role +
                              " STATUS=SERVER_SIDE_PASSWORD_AND_ROLE_MATCH")
        self.stdout.write("EOC_SYNTHETIC_AUTH_DIAG=READ_ONLY_COMPLETE")
