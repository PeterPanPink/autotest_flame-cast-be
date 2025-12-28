"""
================================================================================
Streaming Page Objects
================================================================================

This module defines Page Objects for the live streaming functionality.
It includes pages for stream setup, live broadcasting, and stream management.

Key Features:
- Stream creation and configuration
- Live streaming controls
- Viewer management
- Real-time status monitoring

================================================================================
"""

import allure
from typing import Optional, Dict, Any
from playwright.async_api import Page, expect

from testsuites.ui_testing.framework.page_base import PageBase
from testsuites.ui_testing.framework.smart_locator import SmartLocator


# ================================================================================
# Stream Setup Page
# ================================================================================

class StreamSetupPage(PageBase):
    """
    Page Object for the Stream Setup/Configuration page.
    
    This page is used to configure stream settings before going live.
    """
    
    # ============================================================
    # Page Elements
    # ============================================================
    
    @property
    def select_channel(self) -> SmartLocator:
        """Channel selection dropdown."""
        return self.smart_locator(
            primary="[data-testid='select-channel']",
            fallbacks=[
                "#stream-channel",
                "[aria-label='Select Channel']",
                "select.channel-select"
            ],
            name="Channel Dropdown"
        )
    
    @property
    def input_stream_title(self) -> SmartLocator:
        """Stream title input."""
        return self.smart_locator(
            primary="[data-testid='input-stream-title']",
            fallbacks=[
                "#stream-title",
                "input[name='title']",
                "input[placeholder*='stream title' i]"
            ],
            name="Stream Title Input"
        )
    
    @property
    def input_stream_description(self) -> SmartLocator:
        """Stream description textarea."""
        return self.smart_locator(
            primary="[data-testid='input-stream-description']",
            fallbacks=[
                "#stream-description",
                "textarea[name='description']"
            ],
            name="Stream Description Input"
        )
    
    @property
    def toggle_enable_chat(self) -> SmartLocator:
        """Enable chat toggle."""
        return self.smart_locator(
            primary="[data-testid='toggle-chat']",
            fallbacks=[
                "#enable-chat",
                "[aria-label='Enable Chat']"
            ],
            name="Enable Chat Toggle"
        )
    
    @property
    def toggle_enable_captions(self) -> SmartLocator:
        """Enable captions toggle."""
        return self.smart_locator(
            primary="[data-testid='toggle-captions']",
            fallbacks=[
                "#enable-captions",
                "[aria-label='Enable Captions']"
            ],
            name="Enable Captions Toggle"
        )
    
    @property
    def btn_start_stream(self) -> SmartLocator:
        """Start streaming button."""
        return self.smart_locator(
            primary="[data-testid='btn-start-stream']",
            fallbacks=[
                "button:has-text('Go Live')",
                "button:has-text('Start Streaming')",
                "[aria-label='Start Stream']"
            ],
            name="Start Stream Button"
        )
    
    @property
    def btn_cancel(self) -> SmartLocator:
        """Cancel button."""
        return self.smart_locator(
            primary="[data-testid='btn-cancel']",
            fallbacks=[
                "button:has-text('Cancel')",
                "[aria-label='Cancel']"
            ],
            name="Cancel Button"
        )
    
    @property
    def preview_video(self) -> SmartLocator:
        """Video preview element."""
        return self.smart_locator(
            primary="[data-testid='video-preview']",
            fallbacks=[
                "video.preview",
                "#preview-video",
                "[aria-label='Preview']"
            ],
            name="Video Preview"
        )
    
    # ============================================================
    # Page Actions
    # ============================================================
    
    @allure.step("Navigate to Stream Setup page")
    async def navigate(self) -> None:
        """Navigate to the Stream Setup page."""
        await self.page.goto(f"{self.base_url}/stream/new")
        await self.wait_for_page_load()
    
    @allure.step("Select channel: {channel_name}")
    async def select_channel_by_name(self, channel_name: str) -> None:
        """
        Select a channel from the dropdown by name.
        
        Args:
            channel_name: Name of the channel to select
        """
        channel_select = await self.select_channel.locate()
        await channel_select.select_option(label=channel_name)
    
    @allure.step("Fill stream details")
    async def fill_stream_details(
        self,
        title: str,
        description: str = "",
        enable_chat: bool = True,
        enable_captions: bool = False
    ) -> None:
        """
        Fill in the stream configuration form.
        
        Args:
            title: Stream title
            description: Stream description
            enable_chat: Whether to enable chat
            enable_captions: Whether to enable captions
        """
        # Fill title
        title_input = await self.input_stream_title.locate()
        await title_input.clear()
        await title_input.fill(title)
        
        # Fill description if provided
        if description:
            desc_input = await self.input_stream_description.locate()
            await desc_input.clear()
            await desc_input.fill(description)
        
        # Configure toggles
        chat_toggle = await self.toggle_enable_chat.locate()
        is_chat_enabled = await chat_toggle.is_checked()
        if is_chat_enabled != enable_chat:
            await chat_toggle.click()
        
        captions_toggle = await self.toggle_enable_captions.locate()
        is_captions_enabled = await captions_toggle.is_checked()
        if is_captions_enabled != enable_captions:
            await captions_toggle.click()
    
    @allure.step("Start streaming")
    async def start_stream(self) -> bool:
        """
        Click the start stream button.
        
        Returns:
            True if stream started successfully
        """
        start_btn = await self.btn_start_stream.locate()
        await start_btn.click()
        
        # Wait for navigation to live page or error
        try:
            await self.page.wait_for_url("**/stream/live**", timeout=10000)
            return True
        except Exception:
            return False
    
    @allure.step("Configure and start stream")
    async def configure_and_start(
        self,
        channel_name: str,
        title: str,
        description: str = "",
        enable_chat: bool = True
    ) -> bool:
        """
        Complete flow to configure and start a stream.
        
        Args:
            channel_name: Channel to stream on
            title: Stream title
            description: Stream description
            enable_chat: Whether to enable chat
            
        Returns:
            True if stream started successfully
        """
        await self.select_channel_by_name(channel_name)
        await self.fill_stream_details(title, description, enable_chat)
        return await self.start_stream()
    
    # ============================================================
    # Verifications
    # ============================================================
    
    @allure.step("Verify video preview is active")
    async def verify_preview_active(self) -> bool:
        """Verify that the video preview is active."""
        try:
            preview = await self.preview_video.locate()
            await expect(preview).to_be_visible()
            return True
        except Exception:
            return False


# ================================================================================
# Live Stream Page
# ================================================================================

class LiveStreamPage(PageBase):
    """
    Page Object for the Live Streaming page.
    
    This page is displayed when actively streaming and provides
    controls for managing the live broadcast.
    """
    
    # ============================================================
    # Page Elements
    # ============================================================
    
    @property
    def live_indicator(self) -> SmartLocator:
        """LIVE indicator badge."""
        return self.smart_locator(
            primary="[data-testid='live-indicator']",
            fallbacks=[
                ".live-badge",
                "text=LIVE",
                "[aria-label='Live']"
            ],
            name="LIVE Indicator"
        )
    
    @property
    def viewer_count(self) -> SmartLocator:
        """Current viewer count display."""
        return self.smart_locator(
            primary="[data-testid='viewer-count']",
            fallbacks=[
                ".viewer-count",
                "[aria-label='Viewers']"
            ],
            name="Viewer Count"
        )
    
    @property
    def stream_duration(self) -> SmartLocator:
        """Stream duration timer."""
        return self.smart_locator(
            primary="[data-testid='stream-duration']",
            fallbacks=[
                ".stream-timer",
                "[aria-label='Duration']"
            ],
            name="Stream Duration"
        )
    
    @property
    def btn_end_stream(self) -> SmartLocator:
        """End stream button."""
        return self.smart_locator(
            primary="[data-testid='btn-end-stream']",
            fallbacks=[
                "button:has-text('End Stream')",
                "button:has-text('Stop')",
                "[aria-label='End Stream']"
            ],
            name="End Stream Button"
        )
    
    @property
    def btn_mute(self) -> SmartLocator:
        """Mute microphone button."""
        return self.smart_locator(
            primary="[data-testid='btn-mute']",
            fallbacks=[
                "[aria-label='Mute']",
                "button.mute-btn"
            ],
            name="Mute Button"
        )
    
    @property
    def btn_camera_toggle(self) -> SmartLocator:
        """Camera on/off toggle."""
        return self.smart_locator(
            primary="[data-testid='btn-camera']",
            fallbacks=[
                "[aria-label='Camera']",
                "button.camera-btn"
            ],
            name="Camera Toggle"
        )
    
    @property
    def chat_panel(self) -> SmartLocator:
        """Chat panel container."""
        return self.smart_locator(
            primary="[data-testid='chat-panel']",
            fallbacks=[
                ".chat-container",
                "#chat-panel"
            ],
            name="Chat Panel"
        )
    
    @property
    def end_stream_modal(self) -> SmartLocator:
        """End stream confirmation modal."""
        return self.smart_locator(
            primary="[data-testid='modal-end-stream']",
            fallbacks=[
                ".end-stream-modal",
                "[role='dialog']:has-text('End')"
            ],
            name="End Stream Modal"
        )
    
    @property
    def btn_confirm_end(self) -> SmartLocator:
        """Confirm end stream button in modal."""
        return self.smart_locator(
            primary="[data-testid='btn-confirm-end']",
            fallbacks=[
                "button:has-text('Confirm')",
                "button:has-text('Yes, End')"
            ],
            name="Confirm End Button"
        )
    
    # ============================================================
    # Page Actions
    # ============================================================
    
    @allure.step("Get current viewer count")
    async def get_viewer_count(self) -> int:
        """
        Get the current number of viewers.
        
        Returns:
            Number of viewers
        """
        viewer_elem = await self.viewer_count.locate()
        text = await viewer_elem.text_content()
        
        # Extract number from text (e.g., "1,234 viewers" -> 1234)
        import re
        numbers = re.findall(r'\d+', text.replace(',', ''))
        return int(numbers[0]) if numbers else 0
    
    @allure.step("Get stream duration")
    async def get_stream_duration(self) -> str:
        """
        Get the current stream duration.
        
        Returns:
            Duration string (e.g., "01:23:45")
        """
        duration_elem = await self.stream_duration.locate()
        return await duration_elem.text_content()
    
    @allure.step("Toggle mute")
    async def toggle_mute(self) -> None:
        """Toggle microphone mute state."""
        mute_btn = await self.btn_mute.locate()
        await mute_btn.click()
    
    @allure.step("Toggle camera")
    async def toggle_camera(self) -> None:
        """Toggle camera on/off."""
        camera_btn = await self.btn_camera_toggle.locate()
        await camera_btn.click()
    
    @allure.step("End stream")
    async def end_stream(self, confirm: bool = True) -> bool:
        """
        End the live stream.
        
        Args:
            confirm: Whether to confirm in the modal
            
        Returns:
            True if stream ended successfully
        """
        end_btn = await self.btn_end_stream.locate()
        await end_btn.click()
        
        # Wait for confirmation modal
        modal = await self.end_stream_modal.locate()
        await expect(modal).to_be_visible()
        
        if confirm:
            confirm_btn = await self.btn_confirm_end.locate()
            await confirm_btn.click()
            
            # Wait for navigation away from live page
            try:
                await self.page.wait_for_url("**/stream/ended**", timeout=10000)
                return True
            except Exception:
                return False
        else:
            # Click cancel or dismiss
            await self.page.keyboard.press("Escape")
            return False
    
    # ============================================================
    # Verifications
    # ============================================================
    
    @allure.step("Verify stream is live")
    async def verify_stream_is_live(self) -> bool:
        """Verify that the stream is currently live."""
        try:
            live = await self.live_indicator.locate()
            await expect(live).to_be_visible()
            return True
        except Exception:
            return False
    
    @allure.step("Verify chat is visible")
    async def verify_chat_visible(self) -> bool:
        """Verify that the chat panel is visible."""
        try:
            chat = await self.chat_panel.locate()
            await expect(chat).to_be_visible()
            return True
        except Exception:
            return False


# ================================================================================
# Stream Ended Page
# ================================================================================

class StreamEndedPage(PageBase):
    """
    Page Object for the Stream Ended/Summary page.
    
    This page displays stream statistics and provides options after ending a stream.
    """
    
    # ============================================================
    # Page Elements
    # ============================================================
    
    @property
    def stream_summary(self) -> SmartLocator:
        """Stream summary container."""
        return self.smart_locator(
            primary="[data-testid='stream-summary']",
            fallbacks=[
                ".stream-summary",
                "#stream-summary"
            ],
            name="Stream Summary"
        )
    
    @property
    def total_viewers(self) -> SmartLocator:
        """Total viewers statistic."""
        return self.smart_locator(
            primary="[data-testid='stat-total-viewers']",
            fallbacks=[
                ".stat-viewers",
                "[aria-label='Total Viewers']"
            ],
            name="Total Viewers Stat"
        )
    
    @property
    def peak_viewers(self) -> SmartLocator:
        """Peak concurrent viewers statistic."""
        return self.smart_locator(
            primary="[data-testid='stat-peak-viewers']",
            fallbacks=[
                ".stat-peak",
                "[aria-label='Peak Viewers']"
            ],
            name="Peak Viewers Stat"
        )
    
    @property
    def total_duration(self) -> SmartLocator:
        """Total stream duration statistic."""
        return self.smart_locator(
            primary="[data-testid='stat-duration']",
            fallbacks=[
                ".stat-duration",
                "[aria-label='Duration']"
            ],
            name="Duration Stat"
        )
    
    @property
    def btn_view_recording(self) -> SmartLocator:
        """View recording button."""
        return self.smart_locator(
            primary="[data-testid='btn-view-recording']",
            fallbacks=[
                "button:has-text('View Recording')",
                "[aria-label='View Recording']"
            ],
            name="View Recording Button"
        )
    
    @property
    def btn_go_home(self) -> SmartLocator:
        """Go to home/dashboard button."""
        return self.smart_locator(
            primary="[data-testid='btn-go-home']",
            fallbacks=[
                "button:has-text('Go Home')",
                "button:has-text('Dashboard')"
            ],
            name="Go Home Button"
        )
    
    # ============================================================
    # Page Actions
    # ============================================================
    
    @allure.step("Get stream statistics")
    async def get_stream_stats(self) -> Dict[str, Any]:
        """
        Get all stream statistics.
        
        Returns:
            Dictionary of stream statistics
        """
        stats = {}
        
        try:
            total_elem = await self.total_viewers.locate()
            stats['total_viewers'] = await total_elem.text_content()
        except Exception:
            stats['total_viewers'] = None
        
        try:
            peak_elem = await self.peak_viewers.locate()
            stats['peak_viewers'] = await peak_elem.text_content()
        except Exception:
            stats['peak_viewers'] = None
        
        try:
            duration_elem = await self.total_duration.locate()
            stats['duration'] = await duration_elem.text_content()
        except Exception:
            stats['duration'] = None
        
        return stats
    
    @allure.step("Click view recording")
    async def view_recording(self) -> None:
        """Navigate to view the stream recording."""
        view_btn = await self.btn_view_recording.locate()
        await view_btn.click()
    
    @allure.step("Go to dashboard")
    async def go_to_dashboard(self) -> None:
        """Navigate back to the dashboard."""
        home_btn = await self.btn_go_home.locate()
        await home_btn.click()
        await self.page.wait_for_url("**/dashboard**")

