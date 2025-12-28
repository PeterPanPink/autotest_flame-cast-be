# Architecture Overview

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AI-Powered Automation Framework                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
│  │   API Testing    │  │   UI Testing    │  │  Autotest Tools  │              │
│  │    Framework     │  │    Framework    │  │                 │              │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘              │
│           │                    │                    │                        │
│  ┌────────▼────────┐  ┌────────▼────────┐  ┌────────▼────────┐              │
│  │   HTTP Client   │  │  SmartLocator   │  │  Log Analyzer   │              │
│  │   (httpx)       │  │  (AI-Enhanced)  │  │  (Elasticsearch)│              │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘              │
│           │                    │                    │                        │
│  ┌────────▼────────┐  ┌────────▼────────┐  ┌────────▼────────┐              │
│  │ Token Manager   │  │  Page Objects   │  │ Notion Client   │              │
│  │                 │  │  (POM Pattern)  │  │                 │              │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘              │
│           │                    │                    │                        │
│  ┌────────▼────────┐  ┌────────▼────────┐  ┌────────▼────────┐              │
│  │ Mutation Gen.   │  │ Browser Manager │  │  Data Generator │              │
│  │                 │  │  (Playwright)   │  │                 │              │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘              │
│                                                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                           Common Infrastructure                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
│  │  Config Loader  │  │  Test Data      │  │  Allure         │              │
│  │  (YAML/ENV)     │  │  Factory        │  │  Reporting      │              │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘              │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Component Overview

### 1. API Testing Framework

The API testing framework provides comprehensive HTTP testing capabilities with built-in features for:

- **HTTP Client**: Wrapper around `httpx` with automatic retries, timeout handling, and Allure integration
- **Token Manager**: Centralized authentication token management with automatic refresh
- **Mutation Generator**: AI-powered test case generation for negative/boundary testing
- **Config Loader**: Flexible configuration from YAML files and environment variables

### 2. UI Testing Framework

The UI testing framework leverages Playwright with AI-enhanced capabilities:

- **SmartLocator**: Intelligent element location with fallback strategies
- **Page Objects**: Clean separation of page structure and test logic (POM pattern)
- **Browser Manager**: Playwright browser lifecycle management
- **Wait Helpers**: Robust waiting strategies for dynamic content

### 3. Autotest Tools

Utility tools for test automation support:

- **Log Analyzer**: Elasticsearch-based log search and analysis
- **Notion Client**: Documentation synchronization with Notion
- **Data Generator**: AI-powered test data generation
- **MongoDB Tools**: Database operations for test data management

## Data Flow

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Test Case   │────▶│  Framework   │────▶│   Target     │
│  Definition  │     │  Execution   │     │   System     │
└──────────────┘     └──────────────┘     └──────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │   Allure     │
                     │   Reports    │
                     └──────────────┘
```

## Key Design Principles

1. **Modularity**: Each component is independently testable and replaceable
2. **Configuration-Driven**: All settings externalized to YAML/ENV files
3. **AI-Enhanced**: Leveraging AI for smart locators and data generation
4. **Observability**: Comprehensive logging and Allure reporting
5. **Resilience**: Built-in retry mechanisms and graceful error handling

## Directory Structure

```
@autotest_flame-cast-be/
├── testsuites/
│   ├── api_testing/
│   │   ├── framework/      # API testing framework components
│   │   └── tests/          # API test cases
│   └── ui_testing/
│       ├── framework/      # UI testing framework components
│       ├── pages/          # Page Object Models
│       └── tests/          # UI test cases
├── autotest_tools/
│   ├── log_analyzer/       # Elasticsearch log tools
│   ├── notion_integration/ # Notion API integration
│   ├── mongo_tools/        # MongoDB utilities
│   └── data_generator/     # Test data generation
├── config/                  # Configuration files
├── docs/                    # Documentation
└── .github/workflows/       # CI/CD pipelines
```

## Integration Points

### CI/CD Integration

- GitHub Actions workflows for automated test execution
- Allure report generation and publishing
- Parallel test execution with pytest-xdist

### External Services

- **Elasticsearch**: Log aggregation and analysis
- **Notion**: Documentation management
- **MongoDB**: Test data storage
- **AI Services**: Smart locator and data generation (OpenAI/Anthropic)

