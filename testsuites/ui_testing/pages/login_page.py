"""
================================================================================
Login Page Object (Async / Playwright)
================================================================================

This module provides an async-first Login Page Object.

Design goals:
  - Consistent with async Playwright fixtures used in `testsuites/ui_testing/tests/`
  - Uses SmartLocator for resilient element detection (primary + fallbacks)
  - Includes a *demo-safe* AI concept hook (`ai_login`) without external calls

NOTE:
  Selectors are intentionally generic for GitHub showcase purposes.
  Real projects should prefer stable `data-testid` attributes.

================================================================================
"""

from __future__ import annotations

import os
from typing import Optional

import allure
from loguru import logger
from playwright.async_api import expect

from testsuites.ui_testing.framework.page_base import PageBase


class LoginPage(PageBase):
    """Login page object (async)."""

    URL_PATH = "/login"
    PAGE_TITLE = "Login"

    @allure.step("Open login page")
    async def open(self) -> "LoginPage":
        """Navigate to the login page."""
        await self.navigate()
        await self.wait_for_page_load()
        return self

    @allure.step("Verify login form is displayed")
    async def verify_form_displayed(self) -> bool:
        """Verify login form elements are visible."""
        username_ok = await self.smart.is_visible("username_input", timeout=2000)
        password_ok = await self.smart.is_visible("password_input", timeout=2000)
        button_ok = await self.smart.is_visible("login_button", timeout=2000)
        return username_ok and password_ok and button_ok

    @allure.step("Login (username={username})")
    async def login(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        wait_dashboard: bool = True,
    ) -> None:
        """
        Perform login.

        Args:
            username: Username to login. Defaults to `UI_USERNAME` env var (demo-safe).
            password: Password to login. Defaults to `UI_PASSWORD` env var (demo-safe).
            wait_dashboard: Whether to wait for a dashboard URL after login.
        """
        # Best-effort: ensure we are on login page (useful for reusable fixtures)
        try:
            if "/login" not in (self.page.url or ""):
                await self.open()
        except Exception:
            await self.open()

        if username is None:
            username = os.getenv("UI_USERNAME", "demo_user")
        if password is None:
            password = os.getenv("UI_PASSWORD", "demo_password")

        await self.smart.fill("username_input", username, timeout=8000)
        await self.smart.fill("password_input", password, timeout=8000)
        await self.smart.click("login_button", timeout=8000)

        if wait_dashboard:
            # Demo-friendly: accept either /dashboard or any post-login route
            try:
                await self.page.wait_for_url("**/dashboard**", timeout=15000)
            except Exception:
                await self.wait_for_page_load()

    @allure.step("AI login (concept demo)")
    async def ai_login(self) -> None:
        """
        Conceptual AI-assisted login.

        This method demonstrates how a framework *could* use natural-language intents
        to locate elements (LLM-powered in real projects). Here, it uses heuristic
        matching implemented in `SmartLocator.ai_locate_intent()` (no external calls).
        """
        username = os.getenv("UI_USERNAME", "demo_user")
        password = os.getenv("UI_PASSWORD", "demo_password")

        user_input = await self.smart.ai_locate_intent("username or email input")
        pass_input = await self.smart.ai_locate_intent("password input")
        login_btn = await self.smart.ai_locate_intent("login button")

        await user_input.fill(username)
        await pass_input.fill(password)
        await login_btn.click()

        await self.wait_for_page_load()

    @allure.step("Verify login error is displayed")
    async def verify_error_displayed(self) -> bool:
        """Verify an error toast/message is visible after failed login."""
        # Prefer toast error if available, fall back to generic error container
        if await self.smart.is_visible("toast_error", timeout=1500):
            return True
        locator = self.page.locator("[data-testid='error-message'], .error-message, .alert-danger")
        try:
            await locator.first.wait_for(state="visible", timeout=1500)
            return await locator.first.is_visible()
        except Exception:
            return False

    async def assert_login_page_loaded(self) -> None:
        """Hard assertion helper used by tests."""
        assert await self.verify_form_displayed(), "Login form should be visible"


