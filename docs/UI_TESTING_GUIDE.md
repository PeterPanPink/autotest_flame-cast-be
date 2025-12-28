# UI Testing Guide

## Overview

This guide covers the UI testing framework built on Playwright with AI-enhanced capabilities.

## Getting Started

### Prerequisites

```bash
pip install -r requirements.txt
playwright install chromium
```

### Configuration

Create a `config/config.yaml` file:

```yaml
ui:
  base_url: "https://app.example.com"
  headless: true
  slow_mo: 0
  timeout: 30000

test_user:
  username: "test_user"
  password: "test_pass"
```

## Framework Components

### SmartLocator

AI-enhanced element location with multiple fallback strategies:

```python
from testsuites.ui_testing.framework.smart_locator import SmartLocator

# By test ID (preferred)
element = SmartLocator(page, "[data-testid='submit-btn']")

# By role and text
button = SmartLocator(page, "button", has_text="Submit")

# With AI fallback
input_field = SmartLocator(page, "input[name='email']", use_ai_fallback=True)
```

### Page Object Model

```python
from testsuites.ui_testing.framework.page_base import PageBase
from testsuites.ui_testing.framework.smart_locator import SmartLocator

class LoginPage(PageBase):
    def __init__(self, page):
        super().__init__(page)
        self.username_input = SmartLocator(page, "#username")
        self.password_input = SmartLocator(page, "#password")
        self.login_button = SmartLocator(page, "button[type='submit']")
    
    async def login(self, username: str, password: str):
        await self.username_input.fill(username)
        await self.password_input.fill(password)
        await self.login_button.click()
```

### Browser Manager

```python
from testsuites.ui_testing.framework.browser_manager import BrowserManager

async def setup_browser():
    manager = BrowserManager()
    browser = await manager.launch_browser(headless=True)
    page = await manager.new_page()
    return page
```

## Writing UI Tests

### Basic Test Structure

```python
import allure
import pytest

@allure.feature("User Authentication")
@pytest.mark.ui
class TestLogin:
    
    @allure.story("Successful Login")
    @allure.title("Test login with valid credentials")
    @pytest.mark.P0
    @pytest.mark.smoke
    async def test_login_success(self, login_page, dashboard_page):
        """Test successful login flow."""
        
        with allure.step("Navigate to login page"):
            await login_page.navigate()
        
        with allure.step("Enter credentials and login"):
            await login_page.login("test_user", "test_pass")
        
        with allure.step("Verify dashboard is displayed"):
            is_visible = await dashboard_page.is_dashboard_visible()
            assert is_visible
```

### Using Fixtures

```python
@pytest.fixture
async def login_page(page):
    """Provides LoginPage instance."""
    return LoginPage(page)

@pytest.fixture
async def dashboard_page(page):
    """Provides DashboardPage instance."""
    return DashboardPage(page)

@pytest.fixture
async def authenticated_page(page, login_page):
    """Provides page with logged-in session."""
    await login_page.navigate()
    await login_page.login("test_user", "test_pass")
    return page
```

## Wait Strategies

### Explicit Waits

```python
from testsuites.api_testing.framework.wait_helpers import wait_for_element_visibility

# Wait for element
await wait_for_element_visibility(page.locator("#content"), timeout=10)

# Wait for condition
await wait_for_condition(
    lambda: page.locator(".status").text_content(),
    lambda text: text == "Complete",
    timeout=30
)
```

### Smart Waits in SmartLocator

```python
# Auto-wait is built into SmartLocator
await smart_locator.click()  # Waits for element to be visible and clickable
await smart_locator.fill("text")  # Waits for element to be ready
```

## Screenshots and Debugging

### Automatic Screenshots

```python
@allure.step("Take screenshot of current state")
async def capture_screenshot(page, name: str):
    screenshot = await page.screenshot(full_page=True)
    allure.attach(
        screenshot,
        name=name,
        attachment_type=allure.attachment_type.PNG
    )
```

### On Failure Capture

```python
@pytest.fixture(autouse=True)
async def capture_on_failure(request, page):
    yield
    if request.node.rep_call.failed:
        screenshot = await page.screenshot()
        allure.attach(
            screenshot,
            name="failure_screenshot",
            attachment_type=allure.attachment_type.PNG
        )
```

## Test Markers

| Marker | Description |
|--------|-------------|
| `@pytest.mark.ui` | UI-specific tests |
| `@pytest.mark.P0` | Critical UI tests |
| `@pytest.mark.smoke` | Quick verification tests |
| `@pytest.mark.e2e` | End-to-end flow tests |

## Running Tests

### Run All UI Tests

```bash
pytest testsuites/ui_testing -v
```

### Run with Browser Visible

```bash
pytest testsuites/ui_testing -v --headed
```

### Run Specific Tests

```bash
pytest testsuites/ui_testing -v -k "test_login"
```

### Generate Allure Report

```bash
pytest testsuites/ui_testing -v --alluredir=./allure-results
allure generate ./allure-results -o ./allure-report --clean
allure open ./allure-report
```

## Best Practices

1. **Use Page Objects**: Encapsulate page interactions
2. **Prefer data-testid**: Use stable test attributes for locators
3. **Smart Waits**: Use explicit waits, avoid hardcoded sleeps
4. **Capture Evidence**: Take screenshots at key steps
5. **Independent Tests**: Each test should be self-contained
6. **Clean Up**: Reset state after tests

## Troubleshooting

### Common Issues

1. **Element Not Found**: Check locator strategy, add waits
2. **Timeout Errors**: Increase timeout or check network issues
3. **Flaky Tests**: Review wait strategies, add stability improvements

### Debug Mode

```bash
# Run with Playwright debug mode
PWDEBUG=1 pytest testsuites/ui_testing -v -k "test_login"

# Run with slow motion
pytest testsuites/ui_testing -v --slowmo=500
```

### Recording Tests

```bash
# Use Playwright codegen
playwright codegen https://app.example.com
```

