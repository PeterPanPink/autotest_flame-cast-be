"""
================================================================================
Assertion Executor Module
================================================================================

This module provides a flexible assertion engine for validating API responses.
It supports multiple assertion types including equality, regex matching,
JSON path queries, and database validations.

Key Features:
- Multiple assertion types (equal, not_null, regex, jsonpath, etc.)
- Database assertion support for data consistency validation
- Detailed failure reporting with context
- Allure integration for rich test reports

================================================================================
"""

import re
import json
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum

import allure
from loguru import logger

try:
    from jsonpath_ng import parse as jsonpath_parse
    JSONPATH_AVAILABLE = True
except ImportError:
    JSONPATH_AVAILABLE = False
    logger.warning("jsonpath-ng not installed, jsonpath assertions disabled")


# ================================================================================
# Assertion Types
# ================================================================================

class AssertionType(str, Enum):
    """Supported assertion types."""
    EQUAL = "equal"
    NOT_EQUAL = "not_equal"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    REGEX_MATCH = "regex_match"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_THAN_OR_EQUAL = "greater_than_or_equal"
    LESS_THAN_OR_EQUAL = "less_than_or_equal"
    IN_LIST = "in_list"
    NOT_IN_LIST = "not_in_list"
    LENGTH_EQUAL = "length_equal"
    LENGTH_GREATER_THAN = "length_greater_than"
    JSONPATH = "jsonpath"
    SCHEMA_MATCH = "schema_match"


@dataclass
class AssertionResult:
    """Result of a single assertion execution."""
    passed: bool
    assertion_type: str
    field: str
    expected: Any
    actual: Any
    message: str
    details: Optional[Dict[str, Any]] = None


# ================================================================================
# Assertion Executor
# ================================================================================

class AssertionExecutor:
    """
    Executes and validates assertions against API responses.
    
    This class provides a comprehensive set of assertion methods for
    validating API response data, with support for nested field access,
    regex patterns, and JSONPath queries.
    
    Example:
        executor = AssertionExecutor(response_data)
        results = executor.execute_assertions([
            {"type": "equal", "field": "success", "expected": True},
            {"type": "is_not_null", "field": "results.user_id"},
            {"type": "regex_match", "field": "results.email", "expected": r"^[\\w.-]+@[\\w.-]+\\.\\w+$"}
        ])
    """
    
    def __init__(self, response_data: Dict[str, Any]):
        """
        Initialize the assertion executor.
        
        Args:
            response_data: The API response data to validate
        """
        self.response_data = response_data
        self.results: List[AssertionResult] = []
    
    def get_field_value(self, field_path: str) -> Any:
        """
        Extract a value from nested response data using dot notation.
        
        Args:
            field_path: Dot-separated path to the field (e.g., "results.user.id")
            
        Returns:
            The value at the specified path, or None if not found
        """
        if not field_path:
            return self.response_data
        
        parts = field_path.split(".")
        current = self.response_data
        
        for part in parts:
            if current is None:
                return None
            
            # Handle array indexing (e.g., "items[0]")
            if "[" in part and "]" in part:
                key = part[:part.index("[")]
                index = int(part[part.index("[") + 1:part.index("]")])
                
                if isinstance(current, dict):
                    current = current.get(key, [])
                
                if isinstance(current, list) and len(current) > index:
                    current = current[index]
                else:
                    return None
            else:
                if isinstance(current, dict):
                    current = current.get(part)
                else:
                    return None
        
        return current
    
    def execute_assertion(self, assertion: Dict[str, Any]) -> AssertionResult:
        """
        Execute a single assertion.
        
        Args:
            assertion: Assertion configuration dict with type, field, and expected value
            
        Returns:
            AssertionResult with pass/fail status and details
        """
        assertion_type = assertion.get("type", AssertionType.EQUAL)
        field = assertion.get("field", "")
        expected = assertion.get("expected")
        description = assertion.get("description", "")
        
        actual = self.get_field_value(field)
        
        # Execute based on assertion type
        handlers = {
            AssertionType.EQUAL: self._assert_equal,
            AssertionType.NOT_EQUAL: self._assert_not_equal,
            AssertionType.IS_NULL: self._assert_is_null,
            AssertionType.IS_NOT_NULL: self._assert_is_not_null,
            AssertionType.CONTAINS: self._assert_contains,
            AssertionType.NOT_CONTAINS: self._assert_not_contains,
            AssertionType.REGEX_MATCH: self._assert_regex_match,
            AssertionType.GREATER_THAN: self._assert_greater_than,
            AssertionType.LESS_THAN: self._assert_less_than,
            AssertionType.GREATER_THAN_OR_EQUAL: self._assert_greater_than_or_equal,
            AssertionType.LESS_THAN_OR_EQUAL: self._assert_less_than_or_equal,
            AssertionType.IN_LIST: self._assert_in_list,
            AssertionType.NOT_IN_LIST: self._assert_not_in_list,
            AssertionType.LENGTH_EQUAL: self._assert_length_equal,
            AssertionType.LENGTH_GREATER_THAN: self._assert_length_greater_than,
            AssertionType.JSONPATH: self._assert_jsonpath,
        }
        
        handler = handlers.get(assertion_type, self._assert_equal)
        passed, message = handler(actual, expected, field)
        
        result = AssertionResult(
            passed=passed,
            assertion_type=str(assertion_type),
            field=field,
            expected=expected,
            actual=actual,
            message=message or description,
            details={"description": description} if description else None
        )
        
        self.results.append(result)
        return result
    
    def execute_assertions(self, assertions: List[Dict[str, Any]]) -> List[AssertionResult]:
        """
        Execute multiple assertions.
        
        Args:
            assertions: List of assertion configurations
            
        Returns:
            List of AssertionResults
        """
        with allure.step(f"Executing {len(assertions)} assertions"):
            for assertion in assertions:
                result = self.execute_assertion(assertion)
                
                # Log result
                status = "✅ PASS" if result.passed else "❌ FAIL"
                logger.debug(f"{status}: {result.field} - {result.message}")
                
                # Attach to Allure
                allure.attach(
                    json.dumps({
                        "field": result.field,
                        "type": result.assertion_type,
                        "expected": str(result.expected),
                        "actual": str(result.actual),
                        "passed": result.passed
                    }, indent=2),
                    name=f"Assertion: {result.field}",
                    attachment_type=allure.attachment_type.JSON
                )
        
        return self.results
    
    def all_passed(self) -> bool:
        """Check if all assertions passed."""
        return all(r.passed for r in self.results)
    
    def get_failures(self) -> List[AssertionResult]:
        """Get list of failed assertions."""
        return [r for r in self.results if not r.passed]
    
    # ============================================================
    # Assertion Handlers
    # ============================================================
    
    def _assert_equal(self, actual: Any, expected: Any, field: str) -> tuple:
        passed = actual == expected
        message = f"Expected '{field}' to equal {expected}, got {actual}"
        return passed, message
    
    def _assert_not_equal(self, actual: Any, expected: Any, field: str) -> tuple:
        passed = actual != expected
        message = f"Expected '{field}' to not equal {expected}, got {actual}"
        return passed, message
    
    def _assert_is_null(self, actual: Any, expected: Any, field: str) -> tuple:
        passed = actual is None
        message = f"Expected '{field}' to be null, got {actual}"
        return passed, message
    
    def _assert_is_not_null(self, actual: Any, expected: Any, field: str) -> tuple:
        passed = actual is not None
        message = f"Expected '{field}' to not be null"
        return passed, message
    
    def _assert_contains(self, actual: Any, expected: Any, field: str) -> tuple:
        if actual is None:
            return False, f"Field '{field}' is null, cannot check contains"
        passed = expected in actual
        message = f"Expected '{field}' to contain '{expected}'"
        return passed, message
    
    def _assert_not_contains(self, actual: Any, expected: Any, field: str) -> tuple:
        if actual is None:
            return True, f"Field '{field}' is null"
        passed = expected not in actual
        message = f"Expected '{field}' to not contain '{expected}'"
        return passed, message
    
    def _assert_regex_match(self, actual: Any, expected: Any, field: str) -> tuple:
        if actual is None:
            return False, f"Field '{field}' is null, cannot match regex"
        try:
            passed = bool(re.match(expected, str(actual)))
            message = f"Expected '{field}' to match pattern '{expected}'"
            return passed, message
        except re.error as e:
            return False, f"Invalid regex pattern: {e}"
    
    def _assert_greater_than(self, actual: Any, expected: Any, field: str) -> tuple:
        try:
            passed = actual > expected
            message = f"Expected '{field}' ({actual}) to be greater than {expected}"
            return passed, message
        except TypeError:
            return False, f"Cannot compare '{field}' value: {actual}"
    
    def _assert_less_than(self, actual: Any, expected: Any, field: str) -> tuple:
        try:
            passed = actual < expected
            message = f"Expected '{field}' ({actual}) to be less than {expected}"
            return passed, message
        except TypeError:
            return False, f"Cannot compare '{field}' value: {actual}"
    
    def _assert_greater_than_or_equal(self, actual: Any, expected: Any, field: str) -> tuple:
        try:
            passed = actual >= expected
            message = f"Expected '{field}' ({actual}) to be >= {expected}"
            return passed, message
        except TypeError:
            return False, f"Cannot compare '{field}' value: {actual}"
    
    def _assert_less_than_or_equal(self, actual: Any, expected: Any, field: str) -> tuple:
        try:
            passed = actual <= expected
            message = f"Expected '{field}' ({actual}) to be <= {expected}"
            return passed, message
        except TypeError:
            return False, f"Cannot compare '{field}' value: {actual}"
    
    def _assert_in_list(self, actual: Any, expected: List, field: str) -> tuple:
        passed = actual in expected
        message = f"Expected '{field}' ({actual}) to be in {expected}"
        return passed, message
    
    def _assert_not_in_list(self, actual: Any, expected: List, field: str) -> tuple:
        passed = actual not in expected
        message = f"Expected '{field}' ({actual}) to not be in {expected}"
        return passed, message
    
    def _assert_length_equal(self, actual: Any, expected: int, field: str) -> tuple:
        try:
            actual_len = len(actual) if actual else 0
            passed = actual_len == expected
            message = f"Expected '{field}' length to be {expected}, got {actual_len}"
            return passed, message
        except TypeError:
            return False, f"Cannot get length of '{field}'"
    
    def _assert_length_greater_than(self, actual: Any, expected: int, field: str) -> tuple:
        try:
            actual_len = len(actual) if actual else 0
            passed = actual_len > expected
            message = f"Expected '{field}' length ({actual_len}) to be > {expected}"
            return passed, message
        except TypeError:
            return False, f"Cannot get length of '{field}'"
    
    def _assert_jsonpath(self, actual: Any, expected: Dict, field: str) -> tuple:
        if not JSONPATH_AVAILABLE:
            return False, "jsonpath-ng not installed"
        
        expression = expected.get("expression", "")
        condition = expected.get("condition", "exists")
        pattern = expected.get("pattern")
        
        try:
            jsonpath_expr = jsonpath_parse(expression)
            matches = [match.value for match in jsonpath_expr.find(self.response_data)]
            
            if condition == "exists":
                passed = len(matches) > 0
                message = f"JSONPath '{expression}' should exist"
            elif condition == "all_match" and pattern:
                passed = all(re.match(pattern, str(m)) for m in matches)
                message = f"All JSONPath matches should match pattern '{pattern}'"
            elif condition == "all_not_null":
                passed = all(m is not None for m in matches)
                message = f"All JSONPath matches should not be null"
            else:
                passed = len(matches) > 0
                message = f"JSONPath '{expression}' evaluation"
            
            return passed, message
        except Exception as e:
            return False, f"JSONPath error: {e}"


# ================================================================================
# Database Assertion Executor
# ================================================================================

class DatabaseAssertionExecutor:
    """
    Executes assertions against database records.
    
    This class provides methods to validate that API operations
    correctly persist data to the database.
    
    Example:
        executor = DatabaseAssertionExecutor(mongo_client)
        results = executor.execute_assertions(
            collection="users",
            match_by={"user_id": "user_123"},
            assertions=[
                {"field": "email", "expected": "test@example.com"},
                {"field": "created_at", "type": "is_not_null"}
            ]
        )
    """
    
    def __init__(self, db_client):
        """
        Initialize the database assertion executor.
        
        Args:
            db_client: Database client instance (e.g., MongoDB client)
        """
        self.db_client = db_client
        self.results: List[AssertionResult] = []
    
    def execute_assertions(
        self,
        collection: str,
        match_by: Dict[str, Any],
        assertions: List[Dict[str, Any]]
    ) -> List[AssertionResult]:
        """
        Execute database assertions.
        
        Args:
            collection: Database collection/table name
            match_by: Query to find the record
            assertions: List of field assertions
            
        Returns:
            List of AssertionResults
        """
        with allure.step(f"Database Assertions on {collection}"):
            # Fetch record from database
            record = self.db_client.find_one(collection, match_by)
            
            if record is None:
                result = AssertionResult(
                    passed=False,
                    assertion_type="record_exists",
                    field="",
                    expected="record exists",
                    actual="not found",
                    message=f"No record found matching {match_by}"
                )
                self.results.append(result)
                return self.results
            
            # Execute assertions against the record
            response_executor = AssertionExecutor(record)
            self.results = response_executor.execute_assertions(assertions)
            
            allure.attach(
                json.dumps(record, indent=2, default=str),
                name="Database Record",
                attachment_type=allure.attachment_type.JSON
            )
        
        return self.results
    
    def all_passed(self) -> bool:
        """Check if all database assertions passed."""
        return all(r.passed for r in self.results)

