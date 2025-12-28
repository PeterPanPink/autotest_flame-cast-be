"""
================================================================================
Page Objects
================================================================================

Page Object Model implementations for application pages.

Each page class encapsulates:
    - Element locators
    - Page-specific actions
    - Verification methods

Author: Automation Team
License: MIT
================================================================================
"""

from .login_page import LoginPage
from .dashboard_page import DashboardPage

__all__ = [
    "LoginPage",
    "DashboardPage",
]

