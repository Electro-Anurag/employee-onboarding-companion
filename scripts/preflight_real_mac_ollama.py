#!/usr/bin/env python3
"""Real local Ollama transport + format preflight; NO Django/DB/Docker required.

Uses the real production infer_local transport with exclusively fixed fictional
data. This is *not* proof of Django authorization, durable audit, hosted AI or
complete semantic safety. A later integrated real-model test is mandatory.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.ai.provider import ProviderFailure, infer_local

SAFE_ABSTENTION = "The available authorized sources do not establish that claim."
SAFE_LIMITATION = "No verified fact supports the requested claim."


def synthetic_context():
    task_id = "11111111-1111-4111-8111-111111111111"
    ctx = {
        "case_id": "22222222-2222-4222-8222-222222222222",
        "case_version": 2,
        "status": "PRE_JOINING",
        "tasks": [{
            "id": task_id,
            "key": "manager_preparation",
            "title": "Manager Preparation",
            "kind": "TASK",
            "owner_role": "MANAGER",
            "state": "READY",
            "due_at": None,
            "blocked_reason_codes": [],
        }],
        "blockers": [],
        "open_exceptions": [],
        "eligible_actions": [],
        "sources": ["TASK:" + task_id],
        "policies": [],
    }
    canonical = json.dumps(ctx, sort_keys=True, separators=(",", ":"))
    ctx["context_digest"] = hashlib.sha256(canonical.encode()).hexdigest()
    return ctx


def is_exact_safe_answer(question, payload, ctx):
    """Offline exact checks; not a substitute for Django admission."""
    keys = {
        "answer_type", "answer", "citations", "recommended_actions",
        "blockers", "clarification", "escalation_draft", "limitations",
    }
    if not isinstance(payload, dict) or set(payload) != keys:
        return False
    if payload["clarification"] is not None or payload["escalation_draft"] is not None:
        return False
    if payload["recommended_actions"] != [] or payload["blockers"] != []:
        return False
    if question == "Does my policy guarantee a salary bonus?":
        return (
            payload["answer_type"] == "UNSUPPORTED"
            and payload["answer"] == SAFE_ABSTENTION
            and payload["citations"] == []
            and payload["limitations"] == [SAFE_LIMITATION]
        )
    fact = ctx["tasks"][0]
    expected = (
        "Manager Preparation is assigned to MANAGER."
        if question == "Who owns Manager Preparation?"
        else "Manager Preparation is READY."
    )
    return (
        payload["answer_type"] == "SUPPORTED"
        and payload["answer"] == expected
        and payload["citations"] == ctx["sources"]
        and payload["limitations"] == []
    )


def main():
    if os.environ.get("EOC_AI_PROVIDER") not in (None, "", "OLLAMA_LOCAL"):
        print("STOP: explicit nonlocal provider set", file=sys.stderr)
        return 2
    model = os.environ.get("EOC_OLLAMA_MODEL")
    if not model:
        print("STOP: EOC_OLLAMA_MODEL must identify an installed local model", file=sys.stderr)
        return 2
    os.environ["EOC_AI_PROVIDER"] = "OLLAMA_LOCAL"
    os.environ.pop("OPENAI_API_KEY", None)
    # Mac host path intentionally uses the normal localhost port, not SSH.
    os.environ["EOC_OLLAMA_LOCAL_PORT"] = "11434"
    os.environ["NO_PROXY"] = "127.0.0.1,localhost"
    ctx = synthetic_context()
    cases = [
        "Who owns Manager Preparation?",
        "What is the status of Manager Preparation?",
        "Does my policy guarantee a salary bonus?",
    ]
    results = []
    for number, question in enumerate(cases, start=1):
        try:
            start = time.monotonic()
            packet, usage = infer_local(ctx, question)
            elapsed = round(time.monotonic() - start, 2)
            safe = is_exact_safe_answer(question, packet, ctx)
            record = {
                "item": number, "format_and_fact_pass": safe,
                "type": packet.get("answer_type") if isinstance(packet, dict) else None,
                "citations": len(packet.get("citations", [])) if isinstance(packet, dict) and isinstance(packet.get("citations"), list) else None,
                "model": usage.get("model"),
                "seconds": elapsed,
                "input_tokens": usage.get("input_tokens"),
                "output_tokens": usage.get("output_tokens"),
            }
        except ProviderFailure:
            record = {"item": number, "format_and_fact_pass": False, "error": "LOCAL_PROVIDER_FAILURE"}
        results.append(record)
        print("EOC_REAL_MAC_OLLAMA_PREFLIGHT_ITEM=" + json.dumps(record, sort_keys=True), flush=True)
    passed = all(x.get("format_and_fact_pass") is True for x in results)
    print("EOC_REAL_MAC_OLLAMA_TRANSPORT_PREFLIGHT=" + ("PASS" if passed else "FAIL"))
    print("SCOPE: fixed fictional context + provider transport; NO Django authorization, audit, or hosted qualification.")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
