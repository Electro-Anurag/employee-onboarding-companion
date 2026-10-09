"""Synthetic policy fixtures only; NOT legal or employer policy advice."""
import hashlib

POLICIES={
  'conduct_ack':('synthetic-conduct-v1',
      'Synthetic Aster Vale Labs conduct policy: Treat coworkers respectfully, '
      'report security concerns to the onboarding owner, and use only approved '
      'systems and accounts. This is test content, not an employment agreement.'),
  'privacy_ack':('synthetic-privacy-v1',
      'Synthetic Aster Vale Labs privacy guidance: Do not upload real identity '
      'documents or secrets to this demonstration. Access onboarding information '
      'only within your assigned role. This is not an actual privacy notice.'),
  'benefits_ack':('synthetic-benefits-v1',
      'Synthetic Aster Vale Labs benefits orientation: Contact the HR owner '
      'to confirm any applicable benefits. No compensation, enrollment, or '
      'legal rights are established by this demonstration text.'),
}
def policy_evidence(key):
    edition,body=POLICIES[key]
    return {'type':'POLICY_ACK','policy_key':key,'policy_version':edition,
            'policy_text':body,'content_sha256':hashlib.sha256(body.encode()).hexdigest()}
