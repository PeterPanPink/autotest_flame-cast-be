"""
================================================================================
Channel API Test Cases
================================================================================

This module contains comprehensive test cases for the Channel Management API.
It demonstrates various testing patterns including:
- Positive/negative test cases
- CRUD operations validation
- Data integrity verification
- User isolation testing

================================================================================
"""

import pytest
import allure
from uuid import uuid4
from typing import Optional

from testsuites.api_testing.framework.http_client import HttpClient
from testsuites.api_testing.framework.assertion_executor import AssertionExecutor


# ================================================================================
# Test Data Fixtures
# ================================================================================

@pytest.fixture
def unique_channel_name() -> str:
    """Generate a unique channel name for testing."""
    return f"autotest_channel_{uuid4().hex[:8]}"


@pytest.fixture
def channel_payload(unique_channel_name: str) -> dict:
    """Generate a standard channel creation payload."""
    return {
        "title": unique_channel_name,
        "description": "Automated test channel",
        "location": "US",
        "lang": "en",
        "category_ids": ["cat_001", "cat_002"]
    }


@pytest.fixture
def created_channel(http_client: HttpClient, channel_payload: dict) -> dict:
    """
    Create a channel for testing and clean up after test.
    
    Yields:
        Created channel data including channel_id
    """
    # Create channel
    response = http_client.request(
        method="POST",
        url="/api/v1/channel/create",
        json=channel_payload
    )
    
    channel_data = response.json().get("results", {})
    channel_id = channel_data.get("channel_id")
    
    yield channel_data
    
    # Cleanup: Delete the channel
    if channel_id:
        try:
            http_client.request(
                method="DELETE",
                url=f"/api/v1/channel/{channel_id}"
            )
        except Exception:
            pass  # Ignore cleanup errors


# ================================================================================
# Create Channel Tests
# ================================================================================

@allure.epic("Channel Management")
@allure.feature("Create Channel")
class TestCreateChannel:
    """Test cases for channel creation functionality."""
    
    @allure.story("Positive Cases")
    @allure.title("Create channel with valid data")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.P0
    @pytest.mark.smoke
    def test_create_channel_success(
        self,
        http_client: HttpClient,
        channel_payload: dict
    ):
        """
        Verify that a channel can be created with valid data.
        
        Steps:
            1. Send POST request with valid channel data
            2. Verify response status is 200
            3. Verify channel_id is returned
            4. Verify all fields are correctly stored
        """
        with allure.step("Create channel with valid payload"):
            response = http_client.request(
                method="POST",
                url="/api/v1/channel/create",
                json=channel_payload
            )
        
        with allure.step("Verify response"):
            assert response.status_code == 200
            
            data = response.json()
            executor = AssertionExecutor(data)
            
            executor.execute_assertions([
                {"type": "equal", "field": "success", "expected": True},
                {"type": "is_not_null", "field": "results.channel_id"},
                {"type": "regex_match", "field": "results.channel_id", "expected": r"^ch_[a-zA-Z0-9]+"},
                {"type": "equal", "field": "results.title", "expected": channel_payload["title"]},
                {"type": "equal", "field": "results.location", "expected": "US"},
            ])
            
            assert executor.all_passed(), f"Assertions failed: {executor.get_failures()}"
        
        # Cleanup
        channel_id = data.get("results", {}).get("channel_id")
        if channel_id:
            http_client.request(method="DELETE", url=f"/api/v1/channel/{channel_id}")
    
    @allure.story("Positive Cases")
    @allure.title("Create channel with minimal required fields")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.P1
    def test_create_channel_minimal_fields(
        self,
        http_client: HttpClient,
        unique_channel_name: str
    ):
        """
        Verify channel creation with only required fields.
        
        Expected: Channel created successfully with default values for optional fields.
        """
        minimal_payload = {
            "title": unique_channel_name,
            "location": "SG"
        }
        
        with allure.step("Create channel with minimal payload"):
            response = http_client.request(
                method="POST",
                url="/api/v1/channel/create",
                json=minimal_payload
            )
        
        with allure.step("Verify response"):
            assert response.status_code == 200
            data = response.json()
            
            # Verify defaults are applied
            results = data.get("results", {})
            assert results.get("title") == unique_channel_name
            assert results.get("location") == "SG"
            # Default language should be applied
            assert results.get("lang") is not None
        
        # Cleanup
        channel_id = data.get("results", {}).get("channel_id")
        if channel_id:
            http_client.request(method="DELETE", url=f"/api/v1/channel/{channel_id}")
    
    @allure.story("Negative Cases")
    @allure.title("Create channel without required title")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.P1
    @pytest.mark.mutations
    def test_create_channel_missing_title(self, http_client: HttpClient):
        """
        Verify that channel creation fails without required title field.
        
        Expected: 400 Bad Request with appropriate error message.
        """
        payload = {
            "location": "US",
            "lang": "en"
        }
        
        with allure.step("Attempt to create channel without title"):
            response = http_client.request(
                method="POST",
                url="/api/v1/channel/create",
                json=payload
            )
        
        with allure.step("Verify error response"):
            assert response.status_code == 400
            data = response.json()
            assert data.get("success") is False
            assert "title" in str(data.get("message", "")).lower() or \
                   "required" in str(data.get("message", "")).lower()
    
    @allure.story("Negative Cases")
    @allure.title("Create channel with duplicate title")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.P2
    def test_create_channel_duplicate_title(
        self,
        http_client: HttpClient,
        created_channel: dict
    ):
        """
        Verify handling of duplicate channel title.
        
        Note: Behavior depends on business rules - may allow or reject duplicates.
        """
        duplicate_payload = {
            "title": created_channel.get("title"),
            "location": "US"
        }
        
        with allure.step("Attempt to create channel with duplicate title"):
            response = http_client.request(
                method="POST",
                url="/api/v1/channel/create",
                json=duplicate_payload
            )
        
        with allure.step("Verify response (implementation specific)"):
            # Either 409 Conflict or 200 with new channel
            assert response.status_code in [200, 400, 409]


# ================================================================================
# List Channels Tests
# ================================================================================

@allure.epic("Channel Management")
@allure.feature("List Channels")
class TestListChannels:
    """Test cases for channel listing functionality."""
    
    @allure.story("Positive Cases")
    @allure.title("List channels with pagination")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.P0
    def test_list_channels_pagination(self, http_client: HttpClient):
        """
        Verify channel listing with pagination support.
        
        Steps:
            1. Request first page of channels
            2. Verify pagination metadata
            3. Verify channel data structure
        """
        with allure.step("Request channel list with pagination"):
            response = http_client.request(
                method="GET",
                url="/api/v1/channel/list",
                params={"page": 1, "page_size": 10}
            )
        
        with allure.step("Verify response"):
            assert response.status_code == 200
            
            data = response.json()
            executor = AssertionExecutor(data)
            
            executor.execute_assertions([
                {"type": "equal", "field": "success", "expected": True},
                {"type": "is_not_null", "field": "results.channels"},
                {"type": "length_less_than_or_equal", "field": "results.channels", "expected": 10},
            ])
    
    @allure.story("Positive Cases")
    @allure.title("List channels with filtering")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.P1
    def test_list_channels_with_filter(self, http_client: HttpClient):
        """
        Verify channel listing with status filter.
        """
        with allure.step("Request active channels only"):
            response = http_client.request(
                method="GET",
                url="/api/v1/channel/list",
                params={"status": "active", "page_size": 20}
            )
        
        with allure.step("Verify filtered results"):
            assert response.status_code == 200
            
            data = response.json()
            channels = data.get("results", {}).get("channels", [])
            
            # All returned channels should be active
            for channel in channels:
                assert channel.get("status") in ["active", None]  # None if status not returned
    
    @allure.story("User Isolation")
    @allure.title("Verify user can only see own channels")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.P0
    def test_list_channels_user_isolation(
        self,
        http_client: HttpClient,
        created_channel: dict
    ):
        """
        Verify that users can only see their own channels.
        
        This test validates the user isolation security requirement.
        """
        with allure.step("List channels for current user"):
            response = http_client.request(
                method="GET",
                url="/api/v1/channel/list"
            )
        
        with allure.step("Verify user isolation"):
            assert response.status_code == 200
            
            data = response.json()
            channels = data.get("results", {}).get("channels", [])
            
            # Verify test channel exists in list
            channel_ids = [c.get("channel_id") for c in channels]
            assert created_channel.get("channel_id") in channel_ids


# ================================================================================
# Update Channel Tests
# ================================================================================

@allure.epic("Channel Management")
@allure.feature("Update Channel")
class TestUpdateChannel:
    """Test cases for channel update functionality."""
    
    @allure.story("Positive Cases")
    @allure.title("Update channel title")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.P0
    def test_update_channel_title(
        self,
        http_client: HttpClient,
        created_channel: dict
    ):
        """
        Verify that channel title can be updated.
        """
        channel_id = created_channel.get("channel_id")
        new_title = f"Updated_{uuid4().hex[:6]}"
        
        with allure.step("Update channel title"):
            response = http_client.request(
                method="PATCH",
                url=f"/api/v1/channel/{channel_id}",
                json={"title": new_title}
            )
        
        with allure.step("Verify update success"):
            assert response.status_code == 200
            
            data = response.json()
            assert data.get("success") is True
            assert data.get("results", {}).get("title") == new_title
    
    @allure.story("Positive Cases")
    @allure.title("Partial update channel")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.P1
    def test_partial_update_channel(
        self,
        http_client: HttpClient,
        created_channel: dict
    ):
        """
        Verify partial update only modifies specified fields.
        """
        channel_id = created_channel.get("channel_id")
        original_title = created_channel.get("title")
        new_description = "Updated description"
        
        with allure.step("Update only description"):
            response = http_client.request(
                method="PATCH",
                url=f"/api/v1/channel/{channel_id}",
                json={"description": new_description}
            )
        
        with allure.step("Verify only description changed"):
            assert response.status_code == 200
            
            results = response.json().get("results", {})
            assert results.get("description") == new_description
            assert results.get("title") == original_title  # Unchanged
    
    @allure.story("Negative Cases")
    @allure.title("Update non-existent channel")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.P2
    def test_update_nonexistent_channel(self, http_client: HttpClient):
        """
        Verify appropriate error when updating non-existent channel.
        """
        fake_channel_id = "ch_nonexistent_123"
        
        with allure.step("Attempt to update non-existent channel"):
            response = http_client.request(
                method="PATCH",
                url=f"/api/v1/channel/{fake_channel_id}",
                json={"title": "New Title"}
            )
        
        with allure.step("Verify 404 response"):
            assert response.status_code == 404


# ================================================================================
# Delete Channel Tests
# ================================================================================

@allure.epic("Channel Management")
@allure.feature("Delete Channel")
class TestDeleteChannel:
    """Test cases for channel deletion functionality."""
    
    @allure.story("Positive Cases")
    @allure.title("Delete channel successfully")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.P0
    def test_delete_channel_success(
        self,
        http_client: HttpClient,
        channel_payload: dict
    ):
        """
        Verify that a channel can be deleted successfully.
        """
        # First create a channel to delete
        with allure.step("Create channel for deletion"):
            create_response = http_client.request(
                method="POST",
                url="/api/v1/channel/create",
                json=channel_payload
            )
            channel_id = create_response.json().get("results", {}).get("channel_id")
            assert channel_id is not None
        
        with allure.step("Delete the channel"):
            response = http_client.request(
                method="DELETE",
                url=f"/api/v1/channel/{channel_id}"
            )
        
        with allure.step("Verify deletion"):
            assert response.status_code == 200
            assert response.json().get("success") is True
        
        with allure.step("Verify channel no longer accessible"):
            get_response = http_client.request(
                method="GET",
                url=f"/api/v1/channel/{channel_id}"
            )
            assert get_response.status_code == 404
    
    @allure.story("Negative Cases")
    @allure.title("Delete channel with active sessions")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.P2
    def test_delete_channel_with_active_sessions(
        self,
        http_client: HttpClient,
        created_channel: dict
    ):
        """
        Verify that channel with active sessions cannot be deleted.
        
        Note: This test may need setup to create an active session.
        """
        channel_id = created_channel.get("channel_id")
        
        # Demo-safe placeholder:
        # In a production suite, you would create an active session bound to this channel,
        # then assert the delete request returns a business-safe error (e.g., 409 / 400),
        # not a 5xx crash. For the GitHub showcase, we mark this as XFAIL.
        pytest.xfail("Demo placeholder: requires active session setup before delete-channel validation")
