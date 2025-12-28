# API Testing Guide

## Overview

This guide covers the API testing framework, including setup, writing tests, and best practices.

## Getting Started

### Prerequisites

```bash
pip install -r requirements.txt
```

### Configuration

Create a `config/config.yaml` file:

```yaml
api:
  base_url: "https://api.example.com"
  timeout: 30
  retry_count: 3

auth:
  token_url: "/auth/token"
  username: "test_user"
  password: "test_pass"
```

## Writing API Tests

### Basic Test Structure

```python
import allure
import pytest

@allure.feature("User Management")
@pytest.mark.api
class TestUserAPI:
    
    @allure.story("Create User")
    @allure.title("Test creating a new user successfully")
    @pytest.mark.P0
    async def test_create_user_success(self, http_client):
        """
        Tests the successful creation of a new user.
        """
        user_data = {
            "username": "test_user",
            "email": "test@example.com"
        }
        
        with allure.step("Send POST request to create user"):
            response = await http_client.post("/api/v1/users", json=user_data)
        
        with allure.step("Verify response status and data"):
            assert response.status_code == 201
            assert response.json()["username"] == user_data["username"]
```

### Using Test Data Factory

```python
from testsuites.api_testing.framework.test_data_factory import TestDataFactory

async def test_with_generated_data(self, http_client):
    user_data = TestDataFactory.generate_user_data()
    response = await http_client.post("/api/v1/users", json=user_data)
    assert response.status_code == 201
```

### Mutation Testing

```python
from testsuites.api_testing.framework.mutation_generator import MutationGenerator

@pytest.mark.mutation
async def test_invalid_input(self, http_client):
    """Test API response to invalid input."""
    mutations = MutationGenerator.generate_invalid_payloads(valid_data)
    
    for mutation_name, payload in mutations:
        response = await http_client.post("/api/v1/users", json=payload)
        assert response.status_code == 400
```

## Test Fixtures

### HTTP Client Fixture

```python
@pytest.fixture(scope="session")
async def http_client():
    """Provides configured HTTP client."""
    config = ConfigLoader()
    client = HttpClient(config)
    yield client
    await client.close()
```

### Authentication Fixture

```python
@pytest.fixture(scope="session")
async def authenticated_client(http_client):
    """Provides authenticated HTTP client."""
    await http_client.authenticate()
    yield http_client
```

## Test Markers

| Marker | Description |
|--------|-------------|
| `@pytest.mark.P0` | Critical tests (smoke) |
| `@pytest.mark.P1` | High priority (regression) |
| `@pytest.mark.P2` | Medium priority (edge cases) |
| `@pytest.mark.P3` | Low priority (extensive) |
| `@pytest.mark.api` | API-specific tests |
| `@pytest.mark.mutation` | Mutation/negative tests |

## Running Tests

### Run All API Tests

```bash
pytest testsuites/api_testing -v
```

### Run by Priority

```bash
pytest testsuites/api_testing -v -m "P0"
```

### Run with Allure Report

```bash
pytest testsuites/api_testing -v --alluredir=./allure-results
allure serve ./allure-results
```

### Parallel Execution

```bash
pytest testsuites/api_testing -v -n auto
```

## Best Practices

1. **Use Descriptive Names**: Test names should describe the scenario
2. **One Assertion Per Test**: Keep tests focused on single behaviors
3. **Use Fixtures**: Leverage fixtures for setup/teardown
4. **Add Allure Steps**: Improve report readability
5. **Handle Cleanup**: Always clean up test data
6. **Use Data Factories**: Avoid hardcoded test data

## Troubleshooting

### Common Issues

1. **Authentication Failures**: Check token configuration
2. **Timeout Errors**: Adjust timeout settings in config
3. **Rate Limiting**: Configure retry settings appropriately

### Debug Mode

```bash
pytest testsuites/api_testing -v -s --log-cli-level=DEBUG
```

