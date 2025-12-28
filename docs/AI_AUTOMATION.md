### AI Automation Capabilities (Showcase)

This repository demonstrates **where AI fits** into a modern automation platform.
The implementation here is intentionally “safe-by-default” (no hard-coded secrets,
no external AI calls during normal test runs), but the architecture supports:

## AI + UI Automation

- **Self-healing locators**
  - When a `data-testid` breaks, the framework falls back to `aria-label`, role+name, and text.
  - Locator fallbacks are tracked (maintenance signal).

- **Intent-based element location**
  - A demo hook exists in `testsuites/ui_testing/framework/smart_locator.py`:
    - `SmartLocator.ai_locate_intent(intent: str)`
  - In real projects, this can be upgraded to:
    - capture DOM / accessibility tree
    - ask an LLM for a stable selector strategy
    - validate / persist the strategy for future runs

## AI + API Automation

- **Schema-driven negative testing**
  - `MutationGenerator` is designed to generate invalid payloads from schemas.
  - In real usage, AI can propose:
    - edge-case values
    - likely injection patterns
    - missing-field combinations aligned with backend validation style

- **YAML-driven test cases**
  - Under `testsuites/api_testing/cases/` you’ll find example YAML definitions.
  - `testsuites/api_testing/tests/test_yaml_driven_cases.py` shows how YAML cases
    can be loaded and executed.

## Where to plug real AI services (recommended)

- **Offline generation** (preferred):
  - Use AI to generate new YAML cases / page locators.
  - Commit the generated artifacts after review.
  - Keep CI deterministic.

- **Online inference** (optional):
  - Only enable AI calls via explicit CI flags (e.g., `ENABLE_AI=true`).
  - Always redact payloads before sending to any external AI provider.

## Non-goals for this portfolio repo

- No production secrets
- No external AI calls by default
- No customer data or internal endpoints


