"""
================================================================================
Test Case Loader Module
================================================================================

This module provides functionality to load API test cases from YAML files.
It supports structured test case definitions with request configurations,
assertions, and database validations.

Key Features:
- YAML-based test case definitions
- Parameter interpolation with variables
- Dynamic test case generation
- Validation of test case structure

================================================================================
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field

import yaml
from loguru import logger


# ================================================================================
# Data Models
# ================================================================================

@dataclass
class TestCaseRequest:
    """Request configuration for a test case."""
    method: str
    url: str
    headers: Dict[str, str] = field(default_factory=dict)
    params: Dict[str, Any] = field(default_factory=dict)
    json_body: Dict[str, Any] = field(default_factory=dict)
    form_data: Dict[str, Any] = field(default_factory=dict)
    timeout: int = 30


@dataclass
class TestCaseAssertion:
    """Assertion configuration for a test case."""
    assertion_type: str
    field: str
    expected: Any = None
    description: str = ""


@dataclass
class DatabaseAssertion:
    """Database assertion configuration."""
    collection: str
    match_by: str
    match_field: str
    verify: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class TestCase:
    """Complete test case definition."""
    name: str
    description: str
    method: str
    url: str
    tags: List[str] = field(default_factory=list)
    severity: str = "normal"
    headers: Dict[str, str] = field(default_factory=dict)
    params: Dict[str, Any] = field(default_factory=dict)
    json_body: Dict[str, Any] = field(default_factory=dict)
    expected_status: int = 200
    assertions: List[TestCaseAssertion] = field(default_factory=list)
    db_assertions: Optional[DatabaseAssertion] = None
    setup: List[Dict[str, Any]] = field(default_factory=list)
    teardown: List[Dict[str, Any]] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)


# ================================================================================
# Test Case Loader
# ================================================================================

class TestCaseLoader:
    """
    Loads and parses test cases from YAML files.
    
    This class handles the loading of structured test case definitions
    from YAML files, supporting variable interpolation and validation.
    
    Example:
        loader = TestCaseLoader("testsuites/api_testing/cases")
        cases = loader.load_all()
        
        for case in cases:
            print(f"Loaded: {case.name}")
    """
    
    # Variable pattern for interpolation
    VARIABLE_PATTERN = re.compile(r'\$\{([^}]+)\}')
    
    def __init__(self, cases_directory: Union[str, Path]):
        """
        Initialize the test case loader.
        
        Args:
            cases_directory: Path to the directory containing YAML test cases
        """
        self.cases_dir = Path(cases_directory)
        self.global_variables: Dict[str, Any] = {}
        self.loaded_cases: List[TestCase] = []
    
    def set_global_variables(self, variables: Dict[str, Any]) -> None:
        """
        Set global variables for interpolation.
        
        Args:
            variables: Dictionary of variable names and values
        """
        self.global_variables.update(variables)
    
    def load_file(self, file_path: Union[str, Path]) -> List[TestCase]:
        """
        Load test cases from a single YAML file.
        
        Args:
            file_path: Path to the YAML file
            
        Returns:
            List of TestCase objects
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            logger.error(f"Test case file not found: {file_path}")
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = yaml.safe_load(f)
            
            if content is None:
                logger.warning(f"Empty YAML file: {file_path}")
                return []
            
            # Handle both single case and list of cases
            test_cases_data = content.get('test_cases', [content])
            
            if not isinstance(test_cases_data, list):
                test_cases_data = [test_cases_data]
            
            cases = []
            for case_data in test_cases_data:
                case = self._parse_test_case(case_data, file_path)
                if case:
                    cases.append(case)
            
            logger.info(f"Loaded {len(cases)} test cases from {file_path.name}")
            return cases
            
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error in {file_path}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
            return []
    
    def load_all(self, pattern: str = "*.yaml") -> List[TestCase]:
        """
        Load all test cases from the configured directory.
        
        Args:
            pattern: Glob pattern for matching YAML files
            
        Returns:
            List of all loaded TestCase objects
        """
        if not self.cases_dir.exists():
            logger.error(f"Cases directory not found: {self.cases_dir}")
            return []
        
        yaml_files = list(self.cases_dir.glob(pattern))
        yaml_files.extend(self.cases_dir.glob("*.yml"))
        
        logger.info(f"Found {len(yaml_files)} test case files in {self.cases_dir}")
        
        all_cases = []
        for file_path in sorted(yaml_files):
            cases = self.load_file(file_path)
            all_cases.extend(cases)
        
        self.loaded_cases = all_cases
        logger.info(f"Total loaded test cases: {len(all_cases)}")
        
        return all_cases
    
    def load_by_tags(self, tags: List[str]) -> List[TestCase]:
        """
        Load and filter test cases by tags.
        
        Args:
            tags: List of tags to filter by
            
        Returns:
            List of TestCase objects matching any of the specified tags
        """
        if not self.loaded_cases:
            self.load_all()
        
        filtered = [
            case for case in self.loaded_cases
            if any(tag in case.tags for tag in tags)
        ]
        
        logger.info(f"Filtered {len(filtered)} cases with tags: {tags}")
        return filtered
    
    def _parse_test_case(self, data: Dict[str, Any], source_file: Path) -> Optional[TestCase]:
        """
        Parse a single test case from dictionary data.
        
        Args:
            data: Test case data dictionary
            source_file: Source file path for error reporting
            
        Returns:
            TestCase object or None if parsing fails
        """
        try:
            # Required fields
            name = data.get('name')
            method = data.get('method', 'GET').upper()
            url = data.get('url')
            
            if not name or not url:
                logger.warning(f"Missing required fields in {source_file}")
                return None
            
            # Parse assertions
            assertions = []
            for assertion_data in data.get('assertions', []):
                assertion = TestCaseAssertion(
                    assertion_type=assertion_data.get('type', 'equal'),
                    field=assertion_data.get('field', ''),
                    expected=assertion_data.get('expected'),
                    description=assertion_data.get('description', '')
                )
                assertions.append(assertion)
            
            # Parse database assertions
            db_assertions = None
            db_data = data.get('db_assertions')
            if db_data:
                db_assertions = DatabaseAssertion(
                    collection=db_data.get('collection', ''),
                    match_by=db_data.get('match_by', ''),
                    match_field=db_data.get('match_field', ''),
                    verify=db_data.get('verify', [])
                )
            
            # Interpolate variables in request data
            params = self._interpolate_variables(data.get('params', {}))
            json_body = self._interpolate_variables(data.get('json', {}))
            headers = self._interpolate_variables(data.get('headers', {}))
            
            return TestCase(
                name=name,
                description=data.get('description', ''),
                method=method,
                url=self._interpolate_string(url),
                tags=data.get('tags', []),
                severity=data.get('severity', 'normal'),
                headers=headers,
                params=params,
                json_body=json_body,
                expected_status=data.get('expected_status', 200),
                assertions=assertions,
                db_assertions=db_assertions,
                setup=data.get('setup', []),
                teardown=data.get('teardown', []),
                variables=data.get('variables', {})
            )
            
        except Exception as e:
            logger.error(f"Error parsing test case in {source_file}: {e}")
            return None
    
    def _interpolate_variables(self, data: Any) -> Any:
        """
        Recursively interpolate variables in data structure.
        
        Args:
            data: Data structure to interpolate
            
        Returns:
            Interpolated data structure
        """
        if isinstance(data, str):
            return self._interpolate_string(data)
        elif isinstance(data, dict):
            return {k: self._interpolate_variables(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._interpolate_variables(item) for item in data]
        else:
            return data
    
    def _interpolate_string(self, text: str) -> str:
        """
        Interpolate variables in a string.
        
        Args:
            text: String with variable placeholders
            
        Returns:
            Interpolated string
        """
        def replace_var(match):
            var_name = match.group(1)
            
            # Check environment variables first
            if var_name.startswith('env.'):
                env_key = var_name[4:]
                return os.environ.get(env_key, match.group(0))
            
            # Check global variables
            return str(self.global_variables.get(var_name, match.group(0)))
        
        return self.VARIABLE_PATTERN.sub(replace_var, text)


# ================================================================================
# YAML Case Generator
# ================================================================================

class YAMLCaseGenerator:
    """
    Generates YAML test case templates from API specifications.
    
    This utility helps create initial test case files based on
    API endpoint definitions.
    """
    
    @staticmethod
    def generate_template(
        name: str,
        method: str,
        url: str,
        description: str = "",
        tags: List[str] = None
    ) -> str:
        """
        Generate a YAML test case template.
        
        Args:
            name: Test case name
            method: HTTP method
            url: API endpoint URL
            description: Test case description
            tags: List of tags
            
        Returns:
            YAML template string
        """
        tags = tags or ["P1", "regression"]
        
        template = f"""# Auto-generated test case template
name: "{name}"
description: "{description}"
method: {method.upper()}
url: "{url}"
tags: {tags}
severity: normal

# Request headers (optional)
headers:
  Content-Type: "application/json"

# Query parameters (for GET requests)
params: {{}}

# Request body (for POST/PUT/PATCH)
json: {{}}

# Expected response status
expected_status: 200

# Response assertions
assertions:
  - type: equal
    field: success
    expected: true
    description: "API should return success"
  
  - type: is_not_null
    field: results
    description: "Results should not be null"

# Database assertions (optional)
# db_assertions:
#   collection: users
#   match_by: results.user_id
#   match_field: user_id
#   verify:
#     - field: email
#       expected: "test@example.com"
"""
        return template
    
    @staticmethod
    def save_template(
        output_path: Union[str, Path],
        name: str,
        method: str,
        url: str,
        **kwargs
    ) -> None:
        """
        Generate and save a YAML test case template.
        
        Args:
            output_path: Path to save the YAML file
            name: Test case name
            method: HTTP method
            url: API endpoint URL
            **kwargs: Additional template parameters
        """
        template = YAMLCaseGenerator.generate_template(
            name=name,
            method=method,
            url=url,
            **kwargs
        )
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(template)
        
        logger.info(f"Generated test case template: {output_path}")

