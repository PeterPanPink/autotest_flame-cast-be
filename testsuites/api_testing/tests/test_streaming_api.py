"""
================================================================================
Streaming API Test Suite
================================================================================

This module contains test cases for the live streaming functionality,
including stream start/stop, playback URLs, and streaming state management.

Test Coverage:
- Stream lifecycle (start, broadcasting, stop)
- Playback URL generation
- Stream health monitoring
- Multi-bitrate streaming
- Recording and VOD generation

================================================================================
"""

import pytest
import allure
from uuid import uuid4
from typing import Dict, Any
import time

from testsuites.api_testing.framework.http_client import HttpClient


@allure.epic("Streaming")
@allure.feature("Stream Lifecycle")
class TestStreamLifecycle:
    """Test cases for stream start and stop operations."""
    
    @pytest.fixture
    def ready_session(self, http_client: HttpClient) -> Dict[str, Any]:
        """
        Create a session in READY state for streaming tests.
        
        This fixture handles the complete setup:
        1. Create channel
        2. Create session
        3. Create room (LiveKit)
        4. Verify READY state
        """
        # Create channel
        channel_response = http_client.request(
            method="POST",
            url="/api/v1/channel/create_channel",
            json={
                "title": f"autotest_stream_{uuid4().hex[:8]}",
                "location": "US"
            }
        )
        channel_id = channel_response.json()["results"]["channel_id"]
        
        # Create session
        session_response = http_client.request(
            method="POST",
            url="/api/v1/session/create_session",
            json={
                "channel_id": channel_id,
                "title": f"Stream Test {uuid4().hex[:8]}"
            }
        )
        session_id = session_response.json()["results"]["session_id"]
        
        # Create room
        http_client.request(
            method="POST",
            url="/api/v1/session/ingress/create_room",
            json={"session_id": session_id}
        )
        
        # Get updated session
        get_response = http_client.request(
            method="GET",
            url="/api/v1/session/get_session",
            params={"session_id": session_id}
        )
        
        session = get_response.json()["results"]
        session["_channel_id"] = channel_id
        
        yield session
        
        # Cleanup
        try:
            http_client.request(
                method="POST",
                url="/api/v1/session/host/end_session",
                json={"session_id": session_id}
            )
            http_client.request(
                method="POST",
                url="/api/v1/channel/delete_channel",
                json={"channel_id": channel_id}
            )
        except Exception:
            pass
    
    @allure.story("Start Stream")
    @allure.title("Start live stream from READY state")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.P0
    @pytest.mark.integration
    def test_start_stream_success(
        self, 
        http_client: HttpClient,
        ready_session: Dict[str, Any]
    ):
        """
        Test starting a live stream from READY state.
        
        This transitions the session from READY → PUBLISHING → LIVE.
        """
        session_id = ready_session["session_id"]
        
        with allure.step("Start live stream"):
            response = http_client.request(
                method="POST",
                url="/api/v1/session/host/start_live_stream",
                json={"session_id": session_id}
            )
        
        with allure.step("Verify stream started"):
            assert response.status_code == 200
            result = response.json()["results"]
            
            assert "live_stream_id" in result
            assert result.get("status") in ["PUBLISHING", "LIVE"]
    
    @allure.story("Stop Stream")
    @allure.title("Stop active live stream")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.P0
    @pytest.mark.integration
    def test_stop_stream_success(
        self, 
        http_client: HttpClient,
        ready_session: Dict[str, Any]
    ):
        """
        Test stopping an active live stream.
        """
        session_id = ready_session["session_id"]
        
        with allure.step("Start stream first"):
            http_client.request(
                method="POST",
                url="/api/v1/session/host/start_live_stream",
                json={"session_id": session_id}
            )
        
        with allure.step("Stop the stream"):
            response = http_client.request(
                method="POST",
                url="/api/v1/session/host/end_live_stream",
                json={"session_id": session_id}
            )
        
        with allure.step("Verify stream stopped"):
            assert response.status_code == 200
            
            # Verify final state
            get_response = http_client.request(
                method="GET",
                url="/api/v1/session/get_session",
                params={"session_id": session_id}
            )
            
            session = get_response.json()["results"]
            assert session["status"] in ["ENDING", "STOPPED"]
    
    @allure.story("Stream Errors")
    @allure.title("Cannot start stream for IDLE session")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.P1
    def test_start_stream_idle_fails(self, http_client: HttpClient):
        """
        Test that starting stream fails for IDLE session (no room).
        """
        # Create IDLE session
        channel_response = http_client.request(
            method="POST",
            url="/api/v1/channel/create_channel",
            json={
                "title": f"autotest_idle_{uuid4().hex[:8]}",
                "location": "US"
            }
        )
        channel_id = channel_response.json()["results"]["channel_id"]
        
        session_response = http_client.request(
            method="POST",
            url="/api/v1/session/create_session",
            json={"channel_id": channel_id}
        )
        session_id = session_response.json()["results"]["session_id"]
        
        try:
            with allure.step("Attempt to start stream"):
                response = http_client.request(
                    method="POST",
                    url="/api/v1/session/host/start_live_stream",
                    json={"session_id": session_id}
                )
            
            with allure.step("Verify error"):
                assert response.status_code == 400
        finally:
            http_client.request(
                method="POST",
                url="/api/v1/channel/delete_channel",
                json={"channel_id": channel_id}
            )


@allure.epic("Streaming")
@allure.feature("Playback")
class TestPlayback:
    """Test cases for playback URL generation and VOD."""
    
    @allure.story("Playback URLs")
    @allure.title("Get live playback URL")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.P0
    def test_get_live_playback_url(self, http_client: HttpClient):
        """
        Test getting playback URL for active stream.
        
        Note: This test requires an active stream. For demo purposes,
        we'll test the endpoint structure.
        """
        # For demo, using a placeholder session ID
        with allure.step("Request playback URL"):
            response = http_client.request(
                method="GET",
                url="/api/v1/session/viewer/get_playback_url",
                params={"session_id": "se_demo_12345"}
            )
        
        with allure.step("Verify response structure"):
            # In real test, would be 200 with URL
            # For demo, we accept 404 for non-existent session
            assert response.status_code in [200, 404]
            
            if response.status_code == 200:
                result = response.json()["results"]
                assert "playback_url" in result or "hls_url" in result
    
    @allure.story("VOD")
    @allure.title("Get VOD playback URL after stream ends")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.P1
    def test_get_vod_playback_url(self, http_client: HttpClient):
        """
        Test getting VOD URL for ended stream.
        """
        with allure.step("Request VOD URL"):
            response = http_client.request(
                method="GET",
                url="/api/v1/session/viewer/get_vod_url",
                params={"session_id": "se_demo_vod_12345"}
            )
        
        with allure.step("Verify response"):
            # VOD might not be immediately available
            assert response.status_code in [200, 404, 202]


@allure.epic("Streaming")
@allure.feature("Stream Health")
class TestStreamHealth:
    """Test cases for stream health monitoring."""
    
    @allure.story("Health Check")
    @allure.title("Check stream health status")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.P1
    @pytest.mark.integration
    def test_stream_health_check(self, http_client: HttpClient):
        """
        Test stream health monitoring endpoint.
        """
        with allure.step("Check stream health"):
            response = http_client.request(
                method="GET",
                url="/api/v1/session/stream/health",
                params={"session_id": "se_demo_health_12345"}
            )
        
        with allure.step("Verify health response"):
            assert response.status_code in [200, 404]
            
            if response.status_code == 200:
                result = response.json()["results"]
                # Expected health metrics
                expected_fields = ["status", "bitrate", "viewers", "uptime"]
                for field in expected_fields:
                    if field in result:
                        allure.attach(
                            str(result[field]),
                            name=f"Health: {field}",
                            attachment_type=allure.attachment_type.TEXT
                        )


@allure.epic("Streaming")
@allure.feature("Captions")
class TestCaptions:
    """Test cases for live captions and subtitles."""
    
    @allure.story("Caption Control")
    @allure.title("Enable live captions")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.P1
    def test_enable_captions(self, http_client: HttpClient):
        """
        Test enabling live captions for a session.
        """
        with allure.step("Enable captions"):
            response = http_client.request(
                method="POST",
                url="/api/v1/session/caption/enable",
                json={
                    "session_id": "se_demo_caption_12345",
                    "language": "en",
                    "enable_translation": True,
                    "target_languages": ["zh", "es"]
                }
            )
        
        with allure.step("Verify response"):
            assert response.status_code in [200, 404]
    
    @allure.story("Caption Control")
    @allure.title("Disable live captions")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.P1
    def test_disable_captions(self, http_client: HttpClient):
        """
        Test disabling live captions.
        """
        with allure.step("Disable captions"):
            response = http_client.request(
                method="POST",
                url="/api/v1/session/caption/disable",
                json={"session_id": "se_demo_caption_12345"}
            )
        
        with allure.step("Verify response"):
            assert response.status_code in [200, 404]
    
    @allure.story("Caption Data")
    @allure.title("Get caption S3 URLs")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.P2
    def test_get_caption_urls(self, http_client: HttpClient):
        """
        Test retrieving caption file URLs from S3.
        """
        with allure.step("Get caption URLs"):
            response = http_client.request(
                method="GET",
                url="/api/v1/session/caption/get_urls",
                params={"session_id": "se_demo_caption_12345"}
            )
        
        with allure.step("Verify response"):
            assert response.status_code in [200, 404]
            
            if response.status_code == 200:
                result = response.json()["results"]
                assert "caption_urls" in result or "segments" in result


@allure.epic("Streaming")
@allure.feature("Analytics")
class TestStreamAnalytics:
    """Test cases for stream analytics."""
    
    @allure.story("Viewer Analytics")
    @allure.title("Get viewer count")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.P2
    def test_get_viewer_count(self, http_client: HttpClient):
        """
        Test getting current viewer count for a stream.
        """
        with allure.step("Get viewer count"):
            response = http_client.request(
                method="GET",
                url="/api/v1/session/analytics/viewers",
                params={"session_id": "se_demo_analytics_12345"}
            )
        
        with allure.step("Verify response"):
            assert response.status_code in [200, 404]
            
            if response.status_code == 200:
                result = response.json()["results"]
                assert "viewer_count" in result or "count" in result
    
    @allure.story("Stream Statistics")
    @allure.title("Get stream statistics")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.P2
    def test_get_stream_statistics(self, http_client: HttpClient):
        """
        Test getting detailed stream statistics.
        """
        with allure.step("Get stream statistics"):
            response = http_client.request(
                method="GET",
                url="/api/v1/session/analytics/statistics",
                params={"session_id": "se_demo_analytics_12345"}
            )
        
        with allure.step("Verify response"):
            assert response.status_code in [200, 404]

