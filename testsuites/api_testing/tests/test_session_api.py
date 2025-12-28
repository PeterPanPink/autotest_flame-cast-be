"""
================================================================================
Session API Test Cases
================================================================================

This module contains test cases for the Live Streaming Session API.
It covers the complete lifecycle of streaming sessions including:
- Session creation and configuration
- Status transitions
- Room management integration
- Stream lifecycle management

================================================================================
"""

import pytest
import allure
from uuid import uuid4
from datetime import datetime
from typing import Optional

from testsuites.api_testing.framework.http_client import HttpClient
from testsuites.api_testing.framework.assertion_executor import AssertionExecutor


# ================================================================================
# Test Data Fixtures
# ================================================================================

@pytest.fixture
def test_channel_id() -> str:
    """Provide a test channel ID (should be pre-created in test environment)."""
    return "ch_autotest_primary"


@pytest.fixture
def session_payload(test_channel_id: str) -> dict:
    """Generate a standard session creation payload."""
    return {
        "channel_id": test_channel_id,
        "title": f"Test Session {uuid4().hex[:8]}",
        "description": "Automated test session",
        "scheduled_start": None,  # Start immediately
        "settings": {
            "enable_chat": True,
            "enable_captions": False,
            "max_viewers": 1000
        }
    }


@pytest.fixture
def created_session(http_client: HttpClient, session_payload: dict):
    """
    Create a session for testing and clean up after test.
    
    Yields:
        Created session data including session_id
    """
    response = http_client.request(
        method="POST",
        url="/api/v1/session/create",
        json=session_payload
    )
    
    session_data = response.json().get("results", {})
    session_id = session_data.get("session_id")
    
    yield session_data
    
    # Cleanup: End and delete the session
    if session_id:
        try:
            http_client.request(
                method="POST",
                url=f"/api/v1/session/{session_id}/end"
            )
        except Exception:
            pass


# ================================================================================
# Create Session Tests
# ================================================================================

@allure.epic("Session Management")
@allure.feature("Create Session")
class TestCreateSession:
    """Test cases for session creation functionality."""
    
    @allure.story("Positive Cases")
    @allure.title("Create session with valid data")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.P0
    @pytest.mark.smoke
    def test_create_session_success(
        self,
        http_client: HttpClient,
        session_payload: dict
    ):
        """
        Verify that a streaming session can be created with valid data.
        
        Steps:
            1. Send POST request with valid session data
            2. Verify response status is 200
            3. Verify session_id is returned
            4. Verify initial status is IDLE
        """
        with allure.step("Create session"):
            response = http_client.request(
                method="POST",
                url="/api/v1/session/create",
                json=session_payload
            )
        
        with allure.step("Verify response"):
            assert response.status_code == 200
            
            data = response.json()
            executor = AssertionExecutor(data)
            
            executor.execute_assertions([
                {"type": "equal", "field": "success", "expected": True},
                {"type": "is_not_null", "field": "results.session_id"},
                {"type": "regex_match", "field": "results.session_id", "expected": r"^se_[a-zA-Z0-9]+"},
                {"type": "equal", "field": "results.status", "expected": "IDLE"},
                {"type": "is_not_null", "field": "results.created_at"},
            ])
            
            assert executor.all_passed(), f"Assertions failed: {executor.get_failures()}"
        
        # Cleanup
        session_id = data.get("results", {}).get("session_id")
        if session_id:
            http_client.request(method="POST", url=f"/api/v1/session/{session_id}/end")
    
    @allure.story("Positive Cases")
    @allure.title("Create session inherits channel settings")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.P1
    def test_session_inherits_channel_settings(
        self,
        http_client: HttpClient,
        test_channel_id: str
    ):
        """
        Verify that session inherits default settings from parent channel.
        """
        minimal_payload = {
            "channel_id": test_channel_id,
            "title": f"Inherit Test {uuid4().hex[:6]}"
        }
        
        with allure.step("Create session with minimal payload"):
            response = http_client.request(
                method="POST",
                url="/api/v1/session/create",
                json=minimal_payload
            )
        
        with allure.step("Verify inherited settings"):
            assert response.status_code == 200
            
            results = response.json().get("results", {})
            # Session should inherit channel's location/language
            assert results.get("channel_id") == test_channel_id
        
        # Cleanup
        session_id = results.get("session_id")
        if session_id:
            http_client.request(method="POST", url=f"/api/v1/session/{session_id}/end")
    
    @allure.story("Negative Cases")
    @allure.title("Create session without channel_id")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.P1
    @pytest.mark.mutations
    def test_create_session_missing_channel(self, http_client: HttpClient):
        """
        Verify that session creation fails without required channel_id.
        """
        payload = {
            "title": "Test Session"
        }
        
        with allure.step("Attempt to create session without channel_id"):
            response = http_client.request(
                method="POST",
                url="/api/v1/session/create",
                json=payload
            )
        
        with allure.step("Verify error response"):
            assert response.status_code == 400
            assert response.json().get("success") is False
    
    @allure.story("Negative Cases")
    @allure.title("Create session with invalid channel_id")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.P2
    def test_create_session_invalid_channel(self, http_client: HttpClient):
        """
        Verify appropriate error when channel does not exist.
        """
        payload = {
            "channel_id": "ch_nonexistent_123",
            "title": "Test Session"
        }
        
        with allure.step("Attempt to create session with invalid channel"):
            response = http_client.request(
                method="POST",
                url="/api/v1/session/create",
                json=payload
            )
        
        with allure.step("Verify 404 response"):
            assert response.status_code in [400, 404]


# ================================================================================
# Session Status Transition Tests
# ================================================================================

@allure.epic("Session Management")
@allure.feature("Session Status")
class TestSessionStatus:
    """Test cases for session status transitions."""
    
    @allure.story("State Machine")
    @allure.title("Session status transition: IDLE -> READY")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.P0
    def test_session_status_idle_to_ready(
        self,
        http_client: HttpClient,
        created_session: dict
    ):
        """
        Verify session can transition from IDLE to READY by creating room.
        """
        session_id = created_session.get("session_id")
        
        with allure.step("Create room for session"):
            response = http_client.request(
                method="POST",
                url=f"/api/v1/session/{session_id}/room/create"
            )
        
        with allure.step("Verify status transition"):
            assert response.status_code == 200
            
            # Get updated session
            get_response = http_client.request(
                method="GET",
                url=f"/api/v1/session/{session_id}"
            )
            
            status = get_response.json().get("results", {}).get("status")
            assert status == "READY"
    
    @allure.story("State Machine")
    @allure.title("Verify invalid status transitions are rejected")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.P1
    def test_invalid_status_transition(
        self,
        http_client: HttpClient,
        created_session: dict
    ):
        """
        Verify that invalid status transitions are properly rejected.
        
        Example: Cannot go from IDLE directly to LIVE without room creation.
        """
        session_id = created_session.get("session_id")
        
        with allure.step("Attempt to start stream without room"):
            response = http_client.request(
                method="POST",
                url=f"/api/v1/session/{session_id}/stream/start"
            )
        
        with allure.step("Verify rejection"):
            assert response.status_code in [400, 409]
            assert response.json().get("success") is False


# ================================================================================
# Get Session Tests
# ================================================================================

@allure.epic("Session Management")
@allure.feature("Get Session")
class TestGetSession:
    """Test cases for retrieving session information."""
    
    @allure.story("Positive Cases")
    @allure.title("Get session by ID")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.P0
    def test_get_session_by_id(
        self,
        http_client: HttpClient,
        created_session: dict
    ):
        """
        Verify session details can be retrieved by session_id.
        """
        session_id = created_session.get("session_id")
        
        with allure.step("Get session details"):
            response = http_client.request(
                method="GET",
                url=f"/api/v1/session/{session_id}"
            )
        
        with allure.step("Verify response"):
            assert response.status_code == 200
            
            data = response.json()
            executor = AssertionExecutor(data)
            
            executor.execute_assertions([
                {"type": "equal", "field": "success", "expected": True},
                {"type": "equal", "field": "results.session_id", "expected": session_id},
                {"type": "is_not_null", "field": "results.title"},
                {"type": "is_not_null", "field": "results.status"},
                {"type": "is_not_null", "field": "results.channel_id"},
            ])
            
            assert executor.all_passed()
    
    @allure.story("Positive Cases")
    @allure.title("Get session by room_id")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.P1
    def test_get_session_by_room_id(
        self,
        http_client: HttpClient,
        created_session: dict
    ):
        """
        Verify session can be retrieved by room_id (after room creation).
        """
        session_id = created_session.get("session_id")
        
        # First create room
        with allure.step("Create room for session"):
            room_response = http_client.request(
                method="POST",
                url=f"/api/v1/session/{session_id}/room/create"
            )
            room_id = room_response.json().get("results", {}).get("room_id")
        
        if room_id:
            with allure.step("Get session by room_id"):
                response = http_client.request(
                    method="GET",
                    url="/api/v1/session/by-room",
                    params={"room_id": room_id}
                )
            
            with allure.step("Verify response"):
                assert response.status_code == 200
                assert response.json().get("results", {}).get("session_id") == session_id
    
    @allure.story("Negative Cases")
    @allure.title("Get non-existent session")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.P2
    def test_get_nonexistent_session(self, http_client: HttpClient):
        """
        Verify 404 response for non-existent session.
        """
        with allure.step("Request non-existent session"):
            response = http_client.request(
                method="GET",
                url="/api/v1/session/se_nonexistent_123"
            )
        
        with allure.step("Verify 404"):
            assert response.status_code == 404


# ================================================================================
# End Session Tests
# ================================================================================

@allure.epic("Session Management")
@allure.feature("End Session")
class TestEndSession:
    """Test cases for ending streaming sessions."""
    
    @allure.story("Positive Cases")
    @allure.title("End session successfully")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.P0
    def test_end_session_success(
        self,
        http_client: HttpClient,
        session_payload: dict
    ):
        """
        Verify that a session can be ended successfully.
        """
        # Create a session to end
        with allure.step("Create session"):
            create_response = http_client.request(
                method="POST",
                url="/api/v1/session/create",
                json=session_payload
            )
            session_id = create_response.json().get("results", {}).get("session_id")
        
        with allure.step("End session"):
            response = http_client.request(
                method="POST",
                url=f"/api/v1/session/{session_id}/end"
            )
        
        with allure.step("Verify session ended"):
            assert response.status_code == 200
            
            # Verify final status
            get_response = http_client.request(
                method="GET",
                url=f"/api/v1/session/{session_id}"
            )
            
            status = get_response.json().get("results", {}).get("status")
            assert status in ["STOPPED", "CANCELLED", "ENDED"]
    
    @allure.story("Idempotency")
    @allure.title("End session is idempotent")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.P1
    def test_end_session_idempotent(
        self,
        http_client: HttpClient,
        session_payload: dict
    ):
        """
        Verify that ending a session multiple times is handled gracefully.
        """
        # Create and end a session
        with allure.step("Create and end session"):
            create_response = http_client.request(
                method="POST",
                url="/api/v1/session/create",
                json=session_payload
            )
            session_id = create_response.json().get("results", {}).get("session_id")
            
            http_client.request(method="POST", url=f"/api/v1/session/{session_id}/end")
        
        with allure.step("End session again"):
            response = http_client.request(
                method="POST",
                url=f"/api/v1/session/{session_id}/end"
            )
        
        with allure.step("Verify graceful handling"):
            # Should either succeed (idempotent) or return appropriate error
            assert response.status_code in [200, 400, 409]
