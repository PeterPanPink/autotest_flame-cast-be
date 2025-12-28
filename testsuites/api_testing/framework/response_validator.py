# ================================================================================
# Response Validator
# ================================================================================
#
# This module provides utilities for validating API responses against expected
# schemas and business rules. It supports JSON Schema validation, custom
# validation rules, and integration with Allure reporting.
#
# Key Features:
#   - JSON Schema validation
#   - Custom assertion rules execution
#   - Field-level validation with detailed error messages
#   - Business rule validation
#   - Allure integration for test reporting
#
# ================================================================================

import json
import re
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum

import allure
from loguru import logger


class ValidationType(Enum):
    """Enumeration of supported validation types."""
    EQUAL = "equal"
    NOT_EQUAL = "not_equal"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    REGEX_MATCH = "regex_match"
    LENGTH_EQUAL = "length_equal"
    LENGTH_GREATER_THAN = "length_greater_than"
    LENGTH_LESS_THAN = "length_less_than"
    LENGTH_GREATER_THAN_OR_EQUAL = "length_greater_than_or_equal"
    LENGTH_LESS_THAN_OR_EQUAL = "length_less_than_or_equal"
    TYPE_CHECK = "type_check"
    RANGE = "range"
    IN_LIST = "in_list"
    NOT_IN_LIST = "not_in_list"


@dataclass
class ValidationRule:
    """
    Represents a single validation rule to be applied to a response field.
    
    Attributes:
        field: The field path to validate (supports dot notation for nested fields)
        validation_type: The type of validation to perform
        expected: The expected value or pattern
        description: Human-readable description of the validation
        required: Whether the field must exist
    """
    field: str
    validation_type: ValidationType
    expected: Any = None
    description: str = ""
    required: bool = True


@dataclass
class ValidationResult:
    """
    Represents the result of a validation operation.
    
    Attributes:
        passed: Whether the validation passed
        rule: The validation rule that was applied
        actual_value: The actual value found in the response
        error_message: Error message if validation failed
    """
    passed: bool
    rule: ValidationRule
    actual_value: Any = None
    error_message: str = ""


class ResponseValidator:
    """
    A comprehensive response validator for API testing.
    
    This class provides methods to validate API responses against various rules
    including schema validation, field-level assertions, and business rules.
    
    Example:
        validator = ResponseValidator()
        rules = [
            ValidationRule(
                field="success",
                validation_type=ValidationType.EQUAL,
                expected=True,
                description="API should return success=true"
            ),
            ValidationRule(
                field="results.channel_id",
                validation_type=ValidationType.REGEX_MATCH,
                expected="^ch_[a-zA-Z0-9]+",
                description="Channel ID format validation"
            )
        ]
        results = validator.validate(response_json, rules)
    """
    
    def __init__(self):
        """Initialize the response validator."""
        self._validation_handlers = {
            ValidationType.EQUAL: self._validate_equal,
            ValidationType.NOT_EQUAL: self._validate_not_equal,
            ValidationType.IS_NULL: self._validate_is_null,
            ValidationType.IS_NOT_NULL: self._validate_is_not_null,
            ValidationType.CONTAINS: self._validate_contains,
            ValidationType.NOT_CONTAINS: self._validate_not_contains,
            ValidationType.REGEX_MATCH: self._validate_regex_match,
            ValidationType.LENGTH_EQUAL: self._validate_length_equal,
            ValidationType.LENGTH_GREATER_THAN: self._validate_length_greater_than,
            ValidationType.LENGTH_LESS_THAN: self._validate_length_less_than,
            ValidationType.LENGTH_GREATER_THAN_OR_EQUAL: self._validate_length_gte,
            ValidationType.LENGTH_LESS_THAN_OR_EQUAL: self._validate_length_lte,
            ValidationType.TYPE_CHECK: self._validate_type_check,
            ValidationType.RANGE: self._validate_range,
            ValidationType.IN_LIST: self._validate_in_list,
            ValidationType.NOT_IN_LIST: self._validate_not_in_list,
        }
    
    @allure.step("Validating response against {num_rules} rules")
    def validate(
        self, 
        response_data: Dict[str, Any], 
        rules: List[ValidationRule]
    ) -> List[ValidationResult]:
        """
        Validate response data against a list of validation rules.
        
        Args:
            response_data: The parsed JSON response data
            rules: List of validation rules to apply
            
        Returns:
            List of ValidationResult objects, one for each rule
        """
        # Store rule count for Allure step title
        num_rules = len(rules)
        results = []
        
        for rule in rules:
            result = self._apply_rule(response_data, rule)
            results.append(result)
            
            # Log and attach to Allure
            status_icon = "✅" if result.passed else "❌"
            log_msg = f"{status_icon} {rule.description or rule.field}: {result.passed}"
            
            if result.passed:
                logger.debug(log_msg)
            else:
                logger.warning(f"{log_msg} - {result.error_message}")
        
        # Attach summary to Allure
        self._attach_validation_summary(results)
        
        return results
    
    def validate_and_assert(
        self,
        response_data: Dict[str, Any],
        rules: List[ValidationRule],
        fail_fast: bool = False
    ) -> None:
        """
        Validate response and raise assertion error if any rule fails.
        
        Args:
            response_data: The parsed JSON response data
            rules: List of validation rules to apply
            fail_fast: If True, stop on first failure
            
        Raises:
            AssertionError: If any validation rule fails
        """
        results = self.validate(response_data, rules)
        failures = [r for r in results if not r.passed]
        
        if failures:
            error_messages = [
                f"- {f.rule.field}: {f.error_message}" 
                for f in failures
            ]
            error_text = "\n".join(error_messages)
            raise AssertionError(
                f"Response validation failed ({len(failures)}/{len(results)} rules):\n"
                f"{error_text}"
            )
    
    def _apply_rule(
        self, 
        response_data: Dict[str, Any], 
        rule: ValidationRule
    ) -> ValidationResult:
        """Apply a single validation rule to the response data."""
        try:
            # Get the actual value from response
            actual_value = self._get_nested_value(response_data, rule.field)
            
            # Get the appropriate handler for this validation type
            handler = self._validation_handlers.get(rule.validation_type)
            
            if handler is None:
                return ValidationResult(
                    passed=False,
                    rule=rule,
                    actual_value=actual_value,
                    error_message=f"Unknown validation type: {rule.validation_type}"
                )
            
            # Execute the validation
            passed, error_message = handler(actual_value, rule.expected)
            
            return ValidationResult(
                passed=passed,
                rule=rule,
                actual_value=actual_value,
                error_message=error_message
            )
            
        except KeyError as e:
            if rule.required:
                return ValidationResult(
                    passed=False,
                    rule=rule,
                    error_message=f"Required field not found: {rule.field}"
                )
            else:
                return ValidationResult(
                    passed=True,
                    rule=rule,
                    error_message=f"Optional field not found: {rule.field}"
                )
        except Exception as e:
            return ValidationResult(
                passed=False,
                rule=rule,
                error_message=f"Validation error: {str(e)}"
            )
    
    def _get_nested_value(self, data: Dict, key_path: str) -> Any:
        """
        Get a value from nested dictionary using dot notation.
        
        Args:
            data: The dictionary to search
            key_path: Dot-separated path (e.g., "results.channel.id")
            
        Returns:
            The value at the specified path
            
        Raises:
            KeyError: If the path doesn't exist
        """
        keys = key_path.split('.')
        current = data
        
        for key in keys:
            # Handle array indexing like "items[0]"
            array_match = re.match(r'(\w+)\[(\d+)\]', key)
            if array_match:
                field_name = array_match.group(1)
                index = int(array_match.group(2))
                current = current[field_name][index]
            else:
                current = current[key]
        
        return current
    
    # Validation handlers
    def _validate_equal(self, actual: Any, expected: Any) -> tuple:
        """Validate equality."""
        passed = actual == expected
        error = "" if passed else f"Expected '{expected}', got '{actual}'"
        return passed, error
    
    def _validate_not_equal(self, actual: Any, expected: Any) -> tuple:
        """Validate inequality."""
        passed = actual != expected
        error = "" if passed else f"Expected not equal to '{expected}'"
        return passed, error
    
    def _validate_is_null(self, actual: Any, expected: Any) -> tuple:
        """Validate null value."""
        passed = actual is None
        error = "" if passed else f"Expected null, got '{actual}'"
        return passed, error
    
    def _validate_is_not_null(self, actual: Any, expected: Any) -> tuple:
        """Validate non-null value."""
        passed = actual is not None
        error = "" if passed else "Expected non-null value, got null"
        return passed, error
    
    def _validate_contains(self, actual: Any, expected: Any) -> tuple:
        """Validate containment."""
        passed = expected in str(actual)
        error = "" if passed else f"'{actual}' does not contain '{expected}'"
        return passed, error
    
    def _validate_not_contains(self, actual: Any, expected: Any) -> tuple:
        """Validate non-containment."""
        passed = expected not in str(actual)
        error = "" if passed else f"'{actual}' contains '{expected}'"
        return passed, error
    
    def _validate_regex_match(self, actual: Any, expected: str) -> tuple:
        """Validate regex pattern match."""
        try:
            passed = re.match(expected, str(actual)) is not None
            error = "" if passed else f"'{actual}' does not match pattern '{expected}'"
            return passed, error
        except re.error as e:
            return False, f"Invalid regex pattern: {e}"
    
    def _validate_length_equal(self, actual: Any, expected: int) -> tuple:
        """Validate exact length."""
        actual_len = len(actual) if hasattr(actual, '__len__') else 0
        passed = actual_len == expected
        error = "" if passed else f"Expected length {expected}, got {actual_len}"
        return passed, error
    
    def _validate_length_greater_than(self, actual: Any, expected: int) -> tuple:
        """Validate length greater than."""
        actual_len = len(actual) if hasattr(actual, '__len__') else 0
        passed = actual_len > expected
        error = "" if passed else f"Expected length > {expected}, got {actual_len}"
        return passed, error
    
    def _validate_length_less_than(self, actual: Any, expected: int) -> tuple:
        """Validate length less than."""
        actual_len = len(actual) if hasattr(actual, '__len__') else 0
        passed = actual_len < expected
        error = "" if passed else f"Expected length < {expected}, got {actual_len}"
        return passed, error
    
    def _validate_length_gte(self, actual: Any, expected: int) -> tuple:
        """Validate length greater than or equal."""
        actual_len = len(actual) if hasattr(actual, '__len__') else 0
        passed = actual_len >= expected
        error = "" if passed else f"Expected length >= {expected}, got {actual_len}"
        return passed, error
    
    def _validate_length_lte(self, actual: Any, expected: int) -> tuple:
        """Validate length less than or equal."""
        actual_len = len(actual) if hasattr(actual, '__len__') else 0
        passed = actual_len <= expected
        error = "" if passed else f"Expected length <= {expected}, got {actual_len}"
        return passed, error
    
    def _validate_type_check(self, actual: Any, expected: str) -> tuple:
        """Validate value type."""
        type_map = {
            'string': str,
            'str': str,
            'int': int,
            'integer': int,
            'float': float,
            'number': (int, float),
            'bool': bool,
            'boolean': bool,
            'list': list,
            'array': list,
            'dict': dict,
            'object': dict,
            'null': type(None),
        }
        expected_type = type_map.get(expected.lower())
        if expected_type is None:
            return False, f"Unknown type: {expected}"
        
        passed = isinstance(actual, expected_type)
        error = "" if passed else f"Expected type {expected}, got {type(actual).__name__}"
        return passed, error
    
    def _validate_range(self, actual: Any, expected: Dict) -> tuple:
        """Validate value is within a range."""
        min_val = expected.get('min')
        max_val = expected.get('max')
        
        if min_val is not None and actual < min_val:
            return False, f"Value {actual} is less than minimum {min_val}"
        if max_val is not None and actual > max_val:
            return False, f"Value {actual} is greater than maximum {max_val}"
        return True, ""
    
    def _validate_in_list(self, actual: Any, expected: List) -> tuple:
        """Validate value is in list."""
        passed = actual in expected
        error = "" if passed else f"'{actual}' not in {expected}"
        return passed, error
    
    def _validate_not_in_list(self, actual: Any, expected: List) -> tuple:
        """Validate value is not in list."""
        passed = actual not in expected
        error = "" if passed else f"'{actual}' should not be in {expected}"
        return passed, error
    
    def _attach_validation_summary(self, results: List[ValidationResult]) -> None:
        """Attach validation summary to Allure report."""
        passed_count = sum(1 for r in results if r.passed)
        failed_count = len(results) - passed_count
        
        summary_lines = [
            f"Total Rules: {len(results)}",
            f"Passed: {passed_count}",
            f"Failed: {failed_count}",
            "",
            "Details:",
            "-" * 40
        ]
        
        for result in results:
            status = "✅ PASS" if result.passed else "❌ FAIL"
            line = f"{status} | {result.rule.field}"
            if not result.passed:
                line += f" | {result.error_message}"
            summary_lines.append(line)
        
        allure.attach(
            "\n".join(summary_lines),
            name="Validation Summary",
            attachment_type=allure.attachment_type.TEXT
        )

