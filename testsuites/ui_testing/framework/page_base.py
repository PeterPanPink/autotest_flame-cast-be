"""
================================================================================
Base Page Object
================================================================================

Foundation class for Page Object Model implementation.

Provides:
    - Common page interactions
    - Smart element location
    - Screenshot and debugging utilities
    - Wait strategies
    - API request capture

Author: Automation Team
License: MIT
================================================================================
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import allure
from loguru import logger
from playwright.async_api import Page, Response

from .smart_locator import SmartLocator


# Default output directory for screenshots
SCREENSHOT_DIR = Path(__file__).parent.parent / "screenshots"


class BasePage:
    """
    Base class for all page objects.
    
    Provides common functionality for:
        - Navigation and URL handling
        - Smart element interaction
        - Screenshot capture
        - API request/response logging
        - Wait utilities
    
    Usage:
        class LoginPage(BasePage):
            URL_PATH = "/login"
            
            async def login(self, username: str, password: str):
                await self.fill("username_input", username)
                await self.fill("password_input", password)
                await self.click("login_button")
    """

    # Override in subclasses
    URL_PATH: str = "/"
    PAGE_TITLE: str = ""

    def __init__(
        self,
        page: Page,
        base_url: str = "",
    ):
        """
        Initialize page object.
        
        Args:
            page: Playwright Page object
            base_url: Base URL for the application
        """
        self.page = page
        if not base_url:
            # Demo-safe default. Real deployments should override via config/env.
            base_url = os.getenv("UI_BASE_URL", "http://localhost:3000")
        self.base_url = base_url.rstrip("/")
        self.smart = SmartLocator(page)
        
        # API request capture
        self._captured_requests: List[Dict[str, Any]] = []
        self._setup_request_capture()

    def _setup_request_capture(self) -> None:
        """Set up API request/response capture for debugging."""
        
        async def capture_response(response: Response) -> None:
            if "/api/" in response.url:
                try:
                    body = await response.text()
                except Exception:
                    body = "<unable to read>"
                
                self._captured_requests.append({
                    "timestamp": datetime.now().isoformat(),
                    "url": response.url,
                    "status": response.status,
                    "body": body[:1000] if len(body) > 1000 else body,
                })
                
                # Keep only last 20 requests
                if len(self._captured_requests) > 20:
                    self._captured_requests.pop(0)
        
        self.page.on("response", capture_response)

    @property
    def url(self) -> str:
        """Get full page URL."""
        return f"{self.base_url}{self.URL_PATH}"

    async def navigate(self, wait_for: str = "networkidle") -> None:
        """
        Navigate to this page.
        
        Args:
            wait_for: Wait condition - 'load', 'domcontentloaded', 'networkidle'
        """
        with allure.step(f"Navigate to {self.URL_PATH}"):
            await self.page.goto(self.url, wait_until=wait_for)
            logger.debug(f"Navigated to: {self.url}")

    async def wait_for_page_load(
        self,
        state: str = "networkidle",
        timeout: int = 15000,
    ) -> None:
        """
        Wait for the page to reach a stable load state.

        Args:
            state: Playwright load state ('load', 'domcontentloaded', 'networkidle')
            timeout: Timeout in milliseconds
        """
        await self.page.wait_for_load_state(state, timeout=timeout)

    def smart_locator(
        self,
        primary: str,
        fallbacks: Optional[List[str]] = None,
        name: str = "custom_element",
    ) -> SmartLocator:
        """
        Build a SmartLocator in *element mode* with primary + fallback selectors.

        This is a convenience wrapper used by Page Objects that want to declare
        element locators as properties and resolve them later via `await .locate()`.

        Args:
            primary: Primary selector (recommended: data-testid)
            fallbacks: Fallback selectors to try when primary fails
            name: Human-readable element name for logging/Allure

        Returns:
            SmartLocator instance configured for a single element
        """
        locators: Dict[str, str] = {"primary": primary}
        for i, fb in enumerate(fallbacks or [], start=1):
            locators[f"fallback_{i}"] = fb
        return SmartLocator(self.page, element_name=name, locators=locators)

    async def navigate_to(
        self,
        path: str,
        wait_for: str = "networkidle",
    ) -> None:
        """
        Navigate to specific path.
        
        Args:
            path: URL path to navigate to
            wait_for: Wait condition
        """
        full_url = f"{self.base_url}{path}"
        with allure.step(f"Navigate to {path}"):
            await self.page.goto(full_url, wait_until=wait_for)

    # =========================================================================
    # Smart Element Interactions
    # =========================================================================

    async def click(
        self,
        element_name: str,
        timeout: int = 5000,
        **kwargs: Any,
    ) -> None:
        """
        Click element using smart location.
        
        Args:
            element_name: Name of element from SmartLocator
            timeout: Timeout for element location
            **kwargs: Additional click options
        """
        with allure.step(f"Click: {element_name}"):
            await self.smart.click(element_name, timeout, **kwargs)

    async def fill(
        self,
        element_name: str,
        value: str,
        timeout: int = 5000,
        **kwargs: Any,
    ) -> None:
        """
        Fill input element.
        
        Args:
            element_name: Name of input element
            value: Value to fill
            timeout: Timeout for element location
            **kwargs: Additional fill options
        """
        with allure.step(f"Fill {element_name}: {'*' * len(value) if 'password' in element_name.lower() else value}"):
            await self.smart.fill(element_name, value, timeout, **kwargs)

    async def get_text(
        self,
        element_name: str,
        timeout: int = 5000,
    ) -> str:
        """
        Get text content of element.
        
        Args:
            element_name: Name of element
            timeout: Timeout for element location
        
        Returns:
            Text content
        """
        return await self.smart.get_text(element_name, timeout)

    async def is_visible(
        self,
        element_name: str,
        timeout: int = 2000,
    ) -> bool:
        """
        Check if element is visible.
        
        Args:
            element_name: Name of element
            timeout: Timeout for visibility check
        
        Returns:
            True if visible
        """
        return await self.smart.is_visible(element_name, timeout)

    # =========================================================================
    # Direct Locator Access
    # =========================================================================

    async def click_selector(
        self,
        selector: str,
        timeout: int = 5000,
    ) -> None:
        """
        Click element by direct CSS selector.
        
        Use for one-off elements not in SmartLocator.
        """
        with allure.step(f"Click selector: {selector}"):
            await self.page.click(selector, timeout=timeout)

    async def fill_selector(
        self,
        selector: str,
        value: str,
        timeout: int = 5000,
    ) -> None:
        """
        Fill element by direct CSS selector.
        """
        with allure.step(f"Fill selector: {selector}"):
            await self.page.fill(selector, value, timeout=timeout)

    # =========================================================================
    # Wait Utilities
    # =========================================================================

    async def wait_for_url(
        self,
        url_pattern: str,
        timeout: int = 10000,
    ) -> None:
        """
        Wait for URL to match pattern.
        
        Args:
            url_pattern: URL pattern (supports wildcards)
            timeout: Timeout in milliseconds
        """
        with allure.step(f"Wait for URL: {url_pattern}"):
            await self.page.wait_for_url(url_pattern, timeout=timeout)

    async def wait_for_network_idle(self, timeout: int = 5000) -> None:
        """Wait for network to be idle."""
        await self.page.wait_for_load_state("networkidle", timeout=timeout)

    async def wait_for_element(
        self,
        selector: str,
        state: str = "visible",
        timeout: int = 5000,
    ) -> None:
        """
        Wait for element to reach specified state.
        
        Args:
            selector: CSS selector
            state: Target state - 'visible', 'hidden', 'attached', 'detached'
            timeout: Timeout in milliseconds
        """
        await self.page.wait_for_selector(selector, state=state, timeout=timeout)

    async def wait_for_toast(
        self,
        text: str,
        timeout: int = 5000,
    ) -> bool:
        """
        Wait for toast/notification with specific text.
        
        Args:
            text: Text to look for in toast
            timeout: Timeout in milliseconds
        
        Returns:
            True if toast appeared
        """
        try:
            toast = self.page.locator(f".toast:has-text('{text}')")
            await toast.wait_for(state="visible", timeout=timeout)
            return True
        except Exception:
            return False

    # =========================================================================
    # Screenshot and Debug Utilities
    # =========================================================================

    async def screenshot(
        self,
        name: str,
        full_page: bool = False,
        attach_to_allure: bool = True,
    ) -> Path:
        """
        Take screenshot and optionally attach to Allure.
        
        Args:
            name: Screenshot name (without extension)
            full_page: Capture full scrollable page
            attach_to_allure: Whether to attach to Allure report
        
        Returns:
            Path to saved screenshot
        """
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{timestamp}.png"
        filepath = SCREENSHOT_DIR / filename
        
        await self.page.screenshot(path=str(filepath), full_page=full_page)
        
        if attach_to_allure:
            with open(filepath, "rb") as f:
                allure.attach(
                    f.read(),
                    name=name,
                    attachment_type=allure.attachment_type.PNG
                )
        
        logger.debug(f"Screenshot saved: {filepath}")
        return filepath

    async def capture_failure(self, test_name: str) -> None:
        """
        Capture debugging information on test failure.
        
        Saves:
            - Screenshot
            - API requests log
            - Current URL
        """
        with allure.step("Capture failure details"):
            # Screenshot
            await self.screenshot(f"failure_{test_name}", attach_to_allure=True)
            
            # Current URL
            allure.attach(
                self.page.url,
                name="Current URL",
                attachment_type=allure.attachment_type.TEXT
            )
            
            # Recent API requests
            if self._captured_requests:
                allure.attach(
                    json.dumps(self._captured_requests[-10:], indent=2),
                    name="Recent API Requests",
                    attachment_type=allure.attachment_type.JSON
                )

    def get_locator_health_report(self) -> str:
        """Get smart locator health report."""
        return self.smart.get_health_report()


__all__ = [
    "BasePage",
    "PageBase",
]

# Backward-compatible alias (many Page Objects prefer PageBase naming)
PageBase = BasePage

