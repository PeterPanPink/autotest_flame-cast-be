"""
================================================================================
Browser Manager
================================================================================

Browser lifecycle management for UI automation.

Features:
    - Browser instance pooling
    - Context isolation for parallel testing
    - Authentication state persistence
    - Browser configuration presets

Author: Automation Team
License: MIT
================================================================================
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from loguru import logger
from playwright.async_api import (
    async_playwright,
    Browser,
    BrowserContext,
    Page,
    Playwright,
)


# Storage state file for authentication persistence
AUTH_STATE_FILE = Path(__file__).parent.parent / ".auth_state.json"


class BrowserManager:
    """
    Manages browser instances and contexts for UI testing.
    
    Features:
        - Single browser instance for performance
        - Isolated contexts for test independence
        - Authentication state persistence
        - Configurable browser settings
    
    Usage:
        async with BrowserManager() as manager:
            page = await manager.new_page()
            await page.goto("https://example.com")
            
        # Or with authentication
        async with BrowserManager(restore_auth=True) as manager:
            page = await manager.new_page()
            # Already logged in!
    """

    # Default browser launch options
    DEFAULT_LAUNCH_OPTIONS: Dict[str, Any] = {
        "headless": True,
        "args": [
            "--ignore-certificate-errors",
            "--disable-features=IsolateOrigins,site-per-process",
            "--use-fake-ui-for-media-stream",
            "--use-fake-device-for-media-stream",
        ],
    }

    # Default context options
    DEFAULT_CONTEXT_OPTIONS: Dict[str, Any] = {
        "viewport": {"width": 1920, "height": 1080},
        "ignore_https_errors": True,
        "permissions": ["camera", "microphone"],
    }

    def __init__(
        self,
        headless: bool = True,
        restore_auth: bool = False,
        browser_type: str = "chromium",
    ):
        """
        Initialize browser manager.
        
        Args:
            headless: Run browser in headless mode
            restore_auth: Restore authentication state from file
            browser_type: Browser to use - 'chromium', 'firefox', 'webkit'
        """
        self.headless = headless
        self.restore_auth = restore_auth
        self.browser_type = browser_type
        
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._contexts: list[BrowserContext] = []

    async def __aenter__(self) -> "BrowserManager":
        """Async context manager entry - start browser."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit - close browser."""
        await self.close()

    async def start(self) -> None:
        """Start Playwright and launch browser."""
        self._playwright = await async_playwright().start()
        
        # Select browser type
        if self.browser_type == "firefox":
            browser_launcher = self._playwright.firefox
        elif self.browser_type == "webkit":
            browser_launcher = self._playwright.webkit
        else:
            browser_launcher = self._playwright.chromium
        
        # Build launch options
        launch_options = {
            **self.DEFAULT_LAUNCH_OPTIONS,
            "headless": self.headless,
        }
        
        self._browser = await browser_launcher.launch(**launch_options)
        logger.debug(
            f"Browser started: {self.browser_type} "
            f"(headless={self.headless})"
        )

    async def close(self) -> None:
        """Close all contexts and browser."""
        # Close all contexts
        for context in self._contexts:
            try:
                await context.close()
            except Exception:
                pass
        self._contexts.clear()
        
        # Close browser
        if self._browser:
            await self._browser.close()
            self._browser = None
        
        # Stop Playwright
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        
        logger.debug("Browser closed")

    async def new_context(
        self,
        **options: Any,
    ) -> BrowserContext:
        """
        Create new browser context.
        
        Each context is isolated - separate cookies, localStorage, etc.
        
        Args:
            **options: Additional context options
        
        Returns:
            New BrowserContext
        """
        if not self._browser:
            raise RuntimeError("Browser not started. Call start() first.")
        
        context_options = {**self.DEFAULT_CONTEXT_OPTIONS, **options}
        
        # Restore authentication state if requested
        if self.restore_auth and AUTH_STATE_FILE.exists():
            context_options["storage_state"] = str(AUTH_STATE_FILE)
            logger.debug("Restored authentication state from file")
        
        context = await self._browser.new_context(**context_options)
        self._contexts.append(context)
        
        return context

    async def new_page(
        self,
        context: Optional[BrowserContext] = None,
        **context_options: Any,
    ) -> Page:
        """
        Create new page in new or existing context.
        
        Args:
            context: Existing context to use (creates new if None)
            **context_options: Options for new context
        
        Returns:
            New Page
        """
        if context is None:
            context = await self.new_context(**context_options)
        
        return await context.new_page()

    async def save_auth_state(self, context: BrowserContext) -> None:
        """
        Save authentication state for reuse.
        
        Saves cookies and localStorage to file for future sessions.
        
        Args:
            context: Context with authentication to save
        """
        await context.storage_state(path=str(AUTH_STATE_FILE))
        logger.info(f"Authentication state saved to: {AUTH_STATE_FILE}")

    @property
    def browser(self) -> Optional[Browser]:
        """Get browser instance."""
        return self._browser


# =============================================================================
# Convenience Functions
# =============================================================================

async def create_authenticated_page(
    base_url: str,
    login_func: callable,
    headless: bool = True,
) -> tuple[BrowserManager, Page]:
    """
    Create page with authentication.
    
    If saved auth state exists, restores it. Otherwise, performs
    login and saves state for future use.
    
    Args:
        base_url: Application base URL
        login_func: Async function to perform login (receives page)
        headless: Run browser in headless mode
    
    Returns:
        Tuple of (BrowserManager, authenticated Page)
    
    Usage:
        async def do_login(page):
            await page.fill("#username", "user")
            await page.fill("#password", "pass")
            await page.click("#login")
            await page.wait_for_url("**/dashboard**")
        
        manager, page = await create_authenticated_page(
            "https://app.example.com",
            do_login
        )
    """
    manager = BrowserManager(headless=headless, restore_auth=True)
    await manager.start()
    
    context = await manager.new_context()
    page = await context.new_page()
    
    # Check if we need to login
    await page.goto(base_url)
    
    # If redirected to login, perform login
    if "login" in page.url.lower():
        logger.info("No valid auth state, performing login...")
        await login_func(page)
        await manager.save_auth_state(context)
    else:
        logger.info("Restored authentication from saved state")
    
    return manager, page


__all__ = [
    "BrowserManager",
    "create_authenticated_page",
]

