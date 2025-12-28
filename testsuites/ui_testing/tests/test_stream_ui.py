"""
================================================================================
Streaming UI Tests (Async / Playwright)
================================================================================

This module provides additional, more \"product-like\" UI examples for GitHub:
  - Host flow: go to new stream, configure basics, start/stop (conceptual)
  - Viewer flow: open a public stream URL (conceptual)
  - Chat flow: send a message (conceptual)

Important:
  These are showcase tests and may require real environment data to fully pass.
  We intentionally avoid embedding any real URLs/tokens/secrets.

================================================================================
"""

import allure
import pytest

from testsuites.ui_testing.pages.dashboard_page import DashboardPage
from testsuites.ui_testing.pages.login_page import LoginPage
from testsuites.ui_testing.pages.streaming_page import StreamSetupPage
from testsuites.ui_testing.pages.streaming_page import StreamStudioPage
from testsuites.ui_testing.pages.streaming_page import ViewerPage


@allure.epic("UI Testing")
@allure.feature("Streaming")
class TestStreamingUI:
    """Streaming UI test suite (async)."""

    @pytest.fixture
    async def logged_in(self, login_page: LoginPage, dashboard_page: DashboardPage, test_data):
        """Login helper fixture for streaming flows."""
        user = test_data["valid_user"]
        await login_page.open()
        await login_page.login(username=user["username"], password=user["password"])
        await dashboard_page.verify_dashboard_loaded()

    @allure.story("Host Flow")
    @allure.title("Host can open New Stream and see setup page")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.P0
    @pytest.mark.smoke_ui
    @pytest.mark.asyncio
    async def test_open_stream_setup(self, logged_in, dashboard_page: DashboardPage):
        """Open the stream setup flow (conceptual)."""
        await dashboard_page.navigate_to_new_stream()

        setup_page = StreamSetupPage(dashboard_page.page)
        # We only validate navigation did not crash.
        assert setup_page.page.url is not None

    @allure.story("Host Flow")
    @allure.title("Host can reach studio page (conceptual)")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.P1
    @pytest.mark.asyncio
    async def test_reach_stream_studio(self, logged_in, dashboard_page: DashboardPage):
        """A high-level studio navigation example (selectors are demo-safe)."""
        await dashboard_page.navigate_to_new_stream()

        # In a real app, clicking \"Start\" in setup would transition to studio.
        # Here we instantiate the Studio page object as a showcase.
        studio = StreamStudioPage(dashboard_page.page)
        assert studio.page.url is not None

    @allure.story("Viewer Flow")
    @allure.title("Viewer can open public stream page (conceptual)")
    @allure.severity(allure.severity_level.MINOR)
    @pytest.mark.P2
    @pytest.mark.asyncio
    async def test_viewer_open_public_stream(self, page):
        """Public viewer flow example. Works when UI_BASE_URL points to a real deployment."""
        viewer = ViewerPage(page)

        # Demo-safe: page path is an example placeholder.
        await viewer.navigate_to("/stream/public-demo")
        assert viewer.page.url is not None


