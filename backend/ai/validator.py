"""Deny model-invented evidence and actions, even if provider returned JSON."""
import re
from backend.onboarding.services import get_authorized_case

TYPES=frozenset({'SUPPORTED','PARTIAL','UNSUPPORTED','CONFLICT'})
TEXT_RE=re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f]')


class UnsafeAIAnswer(ValueError):
    pass


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
    # This function only returns validated *text/candidate identifiers*.
    # It cannot call existing mutations, accept approvals or send messages.
    return {**payload,'case_version':context['case_version'],
        'context_digest':context['context_digest']}
