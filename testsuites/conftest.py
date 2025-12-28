"""
================================================================================
Root Pytest Configuration
================================================================================

This module provides the root pytest configuration for the entire test suite.
It registers common markers and provides shared fixtures.

================================================================================
"""

import pytest


def pytest_configure(config):
    """Configure pytest with project-wide custom markers."""
    
    # Priority markers
    config.addinivalue_line(
        "markers", "P0: Critical priority tests - must pass for deployment"
    )
    config.addinivalue_line(
        "markers", "P1: High priority tests - important functionality"
    )
    config.addinivalue_line(
        "markers", "P2: Medium priority tests - edge cases and minor features"
    )
    config.addinivalue_line(
        "markers", "P3: Low priority tests - extensive validation"
    )
    
    # Test type markers
    config.addinivalue_line(
        "markers", "smoke: Quick verification tests"
    )
    config.addinivalue_line(
        "markers", "regression: Full regression test suite"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests between components"
    )
    config.addinivalue_line(
        "markers", "e2e: End-to-end tests simulating user flows"
    )
    
    # Domain markers
    config.addinivalue_line(
        "markers", "api: API-specific tests"
    )
    config.addinivalue_line(
        "markers", "ui: UI-specific tests"
    )
    config.addinivalue_line(
        "markers", "mutation: Mutation/negative tests"
    )
    
    # Feature markers
    config.addinivalue_line(
        "markers", "channel: Tests related to channel management"
    )
    config.addinivalue_line(
        "markers", "session: Tests related to user sessions"
    )
    config.addinivalue_line(
        "markers", "streaming: Tests related to streaming functionalities"
    )
    config.addinivalue_line(
        "markers", "auth: Tests related to authentication"
    )


def pytest_collection_modifyitems(config, items):
    """
    Modify collected test items.
    
    This hook can be used to add markers to tests dynamically or
    to reorder tests for optimization.
    """
    for item in items:
        # Auto-add 'api' marker to tests in api_testing directory
        if "api_testing" in str(item.fspath):
            item.add_marker(pytest.mark.api)
        
        # Auto-add 'ui' marker to tests in ui_testing directory
        if "ui_testing" in str(item.fspath):
            item.add_marker(pytest.mark.ui)


def pytest_report_header(config):
    """Add custom header to pytest output."""
    return [
        "",
        "=" * 60,
        "AI-Powered Automation Testing Framework",
        "=" * 60,
        "",
    ]

