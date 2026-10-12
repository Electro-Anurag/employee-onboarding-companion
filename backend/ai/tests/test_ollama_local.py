"""Local-only Ollama transport is opt-in and shares source/claim validation.

Entire suite is fake HTTP in CI: passing does not claim a real model run.
"""
import json
from unittest.mock import patch

import pytest

from backend.ai.provider import ProviderFailure, infer_local
from backend.onboarding.tests.test_m2_workflow import world


class Response:
    def __init__(self, body):
        self.body = body
    def __enter__(self):
        return self
    def __exit__(self, *_args):
        return False
    def read(self, n):
        return self.body[:n]


def allowed():
    return {
        "answer_type": "UNSUPPORTED",
        "answer": "The available authorized sources do not establish that claim.",
        "citations": [], "recommended_actions": [], "blockers": [],
        "clarification": None, "escalation_draft": None,
        "limitations": ["No verified fact supports the requested claim."],
    }


def test_local_model_requires_explicit_opt_in_and_valid_model(monkeypatch):
    monkeypatch.delenv("EOC_AI_PROVIDER", raising=False)
    monkeypatch.delenv("EOC_OLLAMA_MODEL", raising=False)
    with patch("backend.ai.provider.request.urlopen") as outbound:
        with pytest.raises(ProviderFailure, match="PROVIDER_NOT_CONFIGURED"):
            infer_local({}, "What is this?")
        outbound.assert_not_called()
    monkeypatch.setenv("EOC_AI_PROVIDER", "OLLAMA_LOCAL")
    monkeypatch.setenv("EOC_OLLAMA_MODEL", "https://malicious.invalid/api")
    with patch("backend.ai.provider.request.urlopen") as outbound:
        with pytest.raises(ProviderFailure, match="PROVIDER_NOT_CONFIGURED"):
            infer_local({}, "Question")
        outbound.assert_not_called()


def test_local_model_uses_pinned_loopback_only_and_strict_schema(monkeypatch):
    monkeypatch.setenv("EOC_AI_PROVIDER", "OLLAMA_LOCAL")
    monkeypatch.setenv("EOC_OLLAMA_MODEL", "gpt-oss:20b")
    calls = []
    def fake(req, timeout):
        calls.append((req.full_url, timeout))
        body = json.loads(req.data)
        assert req.full_url == "http://127.0.0.1:11434/api/chat"
        assert "Authorization" not in req.headers
        assert body["stream"] is False and body["format"]["additionalProperties"] is False
        assert body["options"]["num_predict"] == 650
        assert body["model"] == "gpt-oss:20b"
        assert len(body["messages"]) == 2
        return Response(json.dumps({
            "model": "gpt-oss:20b", "done": True,
            "message": {"role": "assistant", "content": json.dumps(allowed())},
            "prompt_eval_count": 22, "eval_count": 18,
        }).encode())
    monkeypatch.setattr("backend.ai.provider.request.urlopen", fake)
    answer,usage = infer_local({"sources":[]}, "Is my salary guaranteed?")
    assert answer["answer_type"] == "UNSUPPORTED"
    assert usage["model"] == "gpt-oss:20b"
    assert usage["input_tokens"] == 22
    assert usage["output_tokens"] == 18
    assert usage["response_id"] == "local-ollama"
    assert calls == [("http://127.0.0.1:11434/api/chat",45)]


@pytest.mark.parametrize("message", [
    {"model": "gpt-oss:20b", "done": False, "message": {"role":"assistant","content":"{}"}},
    {"model": "other-model", "done": True, "message": {"role":"assistant","content":"{}"}},
    {"model": "gpt-oss:20b", "done": True, "message": {"role":"user","content":"{}"}},
    {"model": "gpt-oss:20b", "done": True, "message": {"role":"assistant","content":"bad json"}},
    {"model": "gpt-oss:20b", "done": True, "message": {"role":"assistant","content":[]}},
])
def test_local_model_invalid_output_refused_without_data_leak(monkeypatch,message):
    monkeypatch.setenv("EOC_AI_PROVIDER", "OLLAMA_LOCAL")
    monkeypatch.setenv("EOC_OLLAMA_MODEL", "gpt-oss:20b")
    with patch("backend.ai.provider.request.urlopen",return_value=Response(json.dumps(message).encode())):
        with pytest.raises(ProviderFailure) as e:
            infer_local({"secret":"synthetic-private-token"}, "synthetic-private-question")
        assert "synthetic-private-question" not in str(e.value)
        assert "synthetic-private-token" not in str(e.value)


def test_local_model_bounded_context_refuses_before_network(monkeypatch):
    monkeypatch.setenv("EOC_AI_PROVIDER", "OLLAMA_LOCAL")
    monkeypatch.setenv("EOC_OLLAMA_MODEL", "gpt-oss:20b")
    with patch("backend.ai.provider.request.urlopen") as outbound:
        with pytest.raises(ProviderFailure, match="CONTEXT_TOO_LARGE"):
            infer_local({"untrusted_text": "x"*20000}, "Question")
        outbound.assert_not_called()


@pytest.mark.django_db(transaction=True)
def test_local_model_mode_reuses_actual_auth_citation_relevance_audit_and_no_write(
        world, monkeypatch):
    import uuid
    from backend.onboarding.tests.test_m2_workflow import published, create
    from backend.onboarding.commands import activate_case
    from backend.onboarding.models import OnboardingCase, TaskCompletion
    from backend.ai.context import authorized_context
    from backend.ai.answers import answer_question
    from backend.audit.models import AuditEvent

    _, actors = world
    created, _ = create(world, published(world))
    case = OnboardingCase.objects.get(pk=created["case_id"])
    activate_case(actor=actors["HR"][0], case_id=case.pk,
                  key=uuid.uuid4(), expected_version=1)
    user = actors["MANAGER"][0]
    context = authorized_context(user, case.pk)
    task = next(t for t in context["tasks"] if t["key"] == "manager_preparation")
    source = "TASK:" + task["id"]
    monkeypatch.setenv("EOC_AI_PROVIDER", "OLLAMA_LOCAL")
    monkeypatch.setenv("EOC_OLLAMA_MODEL", "gpt-oss:20b")
    def result(_ctx, question):
        assert question == "Who owns Manager Preparation?"
        assert _ctx["context_digest"] == context["context_digest"]
        return {
            "answer_type": "SUPPORTED",
            "answer": "Manager Preparation is assigned to MANAGER.",
            "citations": [source], "recommended_actions": [], "blockers": [],
            "clarification": None, "escalation_draft": None, "limitations": [],
        }, {"model": "gpt-oss:20b", "response_id": "local-ollama",
            "input_tokens": 24, "output_tokens": 17}
    monkeypatch.setattr("backend.ai.answers.infer_local", result)
    before = TaskCompletion.objects.count()
    good = answer_question(user, case.pk, "Who owns Manager Preparation?")
    assert good["mode"] == "MODEL_VALIDATED"
    assert good["ai_model_used"] is True
    assert good["answer"]["citations"] == [source]
    assert TaskCompletion.objects.count() == before
    attempt = AuditEvent.objects.get(actor=user, event_type="AI_MODEL_ATTEMPT")
    assert attempt.sanitized_change["provider"] == "OLLAMA_LOCAL"

    def invented(_ctx, _question):
        data, usage = result(_ctx, "Who owns Manager Preparation?")
        return {**data, "citations": ["TASK:invented"]}, usage
    monkeypatch.setattr("backend.ai.answers.infer_local", invented)
    denied = answer_question(user, case.pk, "Who owns Manager Preparation?")
    assert denied["mode"] == "DETERMINISTIC_FALLBACK"
    assert denied["ai_model_used"] is False
    assert denied["error_code"] == "MODEL_OUTPUT_REJECTED"
    assert TaskCompletion.objects.count() == before
    assert AuditEvent.objects.filter(
        actor=user, event_type="AI_MODEL_ATTEMPT").count() == 2
    assert AuditEvent.objects.filter(
        actor=user, event_type="AI_MODEL_VALIDATED").count() == 1
    assert AuditEvent.objects.filter(
        actor=user, event_type="AI_MODEL_FAILED").count() == 1
