"""
================================================================================
Login Feature UI Tests (Async / Playwright)
================================================================================

Showcase goals:
  - Async-first UI automation with Playwright
  - Page Object Model (LoginPage + DashboardPage)
  - SmartLocator usage (fallback locators)
  - Demo-safe AI hook (`ai_login`) for international GitHub audiences

Note:
  This repository is a *portfolio-friendly* showcase. Selectors and flows are
  intentionally generic. Real projects should integrate stable `data-testid`s
  and environment-specific URLs/credentials via configuration.

================================================================================
"""

import allure
import pytest

from testsuites.ui_testing.pages.dashboard_page import DashboardPage
from testsuites.ui_testing.pages.login_page import LoginPage


@allure.epic("UI Testing")
@allure.feature("Authentication")
class TestLogin:
    """Login UI test suite (async)."""

    @allure.story("Happy Path")
    @allure.title("Login succeeds with valid credentials")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.P0
    @pytest.mark.smoke_ui
    @pytest.mark.asyncio
    async def test_login_success(self, login_page: LoginPage, dashboard_page: DashboardPage, test_data):
        """Verify user can login and reach dashboard."""
        user = test_data["valid_user"]

        with allure.step("Open login page and verify form"):
            await login_page.open()
            await login_page.assert_login_page_loaded()

        with allure.step("Login"):
            await login_page.login(username=user["username"], password=user["password"])

        with allure.step("Verify dashboard loaded"):
            assert "/dashboard" in login_page.page.url
            await dashboard_page.verify_dashboard_loaded()

    @allure.story("Negative Path")
    @allure.title("Login fails with invalid credentials")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.P0
    @pytest.mark.smoke_ui
    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, login_page: LoginPage, test_data):
        """Verify invalid credential login displays an error."""
        user = test_data["invalid_user"]

        await login_page.open()
        await login_page.login(username=user["username"], password=user["password"], wait_dashboard=False)

        assert "/login" in login_page.page.url or "/dashboard" not in login_page.page.url
        assert await login_page.verify_error_displayed()

    @allure.story("Form Validation")
    @allure.title("Login fails with empty username")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.P1
    @pytest.mark.regression_ui
    @pytest.mark.asyncio
    async def test_login_empty_username(self, login_page: LoginPage, test_data):
        """Verify basic validation blocks empty username submissions (demo)."""
        user = test_data["valid_user"]

        await login_page.open()

        # Intentionally only fill password; selectors are demo-safe
        await login_page.smart.fill("password_input", user["password"])
        await login_page.smart.click("login_button")

        # App may show inline validation or toast error; accept either for showcase.
        assert await login_page.verify_error_displayed() or "/login" in login_page.page.url

    @allure.story("AI Assistance")
    @allure.title("AI-assisted login demo (heuristic, no external calls)")
    @allure.severity(allure.severity_level.MINOR)
    @pytest.mark.P2
    @pytest.mark.asyncio
    async def test_ai_login_demo(self, login_page: LoginPage):
        """Showcase how AI hooks could be integrated safely."""
        await login_page.open()
        await login_page.ai_login()
        # This is a demo, so we only assert the flow did not crash.
        assert login_page.page.url is not None


