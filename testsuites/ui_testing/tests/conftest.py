"""
================================================================================
UI Testing Pytest Configuration
================================================================================

This module configures pytest for UI tests, providing fixtures for browser
management, page objects, and test setup/teardown.

Key Features:
- Browser and page lifecycle management
- Page Object fixtures for all pages
- Screenshot capture on failure
- Session management

================================================================================
"""

import pytest
from typing import AsyncGenerator
from pathlib import Path

from playwright.async_api import async_playwright, Page, Browser, BrowserContext
import allure

from testsuites.ui_testing.pages.login_page import LoginPage
from testsuites.ui_testing.pages.dashboard_page import DashboardPage
from testsuites.ui_testing.framework.browser_manager import BrowserManager


# ================================================================================
# Pytest Configuration
# ================================================================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "ui: mark test as UI test"
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as end-to-end test"
    )
    config.addinivalue_line(
        "markers", "P0: mark test as critical priority"
    )
    config.addinivalue_line(
        "markers", "P1: mark test as high priority"
    )
    config.addinivalue_line(
        "markers", "P2: mark test as medium priority"
    )
    config.addinivalue_line(
        "markers", "P3: mark test as low priority"
    )
    config.addinivalue_line(
        "markers", "smoke: mark test as smoke test"
    )
    config.addinivalue_line(
        "markers", "regression: mark test as regression test"
    )


# ================================================================================
# Browser Fixtures
# ================================================================================

@pytest.fixture(scope="session")
async def browser_manager() -> AsyncGenerator[BrowserManager, None]:
    """
    Session-scoped browser manager fixture.
    
    Provides a single browser manager instance for all tests in the session,
    reducing browser launch overhead.
    """
    manager = BrowserManager()
    yield manager
    await manager.close()


@pytest.fixture(scope="session")
async def browser(browser_manager: BrowserManager) -> AsyncGenerator[Browser, None]:
    """
    Session-scoped browser fixture.
    
    Provides a browser instance that is shared across all tests.
    """
    browser = await browser_manager.launch_browser(headless=True)
    yield browser


@pytest.fixture(scope="function")
async def context(browser: Browser) -> AsyncGenerator[BrowserContext, None]:
    """
    Function-scoped browser context fixture.
    
    Creates a new browser context for each test, providing isolation.
    """
    context = await browser.new_context(
        viewport={"width": 1920, "height": 1080},
        ignore_https_errors=True,
    )
    yield context
    await context.close()


@pytest.fixture(scope="function")
async def page(context: BrowserContext) -> AsyncGenerator[Page, None]:
    """
    Function-scoped page fixture.
    
    Creates a new page for each test within the browser context.
    """
    page = await context.new_page()
    yield page
    await page.close()


# ================================================================================
# Page Object Fixtures
# ================================================================================

@pytest.fixture
def login_page(page: Page) -> LoginPage:
    """
    Provides LoginPage instance.
    
    Use this fixture for tests that interact with the login page.
    """
    return LoginPage(page)


@pytest.fixture
def dashboard_page(page: Page) -> DashboardPage:
    """
    Provides DashboardPage instance.
    
    Use this fixture for tests that interact with the dashboard.
    """
    return DashboardPage(page)


#
# NOTE:
# We intentionally do NOT provide a single `channel_page` / `streaming_page` fixture here,
# because the showcase repository contains multiple Page Objects (list/detail/forms/studio/viewer).
# Tests should import and construct the specific Page Object they need.


# ================================================================================
# Authentication Fixtures
# ================================================================================

@pytest.fixture
async def authenticated_page(
    page: Page,
    login_page: LoginPage
) -> AsyncGenerator[Page, None]:
    """
    Provides a page with an authenticated session.
    
    Logs in before yielding the page, useful for tests that require
    an authenticated user.
    """
    await login_page.navigate()
    await login_page.login("test_user", "test_password")
    yield page


@pytest.fixture
async def authenticated_dashboard(
    authenticated_page: Page,
    dashboard_page: DashboardPage
) -> AsyncGenerator[DashboardPage, None]:
    """
    Provides DashboardPage with authenticated session.
    """
    yield dashboard_page


# ================================================================================
# Test Lifecycle Hooks
# ================================================================================

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Hook to capture screenshots on test failure.
    
    Automatically takes a screenshot when a UI test fails and attaches
    it to the Allure report.
    """
    outcome = yield
    report = outcome.get_result()
    
    if report.when == "call" and report.failed:
        # Check if this is a UI test with a page fixture
        if hasattr(item, "funcargs") and "page" in item.funcargs:
            page = item.funcargs["page"]
            try:
                # Capture screenshot
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # When running under pytest-asyncio, the loop is already running.
                    # We attach the screenshot asynchronously via callback (best-effort).
                    task = loop.create_task(page.screenshot(full_page=True))

                    def _attach_done(t):
                        try:
                            allure.attach(
                                t.result(),
                                name="failure_screenshot",
                                attachment_type=allure.attachment_type.PNG,
                            )
                        except Exception:
                            pass

                    task.add_done_callback(_attach_done)
                else:
                    screenshot = loop.run_until_complete(page.screenshot(full_page=True))
                    allure.attach(
                        screenshot,
                        name="failure_screenshot",
                        attachment_type=allure.attachment_type.PNG,
                    )
            except Exception as e:
                # Log but don't fail if screenshot capture fails
                from loguru import logger
                logger.warning(f"Failed to capture screenshot on failure: {e}")


# ================================================================================
# Utility Fixtures
# ================================================================================

@pytest.fixture
def screenshots_dir(tmp_path: Path) -> Path:
    """
    Provides a temporary directory for screenshots.
    """
    screenshots = tmp_path / "screenshots"
    screenshots.mkdir(exist_ok=True)
    return screenshots


@pytest.fixture
def test_data():
    """
    Provides common test data for UI tests.
    """
    return {
        "valid_user": {
            "username": "test_user",
            "password": "test_password",
        },
        "invalid_user": {
            "username": "invalid_user",
            "password": "wrong_password",
        },
        "test_channel": {
            "name": "Test Channel",
            "description": "A test channel for automation",
        },
        "test_stream": {
            "title": "Test Stream",
            "description": "A test stream",
        },
    }
