### Security & Redaction Notes (GitHub Portfolio Version)

This repository is a **portfolio-friendly** version of an internal automation framework.
To avoid leaking any sensitive information, the project intentionally uses:

- **Placeholder URLs** (e.g., `http://localhost:8000`, `http://localhost:3000`)
- **Demo credentials** (e.g., `demo_user / demo_password`)
- **Example configs only** under `config/` (`config.example.yaml`, `env.example.txt`)
- **No hard-coded API keys / tokens / tenant identifiers**
- **No production endpoints or customer data**

### What was intentionally removed or obfuscated

- **Real infrastructure**:
  - production/staging domains
  - internal network details
  - service accounts / IAM policies
- **Credentials**:
  - API keys
  - session tokens
  - database passwords
  - Notion secrets / Elasticsearch credentials
- **Company-specific logic**:
  - proprietary business rules
  - exact database schema / indexes
  - real error code catalog (only sample placeholders remain)

### How to run this repo safely

- **Local demo**:
  - Set `UI_BASE_URL` and `API_BASE_URL` to a sandbox environment you control.
  - Use dedicated demo users and demo data.
- **CI**:
  - Store secrets in GitHub Actions `Secrets` / `Variables`.
  - Do not commit `.env` files.

### Recommended CI secret names (examples)

- `API_BASE_URL`
- `SECURITY_API_KEY`
- `UI_BASE_URL`
- `UI_USERNAME`
- `UI_PASSWORD`
- `NOTION_TOKEN`
- `ELASTICSEARCH_URL`
- `ELASTICSEARCH_API_KEY`

### Design choice

This project favors **explicit placeholders** over hidden magic:
reviewers can clearly see where real values should be injected (env/config),
without risking accidental exposure.


