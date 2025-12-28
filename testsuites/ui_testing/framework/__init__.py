"""
================================================================================
UI Testing Framework
================================================================================

Playwright-based UI automation framework with AI-assisted capabilities.

Components:
    - smart_locator: Intelligent element location with fallback strategies
    - page_base: Base page object for common operations
    - browser_manager: Browser lifecycle management
    - screenshot_manager: Screenshot capture and comparison

Author: Automation Team
License: MIT
================================================================================
"""

from .smart_locator import SmartLocator, ElementNotFoundError
from .page_base import BasePage
from .browser_manager import BrowserManager

__all__ = [
    "SmartLocator",
    "ElementNotFoundError",
    "BasePage",
    "BrowserManager",
]

