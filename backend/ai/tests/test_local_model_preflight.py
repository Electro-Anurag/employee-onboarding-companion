"""Offline structural admission tests for the owner-run REAL Mac Ollama preflight.

No network, PostgreSQL or actual model is used by these unit tests.
"""
import pytest

from scripts import preflight_real_mac_ollama as preflight


def candidate(*, answer_type="SUPPORTED", answer=None, citations=None,
              limitations=None):
    ctx = preflight.synthetic_context()
    return {
        "answer_type": answer_type,
        "answer": answer if answer is not None else "Manager Preparation is assigned to MANAGER.",
        "citations": ctx["sources"] if citations is None else citations,
        "recommended_actions": [], "blockers": [],
        "clarification": None, "escalation_draft": None,
        "limitations": [] if limitations is None else limitations,
    }


def test_preflight_synthetic_context_contains_no_real_personal_data():
    ctx = preflight.synthetic_context()
    assert ctx["case_id"] == "22222222-2222-4222-8222-222222222222"
    assert ctx["tasks"][0]["owner_role"] == "MANAGER"
    assert ctx["sources"] == ["TASK:11111111-1111-4111-8111-111111111111"]
    assert "@" not in str(ctx)
    assert "context_digest" in ctx and len(ctx["context_digest"]) == 64


def test_preflight_exact_owner_and_status_admission():
    ctx = preflight.synthetic_context()
    owner = candidate()
    assert preflight.is_exact_safe_answer("Who owns Manager Preparation?", owner, ctx)
    status = candidate(answer="Manager Preparation is READY.")
    assert preflight.is_exact_safe_answer("What is the status of Manager Preparation?", status, ctx)
    assert not preflight.is_exact_safe_answer("What is the status of Manager Preparation?", owner, ctx)
    assert not preflight.is_exact_safe_answer(
        "Who owns Manager Preparation?",
        candidate(answer="Manager Preparation is assigned to HR."), ctx,
    )
    assert not preflight.is_exact_safe_answer(
        "Who owns Manager Preparation?",
        candidate(citations=["TASK:invented"]), ctx,
    )


def test_preflight_abstention_is_exact_and_nonhallucinated():
    ctx = preflight.synthetic_context()
    q = "Does my policy guarantee a salary bonus?"
    packet = candidate(
        answer_type="UNSUPPORTED",
        answer=preflight.SAFE_ABSTENTION,
        citations=[],
        limitations=[preflight.SAFE_LIMITATION],
    )
    assert preflight.is_exact_safe_answer(q, packet, ctx)
    assert not preflight.is_exact_safe_answer(q, candidate(), ctx)
    for key, val in [
        ("answer", "You get a bonus."),
        ("citations", ctx["sources"]),
        ("limitations", []),
        ("recommended_actions", ["ACTION:invented"]),
    ]:
        invalid = {**packet, key: val}
        assert not preflight.is_exact_safe_answer(q, invalid, ctx)


def test_preflight_does_not_claim_inference_when_model_unconfigured(monkeypatch):
    monkeypatch.delenv("EOC_OLLAMA_MODEL", raising=False)
    assert preflight.main() == 2


def test_preflight_uses_actual_transport_interface_with_three_checks_when_mocked(monkeypatch, capsys):
    monkeypatch.setenv("EOC_OLLAMA_MODEL", "gpt-oss:20b")
    monkeypatch.delenv("EOC_AI_PROVIDER", raising=False)
    calls = []
    def fake(ctx, question):
        calls.append(question)
        if question == "Does my policy guarantee a salary bonus?":
            packet = candidate(
                answer_type="UNSUPPORTED",
                answer=preflight.SAFE_ABSTENTION,
                citations=[],
                limitations=[preflight.SAFE_LIMITATION],
            )
        elif question == "What is the status of Manager Preparation?":
            packet = candidate(answer="Manager Preparation is READY.")
        else:
            packet = candidate()
        assert ctx["context_digest"]
        return packet, {"model": "gpt-oss:20b", "input_tokens": 10, "output_tokens": 20}
    monkeypatch.setattr(preflight, "infer_local", fake)
    assert preflight.main() == 0
    assert calls == [
        "Who owns Manager Preparation?", "What is the status of Manager Preparation?",
        "Does my policy guarantee a salary bonus?",
    ]
    out = capsys.readouterr().out
    assert "EOC_REAL_MAC_OLLAMA_TRANSPORT_PREFLIGHT=PASS" in out
    assert "NO Django authorization" in out
