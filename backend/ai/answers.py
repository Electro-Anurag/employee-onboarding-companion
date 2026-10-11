"""Governed M6 question-answer operation with durable, sanitized outcomes.

The provider is opt-in and receives only source-validated synthetic case
context. Every attempted call is counted *before* an external request;
a failure returns clearly marked deterministic guidance, not fake AI.
"""
import hashlib
import json
import os
import uuid
from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from backend.accounts.models import User
from backend.audit.models import AuditEvent
from backend.audit.services import append_event
from backend.ai.context import authorized_context
from backend.ai.guidance import current_guidance
from backend.ai.provider import ProviderFailure, infer
from backend.ai.offline_policy import offline_policy_answer, requested_policy_key
from backend.ai.validator import UnsafeAIAnswer, validate_answer

MAX_CALLS_PER_USER_24H = 3


def _fallback(actor, case_id, reason):
    return {
        "mode": "DETERMINISTIC_FALLBACK",
        "ai_model_used": False,
        "error_code": reason,
        "guidance": current_guidance(actor, case_id),
    }


def answer_question(actor, case_id, question):
    if not isinstance(question, str) or not 1 <= len(question.strip()) <= 400:
        raise ValueError("INVALID_QUESTION")
    question = question.strip()
    context = authorized_context(actor, case_id)
    # Explicit, single-edition policy reads are always source-rendered first,
    # even when a provider is configured. This prevents irrelevant model
    # selections and unnecessary external calls or inference budget use.
    if requested_policy_key(question) is not None:
        verified_policy = offline_policy_answer(
            question=question, context=context, actor=actor, case_id=case_id,
        )
        if verified_policy is not None:
            return verified_policy
        return _fallback(actor, case_id, "POLICY_SOURCE_UNAVAILABLE")
    if (os.environ.get("EOC_AI_PROVIDER") != "OPENAI"
            or not os.environ.get("OPENAI_API_KEY")):
        return _fallback(actor, case_id, "MODEL_NOT_CONFIGURED")
    digest = hashlib.sha256(question.encode("utf-8")).hexdigest()
    stream = "case:" + str(case_id)
    attempt_id = uuid.uuid4()
    with transaction.atomic():
        # Serialize the daily budget check across concurrent user requests.
        User.objects.select_for_update().get(pk=actor.pk)
        used = AuditEvent.objects.filter(
            actor=actor, event_type="AI_MODEL_ATTEMPT",
            created_at__gte=timezone.now() - timedelta(hours=24),
        ).count()
        if used >= MAX_CALLS_PER_USER_24H:
            return _fallback(actor, case_id, "DAILY_INFERENCE_LIMIT")
        append_event(
            stream_key=stream, actor=actor, entity_id=case_id,
            event_type="AI_MODEL_ATTEMPT", command_id=attempt_id,
            changes={"question_sha256": digest,
                     "context_digest": context["context_digest"],
                     "case_version": context["case_version"],
                     "provider": "OPENAI", "max_output_tokens": 650},
        )
    try:
        payload, usage = infer(context, question)
        validated = validate_answer(payload, context, actor=actor, case_id=case_id)
        from backend.ai.relevance import ensure_question_relevance
        ensure_question_relevance(question, validated, context)
    except (ProviderFailure, UnsafeAIAnswer) as exc:
        reason = ("MODEL_OUTPUT_REJECTED" if isinstance(exc, UnsafeAIAnswer)
                  else "PROVIDER_UNAVAILABLE")
        # Never log raw provider output, user question, token or private context.
        append_event(
            stream_key=stream, actor=actor, entity_id=case_id,
            event_type="AI_MODEL_FAILED", command_id=attempt_id,
            changes={"question_sha256": digest,
                     "context_digest": context["context_digest"],
                     "reason": reason},
        )
        return _fallback(actor, case_id, reason)
    result_hash = hashlib.sha256(
        json.dumps(validated, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    append_event(
        stream_key=stream, actor=actor, entity_id=case_id,
        event_type="AI_MODEL_VALIDATED", command_id=attempt_id,
        changes={"answer_sha256": result_hash,
                 "question_sha256": digest,
                 "context_digest": context["context_digest"],
                 "citations": validated["citations"],
                 "model": usage["model"],
                 "response_id": usage["response_id"],
                 "input_tokens": usage["input_tokens"],
                 "output_tokens": usage["output_tokens"]},
    )
    return {
        "mode": "MODEL_VALIDATED", "ai_model_used": True,
        "answer": validated, "model": usage["model"],
        "input_tokens": usage["input_tokens"],
        "output_tokens": usage["output_tokens"],
    }
