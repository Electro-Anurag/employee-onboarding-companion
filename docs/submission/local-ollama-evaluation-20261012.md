# Optional local real-model evaluation with Ollama

The senior's EOC assignment does **not** require paid API infrastructure. A local real-model demo may run on the owner's own machine, using fictional onboarding data only. This path is **OFF by default** and never contacts the paid OpenAI endpoint.

## Source transport

- Opt in explicitly with `EOC_AI_PROVIDER=OLLAMA_LOCAL` and `EOC_OLLAMA_MODEL=<installed-model-name>`.
- Fixed endpoint: `http://127.0.0.1:11434/api/chat`. No configurable host; no external provider, network proxy override or arbitrary URL.
- Strict JSON schema derived from existing `OUTPUT_SCHEMA`, stream disabled, zero temperature, 650-token output, 16KB authorized context, 64KB maximum response, 45-second timeout.
- The existing shared validation in `answer_question` **still** checks current role/case state, limited supported question grammar, exact source citations, one valid fact, no freeform generated workflow commands, no unauthorized tool execution, audited attempts, max 3 attempts per user per 24 hours, and safe fallback.
- If the local model is unavailable, too slow, returns an incomplete answer, fails claim admission or hallucinates, the app shows a **deterministic fallback explicitly marked not AI**.
- No model has been admitted through actual Ollama runtime merely because the mocked transport CI passes. Verify `MODEL_VALIDATED` against genuinely supported questions and safe unsupported responses in the running local model before claiming it as a real AI demo.

## Local synthetic-only demo (owner's computer)

Install/start Ollama through its official workflow, and choose a model that is already locally installed and approved for testing, e.g., `gpt-oss:20b` if present. **Do not download any additional model automatically from EOC.**

```bash
export EOC_AI_PROVIDER=OLLAMA_LOCAL
export EOC_OLLAMA_MODEL='gpt-oss:20b'
# Run the project's Django server with its isolated synthetic local PostgreSQL.
# Ollama must be accessible on the SAME host as Django at 127.0.0.1:11434.
```

If Django runs inside a container/VM and Ollama runs on macOS, loopback points to the container/VM, **not** the host. Do not open Ollama on `0.0.0.0` or public internet to work around this. Use a supported **local-only** server placement instead, or report that live model inference was not demonstrated.

Suggested exact synthetic prompts after HR creates/activates the case:
- Manager: `Who owns Manager Preparation?`
- Manager: `What is the status of Manager Preparation?`
- Employee: `Which benefits policy edition is available?` (note: this may be fulfilled by the deterministic policy reader, explicitly marked NOT AI)
- Employee: `Does my policy guarantee a salary bonus?` (unsupported, should abstain)

Record the response's `mode` and `ai_model_used`; only `MODEL_VALIDATED` plus `ai_model_used=true` is a real model-validated result. Never include credentials, question logs with real personal data, or copied identity documents in a demonstration.

**Hosting:** Render Free will remain `EOC_AI_PROVIDER=DISABLED` unless explicitly authorized. This local adapter does not make J04 a hosted PASS.

## Real-model admission gate added 12 October 2026 — NOT YET EXECUTED

Test source: `backend/ai/tests/test_ollama_live_synthetic.py`, committed as `881446c675c3ae6b4de70340dc0db68dc1258c18`. It is **skipped by default**. Ordinary PostgreSQL/CI regressions or a successful mock do not establish that Ollama returned an acceptable answer.

Prerequisites: a privately installed Ollama model on the **same machine that runs Django/pytest**; an isolated, disposable PostgreSQL test database with the project's migrations and local development dependencies; absolutely no real employee data. Do **not** use the shared hosted PostgreSQL, Render credentials or a paid provider. Ensure your test environment points to your private local DB and Ollama at loopback. From the repository root, explicitly opt in:

```bash
EOC_RUN_REAL_OLLAMA_TEST=1 \
EOC_AI_PROVIDER=OLLAMA_LOCAL \
EOC_OLLAMA_MODEL='gpt-oss:20b' \
uv run pytest -q -s backend/ai/tests/test_ollama_live_synthetic.py
```

Use the model name only when `ollama list` confirms it is already installed. The test constructs **fictional** HR, Employee, Manager and IT identities and a new activated 17-task case in the local pytest database. It sends three bounded Manager questions through the **real localhost transport** and the same case-scoped authorization, source citation, semantic admission, auditing, fallback and model-call quota as the app. The first two ask the owner and status of Manager Preparation; the third challenges an unsupported bonus guarantee. It requires three genuine audited model attempts, at least one validated supported answer citing exactly one source, truthful model-use flags, no unsupported model-accepted bonus claim and no task mutation. It prints **modes/counts, not raw answer text**.

**Qualification remains OPEN** until the opt-in command really runs and its exact model, machine, app SHA, PostgreSQL isolation, observed modes, positive/negative acceptance and output are preserved. A failing or entirely fallback-only run is a substantive model admission failure, not a qualified demo. A clean run still proves only this three-question sample, not hallucination resistance in general or a hosted J04 pass. Citation fabrication / provider outages continue to be probed by separate controlled contract tests; do not conflate them with a real-model adversarial demonstration. Never expose Ollama on the public network to make the local test work.
