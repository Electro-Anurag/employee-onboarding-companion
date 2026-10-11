"""Explicit owner-gated *existing* synthetic account credential recovery.

This command cannot create accounts, add/change memberships, modify ordinary
accounts, or run during a normal service start. No passwords or password
hashes are logged. A separate audit event is committed transactionally.
"""
import os
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from backend.accounts.models import User, Membership, Organization, OneTimeToken
from backend.accounts.security import _bounded_credential_transaction
from backend.audit.services import append_event

DEMO_ORG_NAME = "Hosted Onboarding Synthetic Demo"
ROLES = ("HR", "EMPLOYEE", "IT", "MANAGER")
DEMO_DOMAIN = "@hosted-onboarding-demo.invalid"


class Command(BaseCommand):
    help = "Explicitly rotate only four preexisting synthetic hosted demo passwords"

    def add_arguments(self, parser):
        parser.add_argument("--confirm-synthetic-rotation", action="store_true")

    def handle(self, *args, **options):
        if (settings.DEBUG
                or not options["confirm_synthetic_rotation"]
                or os.environ.get("EOC_HOSTED_DEMO_CREDENTIAL_ROTATE") != "1"
                or os.environ.get("EOC_HOSTED_DEMO_BOOTSTRAP", "0") == "1"):
            raise CommandError(
                "Synthetic rotation needs DEBUG=0, explicit confirmation, "
                "EOC_HOSTED_DEMO_CREDENTIAL_ROTATE=1 and bootstrap disabled"
            )

        passwords = {}
        for role in ROLES:
            value = os.environ.get("EOC_DEMO_" + role + "_PASSWORD", "")
            if not value or len(value) > 256:
                raise CommandError("Missing/invalid synthetic credential for " + role)
            try:
                validate_password(value)
            except Exception as exc:
                raise CommandError(
                    "Synthetic credential rejected by password policy for " + role
                ) from exc
            passwords[role] = value
        if len(set(passwords.values())) != len(ROLES):
            raise CommandError("Each synthetic role requires a distinct password")

        expected_emails = {role: role.lower() + DEMO_DOMAIN for role in ROLES}
        with transaction.atomic():
            _bounded_credential_transaction()
            orgs = list(
                Organization.objects.select_for_update().filter(name=DEMO_ORG_NAME)
            )
            if len(orgs) != 1:
                raise CommandError(
                    "Exact synthetic organization missing or ambiguous; no changes made"
                )
            org = orgs[0]
            users = list(
                User.objects.select_for_update()
                .filter(email__in=expected_emails.values())
                .order_by("email")
            )
            if len(users) != len(ROLES):
                raise CommandError(
                    "Expected exactly four preexisting synthetic users; no changes made"
                )
            by_email = {u.email: u for u in users}
            if set(by_email) != set(expected_emails.values()):
                raise CommandError("Synthetic identities do not match exact allowlist")

            memberships = list(
                Membership.objects.select_for_update()
                .filter(organization=org)
                .order_by("id")
            )
            all_related = list(
                Membership.objects.filter(user__in=users).order_by("id")
            )
            if len(memberships) != 4 or len(all_related) != 4:
                raise CommandError(
                    "Unexpected demo organization or cross-org memberships; no changes made"
                )
            expected_user_ids = {u.pk for u in users}
            if ({m.user_id for m in memberships} != expected_user_ids
                    or {m.pk for m in memberships} != {m.pk for m in all_related}):
                raise CommandError(
                    "Synthetic membership identities are inconsistent; no changes made"
                )

            by_user = {m.user_id: m for m in memberships}
            for role in ROLES:
                u = by_email[expected_emails[role]]
                member = by_user[u.pk]
                if (not u.is_active or u.is_staff or u.is_superuser
                        or not member.active or not member.available
                        or member.role != role
                        or bool(member.can_manage_templates) != (role == "HR")
                        or bool(member.can_coordinate_ownership) != (role == "HR")):
                    raise CommandError(
                        "Synthetic user/membership safety check failed for " + role
                    )
                validate_password(passwords[role], u)

            mismatched = [
                role for role in ROLES
                if not by_email[expected_emails[role]].check_password(passwords[role])
            ]
            if not mismatched:
                self.stdout.write(
                    "Hosted synthetic credentials already match all four roles. "
                    "No database changes made."
                )
                return

            for role in mismatched:
                user = by_email[expected_emails[role]]
                user.set_password(passwords[role])
                user.save(update_fields=["password"])

            OneTimeToken.objects.filter(
                user__in=users, used_at__isnull=True
            ).update(used_at=timezone.now())

            append_event(
                stream_key="org:" + str(org.pk),
                actor=None,
                event_type="SYNTHETIC_DEMO_CREDENTIAL_ROTATION",
                entity_id=org.pk,
                changes={
                    "synthetic_only": True,
                    "rotated_roles": sorted(mismatched),
                    "no_membership_changes": True,
                },
                reason="Owner-gated hosted synthetic test credential recovery",
            )
        self.stdout.write(
            "Synthetic hosted credential recovery completed for "
            + str(len(mismatched)) +
            " existing demo role(s). No usernames, secrets or hashes disclosed."
        )
