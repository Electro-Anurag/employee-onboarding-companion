"""Opt-in provider transport rejection paths, entirely fake HTTP, zero billing."""
import json
from urllib.error import HTTPError, URLError
from io import BytesIO
import pytest
from backend.ai.provider import infer, ProviderFailure


class Response:
    def __init__(self, content):
        self.data = content
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, size):
        return self.data[:size]


def envelope(*, output=None, status="completed", usage=None):
    if output is None:
        output = [{
            "type": "message",
            "content": [{"type": "output_text", "text": json.dumps({
                "answer_type": "UNSUPPORTED",
                "answer": "The available authorized sources do not establish that claim.",
                "citations": [], "recommended_actions": [], "blockers": [],
                "clarification": None, "escalation_draft": None,
                "limitations": ["No verified fact supports the requested claim."],
            })}],
        }]
    return json.dumps({
        "id": "resp_synthetic", "status": status,
        "usage": usage if usage is not None else {
            "input_tokens": 3, "output_tokens": 9,
        },
        "output": output,
    }).encode()


def setup(monkeypatch, data):
    monkeypatch.setenv("OPENAI_API_KEY", "dummy-no-network")
    monkeypatch.setenv("EOC_AI_MODEL", "gpt-4o-mini")
    def urlopen(req, timeout):
        assert req.full_url == "https://api.openai.com/v1/responses"
        assert timeout == 12
        body = json.loads(req.data)
        assert body["store"] is False
        assert body["max_output_tokens"] == 650
        assert body["text"]["format"]["strict"] is True
        assert "Bearer dummy-no-network" == req.headers["Authorization"]
        return Response(data)
    monkeypatch.setattr("backend.ai.provider.request.urlopen", urlopen)


def test_completed_envelope_uses_one_output_and_counts_usage(monkeypatch):
    setup(monkeypatch, envelope())
    answer, usage = infer({"sources": []}, "What do we know?")
    assert answer["answer_type"] == "UNSUPPORTED"
    assert usage["model"] == "gpt-4o-mini"
    assert usage["input_tokens"] == 3
    assert usage["output_tokens"] == 9


@pytest.mark.parametrize("body", [
    envelope(status="incomplete"),
    envelope(output=[]),
    envelope(output=[{"type":"message","content":[{"type":"refusal","refusal":"No"}]}]),
    envelope(output=[{"type":"message","content":[{"type":"output_text","text":"{}"}]},
                     usage={"input_tokens":"wrong", "output_tokens":9}),
    envelope(output=[{"type":"message","content":[{"type":"output_text","text":"{"}]}]),
    envelope(output=[{"type":"message","content":[
        {"type":"output_text","text":"{}"}, {"type":"output_text","text":"{}"}
    ]}]),
    b"\xff",
    b"not json",
    b"X" * 65537,
])
def test_incomplete_refusal_duplicate_bad_usage_and_oversize_are_rejected(monkeypatch, body):
    setup(monkeypatch, body)
    with pytest.raises(ProviderFailure):
        infer({"sources":[]}, "Show the benefits edition?")


def test_http_error_is_redacted_and_not_retried(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "dummy-no-network")
    calls = []
    def bad(request, timeout):
        calls.append(1)
        raise HTTPError(request.full_url, 429,
                        "provider internal token:DO_NOT_LEAK", {}, BytesIO(b"secret"))
    monkeypatch.setattr("backend.ai.provider.request.urlopen", bad)
    with pytest.raises(ProviderFailure, match="PROVIDER_TRANSPORT_OR_FORMAT_FAILURE") as exc:
        infer({"sources":[]}, "Will I be paid?")
    assert "DO_NOT_LEAK" not in str(exc.value)
    assert len(calls) == 1


def test_missing_configuration_and_oversize_context_do_not_call_network(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("backend.ai.provider.request.urlopen",
                        lambda *_args, **_kwargs: pytest.fail("No external calls allowed"))
    with pytest.raises(ProviderFailure, match="PROVIDER_NOT_CONFIGURED"):
        infer({}, "Hello?")
    monkeypatch.setenv("OPENAI_API_KEY", "dummy-no-network")
    with pytest.raises(ProviderFailure, match="CONTEXT_TOO_LARGE"):
        infer({"untrusted_text": "X" * 17000}, "Hello?")


def test_provider_timeout_does_not_disclose_question(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "dummy-no-network")
    def timeout(_req, timeout):
        raise TimeoutError("PRIVATE QUESTION VALUE")
    monkeypatch.setattr("backend.ai.provider.request.urlopen", timeout)
    with pytest.raises(ProviderFailure, match="PROVIDER_TRANSPORT_OR_FORMAT_FAILURE") as err:
        infer({"sources":[]}, "PRIVATE QUESTION VALUE")
    assert "PRIVATE QUESTION VALUE" not in str(err.value)
