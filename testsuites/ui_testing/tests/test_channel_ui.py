"""
================================================================================
Channel UI Test Cases
================================================================================

This module contains UI test cases for Channel management functionality.
It demonstrates end-to-end testing of channel CRUD operations through the UI.

Key Testing Patterns:
- Page Object Model for maintainable tests
- Smart locators for resilient element identification
- Allure integration for detailed reporting

================================================================================
"""

import pytest
import allure
from uuid import uuid4

from testsuites.ui_testing.pages.login_page import LoginPage
from testsuites.ui_testing.pages.dashboard_page import DashboardPage
from testsuites.ui_testing.pages.channel_page import ChannelListPage, ChannelFormPage


# ================================================================================
# Test Fixtures
# ================================================================================

@pytest.fixture
async def channel_list_page(page, login_page: LoginPage) -> ChannelListPage:
    """
    Provide a logged-in ChannelListPage instance.
    
    This fixture handles login and navigation to the channel list.
    """
    # Perform login first (demo-safe credentials come from env defaults in LoginPage)
    await login_page.open()
    await login_page.login(wait_dashboard=False)
    
    # Navigate to channel list
    channel_page = ChannelListPage(page)
    await channel_page.navigate()
    
    return channel_page


@pytest.fixture
async def channel_form_page(page, login_page: LoginPage) -> ChannelFormPage:
    """
    Provide a logged-in ChannelFormPage instance.
    """
    # Perform login (demo-safe)
    await login_page.open()
    await login_page.login(wait_dashboard=False)
    
    return ChannelFormPage(page)


@pytest.fixture
def unique_channel_name() -> str:
    """Generate a unique channel name for testing."""
    return f"UI_Test_Channel_{uuid4().hex[:8]}"


# ================================================================================
# Channel List Tests
# ================================================================================

@allure.epic("Channel Management")
@allure.feature("Channel List UI")
class TestChannelListUI:
    """UI test cases for the Channel List page."""
    
    @allure.story("Page Load")
    @allure.title("Channel list page loads successfully")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.P0_UI
    @pytest.mark.smoke_ui
    @pytest.mark.asyncio
    async def test_channel_list_page_loads(self, channel_list_page: ChannelListPage):
        """
        Verify that the channel list page loads successfully.
        
        Expected:
            - Page loads without errors
            - Channel list container is visible
            - Create channel button is visible
        """
        with allure.step("Verify page loaded"):
            await channel_list_page.wait_for_channels_load()
        
        with allure.step("Verify channel list is visible"):
            await channel_list_page.verify_channel_list_visible()
        
        with allure.step("Verify create button is visible"):
            create_btn = await channel_list_page.btn_create_channel.locate()
            assert await create_btn.is_visible()
    
    @allure.story("Search")
    @allure.title("Search channels by name")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.P1_UI
    @pytest.mark.asyncio
    async def test_search_channels(self, channel_list_page: ChannelListPage):
        """
        Verify channel search functionality.
        
        Steps:
            1. Enter search keyword
            2. Verify filtered results
        """
        search_keyword = "test"
        
        with allure.step(f"Search for '{search_keyword}'"):
            await channel_list_page.search_channel(search_keyword)
            await channel_list_page.page.wait_for_timeout(1000)  # Wait for filter
        
        with allure.step("Verify search results"):
            # Verify page didn't error out
            await channel_list_page.verify_channel_list_visible()
    
    @allure.story("Navigation")
    @allure.title("Navigate to create channel page")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.P0_UI
    @pytest.mark.asyncio
    async def test_navigate_to_create_channel(self, channel_list_page: ChannelListPage):
        """
        Verify navigation to the create channel page.
        """
        with allure.step("Click create channel button"):
            await channel_list_page.click_create_channel()
        
        with allure.step("Verify navigated to create page"):
            assert "/channels/new" in channel_list_page.page.url


# ================================================================================
# Channel Creation Tests
# ================================================================================

@allure.epic("Channel Management")
@allure.feature("Create Channel UI")
class TestCreateChannelUI:
    """UI test cases for channel creation."""
    
    @allure.story("Positive Cases")
    @allure.title("Create channel with valid data via UI")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.P0_UI
    @pytest.mark.asyncio
    async def test_create_channel_success(
        self,
        channel_form_page: ChannelFormPage,
        unique_channel_name: str
    ):
        """
        Verify that a channel can be created successfully via the UI.
        
        Steps:
            1. Navigate to create channel page
            2. Fill in channel details
            3. Submit the form
            4. Verify channel is created
        """
        with allure.step("Navigate to create channel page"):
            await channel_form_page.navigate_to_create()
        
        with allure.step("Fill channel form"):
            await channel_form_page.fill_channel_form(
                title=unique_channel_name,
                description="Automated UI test channel",
                location="US",
                language="en"
            )
        
        with allure.step("Submit form"):
            success = await channel_form_page.create_channel(
                title=unique_channel_name,
                description="Automated UI test channel"
            )
        
        with allure.step("Verify channel created"):
            assert success, "Channel creation should succeed"
            # Should navigate away from create page
            assert "/channels/new" not in channel_form_page.page.url
    
    @allure.story("Negative Cases")
    @allure.title("Create channel with empty title shows error")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.P1_UI
    @pytest.mark.asyncio
    async def test_create_channel_empty_title(self, channel_form_page: ChannelFormPage):
        """
        Verify that creating a channel without a title shows validation error.
        """
        with allure.step("Navigate to create channel page"):
            await channel_form_page.navigate_to_create()
        
        with allure.step("Try to submit empty form"):
            # Don't fill title, just try to submit
            await channel_form_page.submit_form()
        
        with allure.step("Verify error is displayed"):
            has_error = await channel_form_page.verify_error_displayed()
            assert has_error, "Validation error should be displayed"
    
    @allure.story("Form Validation")
    @allure.title("Cancel button discards changes")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.P2_UI
    @pytest.mark.asyncio
    async def test_cancel_discards_changes(
        self,
        channel_form_page: ChannelFormPage,
        unique_channel_name: str
    ):
        """
        Verify that clicking cancel discards form changes.
        """
        with allure.step("Navigate to create channel page"):
            await channel_form_page.navigate_to_create()
        
        with allure.step("Fill form with data"):
            await channel_form_page.fill_channel_form(
                title=unique_channel_name,
                description="This should be discarded"
            )
        
        with allure.step("Click cancel"):
            await channel_form_page.cancel()
        
        with allure.step("Verify navigated away"):
            # Should navigate back to channel list
            assert "/channels/new" not in channel_form_page.page.url


# ================================================================================
# Channel CRUD Flow Tests
# ================================================================================

@allure.epic("Channel Management")
@allure.feature("Channel CRUD Flow")
class TestChannelCRUDFlow:
    """End-to-end UI tests for complete channel CRUD operations."""
    
    @allure.story("E2E Flow")
    @allure.title("Complete channel create-read-update-delete flow")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.P0_UI
    @pytest.mark.e2e_ui
    @pytest.mark.asyncio
    async def test_channel_crud_flow(
        self,
        page,
        login_page: LoginPage,
        unique_channel_name: str
    ):
        """
        Test the complete CRUD lifecycle of a channel through UI.
        
        Steps:
            1. Login
            2. Create a new channel
            3. Verify channel appears in list
            4. Edit the channel
            5. Verify changes saved
            6. Delete the channel
            7. Verify channel removed
        """
        # Setup page objects
        channel_list = ChannelListPage(page)
        channel_form = ChannelFormPage(page)
        
        # Step 1: Login
        with allure.step("Login to application"):
            await login_page.navigate()
            await login_page.login("demo_user", "demo_password")
        
        # Step 2: Create channel
        with allure.step("Create new channel"):
            await channel_form.navigate_to_create()
            success = await channel_form.create_channel(
                title=unique_channel_name,
                description="E2E test channel"
            )
            assert success, "Channel creation should succeed"
        
        # Step 3: Verify in list
        with allure.step("Verify channel in list"):
            await channel_list.navigate()
            await channel_list.wait_for_channels_load()
            exists = await channel_list.verify_channel_exists(unique_channel_name)
            assert exists, "Created channel should appear in list"
        
        # Step 4: Edit channel
        updated_name = f"{unique_channel_name}_updated"
        with allure.step("Edit channel"):
            await channel_list.click_channel(unique_channel_name)
            # Assuming click navigates to edit page
            title_input = await channel_form.input_title.locate()
            await title_input.clear()
            await title_input.fill(updated_name)
            await channel_form.submit_form()
        
        # Step 5: Verify changes
        with allure.step("Verify changes saved"):
            await channel_list.navigate()
            await channel_list.wait_for_channels_load()
            exists = await channel_list.verify_channel_exists(updated_name)
            assert exists, "Updated channel name should appear"
        
        # Step 6: Delete channel
        with allure.step("Delete channel"):
            deleted = await channel_list.delete_channel(updated_name)
            assert deleted, "Channel should be deleted"
        
        # Step 7: Verify deleted
        with allure.step("Verify channel deleted"):
            await channel_list.page.wait_for_timeout(1000)  # Wait for refresh
            exists = await channel_list.verify_channel_exists(updated_name)
            assert not exists, "Deleted channel should not appear in list"
