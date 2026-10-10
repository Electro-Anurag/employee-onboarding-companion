"""M5 explicit, fixed first escalation policy.

Version identifiers participate in durable notification identities. Changes
to policy require a new code version, tests and source review; no silent
tenant-wide defaults or unapproved admin-editable policy are asserted.
This is *in-app only*. External messaging is not implemented.
"""
from datetime import timedelta

BASE_POLICY_VERSION='M5-REMIND-V1'
ESCALATION_POLICY_VERSION='M5-ESCALATE-48H-V1'
ESCALATION_RULE='ESCALATION_48H_HR'
ESCALATION_DELAY=timedelta(hours=48)
ESCALATION_RECIPIENT_ROLE='HR'
