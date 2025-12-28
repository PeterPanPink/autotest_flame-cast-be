"""
================================================================================
API Testing Pytest Configuration
================================================================================

Shared fixtures and configuration for API automation tests.

Fixtures:
    - http_client: Configured HTTP client for API requests
    - config: Configuration loader instance
    - test_data: Dynamic test data fixtures

Author: Automation Team
License: MIT
================================================================================
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, Generator

import pytest
from loguru import logger

from ..framework import ConfigLoader, HttpClient


# =============================================================================
# Custom Pytest Markers
# =============================================================================

def pytest_configure(config):
    """Register custom pytest markers."""
    # Priority markers
    config.addinivalue_line("markers", "P0: Critical smoke tests (must pass)")
    config.addinivalue_line("markers", "P1: Core functionality tests")
    config.addinivalue_line("markers", "P2: Extended coverage tests")
    config.addinivalue_line("markers", "P3: Exploratory/edge case tests")
    
    # Test type markers
    config.addinivalue_line("markers", "smoke: Smoke test suite")
    config.addinivalue_line("markers", "regression: Regression test suite")
    config.addinivalue_line("markers", "mutation: Mutation/negative tests")
    config.addinivalue_line("markers", "e2e: End-to-end flow tests")
    
    # Dependency markers
    config.addinivalue_line(
        "markers", 
        "requires_external: Tests requiring external services"
    )


# =============================================================================
# Session-Scoped Fixtures (Shared across all tests)
# =============================================================================

@pytest.fixture(scope="session")
def config() -> ConfigLoader:
    """
    Provide configuration loader instance.
    
    Session-scoped to ensure configuration is loaded only once.
    """
    return ConfigLoader()


@pytest.fixture(scope="session")
def base_url(config: ConfigLoader) -> str:
    """Get API base URL from configuration."""
    return config.get("api.base_url", "http://localhost:8000")


# =============================================================================
# Function-Scoped Fixtures (Fresh for each test)
# =============================================================================

@pytest.fixture
def http_client(config: ConfigLoader) -> Generator[HttpClient, None, None]:
    """
    Provide configured HTTP client for API requests.
    
    Features:
        - Automatic authentication
        - Retry logic for transient failures
        - Allure logging integration
    
    Usage:
        def test_example(http_client):
            response = http_client.get("/api/v1/users")
            assert response.status_code == 200
    """
    with HttpClient(config) as client:
        yield client


@pytest.fixture
def unique_id() -> str:
    """
    Generate unique identifier for test isolation.
    
    Use this to create unique test data that won't conflict
    with other tests running in parallel.
    """
    return f"autotest_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def test_user_data(unique_id: str) -> Dict[str, Any]:
    """
    Generate test user data with unique identifier.
    
    Returns:
        Dictionary with user data suitable for creation/update
    """
    return {
        "username": f"user_{unique_id}",
        "email": f"{unique_id}@test.example.com",
        "display_name": f"Test User {unique_id}",
    }


# =============================================================================
# Cleanup Fixtures
# =============================================================================

@pytest.fixture
def cleanup_users(http_client: HttpClient):
    """
    Fixture to track and cleanup created users after test.
    
    Usage:
        def test_create_user(http_client, cleanup_users):
            response = http_client.post("/api/v1/users", json=user_data)
            user_id = response.json()["user_id"]
            cleanup_users.append(user_id)  # Will be deleted after test
    """
    created_user_ids = []
    yield created_user_ids
    
    # Cleanup after test
    for user_id in created_user_ids:
        try:
            http_client.delete(f"/api/v1/users/{user_id}")
            logger.debug(f"Cleaned up user: {user_id}")
        except Exception as e:
            logger.warning(f"Failed to cleanup user {user_id}: {e}")


@pytest.fixture
def cleanup_resources(http_client: HttpClient):
    """
    Generic resource cleanup fixture.
    
    Usage:
        def test_create_resource(http_client, cleanup_resources):
            response = http_client.post("/api/v1/items", json=item_data)
            item_id = response.json()["item_id"]
            cleanup_resources.append({
                "type": "item",
                "id": item_id,
                "endpoint": f"/api/v1/items/{item_id}"
            })
    """
    resources = []
    yield resources
    
    # Cleanup in reverse order (handle dependencies)
    for resource in reversed(resources):
        try:
            http_client.delete(resource["endpoint"])
            logger.debug(f"Cleaned up {resource['type']}: {resource['id']}")
        except Exception as e:
            logger.warning(
                f"Failed to cleanup {resource['type']} {resource['id']}: {e}"
            )


# =============================================================================
# Test Data Fixtures
# =============================================================================

@pytest.fixture
def valid_channel_data(unique_id: str) -> Dict[str, Any]:
    """Generate valid channel creation data."""
    return {
        "title": f"Test Channel {unique_id}",
        "description": "Automated test channel",
        "location": "US",
        "lang": "en",
    }


@pytest.fixture
def valid_session_data(unique_id: str) -> Dict[str, Any]:
    """Generate valid session creation data."""
    return {
        "title": f"Test Session {unique_id}",
        "description": "Automated test session",
    }


# =============================================================================
# Allure Reporting Hooks
# =============================================================================

def pytest_exception_interact(node, call, report):
    """Attach additional info on test failure."""
    import allure
    
    if report.failed:
        # Add failure context
        allure.attach(
            str(call.excinfo.value),
            name="Error Details",
            attachment_type=allure.attachment_type.TEXT
        )

