"""
================================================================================
Streaming Page Object
================================================================================

This module defines Page Objects for the live streaming interface.
It covers the streaming studio, viewer page, and stream controls.

Features:
- Stream studio controls
- Live preview
- Chat interaction
- Viewer count display
- Stream settings

================================================================================
"""

from typing import Optional, Dict, List
from playwright.async_api import Page

from testsuites.ui_testing.framework.page_base import PageBase


class StreamStudioPage(PageBase):
    """
    Page Object for the Stream Studio (Host view).
    
    This is the main interface for hosts to control their live stream.
    """
    
    @property
    def _locators(self) -> Dict[str, Dict[str, str]]:
        """Define locators for stream studio."""
        return {
            "go_live_button": {
                "primary": "[data-testid='btn-go-live']",
                "fallback_1": "button:has-text('Go Live')",
                "fallback_2": ".stream-controls .btn-primary"
            },
            "end_stream_button": {
                "primary": "[data-testid='btn-end-stream']",
                "fallback_1": "button:has-text('End Stream')",
                "fallback_2": ".stream-controls .btn-danger"
            },
            "mute_button": {
                "primary": "[data-testid='btn-mute']",
                "fallback_1": "[aria-label='Mute']",
                "fallback_2": ".audio-control button"
            },
            "camera_toggle": {
                "primary": "[data-testid='btn-camera']",
                "fallback_1": "[aria-label='Toggle Camera']",
                "fallback_2": ".video-control button"
            },
            "screen_share": {
                "primary": "[data-testid='btn-screen-share']",
                "fallback_1": "[aria-label='Share Screen']",
                "fallback_2": ".screen-share button"
            },
            "viewer_count": {
                "primary": "[data-testid='viewer-count']",
                "fallback_1": ".viewer-count",
                "fallback_2": ".stats-viewers"
            },
            "stream_duration": {
                "primary": "[data-testid='stream-duration']",
                "fallback_1": ".stream-timer",
                "fallback_2": ".duration"
            },
            "stream_status": {
                "primary": "[data-testid='stream-status']",
                "fallback_1": ".stream-status",
                "fallback_2": ".status-indicator"
            },
            "video_preview": {
                "primary": "[data-testid='video-preview']",
                "fallback_1": "video.local-video",
                "fallback_2": ".preview-container video"
            },
            "chat_input": {
                "primary": "[data-testid='chat-input']",
                "fallback_1": "input[placeholder*='message']",
                "fallback_2": ".chat-input input"
            },
            "send_chat_button": {
                "primary": "[data-testid='btn-send-chat']",
                "fallback_1": "button:has-text('Send')",
                "fallback_2": ".chat-input button"
            },
            "settings_button": {
                "primary": "[data-testid='btn-settings']",
                "fallback_1": "[aria-label='Settings']",
                "fallback_2": ".settings-icon"
            },
            "caption_toggle": {
                "primary": "[data-testid='btn-captions']",
                "fallback_1": "[aria-label='Captions']",
                "fallback_2": ".caption-control"
            }
        }
    
    # ============================================================
    # Stream Controls
    # ============================================================
    
    async def click_go_live(self) -> None:
        """Start the live stream."""
        await self.smart.click(
            self._locators["go_live_button"],
            element_name="Go Live button"
        )
    
    async def click_end_stream(self) -> None:
        """End the live stream."""
        await self.smart.click(
            self._locators["end_stream_button"],
            element_name="End Stream button"
        )
    
    async def toggle_mute(self) -> None:
        """Toggle audio mute."""
        await self.smart.click(
            self._locators["mute_button"],
            element_name="Mute button"
        )
    
    async def toggle_camera(self) -> None:
        """Toggle camera on/off."""
        await self.smart.click(
            self._locators["camera_toggle"],
            element_name="Camera toggle"
        )
    
    async def start_screen_share(self) -> None:
        """Start screen sharing."""
        await self.smart.click(
            self._locators["screen_share"],
            element_name="Screen share button"
        )
    
    async def toggle_captions(self) -> None:
        """Toggle live captions."""
        await self.smart.click(
            self._locators["caption_toggle"],
            element_name="Caption toggle"
        )
    
    # ============================================================
    # Status & Metrics
    # ============================================================
    
    async def get_viewer_count(self) -> int:
        """Get current viewer count."""
        locator = await self.smart.locate(
            self._locators["viewer_count"],
            element_name="Viewer count"
        )
        text = await locator.text_content()
        # Extract number from text like "123 viewers"
        return int(''.join(filter(str.isdigit, text or "0")))
    
    async def get_stream_duration(self) -> str:
        """Get current stream duration."""
        locator = await self.smart.locate(
            self._locators["stream_duration"],
            element_name="Stream duration"
        )
        return await locator.text_content() or "00:00:00"
    
    async def get_stream_status(self) -> str:
        """Get current stream status."""
        locator = await self.smart.locate(
            self._locators["stream_status"],
            element_name="Stream status"
        )
        return (await locator.text_content() or "").strip()
    
    async def is_live(self) -> bool:
        """Check if stream is currently live."""
        status = await self.get_stream_status()
        return status.upper() in ["LIVE", "STREAMING", "ON AIR"]
    
    async def is_video_visible(self) -> bool:
        """Check if video preview is visible."""
        try:
            locator = await self.smart.locate(
                self._locators["video_preview"],
                timeout=3000,
                element_name="Video preview"
            )
            return await locator.is_visible()
        except Exception:
            return False
    
    # ============================================================
    # Chat
    # ============================================================
    
    async def send_chat_message(self, message: str) -> None:
        """
        Send a chat message.
        
        Args:
            message: Message text to send
        """
        await self.smart.fill(
            self._locators["chat_input"],
            message,
            element_name="Chat input"
        )
        await self.smart.click(
            self._locators["send_chat_button"],
            element_name="Send button"
        )
    
    # ============================================================
    # Settings
    # ============================================================
    
    async def open_settings(self) -> None:
        """Open stream settings panel."""
        await self.smart.click(
            self._locators["settings_button"],
            element_name="Settings button"
        )


class ViewerPage(PageBase):
    """
    Page Object for the Viewer page.
    
    This is the interface viewers use to watch live streams.
    """
    
    @property
    def _locators(self) -> Dict[str, Dict[str, str]]:
        """Define locators for viewer page."""
        return {
            "video_player": {
                "primary": "[data-testid='video-player']",
                "fallback_1": "video.stream-video",
                "fallback_2": ".player-container video"
            },
            "play_button": {
                "primary": "[data-testid='btn-play']",
                "fallback_1": "[aria-label='Play']",
                "fallback_2": ".player-controls .play"
            },
            "fullscreen_button": {
                "primary": "[data-testid='btn-fullscreen']",
                "fallback_1": "[aria-label='Fullscreen']",
                "fallback_2": ".player-controls .fullscreen"
            },
            "volume_slider": {
                "primary": "[data-testid='volume-slider']",
                "fallback_1": "input[type='range'][aria-label*='olume']",
                "fallback_2": ".volume-control input"
            },
            "quality_selector": {
                "primary": "[data-testid='quality-select']",
                "fallback_1": ".quality-selector",
                "fallback_2": "[aria-label='Quality']"
            },
            "chat_messages": {
                "primary": "[data-testid='chat-messages']",
                "fallback_1": ".chat-container .messages",
                "fallback_2": ".chat-list"
            },
            "stream_title": {
                "primary": "[data-testid='stream-title']",
                "fallback_1": "h1.stream-title",
                "fallback_2": ".stream-info .title"
            },
            "host_name": {
                "primary": "[data-testid='host-name']",
                "fallback_1": ".host-info .name",
                "fallback_2": ".streamer-name"
            },
            "follow_button": {
                "primary": "[data-testid='btn-follow']",
                "fallback_1": "button:has-text('Follow')",
                "fallback_2": ".follow-btn"
            },
            "like_button": {
                "primary": "[data-testid='btn-like']",
                "fallback_1": "[aria-label='Like']",
                "fallback_2": ".like-btn"
            },
            "share_button": {
                "primary": "[data-testid='btn-share']",
                "fallback_1": "[aria-label='Share']",
                "fallback_2": ".share-btn"
            },
            "offline_message": {
                "primary": "[data-testid='offline-message']",
                "fallback_1": ".offline-state",
                "fallback_2": "text=Stream is offline"
            }
        }
    
    async def is_stream_playing(self) -> bool:
        """Check if the stream is currently playing."""
        try:
            video = await self.smart.locate(
                self._locators["video_player"],
                element_name="Video player"
            )
            # Check if video is playing
            is_paused = await video.evaluate("el => el.paused")
            return not is_paused
        except Exception:
            return False
    
    async def click_play(self) -> None:
        """Click the play button."""
        await self.smart.click(
            self._locators["play_button"],
            element_name="Play button"
        )
    
    async def click_fullscreen(self) -> None:
        """Enter fullscreen mode."""
        await self.smart.click(
            self._locators["fullscreen_button"],
            element_name="Fullscreen button"
        )
    
    async def set_volume(self, level: int) -> None:
        """
        Set volume level.
        
        Args:
            level: Volume level (0-100)
        """
        slider = await self.smart.locate(
            self._locators["volume_slider"],
            element_name="Volume slider"
        )
        await slider.fill(str(level))
    
    async def get_stream_title(self) -> str:
        """Get the stream title."""
        locator = await self.smart.locate(
            self._locators["stream_title"],
            element_name="Stream title"
        )
        return await locator.text_content() or ""
    
    async def get_host_name(self) -> str:
        """Get the host/streamer name."""
        locator = await self.smart.locate(
            self._locators["host_name"],
            element_name="Host name"
        )
        return await locator.text_content() or ""
    
    async def click_follow(self) -> None:
        """Click the follow button."""
        await self.smart.click(
            self._locators["follow_button"],
            element_name="Follow button"
        )
    
    async def click_like(self) -> None:
        """Click the like button."""
        await self.smart.click(
            self._locators["like_button"],
            element_name="Like button"
        )
    
    async def click_share(self) -> None:
        """Click the share button."""
        await self.smart.click(
            self._locators["share_button"],
            element_name="Share button"
        )
    
    async def is_offline(self) -> bool:
        """Check if stream is showing offline state."""
        try:
            locator = await self.smart.locate(
                self._locators["offline_message"],
                timeout=2000,
                element_name="Offline message"
            )
            return await locator.is_visible()
        except Exception:
            return False
    
    async def get_chat_messages(self, limit: int = 10) -> List[str]:
        """
        Get recent chat messages.
        
        Args:
            limit: Maximum number of messages to return
            
        Returns:
            List of chat message texts
        """
        messages = []
        try:
            container = await self.smart.locate(
                self._locators["chat_messages"],
                element_name="Chat messages"
            )
            message_elements = container.locator(".chat-message, .message-item")
            count = await message_elements.count()
            
            for i in range(min(count, limit)):
                text = await message_elements.nth(i).text_content()
                if text:
                    messages.append(text.strip())
        except Exception:
            pass
        
        return messages

