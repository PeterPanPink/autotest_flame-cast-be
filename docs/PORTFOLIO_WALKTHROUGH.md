### Portfolio Walkthrough (What to look at first)

If you’re reviewing this repo as a hiring manager or tech lead, here is the fastest
path to understanding the architecture and engineering depth.

### 1) High-level entry point

- **`run_tests.py`**
  - Unified runner (API / UI / parallel / Allure)
  - Version check placeholders
  - CI-friendly output

### 2) API automation core

- **`testsuites/api_testing/framework/http_client.py`**
  - Retry logic, 429 handling, Allure attachments, cURL reproduction
- **`testsuites/api_testing/framework/token_manager.py`**
  - Token caching (optional `filelock` for cross-process locking)
- **`testsuites/api_testing/cases/*.yaml`**
  - Data-driven case definitions (easy to scale)
- **`testsuites/api_testing/tests/test_yaml_driven_cases.py`**
  - YAML runner example

### 3) UI automation core (AI-ready)

- **`testsuites/ui_testing/framework/smart_locator.py`**
  - Fallback locators + health report
  - `ai_locate_intent()` (demo-safe AI integration point)
- **`testsuites/ui_testing/framework/page_base.py`**
  - Base Page Object with screenshot/debug helpers
- **`testsuites/ui_testing/pages/*`**
  - Page Object Model examples

### 4) Tools / platform engineering

- **`autotest_tools/`**
  - log analyzer, notion integration, mongo tools
  - version checker utilities

### 5) CI/CD

- **`.github/workflows/*.yml`**
  - Separate workflows for API and UI
  - Allure artifact generation (demo-ready)

### Redaction policy

See `docs/SECURITY_REDACTION.md`.


