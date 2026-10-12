"""Explicit opt-in *real* Ollama admission check against fictional Django state.

Never runs an outbound request under routine CI. Uses the real `infer_local`
transport and normal authorization, relevance, citation and audit admission.
Passing mocked-transport unit tests is not a substitute for this check.
"""
import os
import uuid

import pytest

from backend.onboarding.tests.test_m2_workflow import create, published, world


@pytest.mark.django_db(transaction=True)
def test_real_ollama_case_bound_answers_and_unsupported_claim(world):
    if os.environ.get("EOC_RUN_REAL_OLLAMA_TEST") != "1":
        pytest.skip("real local Ollama test requires explicit EOC_RUN_REAL_OLLAMA_TEST=1")
    if os.environ.get("EOC_AI_PROVIDER") != "OLLAMA_LOCAL":
        pytest.fail("set EOC_AI_PROVIDER=OLLAMA_LOCAL explicitly")
    if not os.environ.get("EOC_OLLAMA_MODEL"):
        pytest.fail("select an already installed local model in EOC_OLLAMA_MODEL")

    from backend.ai.answers import answer_question
    from backend.audit.models import AuditEvent
    from backend.onboarding.commands import activate_case
    from backend.onboarding.models import OnboardingCase, TaskCompletion

    _, actors = world
    created, _ = create(world, published(world))
    case = OnboardingCase.objects.get(pk=created["case_id"])
    activate_case(actor=actors["HR"][0], case_id=case.pk,
                  key=uuid.uuid4(), expected_version=1)
    actor = actors["MANAGER"][0]
    before = TaskCompletion.objects.count()
    questions = [
        ("Who owns Manager Preparation?", "SUPPORTED"),
        ("What is the status of Manager Preparation?", "SUPPORTED"),
        ("Does my policy guarantee a salary bonus?", "UNSUPPORTED"),
    ]
    findings = []
    for question, expected in questions:
        result = answer_question(actor, case.pk, question)
        mode = result["mode"]
        answer_type = (
            result.get("answer", {}).get("answer_type")
            if mode == "MODEL_VALIDATED" else None
        )
        citations = (
            result.get("answer", {}).get("citations", [])
            if mode == "MODEL_VALIDATED" else []
        )
        # No answer text, context or user credentials enter the test output.
        findings.append((expected, mode, answer_type, len(citations),
                         result.get("error_code")))
        if expected == "UNSUPPORTED" and mode == "MODEL_VALIDATED":
            assert answer_type == "UNSUPPORTED", "model admitted an unsupported bonus claim"
            assert not citations, "unsupported answer must not cite invented evidence"
        assert mode in {"MODEL_VALIDATED", "DETERMINISTIC_FALLBACK"}
        assert result["ai_model_used"] is (mode == "MODEL_VALIDATED")
        assert TaskCompletion.objects.count() == before, "model must not mutate tasks"

    print("EOC_REAL_LOCAL_OLLAMA_SYNTHETIC_RESULTS", findings)
    attempts = AuditEvent.objects.filter(actor=actor, event_type="AI_MODEL_ATTEMPT").count()
    assert attempts == 3, "each evaluated question must attempt the real local model"
    assert AuditEvent.objects.filter(actor=actor,
                                     event_type="AI_MODEL_VALIDATED").count() == sum(
        finding[1] == "MODEL_VALIDATED" for finding in findings
    )
    # This is an actual inference admission gate, not merely successful HTTP.
    assert any(row[0] == "SUPPORTED" and row[1] == "MODEL_VALIDATED"
               and row[2] == "SUPPORTED" and row[3] == 1
               for row in findings), "no supported question survived model validation"
