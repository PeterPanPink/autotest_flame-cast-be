"""
================================================================================
Smart Locator with AI-Assisted Element Detection
================================================================================

Intelligent element location system with:
    - Multiple fallback locator strategies
    - Automatic degradation when primary locator fails
    - Self-healing capabilities with usage analytics
    - AI-assisted locator generation from natural language

Author: Automation Team
License: MIT
================================================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

from loguru import logger
from playwright.async_api import Locator, Page


class ElementNotFoundError(Exception):
    """Raised when all locator strategies fail to find element."""
    pass


@dataclass
class LocatorHealth:
    """
    Tracks locator health and usage statistics.
    
    Attributes:
        element_name: Human-readable element name
        primary_selector: The preferred selector
        used_fallback: Whether a fallback was used
        fallback_name: Name of fallback used (if any)
        fallback_selector: The fallback selector used (if any)
    """
    element_name: str
    primary_selector: str
    used_fallback: bool = False
    fallback_name: Optional[str] = None
    fallback_selector: Optional[str] = None


class SmartLocator:
    """
    AI-assisted smart element locator with fallback strategies.
    
    Features:
        - Multiple locator strategies per element
        - Automatic fallback on primary locator failure
        - Usage analytics for maintenance insights
        - Natural language to selector conversion (AI-powered)
    
    Locator Priority Order:
        1. data-testid (most stable, recommended)
        2. aria-label (accessibility-based)
        3. role + name combination
        4. Visible text content
        5. CSS selectors
        6. XPath (last resort)
    
    Usage:
        >>> smart = SmartLocator(page)
        >>> await smart.click("login_button")
        >>> await smart.fill("username_input", "test_user")
        
    Configuration:
        Locators are defined in the LOCATORS dictionary. Each element
        can have multiple fallback strategies.
    """

    # Locator definitions with fallback strategies
    # Format: element_name -> {strategy_name: selector}
    LOCATORS: Dict[str, Dict[str, str]] = {
        # Authentication elements
        "login_button": {
            "primary": "[data-testid='btn-login']",
            "fallback_1": "[aria-label='Login']",
            "fallback_2": "button:has-text('Log In')",
            "fallback_3": "#login-button",
        },
        "logout_button": {
            "primary": "[data-testid='btn-logout']",
            "fallback_1": "[aria-label='Logout']",
            "fallback_2": "button:has-text('Log Out')",
        },
        "username_input": {
            "primary": "[data-testid='input-username']",
            "fallback_1": "#username",
            "fallback_2": "input[name='username']",
            "fallback_3": "input[placeholder*='Username']",
        },
        "password_input": {
            "primary": "[data-testid='input-password']",
            "fallback_1": "#password",
            "fallback_2": "input[name='password']",
            "fallback_3": "input[type='password']",
        },
        
        # Navigation elements
        "nav_dashboard": {
            "primary": "[data-testid='nav-dashboard']",
            "fallback_1": "a[href='/dashboard']",
            "fallback_2": "nav >> text=Dashboard",
        },
        "nav_settings": {
            "primary": "[data-testid='nav-settings']",
            "fallback_1": "a[href='/settings']",
            "fallback_2": "nav >> text=Settings",
        },
        
        # Common UI elements
        "submit_button": {
            "primary": "[data-testid='btn-submit']",
            "fallback_1": "button[type='submit']",
            "fallback_2": "button:has-text('Submit')",
        },
        "cancel_button": {
            "primary": "[data-testid='btn-cancel']",
            "fallback_1": "button:has-text('Cancel')",
        },
        "close_modal": {
            "primary": "[data-testid='btn-close-modal']",
            "fallback_1": "[aria-label='Close']",
            "fallback_2": ".modal-close",
        },
        
        # Toast/notification elements
        "toast_success": {
            "primary": "[data-testid='toast-success']",
            "fallback_1": ".toast.success",
            "fallback_2": "[role='alert']:has-text('success')",
        },
        "toast_error": {
            "primary": "[data-testid='toast-error']",
            "fallback_1": ".toast.error",
            "fallback_2": "[role='alert']:has-text('error')",
        },
    }

    async def ai_locate_intent(
        self,
        intent: str,
        timeout: int = 5000,
    ) -> Locator:
        """
        Conceptual AI-assisted locator.

        In a real production framework, this method could:
        - Capture a DOM snapshot (or accessibility tree)
        - Ask an LLM to propose a stable selector strategy
        - Validate the selector against the current page
        - Store/learn the selector for future runs (self-healing)

        For this GitHub showcase, we intentionally keep this implementation
        **heuristic-based** (no external AI calls) to avoid leaking secrets.

        Args:
            intent: Natural-language intent, e.g. \"the username input\"
            timeout: Timeout in milliseconds

        Returns:
            A Playwright Locator
        """
        normalized = intent.lower()
        if "user" in normalized or "email" in normalized:
            return await self.locate("username_input", timeout=timeout)
        if "pass" in normalized:
            return await self.locate("password_input", timeout=timeout)
        if "login" in normalized or "sign in" in normalized:
            return await self.locate("login_button", timeout=timeout)
        if "logout" in normalized:
            return await self.locate("logout_button", timeout=timeout)

        # Fallback: try to locate by visible text (very generic)
        # NOTE: This is intentionally simplistic for demo purposes.
        locator = self.page.get_by_text(intent, exact=False)
        await locator.first.wait_for(state="visible", timeout=timeout)
        return locator.first

    def __init__(
        self,
        page: Page,
        element_name: Optional[str] = None,
        locators: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize SmartLocator with Playwright page.

        This class supports two usage styles:
        1) **Library mode**: `SmartLocator(page)` then `await smart.click("login_button")`
           using the class-level `LOCATORS` map.
        2) **Element mode**: `SmartLocator(page, element_name="X", locators={...})`
           then `await element.locate()` to resolve a single element with fallbacks.
        
        Args:
            page: Playwright Page object
            element_name: Optional human-readable element name (element mode)
            locators: Optional locator map (element mode)
        """
        self.page = page
        self._element_name = element_name
        self._element_locators = locators
        self._health_records: List[LocatorHealth] = []
        self._fallback_used: Dict[str, LocatorHealth] = {}

    async def locate(
        self,
        target: Optional[Union[str, Dict[str, str]]] = None,
        timeout: int = 5000,
        element_name: Optional[str] = None,
        custom_locators: Optional[Dict[str, str]] = None,
    ) -> Locator:
        """
        Locate element using smart fallback strategy.
        
        Tries each locator strategy in order until one succeeds.
        Records usage statistics for maintenance insights.
        
        Args:
            target: Either an element key (str) to look up in `LOCATORS`,
                a locator map (dict) with primary/fallback selectors, or None
                to use the instance's stored locator map (element mode).
            timeout: Timeout in milliseconds for each attempt
            element_name: Optional human-readable name (used for logging/reporting).
                If `target` is a string key, this is not required.
            custom_locators: Override default locators when `target` is a string key.
        
        Returns:
            Playwright Locator for the found element
        
        Raises:
            ElementNotFoundError: When all strategies fail
        """
        # Resolve locator map + display name depending on call style
        if isinstance(target, dict):
            locators = target
            display_name = element_name or self._element_name or "custom_element"
        elif isinstance(target, str):
            locators = custom_locators or self.LOCATORS.get(target, {})
            display_name = target
        else:
            # Element mode: stored locators
            locators = self._element_locators or {}
            display_name = element_name or self._element_name or "custom_element"
        
        if not locators:
            raise ElementNotFoundError(
                f"No locators defined for element: {display_name}"
            )
        
        errors = []
        
        for strategy_name, selector in locators.items():
            try:
                locator = self.page.locator(selector)
                await locator.wait_for(state="visible", timeout=timeout)
                
                # Record health status
                health = LocatorHealth(
                    element_name=display_name,
                    primary_selector=locators.get("primary", selector),
                    used_fallback=(strategy_name != "primary"),
                    fallback_name=strategy_name if strategy_name != "primary" else None,
                    fallback_selector=selector if strategy_name != "primary" else None,
                )
                self._health_records.append(health)
                
                # Log warning if fallback was used
                if strategy_name != "primary":
                    logger.warning(
                        f"⚠️ Element '{display_name}' used fallback: "
                        f"{strategy_name} -> {selector}"
                    )
                    self._fallback_used[display_name] = health
                else:
                    logger.debug(f"✅ Element '{display_name}' found: {selector}")
                
                return locator
                
            except Exception as e:
                errors.append(f"{strategy_name}: {selector} -> {str(e)[:50]}")
                continue
        
        # All strategies failed
        error_msg = (
            f"❌ All locators failed for '{display_name}':\n" +
            "\n".join(f"  - {err}" for err in errors)
        )
        logger.error(error_msg)
        raise ElementNotFoundError(error_msg)

    async def click(
        self,
        target: Union[str, Dict[str, str]],
        timeout: int = 5000,
        element_name: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """
        Click element using smart location.
        
        Args:
            element_name: Name of element to click
            timeout: Timeout for element location
            **kwargs: Additional arguments passed to click()
        """
        locator = await self.locate(target, timeout=timeout, element_name=element_name)
        await locator.click(**kwargs)

    async def fill(
        self,
        target: Union[str, Dict[str, str]],
        value: str,
        timeout: int = 5000,
        element_name: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """
        Fill input element using smart location.
        
        Args:
            element_name: Name of input element
            value: Value to fill
            timeout: Timeout for element location
            **kwargs: Additional arguments passed to fill()
        """
        locator = await self.locate(target, timeout=timeout, element_name=element_name)
        await locator.fill(value, **kwargs)

    async def get_text(
        self,
        target: Union[str, Dict[str, str]],
        timeout: int = 5000,
        element_name: Optional[str] = None,
    ) -> str:
        """
        Get text content of element.
        
        Args:
            target: Element key (str) or locator map (dict)
            timeout: Timeout for element location
            element_name: Optional human-readable name when `target` is a dict
        
        Returns:
            Text content of element
        """
        locator = await self.locate(target, timeout=timeout, element_name=element_name)
        return await locator.text_content() or ""

    async def is_visible(
        self,
        target: Union[str, Dict[str, str]],
        timeout: int = 2000,
        element_name: Optional[str] = None,
    ) -> bool:
        """
        Check if element is visible.
        
        Args:
            target: Element key (str) or locator map (dict)
            timeout: Timeout for visibility check
            element_name: Optional human-readable name when `target` is a dict
        
        Returns:
            True if element is visible, False otherwise
        """
        try:
            locator = await self.locate(target, timeout=timeout, element_name=element_name)
            return await locator.is_visible()
        except ElementNotFoundError:
            return False

    def get_health_report(self) -> str:
        """
        Generate locator health report.
        
        Analyzes usage patterns and identifies locators that
        frequently require fallbacks (maintenance candidates).
        
        Returns:
            Formatted health report string
        """
        if not self._fallback_used:
            return "✅ All elements used primary locators. No maintenance needed."
        
        report_lines = [
            "⚠️ Locator Health Report - Fallbacks Used:",
            "",
            "The following elements used fallback locators.",
            "Consider updating the primary selectors:",
            "",
        ]
        
        for element_name, health in self._fallback_used.items():
            report_lines.extend([
                f"  [{element_name}]",
                f"    Failed primary: {health.primary_selector}",
                f"    Used: {health.fallback_name} -> {health.fallback_selector}",
                "",
            ])
        
        return "\n".join(report_lines)

    def register_locator(
        self,
        element_name: str,
        locators: Dict[str, str],
    ) -> None:
        """
        Register new locator at runtime.
        
        Useful for dynamic elements or AI-generated locators.
        
        Args:
            element_name: Unique name for the element
            locators: Dictionary of strategy -> selector
        """
        self.LOCATORS[element_name] = locators
        logger.debug(f"Registered new locator: {element_name}")


__all__ = [
    "SmartLocator",
    "ElementNotFoundError",
    "LocatorHealth",
]

