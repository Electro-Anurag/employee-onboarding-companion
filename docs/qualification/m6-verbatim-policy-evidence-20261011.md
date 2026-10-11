# M6 exact-edition policy quotation — source-level development record

Context base SHA: `9b0e7c7edcc60a10ebdca67fac2c8d12e8620e0e`. Active branch: `feature/eoc-completion-development`.

**Problem:** Existing exact-fact admission only stated that a policy edition
was available; it did not return policy content for an authorized person.

**Proposed bounded path:** The provider may select one entire assigned policy
body only if it fits a conservative 800-character bound. Its response must
exactly match `Verbatim assigned policy edition <version>:\\n<entire text>`
and be marked PARTIAL with the fixed limitation. The validator checks
the complete model-returned text, source ID and fresh authorized case snapshot.
Policy editions are already SHA-256-verified in `validated_policy`. Models
cannot add prose, paraphrase, omit negations, or select sentence fragments. A
policy longer than the bound cannot be excerpted through this path; use the
existing authorized policy viewer. UI presents it as **model-selected policy
source text**, not a semantic interpretation or a proved response to the
question. The model cannot take actions. Role scope remains HR/Employee.

**Risk intentionally retained:** A model could select a policy irrelevant
to the user's question. Exact quotation proves textual correspondence, not
relevance, legality, source business accuracy, or model semantic performance.
Prompt-injection instructions contained in an assigned edition remain visible
as labelled untrusted source content; no instruction is executed. There are no
real model calls in offline tests; real-provider/hosted J04 remains BLOCKED.

The test contract includes ordinary benefits/conduct/privacy positives,
word modifications, partial deletions, extra financial claims, incorrect
policy citations, model-authored escalation text, wrong role, stale context,
overlong policy and HTML escaping. An exact-SHA CI result is required before
calling this focused implementation tested.

## Observed CI scheduling state

Final code/test SHA `6481876a2328f054eaedaf84db1bcc0b2471ebdc`. [Focused run 38146123757](https://github.com/Electro-Anurag/employee-onboarding-companion/actions/runs/38146123757) queued during this continuation; no test conclusion yet. The only passing M6 run currently inspected belongs to the earlier `be72be32…` boundary. Do not assert the quoted-policy feature is validated or production-ready before exact-SHA qualification. Independent answer relevance and model-source selection remain untested.
