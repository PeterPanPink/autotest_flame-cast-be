"""
================================================================================
Dashboard Page Object (Async / Playwright)
================================================================================

This module provides an async-first Dashboard Page Object.

Highlights:
  - Clean async API aligned with `playwright.async_api`
  - Uses stable locator priorities (data-testid -> aria -> text)
  - Contains workflow helpers used by showcase tests (logout, navigate to new stream)

================================================================================
"""

from __future__ import annotations

import allure
from loguru import logger
from playwright.async_api import expect

from testsuites.ui_testing.framework.page_base import PageBase


class DashboardPage(PageBase):
    """Dashboard page object (async)."""

    URL_PATH = "/dashboard"
    PAGE_TITLE = "Dashboard"

    @allure.step("Open dashboard")
    async def open(self) -> "DashboardPage":
        """Navigate to dashboard."""
        await self.navigate()
        await self.wait_for_page_load()
        return self

    @allure.step("Verify dashboard loaded")
    async def verify_dashboard_loaded(self) -> None:
        """Verify core dashboard elements are visible (demo selectors)."""
        # Prefer a stable testid if present; otherwise accept generic patterns.
        locator = self.page.locator(
            "[data-testid='dashboard-title'], [data-testid='nav-dashboard'], text=Dashboard"
        ).first
        await locator.wait_for(state="visible", timeout=15000)

    @allure.step("Navigate to New Stream flow")
    async def navigate_to_new_stream(self) -> None:
        """
        Navigate to the stream creation/studio flow.

        NOTE: Selectors are placeholders for showcase. Real apps should use stable testids.
        """
        btn = self.page.locator(
            "[data-testid='btn-new-stream'], button:has-text('New Stream'), a:has-text('New Stream')"
        ).first
        await btn.wait_for(state="visible", timeout=10000)
        await btn.click()
        await self.wait_for_page_load()

    @allure.step("Logout")
    async def logout(self) -> None:
        """Logout from the application (demo-safe)."""
        btn = self.page.locator(
            "[data-testid='btn-logout'], [aria-label='Logout'], button:has-text('Log Out')"
        ).first
        await btn.wait_for(state="visible", timeout=10000)
        await btn.click()

        # Best-effort wait: either back to login or public landing page
        try:
            await self.page.wait_for_url("**/login**", timeout=15000)
        except Exception:
            await self.wait_for_page_load()


