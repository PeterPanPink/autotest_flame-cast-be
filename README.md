# 🚀 Enterprise Automation Testing Framework

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Pytest](https://img.shields.io/badge/pytest-7.4+-green.svg)](https://pytest.org/)
[![Playwright](https://img.shields.io/badge/playwright-1.57+-purple.svg)](https://playwright.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A comprehensive, production-ready automation testing framework featuring **AI-powered test generation**, **API automation**, **UI automation**, and **DevOps tooling**. Built for scalability, maintainability, and CI/CD integration.

---

## 📋 Table of Contents

- [Key Features](#-key-features)
- [Architecture Overview](#-architecture-overview)
- [AI-Powered Capabilities](#-ai-powered-capabilities)
- [Documentation](#-documentation)
- [API Testing Framework](#-api-testing-framework)
- [UI Testing Framework](#-ui-testing-framework)
- [DevOps Tools](#-devops-tools)
- [CI/CD Integration](#-cicd-integration)
- [Quick Start](#-quick-start)
- [Project Structure](#-project-structure)
- [Configuration](#-configuration)
- [Reporting](#-reporting)

---

## ✨ Key Features

### 🤖 AI-Powered Test Generation
- **Intelligent Test Case Generation** - Automatically generate test cases from OpenAPI/Swagger specifications
- **AI-Assisted UI Testing** - Browser MCP integration for natural language UI test creation
- **Smart Mutation Testing** - AI-driven boundary value and negative test case generation

### 🔌 API Testing Excellence
- **Multi-Suite Architecture** - Positive tests, negative tests, and E2E business flows
- **Automatic Retry & Rate Limiting** - Built-in 429 handling with exponential backoff
- **Comprehensive Allure Reporting** - Full request/response logging with cURL commands
- **Swagger Synchronization** - Auto-update test cases when API specs change

### 🎭 UI Automation
- **Playwright-Based** - Cross-browser testing with modern async architecture
- **AI-Assisted Locators** - Smart element location with fallback strategies
- **Page Object Model** - Maintainable and reusable page abstractions
- **Visual Testing Ready** - Screenshot comparison and visual regression support

### 🛠️ DevOps Integration
- **Elasticsearch Log Analyzer** - Post-test log analysis for error detection
- **Notion Documentation Sync** - Fetch and manage test documentation from Notion
- **MongoDB Data Tools** - Test data management and database operations
- **GitHub Actions Ready** - Complete CI/CD pipeline configurations

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Test Execution Layer                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌────────────┐ │
│   │  Mutation   │   │  Business   │   │   E2E Flow  │   │     UI     │ │
│   │   Tests     │   │   API Tests │   │    Tests    │   │   Tests    │ │
│   │  (Negative) │   │  (Positive) │   │  (External) │   │(Playwright)│ │
│   └──────┬──────┘   └──────┬──────┘   └──────┬──────┘   └──────┬─────┘ │
│          │                 │                 │                 │       │
│          └─────────────────┴─────────────────┴─────────────────┘       │
│                                    │                                    │
├────────────────────────────────────┼────────────────────────────────────┤
│                          Core Framework Layer                           │
├────────────────────────────────────┼────────────────────────────────────┤
│                                    │                                    │
│   ┌────────────────────────────────┴────────────────────────────┐      │
│   │                     HTTP Client / Browser Driver             │      │
│   │  • Auto-retry with exponential backoff                       │      │
│   │  • Rate limit handling (429)                                 │      │
│   │  • Allure logging integration                                │      │
│   │  • Token management & authentication                         │      │
│   └──────────────────────────────────────────────────────────────┘      │
│                                                                         │
│   ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐      │
│   │  Config Loader  │   │  Token Manager  │   │   Assertion     │      │
│   │  (YAML-based)   │   │  (Auto-refresh) │   │   Executor      │      │
│   └─────────────────┘   └─────────────────┘   └─────────────────┘      │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                          DevOps Tools Layer                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐      │
│   │  ES Log         │   │  Notion Doc     │   │  MongoDB        │      │
│   │  Analyzer       │   │  Integration    │   │  Data Tools     │      │
│   └─────────────────┘   └─────────────────┘   └─────────────────┘      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🤖 AI-Powered Capabilities

### Intelligent Test Generation from OpenAPI

The framework automatically generates comprehensive test cases from Swagger/OpenAPI specifications:

```python
from testsuites.utils.swagger_parser import SwaggerTestGenerator

# Auto-generate test cases from OpenAPI spec
generator = SwaggerTestGenerator(swagger_url="https://api.example.com/openapi.json")

# Generate positive test cases
positive_tests = generator.generate_positive_cases(endpoint="/api/v1/users")

# Generate mutation (negative) test cases
mutation_tests = generator.generate_mutation_cases(
    endpoint="/api/v1/users",
    strategies=["missing_field", "type_error", "boundary", "injection"]
)

---

## 📚 Documentation

- **Architecture**: `docs/ARCHITECTURE.md`
- **CI/CD**: `docs/CICD_GUIDE.md`
- **API testing guide**: `docs/API_TESTING_GUIDE.md`
- **UI testing guide**: `docs/UI_TESTING_GUIDE.md`
- **AI automation overview**: `docs/AI_AUTOMATION.md`
- **Security & redaction policy**: `docs/SECURITY_REDACTION.md`
- **Portfolio walkthrough**: `docs/PORTFOLIO_WALKTHROUGH.md`
```

### AI-Assisted UI Test Creation

Using Browser MCP (Model Context Protocol), create UI tests with natural language:

```python
# Example: AI-generated UI test from natural language description
"""
Test Scenario: User Login Flow
1. Navigate to login page
2. Enter valid credentials
3. Click login button
4. Verify dashboard is displayed
"""

# The AI agent translates this into executable Playwright code
async def test_user_login(page):
    await page.goto("https://app.example.com/login")
    await page.fill("[data-testid='username']", "demo_user")
    await page.fill("[data-testid='password']", "secure_pass")
    await page.click("[data-testid='login-btn']")
    await page.wait_for_url("**/dashboard**")
    assert await page.locator("[data-testid='welcome-message']").is_visible()
```

---

## 🔌 API Testing Framework

### Multi-Layer Test Architecture

```
testsuites/
├── api_testing/
│   ├── mutation_tests/      # Negative test cases (parameter validation)
│   │   ├── api_cases/       # YAML test definitions
│   │   └── framework/       # Mutation generator engine
│   │
│   ├── business_tests/      # Positive API tests
│   │   ├── api_cases/       # YAML test definitions
│   │   └── framework/       # Test execution framework
│   │
│   └── e2e_flows/           # End-to-end business flows
│       ├── tests/           # Flow test implementations
│       └── fixtures/        # Test data fixtures
```

### Smart HTTP Client with Allure Integration

```python
class HttpClient:
    """
    Enterprise HTTP client with built-in resilience and reporting.
    
    Features:
        - Automatic retry with exponential backoff
        - Rate limit (429) handling with Retry-After parsing
        - Full Allure reporting with cURL commands
        - Token auto-refresh and authentication management
    """
    
    def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """
        Execute HTTP request with automatic retry and logging.
        
        All requests are automatically logged to Allure with:
        - Request URL, headers, and body
        - cURL command for easy reproduction
        - Response status and body
        """
        for attempt in range(self.retry_count):
            try:
                response = self._execute_request(method, url, **kwargs)
                
                if response.status_code == 429:
                    # Smart rate limit handling
                    retry_after = self._parse_retry_after(response)
                    time.sleep(retry_after)
                    continue
                
                # Log to Allure report
                self._log_to_allure(method, url, kwargs, response)
                return response
                
            except (httpx.TimeoutException, httpx.NetworkError) as e:
                if attempt == self.retry_count - 1:
                    raise
                time.sleep(self._calculate_backoff(attempt))
```

### YAML-Driven Test Cases

```yaml
# api_cases/user_management.yaml
name: "POST /api/v1/users"
method: POST
url: "/api/v1/users"

# Valid example for positive testing
valid_example:
  username: "autotest_user_001"
  email: "test@example.com"
  role: "member"

# Schema for mutation test generation
request_schema:
  type: object
  required: [username, email]
  properties:
    username:
      type: string
      minLength: 3
      maxLength: 50
    email:
      type: string
      format: email
    role:
      type: string
      enum: [admin, member, guest]

# Mutation strategies to apply
mutations:
  missing_field: true
  type_error: true
  boundary: true
  injection: true

# Database assertions for data verification
db_assertions:
  collection: users
  match_by: results.user_id
  verify:
    - field: username
      expected: "autotest_user_001"
    - field: created_at
      type: is_not_null
```

---

## 🎭 UI Testing Framework

### Modern Playwright-Based Architecture

```python
# testsuites/ui_testing/tests/test_dashboard.py

import pytest
import allure
from playwright.async_api import Page

from ..pages import DashboardPage, LoginPage


@allure.epic("User Dashboard")
@allure.feature("Dashboard Navigation")
class TestDashboard:
    """Dashboard functionality tests with AI-assisted element location."""
    
    @pytest.mark.P0
    @allure.title("Verify dashboard loads with user data")
    async def test_dashboard_displays_user_info(
        self, 
        authenticated_page: Page,
        test_user: dict
    ):
        """
        Verify the dashboard correctly displays user information.
        
        This test uses smart locators with fallback strategies
        for resilient element identification.
        """
        dashboard = DashboardPage(authenticated_page)
        
        with allure.step("Navigate to dashboard"):
            await dashboard.navigate()
        
        with allure.step("Verify welcome message"):
            welcome_text = await dashboard.get_welcome_message()
            assert test_user["username"] in welcome_text
        
        with allure.step("Capture dashboard screenshot"):
            await dashboard.screenshot("dashboard_loaded.png")
```

### Smart Locator with Fallback Strategy

```python
# testsuites/ui_testing/framework/smart_locator.py

class SmartLocator:
    """
    Intelligent element locator with automatic fallback.
    
    Features:
        - Multiple locator strategies per element
        - Automatic fallback on primary locator failure
        - Detailed logging for maintenance
    """
    
    LOCATORS = {
        "login_button": {
            "primary": "[data-testid='btn-login']",
            "fallback_1": "[aria-label='Login']",
            "fallback_2": "button:has-text('Log In')",
            "fallback_3": "#login-button"
        }
    }
    
    async def locate(
        self, 
        element_name: str, 
        timeout: int = 5000
    ) -> Locator:
        """
        Locate element with automatic fallback strategy.
        
        Returns the first successful locator match,
        logging warnings when fallbacks are used.
        """
        locators = self.LOCATORS.get(element_name, {})
        
        for strategy, selector in locators.items():
            try:
                locator = self.page.locator(selector)
                await locator.wait_for(state="visible", timeout=timeout)
                
                if strategy != "primary":
                    logger.warning(
                        f"Element '{element_name}' used fallback: {strategy}"
                    )
                
                return locator
            except TimeoutError:
                continue
        
        raise ElementNotFoundError(f"All locators failed for: {element_name}")
```

---

## 🛠️ DevOps Tools

### Elasticsearch Log Analyzer

Post-test analysis of backend logs to detect errors and warnings:

```python
# autotest_tools/log_analyzer/es_log_tool.py

class ESLogSearchTool:
    """
    Elasticsearch log analyzer for post-test error detection.
    
    Features:
        - Query logs by level (ERROR, WARNING)
        - Time-range filtering with ISO timestamps
        - Automatic classification of expected vs unexpected errors
        - Report generation for CI integration
    """
    
    def search_logs(
        self,
        levels: Sequence[str] = ("error", "warning"),
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        size: int = 200,
    ) -> Dict[str, Any]:
        """
        Search Elasticsearch for log entries matching criteria.
        
        Returns structured results with:
        - Total hit count
        - Simplified log entries
        - Query payload for debugging
        """
        query = self._build_query(levels, start_time, end_time)
        response = self.session.post(
            f"{self.base_url}/{self.index}/_search",
            json=query
        )
        return self._parse_response(response.json())


def run_analyze_log(
    es_levels: Sequence[str],
    es_start_time_iso: str,
) -> Dict[str, int]:
    """
    Main entry point for post-test log analysis.
    
    Analyzes logs and generates level-specific output files
    for review and CI integration.
    """
    # Fetch logs from Elasticsearch
    counts = fetch_es_logs(start_dt, end_dt, es_levels=es_levels)
    
    # Generate analysis reports
    for level in es_levels:
        output_file = ANALYZED_DIR / f"{level}_output.txt"
        # Write formatted log entries
        
    return counts
```

### Notion Documentation Integration

Sync test documentation and requirements from Notion:

```python
# autotest_tools/notion_integration/notion_tool.py

class NotionFetcher:
    """
    Notion API client for documentation synchronization.
    
    Features:
        - Fetch pages and databases recursively
        - Export to Markdown and JSON formats
        - Download embedded images
        - Support for comments and properties
    """
    
    def fetch_and_save(
        self,
        page_id_or_url: str,
        recursive: bool = True,
    ) -> Dict[str, Any]:
        """
        Fetch Notion page and save to local filesystem.
        
        Args:
            page_id_or_url: Notion page ID or full URL
            recursive: Whether to fetch child pages
            
        Returns:
            Summary with page count and output paths
        """
        page = self.fetch_page_recursive(page_id_or_url)
        saved_files = self.save_page(page)
        
        return {
            "root_page": page.title,
            "total_pages": self._count_pages(page),
            "output_directory": str(self.output_config.directory),
        }
```

### MongoDB Data Management

Test data preparation and cleanup utilities:

```python
# autotest_tools/mongo_tools/data_manager.py

class MongoDataManager:
    """
    MongoDB operations for test data management.
    
    Features:
        - Baseline data seeding
        - Test data isolation (autotest_ prefix)
        - Automatic cleanup after test runs
        - Jump server support for secure environments
    """
    
    def cleanup_test_data(
        self,
        collection: str,
        prefix: str = "autotest_"
    ) -> int:
        """
        Remove test data matching the autotest prefix.
        
        Returns the count of deleted documents.
        """
        result = self.db[collection].delete_many({
            "title": {"$regex": f"^{prefix}"}
        })
        return result.deleted_count
```

---

## 🔄 CI/CD Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/test-pipeline.yaml

name: Automation Test Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM

jobs:
  api-tests:
    name: API Automation Tests
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          
      - name: Install dependencies
        run: pip install -r requirements.txt
        
      - name: Run Mutation Tests
        run: |
          pytest testsuites/api_testing/mutation_tests \
            -v -n auto \
            --alluredir=reports/allure-results
            
      - name: Run Business API Tests
        run: |
          pytest testsuites/api_testing/business_tests \
            -v -n 4 \
            --alluredir=reports/allure-results
            
      - name: Analyze Backend Logs
        if: always()
        run: |
          python -c "
          from autotest_tools.log_analyzer import run_analyze_log
          run_analyze_log(['ERROR', 'WARNING'], '${{ github.event.head_commit.timestamp }}')
          "
          
      - name: Generate Allure Report
        uses: simple-elf/allure-report-action@master
        with:
          allure_results: reports/allure-results
          allure_report: reports/allure-report
          
      - name: Upload Test Artifacts
        uses: actions/upload-artifact@v4
        with:
          name: test-reports
          path: reports/

  ui-tests:
    name: UI Automation Tests
    runs-on: ubuntu-latest
    needs: api-tests
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          
      - name: Install Playwright
        run: |
          pip install -r requirements.txt
          playwright install chromium
          
      - name: Run UI Tests
        run: |
          pytest testsuites/ui_testing/tests \
            -v --headed=false \
            --alluredir=reports/allure-results
```

### Docker Support

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium && playwright install-deps

# Copy test code
COPY autotest_flame-cast-be .

# Default command
ENTRYPOINT ["python", "run_tests.py"]
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- pip or uv package manager

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/autotest-framework.git
cd autotest-framework

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers (for UI tests)
playwright install
```

### Configuration

```bash
# Copy example configuration
cp config/config.example.yaml config/config.yaml

# Edit with your settings
vim config/config.yaml
```

### Running Tests

```bash
# Run all mutation tests
pytest testsuites/api_testing/mutation_tests -v

# Run business API tests with concurrency
pytest testsuites/api_testing/business_tests -v -n 4

# Run UI tests
pytest testsuites/ui_testing/tests -v

# Generate Allure report
allure serve reports/allure-results
```

---

## 📁 Project Structure

```
@autotest_flame-cast-be/
├── README.md                    # This documentation
├── requirements.txt             # Python dependencies
├── pytest.ini                   # Pytest configuration
├── Dockerfile                   # Container build file
├── docker-compose.yml           # Container orchestration
│
├── config/                      # Configuration files
│   ├── config.yaml              # Main configuration
│   └── config.example.yaml      # Configuration template
│
├── testsuites/                  # Test suites
│   ├── api_testing/             # API automation
│   │   ├── mutation_tests/      # Negative/boundary tests
│   │   ├── business_tests/      # Positive API tests
│   │   └── e2e_flows/           # End-to-end flows
│   │
│   ├── ui_testing/              # UI automation
│   │   ├── tests/               # Test implementations
│   │   ├── pages/               # Page objects
│   │   └── framework/           # UI test framework
│   │
│   └── utils/                   # Shared utilities
│
├── autotest_tools/              # DevOps utilities
│   ├── log_analyzer/            # ES log analysis
│   ├── notion_integration/      # Notion sync
│   └── mongo_tools/             # MongoDB utilities
│
├── ci_cd/                       # CI/CD configurations
│   └── jenkins/                 # Jenkins pipelines
│
├── .github/                     # GitHub configurations
│   └── workflows/               # GitHub Actions
│
└── reports/                     # Test reports (gitignored)
    ├── allure-results/          # Allure raw data
    └── allure-report/           # Generated reports
```

---

## 📊 Reporting

### Allure Report Features

- **Test execution timeline** - Visual representation of test execution
- **Request/Response logging** - Full HTTP details with cURL commands
- **Screenshot attachments** - Automatic failure screenshots
- **Trend analysis** - Historical pass/fail trends
- **Categories** - Test classification by type and priority

### Sample Report Output

```
📁 Test Suite: User API Tests
    ├── ✅ POST /api/v1/users - Create User (Success)
    │       📎 Request URL: https://api.example.com/api/v1/users
    │       📎 Request Body: {"username": "test_user", ...}
    │       📎 cURL Command: curl -X POST ...
    │       📎 Response Status: 201
    │       📎 Response Body: {"user_id": "u_123", ...}
    │
    ├── ✅ GET /api/v1/users/{id} - Get User Details
    │
    └── ❌ DELETE /api/v1/users/{id} - Permission Denied
            📎 Error Screenshot
            📎 Stack Trace
```

---

## 📝 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guidelines](CONTRIBUTING.md) before submitting PRs.

---

## 📧 Contact

For questions or support, please open an issue or contact the maintainers.

