"""
Repository-level pytest configuration (showcase-safe).

Why this exists:
  - Provide safe defaults for demo environments (no secrets embedded)
  - Make the repo more \"plug-and-play\" for reviewers cloning from GitHub
  - Keep behavior explicit and discoverable

Important:
  This repository is designed for portfolio display. Values below are placeholders.
  Real projects should load secrets from a secure secret manager in CI/CD.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Generator

import pytest


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Return repo root path."""
    return Path(__file__).parent


@pytest.fixture(scope="session", autouse=True)
def _demo_safe_env_defaults() -> Generator[None, None, None]:
    """
    Set demo-safe environment defaults if not already provided by the user/CI.

    This prevents accidental leakage and keeps local runs predictable.
    """
    defaults = {
        # UI
        "UI_BASE_URL": "http://localhost:3000",
        "UI_USERNAME": "demo_user",
        "UI_PASSWORD": "demo_password",
        # API
        "API_BASE_URL": "http://localhost:8000",
        "EXPECTED_API_VERSION": "1.0.0",
        "EXPECTED_UI_VERSION": "1.0.0",
    }

    for k, v in defaults.items():
        os.environ.setdefault(k, v)

    yield


