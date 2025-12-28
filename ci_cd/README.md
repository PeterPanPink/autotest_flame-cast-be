# CI/CD Examples

This folder ships a copy-paste-ready GitHub Actions sample (`github_actions.example.yml`). How to use:

1) Copy the content into `.github/workflows/tests.yml` (or your preferred name).  
2) In GitHub Settings -> Secrets and variables -> Actions, configure these secrets (placeholders only; never commit real values): `API_BASE_URL`, `SECURITY_API_KEY`, `UI_BASE_URL`, `UI_USERNAME`, `UI_PASSWORD`, `NOTION_TOKEN`, `ELASTICSEARCH_URL`, `ELASTICSEARCH_API_KEY`.  
3) By default it runs API/UI tests; UI runs headless. Adjust branch triggers, dependencies, and reporting steps as needed.  
4) Optional: uncomment the Allure report generation and artifact upload steps to keep the report; install `allure-commandline` first if you enable it.  
5) For local pre-checks, pair with a pre-commit hook or lightweight secret scan (e.g., gitleaks/rg rules) to ensure `.env` and real keys are never committed.

