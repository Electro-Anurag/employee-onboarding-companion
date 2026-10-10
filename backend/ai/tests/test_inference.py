"""M6 model adapter contract tests; no real provider or billing is used here."""
import json
import uuid
import pytest
from backend.audit.models import AuditEvent
from backend.onboarding.commands import activate_case
from backend.onboarding.models import OnboardingCase, TaskCompletion
from backend.onboarding.tests.test_m2_workflow import world, published, create
from backend.ai.context import authorized_context
from backend.ai.answers import answer_question
from backend.ai.provider import infer


@pytest.fixture
def m6_case(world):
    _, actors = world
    made, _ = create(world, published(world))
    case = OnboardingCase.objects.get(pk=made['case_id'])
    activate_case(actor=actors['HR'][0], case_id=case.pk,
                  key=uuid.uuid4(), expected_version=1)
    return case, actors


def _synthetic_answer(ctx):
    return {
        'answer_type': 'SUPPORTED',
        'answer': 'Read the assigned synthetic conduct policy and complete eligible acknowledgements.',
        'citations': [next(x for x in ctx['sources'] if x.startswith('POLICY:'))],
        'recommended_actions': [], 'blockers': [],
        'clarification': None, 'escalation_draft': None, 'limitations': [],
    }


@pytest.mark.django_db(transaction=True)
def test_m6_disabled_provider_is_truthful_fallback_without_external_call(monkeypatch, m6_case):
    case, actors = m6_case
    monkeypatch.delenv('EOC_AI_PROVIDER', raising=False)
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    monkeypatch.setattr('backend.ai.answers.infer',
                        lambda *_: pytest.fail('Provider must not be called'))
    result = answer_question(actors['EMPLOYEE'][0], case.pk, 'What is the conduct policy?')
    assert result['mode'] == 'DETERMINISTIC_FALLBACK'
    assert result['ai_model_used'] is False
    assert result['guidance']['mode'] == 'DETERMINISTIC_ONLY'
    assert not AuditEvent.objects.filter(event_type='AI_MODEL_ATTEMPT').exists()


@pytest.mark.django_db(transaction=True)
def test_m6_validated_source_and_bounded_provider_audit(monkeypatch, m6_case):
    case, actors = m6_case
    ctx = authorized_context(actors['EMPLOYEE'][0], case.pk)
    assert any(x.startswith('POLICY:') for x in ctx['sources'])
    assert ctx['policies'] and all(p['text'] for p in ctx['policies'])
    assert 'employee_email' not in str(ctx)
    monkeypatch.setenv('EOC_AI_PROVIDER', 'OPENAI')
    monkeypatch.setenv('OPENAI_API_KEY', 'synthetic-test-token-not-real')
    def fake_infer(snapshot, question):
        assert snapshot['context_digest'] == ctx['context_digest']
        assert question == 'What is the conduct policy?'
        return _synthetic_answer(snapshot), {
            'model': 'gpt-4o-mini', 'response_id': 'test-only-not-real',
            'input_tokens': 80, 'output_tokens': 45,
        }
    monkeypatch.setattr('backend.ai.answers.infer', fake_infer)
    before = TaskCompletion.objects.count()
    for _ in range(3):
        result = answer_question(actors['EMPLOYEE'][0], case.pk,
                                 'What is the conduct policy?')
        assert result['mode'] == 'MODEL_VALIDATED'
        assert result['ai_model_used']
        assert result['answer']['citations'][0] in ctx['sources']
    limited = answer_question(actors['EMPLOYEE'][0], case.pk,
                              'What is the conduct policy?')
    assert limited['mode'] == 'DETERMINISTIC_FALLBACK'
    assert limited['error_code'] == 'DAILY_INFERENCE_LIMIT'
    assert TaskCompletion.objects.count() == before
    assert AuditEvent.objects.filter(event_type='AI_MODEL_ATTEMPT').count() == 3
    assert AuditEvent.objects.filter(event_type='AI_MODEL_VALIDATED').count() == 3


@pytest.mark.django_db(transaction=True)
def test_m6_untrusted_model_citation_is_rejected_and_logged(monkeypatch, m6_case):
    case, actors = m6_case
    monkeypatch.setenv('EOC_AI_PROVIDER', 'OPENAI')
    monkeypatch.setenv('OPENAI_API_KEY', 'synthetic-test-token-not-real')
    def forged(ctx, question):
        payload = _synthetic_answer(ctx)
        payload['citations'] = ['POLICY:invented']
        return payload, {'model': 'gpt-4o-mini', 'response_id': 'test-only',
                         'input_tokens': 10, 'output_tokens': 20}
    monkeypatch.setattr('backend.ai.answers.infer', forged)
    result = answer_question(actors['EMPLOYEE'][0], case.pk, 'Policy?')
    assert result['ai_model_used'] is False
    assert result['error_code'] == 'MODEL_OUTPUT_REJECTED'
    assert AuditEvent.objects.filter(event_type='AI_MODEL_ATTEMPT').count() == 1
    assert AuditEvent.objects.filter(event_type='AI_MODEL_FAILED').count() == 1
    assert not AuditEvent.objects.filter(event_type='AI_MODEL_VALIDATED').exists()


def test_m6_provider_request_boundaries_and_exact_text_extraction(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', 'synthetic-no-billing-token')
    monkeypatch.setenv('EOC_AI_MODEL', 'gpt-4o-mini')
    class FakeStream:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self, n): return json.dumps({
            'status': 'completed', 'id': 'resp_synthetic', 'usage': {
                'input_tokens': 18, 'output_tokens': 12,
            }, 'output': [{'type': 'message', 'content': [{
                'type': 'output_text', 'text': json.dumps({
                    'answer_type': 'UNSUPPORTED', 'answer': 'No approved source',
                    'citations': [], 'recommended_actions': [], 'blockers': [],
                    'clarification': None, 'escalation_draft': None,
                    'limitations': ['Missing source'],
                }),
            }]}],
        }).encode()
    def fake_urlopen(req, timeout):
        assert req.full_url == 'https://api.openai.com/v1/responses'
        assert timeout == 12
        payload = json.loads(req.data)
        assert payload['store'] is False
        assert payload['max_output_tokens'] == 650
        assert payload['text']['format']['strict'] is True
        return FakeStream()
    monkeypatch.setattr('backend.ai.provider.request.urlopen', fake_urlopen)
    result, usage = infer({'sources': [], 'tasks': [], 'policies': []}, 'Unknown policy?')
    assert result['answer_type'] == 'UNSUPPORTED'
    assert usage['response_id'] == 'resp_synthetic'
