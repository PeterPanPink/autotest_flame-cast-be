# CI/CD Integration Guide

## Overview

This guide covers integrating the automation framework with CI/CD pipelines, specifically GitHub Actions.

## GitHub Actions Workflows

### API Tests Workflow

Located at `.github/workflows/api_tests.yml`:

```yaml
name: API Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 6 * * *'  # Daily at 6 AM UTC

jobs:
  api-tests:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          
      - name: Install dependencies
        run: pip install -r requirements.txt
        
      - name: Run API Tests
        run: pytest testsuites/api_testing -v --alluredir=./allure-results
        
      - name: Upload Allure Results
        uses: actions/upload-artifact@v3
        with:
          name: allure-results
          path: allure-results
```

### UI Tests Workflow

Located at `.github/workflows/ui_tests.yml`:

```yaml
name: UI Tests

on:
  push:
    branches: [main]
  schedule:
    - cron: '0 8 * * *'  # Daily at 8 AM UTC

jobs:
  ui-tests:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          playwright install chromium
          
      - name: Run UI Tests
        run: pytest testsuites/ui_testing -v --alluredir=./allure-results
        
      - name: Generate Allure Report
        uses: simple-elf/allure-report-action@master
        with:
          allure_results: allure-results
          allure_history: allure-history
```

## Pipeline Stages

### 1. Build Stage

```yaml
build:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - name: Set up Python
      uses: actions/setup-python@v4
    - name: Install dependencies
      run: pip install -r requirements.txt
```

### 2. Lint Stage

```yaml
lint:
  runs-on: ubuntu-latest
  steps:
    - name: Run Flake8
      run: flake8 testsuites/
    - name: Run Black
      run: black --check testsuites/
```

### 3. Test Stages

```yaml
# Smoke Tests (Fast, P0 only)
smoke-tests:
  needs: build
  runs-on: ubuntu-latest
  steps:
    - name: Run Smoke Tests
      run: pytest -m "smoke and P0" -v

# Regression Tests (Full suite)
regression-tests:
  needs: smoke-tests
  runs-on: ubuntu-latest
  steps:
    - name: Run Regression Tests
      run: pytest -m "regression" -v -n auto
```

### 4. Report Stage

```yaml
report:
  needs: [smoke-tests, regression-tests]
  runs-on: ubuntu-latest
  steps:
    - name: Generate Allure Report
      uses: simple-elf/allure-report-action@master
    - name: Deploy to GitHub Pages
      uses: peaceiris/actions-gh-pages@v3
```

## Environment Configuration

### Secrets Management

Store sensitive data in GitHub Secrets:

```yaml
env:
  API_BASE_URL: ${{ secrets.API_BASE_URL }}
  TEST_USER_PASSWORD: ${{ secrets.TEST_USER_PASSWORD }}
  ELASTICSEARCH_URL: ${{ secrets.ELASTICSEARCH_URL }}
```

### Environment Files

Create environment-specific configs:

```yaml
# .github/workflows/staging.yml
jobs:
  test:
    environment: staging
    env:
      CONFIG_ENV: staging
```

## Parallel Execution

### Using pytest-xdist

```yaml
- name: Run Tests in Parallel
  run: pytest testsuites/ -v -n auto --dist=loadfile
```

### Matrix Strategy

```yaml
jobs:
  test:
    strategy:
      matrix:
        test-suite: [api, ui]
        python-version: ['3.10', '3.11']
    
    steps:
      - name: Run ${{ matrix.test-suite }} Tests
        run: pytest testsuites/${{ matrix.test-suite }}_testing -v
```

## Allure Reporting

### Generate Reports

```yaml
- name: Install Allure
  run: |
    curl -o allure-2.24.0.tgz -Ls https://repo.maven.apache.org/maven2/io/qameta/allure/allure-commandline/2.24.0/allure-commandline-2.24.0.tgz
    tar -zxvf allure-2.24.0.tgz -C /opt/
    echo "/opt/allure-2.24.0/bin" >> $GITHUB_PATH

- name: Generate Allure Report
  run: allure generate allure-results -o allure-report --clean
```

### Publish to GitHub Pages

```yaml
- name: Deploy to GitHub Pages
  uses: peaceiris/actions-gh-pages@v3
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
    publish_dir: ./allure-report
```

## Notifications

### Slack Notification

```yaml
- name: Notify Slack
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    text: 'Test Results: ${{ job.status }}'
    webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

### Email Notification

```yaml
- name: Send Email Report
  uses: dawidd6/action-send-mail@v3
  with:
    server_address: smtp.gmail.com
    subject: 'Test Report - ${{ github.run_number }}'
    to: team@example.com
```

## Scheduled Runs

### Daily Regression

```yaml
on:
  schedule:
    - cron: '0 6 * * *'  # 6 AM UTC daily
```

### Weekly Full Suite

```yaml
on:
  schedule:
    - cron: '0 0 * * 0'  # Midnight UTC on Sundays
```

## Troubleshooting

### Common Issues

1. **Timeout Errors**: Increase job timeout
2. **Flaky Tests**: Add retries with `pytest-rerunfailures`
3. **Resource Issues**: Use larger runners or optimize tests

### Debug Mode

```yaml
- name: Debug Run
  run: pytest testsuites/ -v -s --log-cli-level=DEBUG
  if: failure()
```

### Artifact Collection

```yaml
- name: Upload Debug Artifacts
  if: failure()
  uses: actions/upload-artifact@v3
  with:
    name: debug-logs
    path: |
      logs/
      screenshots/
      allure-results/
```

## Best Practices

1. **Fast Feedback**: Run smoke tests first
2. **Parallel Execution**: Utilize pytest-xdist
3. **Cache Dependencies**: Speed up builds
4. **Fail Fast**: Stop on first failure in CI
5. **Clean Reports**: Generate comprehensive Allure reports
6. **Notifications**: Alert team on failures

