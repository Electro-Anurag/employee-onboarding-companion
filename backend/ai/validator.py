"""Deny model-invented evidence and actions, even if provider returned JSON."""
import re
from backend.onboarding.services import get_authorized_case

TYPES=frozenset({'SUPPORTED','PARTIAL','UNSUPPORTED','CONFLICT'})
TEXT_RE=re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f]')

# These strings are composed by this trusted server boundary, not inferred
# from arbitrary model prose. The model may select an exact fact, not invent it.
SAFE_ABSTENTION = 'The available authorized sources do not establish that claim.'
SAFE_LIMITATION = 'No verified fact supports the requested claim.'
PARTIAL_LIMITATION = 'This answer covers only the cited fact, not the entire question.'

# Full-edition quotation only; never permit model-picked substrings to
# omit negation, scope or qualifications from the assigned document.
MAX_POLICY_QUOTE_CHARS = 800
POLICY_QUOTE_PREFIX = 'Verbatim assigned policy edition '


def canonical_policy_quote(policy):
    """Render a complete edition from hash-verified, role-authorized context.

    Return no candidate for long or malformed editions; a source URL or the
    existing authorized policy reader can handle those without truncation.
    """
    if not isinstance(policy, dict):
        return None
    version, body = policy.get('version'), policy.get('text')
    if (not isinstance(version, str) or not isinstance(body, str)
            or not version or not body or len(body) > MAX_POLICY_QUOTE_CHARS):
        return None
    return POLICY_QUOTE_PREFIX + version + ':\\n' + body


class UnsafeAIAnswer(ValueError):
    pass



def _has_grounded_fact(payload, context):
    """Exact canonical fact admission, not fuzzy matching or NLP entailment.

    One sentence, one source, and at most one task-specific action/blocker.
    Each accepted field comes from the currently authorized server snapshot.
    """
    if len(payload['citations']) != 1:
        return False
    source = payload['citations'][0]
    answer = payload['answer']
    actions = payload['recommended_actions']
    blockers = payload['blockers']
    if actions and blockers:
        return False
    for task in context['tasks']:
        if source != 'TASK:' + task['id']:
            continue
        if not actions and not blockers:
            facts = {
                task['title'] + ' is assigned to ' + task['owner_role'] + '.',
                task['title'] + ' is ' + task['state'] + '.',
            }
            if task['due_at'] is not None:
                facts.add(task['title'] + ' is due ' + str(task['due_at']) + '.')
            if answer in facts:
                return True
        if len(actions) == 1 and not blockers:
            return (answer == 'The action is currently eligible for ' +
                    task['title'] + '.' and
                    any(a['id'] == actions[0] and a['task_id'] == task['id']
                        for a in context['eligible_actions']))
        if len(blockers) == 1 and not actions:
            return (answer == task['title'] + ' is currently blocked.' and
                    task['state'] == 'BLOCKED' and
                    any(b['id'] == blockers[0] and b['task_id'] == task['id']
                        for b in context['blockers']))
        return False
    if actions or blockers:
        return False
    for policy in context['policies']:
        if source != policy['source_id']:
            continue
        if (answer == 'Assigned policy edition ' + str(policy['version']) +
                ' is available for review.'):
            return True
        # A *complete*, byte-for-byte policy body can be shown as a quotation.
        # Relevance to the question is not proved; quote is PARTIAL only.
        canonical = canonical_policy_quote(policy)
        if (canonical is not None and answer == canonical and
                payload['answer_type'] == 'PARTIAL'):
            return True
    for exception in context['open_exceptions']:
        if (source == exception['id'] and
                answer == 'Exception episode ' + str(exception['episode']) +
                ' is ' + exception['status'] + '.'):
            return True
    return False


def _validate_claim_boundary(payload, context):
    """No freeform generated text is published, including optional fields."""
    if payload['clarification'] is not None or payload['escalation_draft'] is not None:
        raise UnsafeAIAnswer('UNVERIFIED_GENERATED_PROSE')
    kind = payload['answer_type']
    if kind in ('SUPPORTED', 'PARTIAL'):
        expected_limits = [] if kind == 'SUPPORTED' else [PARTIAL_LIMITATION]
        if payload['limitations'] != expected_limits:
            raise UnsafeAIAnswer('UNVERIFIED_LIMITATION')
        if not _has_grounded_fact(payload, context):
            raise UnsafeAIAnswer('UNSUPPORTED_ANSWER_CLAIM')
        return
    if (kind != 'UNSUPPORTED' or payload['answer'] != SAFE_ABSTENTION or
            payload['citations'] or payload['blockers'] or
            payload['recommended_actions'] or
            payload['limitations'] != [SAFE_LIMITATION]):
        # A CONFLICT classification requires independent source-conflict
        # verification, which is not implemented; it cannot be admitted yet.
        raise UnsafeAIAnswer('UNVERIFIED_ABSTENTION')

def validate_answer(payload,context,*,actor,case_id):
    # Auth and revision refreshed at publication, not merely at prompt time.
    from backend.ai.context import authorized_context
    current=authorized_context(actor,case_id)
    if (current['case_id']!=context.get('case_id')
            or current['context_digest']!=context.get('context_digest')
            or current['case_version']!=context.get('case_version')):
        raise UnsafeAIAnswer('STALE_OR_UNAUTHORIZED_CONTEXT')
    required={'answer_type','answer','citations','recommended_actions',
              'blockers','clarification','escalation_draft','limitations'}
    if not isinstance(payload,dict) or set(payload)!=required:
        raise UnsafeAIAnswer('INVALID_OUTPUT_SHAPE')
    if not isinstance(payload['answer_type'],str) or payload['answer_type'] not in TYPES:
        raise UnsafeAIAnswer('INVALID_ANSWER_TYPE')
    if (not isinstance(payload['answer'],str) or not payload['answer'].strip()
            or len(payload['answer'])>2400
            or TEXT_RE.search(payload['answer'])):
        raise UnsafeAIAnswer('INVALID_ANSWER_TEXT')
    valid_sources=set(context['sources'])
    valid_actions={x['id'] for x in context['eligible_actions']}
    valid_blockers={x['id'] for x in context['blockers']}
    for field,valid,max_items in (
            ('citations',valid_sources,12),
            ('recommended_actions',valid_actions,3),
            ('blockers',valid_blockers,5)):
        values=payload[field]
        if (not isinstance(values,list) or len(values)>max_items
                or any(not isinstance(v,str) or v not in valid for v in values)
                or len(set(values))!=len(values)):
            raise UnsafeAIAnswer('UNSUPPORTED_'+field.upper())
    for field,max_length in (('clarification',400),('escalation_draft',1000)):
        value=payload[field]
        if value is not None and (not isinstance(value,str)
                or len(value)>max_length or TEXT_RE.search(value)):
            raise UnsafeAIAnswer('INVALID_'+field.upper())
    values=payload['limitations']
    if (not isinstance(values,list) or len(values)>6
            or any(not isinstance(x,str) or len(x)>240 or TEXT_RE.search(x)
                   for x in values)):
        raise UnsafeAIAnswer('INVALID_LIMITATIONS')
    if payload['answer_type'] in ('SUPPORTED','PARTIAL') and not payload['citations']:
        raise UnsafeAIAnswer('CITATIONS_REQUIRED')
    if payload['answer_type']=='PARTIAL' and (
            not payload['limitations'] or any(not x.strip() for x in payload['limitations'])):
        raise UnsafeAIAnswer('PARTIAL_LIMITATION_REQUIRED')
    # A valid citation ID alone is not enough for a proposed task action:
    # the *specific referenced task* must be among the cited evidence.
    # This is an exact provenance consistency check, not semantic verification
    # of arbitrary text in the answer or the underlying task's correctness.
    cited=set(payload['citations'])
    for action in context['eligible_actions']:
        if (action['id'] in payload['recommended_actions']
                and 'TASK:'+action['task_id'] not in cited):
            raise UnsafeAIAnswer('ACTION_TASK_CITATION_REQUIRED')
    for blocker in context['blockers']:
        if (blocker['id'] in payload['blockers']
                and 'TASK:'+blocker['task_id'] not in cited):
            raise UnsafeAIAnswer('BLOCKER_TASK_CITATION_REQUIRED')
    if payload['answer_type'] in ('UNSUPPORTED','CONFLICT'):
        if payload['recommended_actions']:
            raise UnsafeAIAnswer('UNSUPPORTED_ACTION_CLAIM')
        if not payload['limitations'] or any(not x.strip() for x in payload['limitations']):
            raise UnsafeAIAnswer('ABSTENTION_LIMITATION_REQUIRED')
    _validate_claim_boundary(payload, context)
    # This function only returns validated *text/candidate identifiers*.
    # It cannot call existing mutations, accept approvals or send messages.
    return {**payload,'case_version':context['case_version'],
        'context_digest':context['context_digest']}
