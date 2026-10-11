"""Conservative question-to-verified-source relevance admission for model output.

A canonical fact and valid citation are *not sufficient* to answer an
unrelated question. Only exact, narrowly enumerated request grammars may
publish model-produced canonical facts. Unknown/compound/instruction-laden
requests may return a uniform abstention but never a misleading SUPPORTED
answer. This is NOT general semantic entailment and does not license a model.
"""
import re

from backend.ai.validator import UnsafeAIAnswer, canonical_policy_quote


POLICY_KEYS = {
    "conduct": "conduct_ack",
    "privacy": "privacy_ack",
    "benefits": "benefits_ack",
}


def _fullmatch(pattern, text):
    return re.fullmatch(pattern, text, flags=re.IGNORECASE) is not None


def _intent(question, context):
    if not isinstance(question, str):
        return None
    text = " ".join(question.strip().split())
    # Complete question matching rejects bonus clauses, source instructions,
    # extra requests and multiple task names rather than guessing relevance.
    possibilities = []
    for task in context["tasks"]:
        title = re.escape(task["title"])
        patterns = {
            "owner": rf"who (?:owns|is assigned to) {title}\??",
            "status": rf"(?:what is|what's) (?:the )?(?:status|state) of {title}\??",
            "due": rf"when is {title} due\??",
            "start": rf"can i (?:start|begin) {title}\??",
            "blocked": rf"(?:why is {title} blocked|what is blocking {title})\??",
        }
        for kind, pattern in patterns.items():
            if _fullmatch(pattern, text):
                possibilities.append((kind, task, "TASK:" + task["id"]))
    m = re.fullmatch(
        r"(?:what|which) (?:assigned )?(conduct|privacy|benefits) "
        r"policy edition is (?:assigned|available)\??",
        text, flags=re.IGNORECASE
    )
    if m is not None:
        possibilities.extend(_policy_intents(m.group(1), context, "edition"))
    m = re.fullmatch(
        r"quote the assigned (conduct|privacy|benefits) policy verbatim\??",
        text, flags=re.IGNORECASE
    )
    if m is not None:
        possibilities.extend(_policy_intents(m.group(1), context, "quote"))
    return possibilities[0] if len(possibilities) == 1 else None


def _policy_intents(label, context, kind):
    tasks = [t for t in context["tasks"]
             if t["key"] == POLICY_KEYS[label.lower()]
             and t["kind"] == "POLICY_ACK"]
    if len(tasks) != 1:
        return []
    source_prefix = "POLICY:" + tasks[0]["id"] + ":"
    policies = [p for p in context["policies"]
                if p["source_id"].startswith(source_prefix)]
    if len(policies) != 1:
        return []
    return [(kind, policies[0], policies[0]["source_id"])]


def ensure_question_relevance(question, payload, context):
    """Refuse unrelated but factually true model answers.

    Called ONLY after validate_answer's case/version authorization and
    exact canonical fact checks. Safe structured abstentions remain allowed.
    """
    if payload["answer_type"] == "UNSUPPORTED":
        return
    match = _intent(question, context)
    if match is None:
        raise UnsafeAIAnswer("QUESTION_INTENT_UNSUPPORTED_OR_AMBIGUOUS")
    kind, source, citation = match
    if payload["citations"] != [citation]:
        raise UnsafeAIAnswer("ANSWER_SOURCE_UNRELATED_TO_QUESTION")
    expected = None
    if kind == "owner":
        expected = source["title"] + " is assigned to " + source["owner_role"] + "."
    elif kind == "status":
        expected = source["title"] + " is " + source["state"] + "."
    elif kind == "due" and source["due_at"] is not None:
        expected = source["title"] + " is due " + str(source["due_at"]) + "."
    elif kind == "start":
        permitted = [
            item["id"] for item in context["eligible_actions"]
            if item["task_id"] == source["id"] and item["type"] == "START"
        ]
        if len(permitted) == 1 and payload["recommended_actions"] == permitted:
            expected = "The action is currently eligible for " + source["title"] + "."
    elif kind == "blocked":
        blockers = [b["id"] for b in context["blockers"]
                    if b["task_id"] == source["id"]]
        if (source["state"] == "BLOCKED" and len(blockers) == 1
                and payload["blockers"] == blockers):
            expected = source["title"] + " is currently blocked."
    elif kind == "edition":
        expected = "Assigned policy edition " + str(source["version"]) + " is available for review."
    elif kind == "quote" and payload["answer_type"] == "PARTIAL":
        expected = canonical_policy_quote(source)

    if (expected is None or payload["answer"] != expected
            or kind not in ("start",) and payload["recommended_actions"]
            or kind not in ("blocked",) and payload["blockers"]):
        raise UnsafeAIAnswer("ANSWER_NOT_RESPONSIVE_TO_QUESTION")
