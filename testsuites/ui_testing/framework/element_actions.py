# ================================================================================
# Element Actions Module
# ================================================================================
#
# This module provides a comprehensive set of UI element interaction utilities
# with built-in retry logic, wait mechanisms, and Allure integration.
#
# Key Features:
#   - Smart waiting and retry mechanisms
#   - Multiple fallback locator strategies
#   - Automatic screenshot on failure
#   - Allure step integration
#   - Keyboard and mouse actions
#   - Drag and drop support
#
# ================================================================================

import time
from typing import Any, Callable, List, Optional, Union
from functools import wraps

import allure
from loguru import logger
from playwright.sync_api import Page, Locator, expect


class RetryConfig:
    """Configuration for retry behavior."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        delay_seconds: float = 1.0,
        backoff_multiplier: float = 2.0,
        max_delay_seconds: float = 10.0
    ):
        """
        Initialize retry configuration.
        
        Args:
            max_attempts: Maximum number of retry attempts
            delay_seconds: Initial delay between retries
            backoff_multiplier: Multiplier for exponential backoff
            max_delay_seconds: Maximum delay between retries
        """
        self.max_attempts = max_attempts
        self.delay_seconds = delay_seconds
        self.backoff_multiplier = backoff_multiplier
        self.max_delay_seconds = max_delay_seconds


def with_retry(config: RetryConfig = None):
    """
    Decorator for adding retry logic to element actions.
    
    Args:
        config: RetryConfig object for controlling retry behavior
    """
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            delay = config.delay_seconds
            
            for attempt in range(config.max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < config.max_attempts - 1:
                        logger.warning(
                            f"Attempt {attempt + 1}/{config.max_attempts} failed for "
                            f"{func.__name__}: {str(e)}. Retrying in {delay}s..."
                        )
                        time.sleep(delay)
                        delay = min(
                            delay * config.backoff_multiplier,
                            config.max_delay_seconds
                        )
            
            logger.error(
                f"All {config.max_attempts} attempts failed for {func.__name__}: "
                f"{str(last_exception)}"
            )
            raise last_exception
        
        return wrapper
    return decorator


class ElementActions:
    """
    A utility class providing enhanced element interaction methods.
    
    This class wraps Playwright's element operations with additional features
    like automatic retries, smart waiting, fallback locators, and detailed logging.
    
    Example:
        actions = ElementActions(page)
        actions.click_element("button#submit", description="Submit button")
        actions.fill_input("#username", "testuser", description="Username field")
    """
    
    def __init__(self, page: Page, default_timeout: int = 30000):
        """
        Initialize ElementActions with a Playwright page.
        
        Args:
            page: Playwright Page object
            default_timeout: Default timeout for operations in milliseconds
        """
        self.page = page
        self.default_timeout = default_timeout
        self.retry_config = RetryConfig()
    
    @allure.step("Click element: {description}")
    @with_retry()
    def click_element(
        self,
        selector: Union[str, Locator],
        description: str = "",
        timeout: int = None,
        force: bool = False,
        double_click: bool = False
    ) -> None:
        """
        Click on an element with retry logic.
        
        Args:
            selector: CSS selector or Locator object
            description: Human-readable description for reporting
            timeout: Click timeout in milliseconds
            force: Force click even if element is not visible
            double_click: Perform double-click instead of single click
        """
        timeout = timeout or self.default_timeout
        locator = self._get_locator(selector)
        
        logger.info(f"Clicking element: {description or selector}")
        
        locator.wait_for(state="visible", timeout=timeout)
        
        if double_click:
            locator.dblclick(timeout=timeout, force=force)
        else:
            locator.click(timeout=timeout, force=force)
        
        logger.debug(f"Successfully clicked: {description or selector}")
    
    @allure.step("Fill input: {description}")
    @with_retry()
    def fill_input(
        self,
        selector: Union[str, Locator],
        value: str,
        description: str = "",
        clear_first: bool = True,
        timeout: int = None
    ) -> None:
        """
        Fill an input field with text.
        
        Args:
            selector: CSS selector or Locator object
            value: Text to enter
            description: Human-readable description for reporting
            clear_first: Clear existing content before filling
            timeout: Operation timeout in milliseconds
        """
        timeout = timeout or self.default_timeout
        locator = self._get_locator(selector)
        
        logger.info(f"Filling input: {description or selector} with '{value[:50]}...'")
        
        locator.wait_for(state="visible", timeout=timeout)
        
        if clear_first:
            locator.clear()
        
        locator.fill(value, timeout=timeout)
        
        logger.debug(f"Successfully filled: {description or selector}")
    
    @allure.step("Type text: {description}")
    @with_retry()
    def type_text(
        self,
        selector: Union[str, Locator],
        text: str,
        description: str = "",
        delay: int = 50,
        timeout: int = None
    ) -> None:
        """
        Type text character by character (simulates real typing).
        
        Args:
            selector: CSS selector or Locator object
            text: Text to type
            description: Human-readable description for reporting
            delay: Delay between keystrokes in milliseconds
            timeout: Operation timeout in milliseconds
        """
        timeout = timeout or self.default_timeout
        locator = self._get_locator(selector)
        
        logger.info(f"Typing into: {description or selector}")
        
        locator.wait_for(state="visible", timeout=timeout)
        locator.click()  # Focus the element
        locator.type(text, delay=delay)
        
        logger.debug(f"Successfully typed into: {description or selector}")
    
    @allure.step("Select option: {description}")
    @with_retry()
    def select_option(
        self,
        selector: Union[str, Locator],
        value: Union[str, List[str]],
        description: str = "",
        by: str = "value",
        timeout: int = None
    ) -> None:
        """
        Select option(s) from a dropdown.
        
        Args:
            selector: CSS selector or Locator object
            value: Option value(s) to select
            description: Human-readable description for reporting
            by: Selection method - "value", "label", or "index"
            timeout: Operation timeout in milliseconds
        """
        timeout = timeout or self.default_timeout
        locator = self._get_locator(selector)
        
        logger.info(f"Selecting option: {value} in {description or selector}")
        
        locator.wait_for(state="visible", timeout=timeout)
        
        if by == "value":
            locator.select_option(value=value, timeout=timeout)
        elif by == "label":
            locator.select_option(label=value, timeout=timeout)
        elif by == "index":
            locator.select_option(index=value, timeout=timeout)
        else:
            raise ValueError(f"Unknown selection method: {by}")
        
        logger.debug(f"Successfully selected: {value}")
    
    @allure.step("Check checkbox: {description}")
    @with_retry()
    def check_checkbox(
        self,
        selector: Union[str, Locator],
        description: str = "",
        check: bool = True,
        timeout: int = None
    ) -> None:
        """
        Check or uncheck a checkbox.
        
        Args:
            selector: CSS selector or Locator object
            description: Human-readable description for reporting
            check: True to check, False to uncheck
            timeout: Operation timeout in milliseconds
        """
        timeout = timeout or self.default_timeout
        locator = self._get_locator(selector)
        
        action = "Checking" if check else "Unchecking"
        logger.info(f"{action} checkbox: {description or selector}")
        
        locator.wait_for(state="visible", timeout=timeout)
        
        if check:
            locator.check(timeout=timeout)
        else:
            locator.uncheck(timeout=timeout)
    
    @allure.step("Hover element: {description}")
    @with_retry()
    def hover_element(
        self,
        selector: Union[str, Locator],
        description: str = "",
        timeout: int = None
    ) -> None:
        """
        Hover over an element.
        
        Args:
            selector: CSS selector or Locator object
            description: Human-readable description for reporting
            timeout: Operation timeout in milliseconds
        """
        timeout = timeout or self.default_timeout
        locator = self._get_locator(selector)
        
        logger.info(f"Hovering over: {description or selector}")
        
        locator.wait_for(state="visible", timeout=timeout)
        locator.hover(timeout=timeout)
    
    @allure.step("Drag and drop: {source_desc} -> {target_desc}")
    @with_retry()
    def drag_and_drop(
        self,
        source_selector: Union[str, Locator],
        target_selector: Union[str, Locator],
        source_desc: str = "source",
        target_desc: str = "target",
        timeout: int = None
    ) -> None:
        """
        Drag an element and drop it onto another element.
        
        Args:
            source_selector: Source element selector
            target_selector: Target element selector
            source_desc: Description of source element
            target_desc: Description of target element
            timeout: Operation timeout in milliseconds
        """
        timeout = timeout or self.default_timeout
        source = self._get_locator(source_selector)
        target = self._get_locator(target_selector)
        
        logger.info(f"Dragging from {source_desc} to {target_desc}")
        
        source.wait_for(state="visible", timeout=timeout)
        target.wait_for(state="visible", timeout=timeout)
        
        source.drag_to(target)
    
    @allure.step("Upload file: {description}")
    @with_retry()
    def upload_file(
        self,
        selector: Union[str, Locator],
        file_path: Union[str, List[str]],
        description: str = "",
        timeout: int = None
    ) -> None:
        """
        Upload file(s) to a file input.
        
        Args:
            selector: File input selector
            file_path: Path(s) to file(s) to upload
            description: Human-readable description for reporting
            timeout: Operation timeout in milliseconds
        """
        timeout = timeout or self.default_timeout
        locator = self._get_locator(selector)
        
        logger.info(f"Uploading file to: {description or selector}")
        
        locator.set_input_files(file_path, timeout=timeout)
    
    @allure.step("Get text: {description}")
    def get_text(
        self,
        selector: Union[str, Locator],
        description: str = "",
        timeout: int = None
    ) -> str:
        """
        Get text content of an element.
        
        Args:
            selector: CSS selector or Locator object
            description: Human-readable description for reporting
            timeout: Operation timeout in milliseconds
            
        Returns:
            Text content of the element
        """
        timeout = timeout or self.default_timeout
        locator = self._get_locator(selector)
        
        locator.wait_for(state="visible", timeout=timeout)
        text = locator.text_content()
        
        logger.debug(f"Got text from {description or selector}: '{text}'")
        return text
    
    @allure.step("Get attribute: {attribute} from {description}")
    def get_attribute(
        self,
        selector: Union[str, Locator],
        attribute: str,
        description: str = "",
        timeout: int = None
    ) -> Optional[str]:
        """
        Get attribute value of an element.
        
        Args:
            selector: CSS selector or Locator object
            attribute: Attribute name to get
            description: Human-readable description for reporting
            timeout: Operation timeout in milliseconds
            
        Returns:
            Attribute value or None if not found
        """
        timeout = timeout or self.default_timeout
        locator = self._get_locator(selector)
        
        locator.wait_for(timeout=timeout)
        value = locator.get_attribute(attribute)
        
        logger.debug(f"Got attribute {attribute} from {description or selector}: '{value}'")
        return value
    
    @allure.step("Wait for element: {description}")
    def wait_for_element(
        self,
        selector: Union[str, Locator],
        description: str = "",
        state: str = "visible",
        timeout: int = None
    ) -> Locator:
        """
        Wait for an element to reach a specific state.
        
        Args:
            selector: CSS selector or Locator object
            description: Human-readable description for reporting
            state: Expected state - "visible", "hidden", "attached", "detached"
            timeout: Wait timeout in milliseconds
            
        Returns:
            The Locator object
        """
        timeout = timeout or self.default_timeout
        locator = self._get_locator(selector)
        
        logger.info(f"Waiting for {description or selector} to be {state}")
        
        locator.wait_for(state=state, timeout=timeout)
        return locator
    
    @allure.step("Check element visible: {description}")
    def is_visible(
        self,
        selector: Union[str, Locator],
        description: str = "",
        timeout: int = 5000
    ) -> bool:
        """
        Check if an element is visible.
        
        Args:
            selector: CSS selector or Locator object
            description: Human-readable description for reporting
            timeout: Check timeout in milliseconds
            
        Returns:
            True if visible, False otherwise
        """
        try:
            locator = self._get_locator(selector)
            locator.wait_for(state="visible", timeout=timeout)
            return True
        except Exception:
            return False
    
    @allure.step("Press key: {key}")
    def press_key(
        self,
        key: str,
        selector: Union[str, Locator] = None,
        description: str = ""
    ) -> None:
        """
        Press a keyboard key.
        
        Args:
            key: Key to press (e.g., "Enter", "Tab", "Escape")
            selector: Optional element to focus before pressing
            description: Human-readable description for reporting
        """
        if selector:
            locator = self._get_locator(selector)
            locator.press(key)
        else:
            self.page.keyboard.press(key)
        
        logger.debug(f"Pressed key: {key}")
    
    @allure.step("Take screenshot: {name}")
    def take_screenshot(
        self,
        name: str,
        full_page: bool = False
    ) -> bytes:
        """
        Take a screenshot of the page.
        
        Args:
            name: Screenshot name for attachment
            full_page: Whether to capture full scrollable page
            
        Returns:
            Screenshot as bytes
        """
        screenshot = self.page.screenshot(full_page=full_page)
        allure.attach(
            screenshot,
            name=name,
            attachment_type=allure.attachment_type.PNG
        )
        return screenshot
    
    def _get_locator(self, selector: Union[str, Locator]) -> Locator:
        """Convert selector to Locator if needed."""
        if isinstance(selector, Locator):
            return selector
        return self.page.locator(selector)


class ScrollActions:
    """Utility class for scroll-related operations."""
    
    def __init__(self, page: Page):
        self.page = page
    
    @allure.step("Scroll to element: {description}")
    def scroll_to_element(
        self,
        selector: str,
        description: str = "",
        behavior: str = "smooth"
    ) -> None:
        """
        Scroll element into view.
        
        Args:
            selector: Element selector
            description: Human-readable description
            behavior: Scroll behavior - "smooth" or "instant"
        """
        locator = self.page.locator(selector)
        locator.scroll_into_view_if_needed()
    
    @allure.step("Scroll to position: ({x}, {y})")
    def scroll_to_position(self, x: int = 0, y: int = 0) -> None:
        """
        Scroll to specific page position.
        
        Args:
            x: Horizontal scroll position
            y: Vertical scroll position
        """
        self.page.evaluate(f"window.scrollTo({x}, {y})")
    
    @allure.step("Scroll by offset: ({dx}, {dy})")
    def scroll_by(self, dx: int = 0, dy: int = 0) -> None:
        """
        Scroll by offset from current position.
        
        Args:
            dx: Horizontal offset
            dy: Vertical offset
        """
        self.page.evaluate(f"window.scrollBy({dx}, {dy})")
    
    @allure.step("Scroll to top")
    def scroll_to_top(self) -> None:
        """Scroll to top of page."""
        self.page.evaluate("window.scrollTo(0, 0)")
    
    @allure.step("Scroll to bottom")
    def scroll_to_bottom(self) -> None:
        """Scroll to bottom of page."""
        self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

