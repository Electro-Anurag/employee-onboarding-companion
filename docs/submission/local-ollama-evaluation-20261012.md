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
