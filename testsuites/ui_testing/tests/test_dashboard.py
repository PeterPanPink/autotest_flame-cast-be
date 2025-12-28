"""
================================================================================
Dashboard UI Tests (Async / Playwright)
================================================================================

Showcase:
  - Async UI tests using shared Playwright browser/context fixtures
  - Login prerequisite via LoginPage
  - Post-login validations via DashboardPage

================================================================================
"""

import allure
import pytest

from testsuites.ui_testing.pages.dashboard_page import DashboardPage
from testsuites.ui_testing.pages.login_page import LoginPage


@allure.epic("UI Testing")
@allure.feature("Dashboard")
class TestDashboard:
    """Dashboard UI test suite (async)."""

    @allure.story("Page Load")
    @allure.title("Dashboard loads after login")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.P0
    @pytest.mark.smoke_ui
    @pytest.mark.asyncio
    async def test_dashboard_loads(self, login_page: LoginPage, dashboard_page: DashboardPage, test_data):
        """Verify dashboard loads for authenticated user."""
        user = test_data["valid_user"]

        await login_page.open()
        await login_page.login(username=user["username"], password=user["password"])

        await dashboard_page.verify_dashboard_loaded()

    @allure.story("Logout")
    @allure.title("User can logout from dashboard")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.P1
    @pytest.mark.regression_ui
    @pytest.mark.asyncio
    async def test_logout(self, login_page: LoginPage, dashboard_page: DashboardPage, test_data):
        """Verify logout returns user to login page (demo-safe)."""
        user = test_data["valid_user"]

        await login_page.open()
        await login_page.login(username=user["username"], password=user["password"])
        await dashboard_page.verify_dashboard_loaded()

        await dashboard_page.logout()
        assert "/login" in dashboard_page.page.url or "/dashboard" not in dashboard_page.page.url


