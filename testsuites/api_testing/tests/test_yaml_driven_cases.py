"""
================================================================================
YAML-Driven API Tests (Showcase)
================================================================================

This module demonstrates a data-driven approach:
  - Test cases defined in YAML under `testsuites/api_testing/cases/`
  - Loaded via `TestCaseLoader` with variable interpolation
  - Executed by `HttpClient` (retry + Allure attachments)
  - Validated by `AssertionExecutor`

Why this matters for a GitHub portfolio:
  - Test logic stays small and reusable
  - Test data is readable by non-engineers
  - Easy to scale coverage by adding YAML entries

================================================================================
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

import allure
import pytest
from loguru import logger

from testsuites.api_testing.framework.assertion_executor import AssertionExecutor
from testsuites.api_testing.framework.http_client import HttpClient
from testsuites.api_testing.framework.test_case_loader import TestCase, TestCaseLoader


def _load_cases(file_path: Path) -> List[TestCase]:
    """Load YAML cases from a file (helper for parametrization)."""
    loader = TestCaseLoader(file_path.parent)
    loader.set_global_variables(
        {
            # Common showcase variables
            "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "future_time": (datetime.now() + timedelta(hours=1)).isoformat(),
            # Demo-safe placeholders
            "current_user_id": "user_demo",
            "test_channel_id": "ch_autotest_primary",
            "test_session_id": "se_autotest_primary",
            "test_room_id": "rm_autotest_primary",
            "created_channel_id": "ch_created_placeholder",
            "stopped_session_id": "se_stopped_placeholder",
            "live_session_id": "se_live_placeholder",
            "idle_session_id": "se_idle_placeholder",
        }
    )
    return loader.load_file(file_path)


CASES_DIR = Path(__file__).resolve().parents[1] / "cases"
CHANNEL_CASES = _load_cases(CASES_DIR / "channel_api.yaml")
SESSION_CASES = _load_cases(CASES_DIR / "session_api.yaml")


@allure.epic("API Testing")
@allure.feature("YAML-Driven Cases")
class TestYamlDrivenCases:
    """YAML-driven API cases runner."""

    @pytest.mark.P1
    @pytest.mark.regression
    @pytest.mark.parametrize("case", CHANNEL_CASES, ids=lambda c: c.name)
    def test_channel_yaml_case(self, http_client: HttpClient, case: TestCase):
        """Execute a single channel test case defined in YAML."""
        self._execute_case(http_client, case)

    @pytest.mark.P1
    @pytest.mark.regression
    @pytest.mark.parametrize("case", SESSION_CASES, ids=lambda c: c.name)
    def test_session_yaml_case(self, http_client: HttpClient, case: TestCase):
        """Execute a single session test case defined in YAML."""
        self._execute_case(http_client, case)

    def _execute_case(self, http_client: HttpClient, case: TestCase) -> None:
        """Shared execution logic for YAML-driven cases."""
        with allure.step(f"Send {case.method} {case.url}"):
            response = http_client.request(
                method=case.method,
                url=case.url,
                headers=case.headers or None,
                params=case.params or None,
                json=case.json_body or None,
            )

        with allure.step("Verify status code"):
            expected = case.expected_status
            if isinstance(expected, list):
                assert response.status_code in expected
            else:
                assert response.status_code == int(expected)

        with allure.step("Verify assertions"):
            try:
                data = response.json()
            except Exception:
                # For demo purposes, fall back to raw text
                data = {"raw": response.text}

            executor = AssertionExecutor(data)
            assertion_dicts: List[Dict] = [
                {
                    "type": a.assertion_type,
                    "field": a.field,
                    "expected": a.expected,
                    "description": a.description,
                }
                for a in case.assertions
            ]
            executor.execute_assertions(assertion_dicts)

            if not executor.all_passed():
                failures = executor.get_failures()
                logger.warning(f"YAML case failed: {case.name} -> {failures}")
                pytest.fail(f"Assertions failed for {case.name}: {failures}")


