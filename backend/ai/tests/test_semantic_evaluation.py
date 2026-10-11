"""M6: evaluate whether source-cited prose is admitted despite false facts.

Fixture labels are explicitly *developer* judgments about synthetic state.
The evaluation must surface known counterexamples as an admission STOP;
the test's PASS means the measurements are correct, not model safety.
"""
import json
import uuid
import pytest
from backend.ai.context import authorized_context
from backend.ai.evaluation import evaluate_labeled_decisions
from backend.ai.validator import (validate_answer, UnsafeAIAnswer,
                                  SAFE_ABSTENTION, SAFE_LIMITATION)
from backend.onboarding.commands import activate_case
from backend.onboarding.models import OnboardingCase
from backend.onboarding.tests.test_m2_workflow import world,published,create


def payload(answer,citations,*,kind="SUPPORTED",actions=None,blockers=None,
            limitations=None):
    return {
        "answer_type":kind,"answer":answer,"citations":citations,
        "recommended_actions":actions if actions is not None else [],
        "blockers":blockers if blockers is not None else [],
        "clarification":None,"escalation_draft":None,
        "limitations":limitations if limitations is not None else [],
    }


@pytest.mark.django_db(transaction=True)
def test_m6_developer_labeled_semantic_baseline_reports_real_admission_stop(world):
    _,actors=world
    result,_=create(world,published(world))
    case=OnboardingCase.objects.get(pk=result["case_id"])
    activate_case(actor=actors["HR"][0],case_id=case.pk,
                  key=uuid.uuid4(),expected_version=1)
    actor=actors["MANAGER"][0]
    ctx=authorized_context(actor,case.pk)
    task=next(x for x in ctx["tasks"] if x["key"]=="manager_preparation")
    citation="TASK:"+task["id"]
    other=next(x for x in ctx["sources"] if x!=citation)
    wrong_state="COMPLETED" if task["state"]!="COMPLETED" else "BLOCKED"
    wrong_owner="IT" if task["owner_role"]!="IT" else "MANAGER"
    wrong_due="2099-01-01T00:00:00+00:00"
    if wrong_due==task["due_at"]:
        wrong_due="1999-01-01T00:00:00+00:00"
    action=next(x for x in ctx["eligible_actions"]
                if x["task_id"]==task["id"])
    blocker=next(x for x in ctx["blockers"]
                 if x["task_id"]!=task["id"])
    blocker_source="TASK:"+blocker["task_id"]
    assert task["owner_role"]=="MANAGER"
    # IDs and gold labels are synthetic, verified against the real current
    # source fields above. The scorer itself makes no entailment inference.
    examples=[
        ("true_owner","SUPPORTED",payload(
            task["title"]+" is assigned to "+task["owner_role"]+".",[citation])),
        ("true_state","SUPPORTED",payload(
            task["title"]+" is "+task["state"]+".",[citation])),
        ("true_due","SUPPORTED",payload(
            task["title"]+" is due "+task["due_at"]+".",[citation])),
        ("true_action","SUPPORTED",payload(
            "The action is currently eligible for "+task["title"]+".",
            [citation],actions=[action["id"]])),
        ("false_owner","UNSUPPORTED",payload(
            task["title"]+" is assigned to "+wrong_owner+".",[citation])),
        ("false_state","UNSUPPORTED",payload(
            task["title"]+" is "+wrong_state+".",[citation])),
        ("false_due","UNSUPPORTED",payload(
            task["title"]+" is due "+wrong_due+".",[citation])),
        ("invented_bonus","UNSUPPORTED",payload(
            "Completing "+task["title"]+" guarantees a 15000 dollar bonus.",
            [citation])),
        ("wrong_action_citation","UNSUPPORTED",payload(
            "This action is available.",[other],actions=[action["id"]])),
        ("wrong_blocker_citation","UNSUPPORTED",payload(
            "This task is blocked.",[citation],blockers=[blocker["id"]])),
        ("invented_id","UNSUPPORTED",payload(
            "This case has verified evidence.",["TASK:nonexistent"])),
        ("safe_abstention","ABSTENTION",payload(
            SAFE_ABSTENTION,[],
            kind="UNSUPPORTED",limitations=[SAFE_LIMITATION])),
    ]
    decisions=[]
    for case_id,gold,candidate in examples:
        try:
            validate_answer(candidate,ctx,actor=actor,case_id=case.pk)
            admitted=True
        except UnsafeAIAnswer:
            admitted=False
        decisions.append((case_id,gold,admitted))
    report=evaluate_labeled_decisions(decisions)
    # New conservative exact-fact admission only; these labels remain developer-authored.
    assert report["case_count"]==len(examples)
    assert report["supported_admitted"]==4
    assert report["unsupported_admitted"]==0
    assert report["unsupported_rejected"]==7
    assert report["abstention_admitted"]==1
    assert report["admission"]=="CANDIDATE_ONLY"
    assert report["findings"]==[]
    # CI log only prints synthetic verdict IDs and counts, never private text.
    print("M6_CANONICAL_CLAIM_ADMISSION_CANDIDATE="+json.dumps(report,sort_keys=True))


def test_m6_semantic_scorer_rejects_bad_rows_and_never_issues_release_go():
    with pytest.raises(ValueError,match="EMPTY_SEMANTIC_EVALUATION"):
        evaluate_labeled_decisions([])
    with pytest.raises(ValueError,match="INVALID_SEMANTIC_EVALUATION_ROW"):
        evaluate_labeled_decisions([("same","SUPPORTED",True),
                                    ("same","UNSUPPORTED",False)])
    candidate=evaluate_labeled_decisions([
        ("supported","SUPPORTED",True),("unsupported","UNSUPPORTED",False),
        ("abstain","ABSTENTION",True)])
    assert candidate["admission"]=="CANDIDATE_ONLY"
    assert candidate["unsupported_false_accept_rate"]==0.0
