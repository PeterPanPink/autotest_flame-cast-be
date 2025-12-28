"""
================================================================================
Channel Page Object
================================================================================

This module defines the Page Object for the Channel management pages.
It includes both the channel list page and channel detail/edit pages.

Key Features:
- Channel CRUD operations through UI
- AI-powered smart locators for resilient element identification
- Allure step integration for detailed reporting

================================================================================
"""

import allure
from typing import Optional, List, Dict, Any
from playwright.async_api import Page, expect

from testsuites.ui_testing.framework.page_base import PageBase
from testsuites.ui_testing.framework.smart_locator import SmartLocator


# ================================================================================
# Channel List Page
# ================================================================================

class ChannelListPage(PageBase):
    """
    Page Object for the Channel List page.
    
    This page displays all channels owned by the current user and provides
    actions to create, edit, and delete channels.
    """
    
    # ============================================================
    # Page Elements (Smart Locators)
    # ============================================================
    
    @property
    def btn_create_channel(self) -> SmartLocator:
        """Create New Channel button."""
        return self.smart_locator(
            primary="[data-testid='btn-create-channel']",
            fallbacks=[
                "[aria-label='Create Channel']",
                "button:has-text('New Channel')",
                "button:has-text('Create Channel')",
                ".channel-create-btn"
            ],
            name="Create Channel Button"
        )
    
    @property
    def channel_list_container(self) -> SmartLocator:
        """Container for the channel list."""
        return self.smart_locator(
            primary="[data-testid='channel-list']",
            fallbacks=[
                ".channel-list-container",
                "[role='list']",
                "table.channels-table"
            ],
            name="Channel List Container"
        )
    
    @property
    def loading_indicator(self) -> SmartLocator:
        """Loading indicator."""
        return self.smart_locator(
            primary="[data-testid='loading']",
            fallbacks=[
                ".loading-spinner",
                "[aria-busy='true']"
            ],
            name="Loading Indicator"
        )
    
    @property
    def empty_state(self) -> SmartLocator:
        """Empty state when no channels exist."""
        return self.smart_locator(
            primary="[data-testid='empty-channels']",
            fallbacks=[
                ".empty-state",
                "text=No channels yet"
            ],
            name="Empty State"
        )
    
    @property
    def search_input(self) -> SmartLocator:
        """Search input field."""
        return self.smart_locator(
            primary="[data-testid='search-channels']",
            fallbacks=[
                "input[placeholder*='Search']",
                "[aria-label='Search channels']"
            ],
            name="Search Input"
        )
    
    # ============================================================
    # Page Actions
    # ============================================================
    
    @allure.step("Navigate to Channel List page")
    async def navigate(self) -> None:
        """Navigate to the Channel List page."""
        await self.page.goto(f"{self.base_url}/channels")
        await self.wait_for_page_load()
    
    @allure.step("Wait for channels to load")
    async def wait_for_channels_load(self, timeout: int = 10000) -> None:
        """Wait for the channel list to finish loading."""
        # Wait for loading indicator to disappear
        try:
            loading = await self.loading_indicator.locate()
            await loading.wait_for(state="hidden", timeout=timeout)
        except Exception:
            pass  # Loading might complete very quickly
        
        # Wait for either channel list or empty state
        await self.page.wait_for_selector(
            "[data-testid='channel-list'], [data-testid='empty-channels']",
            timeout=timeout
        )
    
    @allure.step("Click Create Channel button")
    async def click_create_channel(self) -> None:
        """Click the Create Channel button."""
        await (await self.btn_create_channel.locate()).click()
        await self.page.wait_for_url("**/channels/new**")
    
    @allure.step("Search for channel: {keyword}")
    async def search_channel(self, keyword: str) -> None:
        """
        Search for channels by keyword.
        
        Args:
            keyword: Search keyword
        """
        search = await self.search_input.locate()
        await search.fill(keyword)
        await self.page.wait_for_timeout(500)  # Debounce
    
    @allure.step("Get channel count")
    async def get_channel_count(self) -> int:
        """Get the number of channels displayed."""
        container = await self.channel_list_container.locate()
        channel_items = container.locator("[data-testid^='channel-item-']")
        return await channel_items.count()

    @allure.step("Get channel titles")
    async def get_channel_titles(self) -> List[str]:
        """
        Get visible channel titles from the list.

        Returns:
            A list of channel title strings (best-effort; demo-safe heuristics).
        """
        container = await self.channel_list_container.locate()
        rows = container.locator("[data-testid^='channel-item-']")
        count = await rows.count()
        titles: List[str] = []

        for i in range(count):
            row = rows.nth(i)
            # Best-effort: try a dedicated title field first, then fall back to row text.
            title_node = row.locator("[data-testid='channel-title']").first
            try:
                if await title_node.count() > 0:
                    text = (await title_node.text_content()) or ""
                else:
                    text = (await row.text_content()) or ""
            except Exception:
                text = ""

            cleaned = " ".join(text.split()).strip()
            if cleaned:
                titles.append(cleaned)

        return titles
    
    @allure.step("Get channel by name: {name}")
    async def get_channel_row(self, name: str) -> Optional[Any]:
        """
        Get a channel row element by channel name.
        
        Args:
            name: Channel name to find
            
        Returns:
            Locator for the channel row, or None if not found
        """
        container = await self.channel_list_container.locate()
        channel_row = container.locator(f"[data-testid^='channel-item-']:has-text('{name}')")
        
        if await channel_row.count() > 0:
            return channel_row.first
        return None
    
    @allure.step("Click channel: {name}")
    async def click_channel(self, name: str) -> None:
        """
        Click on a channel to view its details.
        
        Args:
            name: Channel name to click
        """
        row = await self.get_channel_row(name)
        if row:
            await row.click()
            await self.page.wait_for_url("**/channels/**")
    
    @allure.step("Delete channel: {name}")
    async def delete_channel(self, name: str) -> bool:
        """
        Delete a channel by name.
        
        Args:
            name: Channel name to delete
            
        Returns:
            True if deletion was successful
        """
        row = await self.get_channel_row(name)
        if not row:
            return False
        
        # Click delete button in row
        delete_btn = row.locator("[data-testid='btn-delete']")
        await delete_btn.click()
        
        # Confirm deletion in modal
        confirm_btn = self.page.locator("[data-testid='confirm-delete']")
        await confirm_btn.click()
        
        # Wait for deletion to complete
        await self.page.wait_for_timeout(1000)
        
        return True
    
    # ============================================================
    # Page Verifications
    # ============================================================
    
    @allure.step("Verify channel list is visible")
    async def verify_channel_list_visible(self) -> None:
        """Verify that the channel list container is visible."""
        container = await self.channel_list_container.locate()
        await expect(container).to_be_visible()
    
    @allure.step("Verify channel exists: {name}")
    async def verify_channel_exists(self, name: str) -> bool:
        """
        Verify a channel with the given name exists in the list.
        
        Args:
            name: Channel name to verify
            
        Returns:
            True if channel exists
        """
        row = await self.get_channel_row(name)
        return row is not None


# ================================================================================
# Channel Create/Edit Page
# ================================================================================

class ChannelFormPage(PageBase):
    """
    Page Object for Channel create/edit form.
    
    This page is used for both creating new channels and editing existing ones.
    """
    
    # ============================================================
    # Form Elements
    # ============================================================
    
    @property
    def input_title(self) -> SmartLocator:
        """Channel title input."""
        return self.smart_locator(
            primary="[data-testid='input-channel-title']",
            fallbacks=[
                "#channel-title",
                "input[name='title']",
                "input[placeholder*='title' i]"
            ],
            name="Channel Title Input"
        )
    
    @property
    def input_description(self) -> SmartLocator:
        """Channel description textarea."""
        return self.smart_locator(
            primary="[data-testid='input-channel-description']",
            fallbacks=[
                "#channel-description",
                "textarea[name='description']",
                "textarea[placeholder*='description' i]"
            ],
            name="Channel Description Input"
        )
    
    @property
    def select_location(self) -> SmartLocator:
        """Location dropdown."""
        return self.smart_locator(
            primary="[data-testid='select-location']",
            fallbacks=[
                "#channel-location",
                "select[name='location']",
                "[aria-label='Location']"
            ],
            name="Location Dropdown"
        )
    
    @property
    def select_language(self) -> SmartLocator:
        """Language dropdown."""
        return self.smart_locator(
            primary="[data-testid='select-language']",
            fallbacks=[
                "#channel-language",
                "select[name='language']",
                "[aria-label='Language']"
            ],
            name="Language Dropdown"
        )
    
    @property
    def btn_save(self) -> SmartLocator:
        """Save button."""
        return self.smart_locator(
            primary="[data-testid='btn-save-channel']",
            fallbacks=[
                "button[type='submit']",
                "button:has-text('Save')",
                "button:has-text('Create')"
            ],
            name="Save Button"
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
    def error_message(self) -> SmartLocator:
        """Form error message."""
        return self.smart_locator(
            primary="[data-testid='form-error']",
            fallbacks=[
                ".error-message",
                "[role='alert']",
                ".form-error"
            ],
            name="Error Message"
        )
    
    # ============================================================
    # Form Actions
    # ============================================================
    
    @allure.step("Navigate to Create Channel page")
    async def navigate_to_create(self) -> None:
        """Navigate to the Create Channel page."""
        await self.page.goto(f"{self.base_url}/channels/new")
        await self.wait_for_page_load()
    
    @allure.step("Fill channel form")
    async def fill_channel_form(
        self,
        title: str,
        description: str = "",
        location: str = "US",
        language: str = "en"
    ) -> None:
        """
        Fill the channel creation/edit form.
        
        Args:
            title: Channel title
            description: Channel description
            location: Location code (e.g., "US", "SG")
            language: Language code (e.g., "en", "zh")
        """
        # Fill title
        title_input = await self.input_title.locate()
        await title_input.clear()
        await title_input.fill(title)
        
        # Fill description if provided
        if description:
            desc_input = await self.input_description.locate()
            await desc_input.clear()
            await desc_input.fill(description)
        
        # Select location
        location_select = await self.select_location.locate()
        await location_select.select_option(value=location)
        
        # Select language
        lang_select = await self.select_language.locate()
        await lang_select.select_option(value=language)
    
    @allure.step("Submit channel form")
    async def submit_form(self) -> None:
        """Click the save button to submit the form."""
        save_btn = await self.btn_save.locate()
        await save_btn.click()
    
    @allure.step("Create channel: {title}")
    async def create_channel(
        self,
        title: str,
        description: str = "",
        location: str = "US",
        language: str = "en"
    ) -> bool:
        """
        Complete flow to create a new channel.
        
        Args:
            title: Channel title
            description: Channel description
            location: Location code
            language: Language code
            
        Returns:
            True if channel was created successfully
        """
        await self.fill_channel_form(title, description, location, language)
        await self.submit_form()
        
        # Wait for navigation or error
        try:
            await self.page.wait_for_url("**/channels/**", timeout=5000)
            return True
        except Exception:
            return False
    
    @allure.step("Cancel form")
    async def cancel(self) -> None:
        """Click cancel to discard changes."""
        cancel_btn = await self.btn_cancel.locate()
        await cancel_btn.click()
    
    # ============================================================
    # Form Verifications
    # ============================================================
    
    @allure.step("Verify error message is displayed")
    async def verify_error_displayed(self, expected_text: str = None) -> bool:
        """
        Verify that an error message is displayed.
        
        Args:
            expected_text: Optional expected error text
            
        Returns:
            True if error is displayed (and matches expected text if provided)
        """
        try:
            error = await self.error_message.locate()
            await expect(error).to_be_visible()
            
            if expected_text:
                error_text = await error.text_content()
                return expected_text.lower() in error_text.lower()
            
            return True
        except Exception:
            return False
    
    @allure.step("Verify form is pre-filled")
    async def verify_form_values(self, expected: Dict[str, str]) -> bool:
        """
        Verify form fields have expected values (for edit mode).
        
        Args:
            expected: Dictionary of field names to expected values
            
        Returns:
            True if all values match
        """
        if "title" in expected:
            title_input = await self.input_title.locate()
            actual = await title_input.input_value()
            if actual != expected["title"]:
                return False
        
        if "description" in expected:
            desc_input = await self.input_description.locate()
            actual = await desc_input.input_value()
            if actual != expected["description"]:
                return False
        
        return True


# ================================================================================
# Channel Detail Page (Lightweight, used by streaming flow)
# ================================================================================

class ChannelDetailPage(PageBase):
    """
    Page Object for the Channel Detail page.

    The portfolio repo keeps this intentionally lightweight: it only includes
    the navigation action needed by streaming flow demos (entering the studio).
    """

    @property
    def btn_start_stream(self) -> SmartLocator:
        """Start Stream button on channel detail page (demo selectors)."""
        return self.smart_locator(
            primary="[data-testid='btn-start-stream']",
            fallbacks=[
                "button:has-text('Start Stream')",
                "button:has-text('Go Live')",
                "[aria-label='Start Streaming']",
            ],
            name="Start Stream Button",
        )

    @allure.step("Click Start Stream from channel detail page")
    async def click_start_stream(self) -> None:
        """Click start stream and wait for stream studio/setup route."""
        await (await self.btn_start_stream.locate()).click()
        try:
            await self.page.wait_for_url("**/stream**", timeout=15000)
        except Exception:
            await self.wait_for_page_load()
