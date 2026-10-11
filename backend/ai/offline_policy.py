"""Bounded offline policy reader, not a language model or semantic inference.

Accept explicit, single-policy view requests only. Ambiguity and extra claims
fail closed. Render a complete SHA-256-verified assigned edition, never an
excerpt, summary, advice, or workflow action. Authorization comes from
authorized_context and publication is rechecked by validate_answer.
"""
import re
from backend.ai.validator import (
    PARTIAL_LIMITATION, canonical_policy_quote, validate_answer,
)

POLICY_KEYS = {
    'conduct': 'conduct_ack',
    'privacy': 'privacy_ack',
    'benefits': 'benefits_ack',
}
# Deliberately small grammar: do not strip arbitrary question clauses,
# keywords or modifiers that could change a question's meaning.
REQUEST = re.compile(
    r'(?:show|display|read|view|what is)(?: me)? '
    r'(?:the )?(?:assigned )?'
    r'(conduct|privacy|benefits) (?:policy|guidance|orientation)\??',
    re.ASCII,
)


def offline_policy_answer(*, question, context, actor, case_id):
    """Return a server-verified quote or None; no provider, writes or heuristics."""
    if not isinstance(question, str):
        return None
    normalized = ' '.join(question.strip().casefold().split())
    match = REQUEST.fullmatch(normalized)
    if match is None:
        return None
    key = POLICY_KEYS[match.group(1)]
    matching_tasks = [t for t in context['tasks']
                      if t['key'] == key and t['kind'] == 'POLICY_ACK']
    if len(matching_tasks) != 1:
        return None
    prefix = 'POLICY:' + matching_tasks[0]['id'] + ':'
    policies = [p for p in context['policies']
                if p['source_id'].startswith(prefix)]
    if len(policies) != 1:
        return None
    policy = policies[0]
    quote = canonical_policy_quote(policy)
    if quote is None:
        return None
    payload = {
        'answer_type': 'PARTIAL',
        'answer': quote,
        'citations': [policy['source_id']],
        'recommended_actions': [],
        'blockers': [],
        'clarification': None,
        'escalation_draft': None,
        'limitations': [PARTIAL_LIMITATION],
    }
    verified = validate_answer(payload, context, actor=actor, case_id=case_id)
    return {
        'mode': 'DETERMINISTIC_SOURCE_ANSWER',
        'ai_model_used': False,
        'answer': verified,
        'model': 'Verified case-assigned policy — no AI',
    }
