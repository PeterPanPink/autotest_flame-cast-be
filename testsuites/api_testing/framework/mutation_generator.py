"""
================================================================================
AI-Powered Mutation Test Generator
================================================================================

Automatically generates negative/boundary test cases from API schemas.

Mutation Strategies:
    - missing_field: Remove required fields one by one
    - type_error: Inject wrong types (string -> number, etc.)
    - boundary: Test min/max limits for strings, numbers, arrays
    - format_error: Invalid email, URL, date formats
    - injection: SQL injection, XSS, command injection payloads
    - null_handling: null, undefined, empty values
    - mutually_exclusive: Conflicting parameter combinations

Author: Automation Team
License: MIT
================================================================================
"""

from __future__ import annotations

import copy
import random
import string
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from loguru import logger


@dataclass
class MutationCase:
    """
    Represents a single mutation test case.
    
    Attributes:
        name: Descriptive test case name
        description: What this mutation tests
        strategy: Mutation strategy used
        field: The field being mutated (if applicable)
        payload: The mutated request payload
        expected_status: Expected HTTP status code
        expected_error: Expected error message pattern
    """
    name: str
    description: str
    strategy: str
    field: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    expected_status: int = 400
    expected_error: Optional[str] = None


class MutationGenerator:
    """
    Generate mutation test cases from API schema.
    
    Features:
        - Comprehensive mutation strategies for all data types
        - Schema-aware boundary value generation
        - Security-focused injection payloads
        - Configurable strategy selection
    
    Usage:
        >>> generator = MutationGenerator(schema)
        >>> cases = generator.generate_all(valid_example)
        >>> for case in cases:
        ...     print(f"{case.name}: {case.payload}")
    """

    # SQL injection payloads
    SQL_INJECTION_PAYLOADS = [
        "'; DROP TABLE users; --",
        "1 OR 1=1",
        "' OR '1'='1",
        "1; SELECT * FROM users",
        "' UNION SELECT * FROM users --",
    ]

    # XSS payloads
    XSS_PAYLOADS = [
        "<script>alert('xss')</script>",
        "<img src=x onerror=alert('xss')>",
        "javascript:alert('xss')",
        "<svg onload=alert('xss')>",
        "'\"><script>alert('xss')</script>",
    ]

    # Command injection payloads
    COMMAND_INJECTION_PAYLOADS = [
        "; rm -rf /",
        "| cat /etc/passwd",
        "$(whoami)",
        "`id`",
        "& dir",
    ]

    # Type confusion values
    TYPE_CONFUSION = {
        "string": [123, True, [], {}, None],
        "integer": ["abc", True, [], {}, None, 3.14],
        "number": ["abc", True, [], {}, None],
        "boolean": ["true", 1, "yes", [], {}],
        "array": ["string", 123, True, {}],
        "object": ["string", 123, True, []],
    }

    def __init__(
        self,
        schema: Dict[str, Any],
        strategies: Optional[Sequence[str]] = None,
    ):
        """
        Initialize mutation generator.
        
        Args:
            schema: JSON Schema for the request body
            strategies: List of mutation strategies to apply.
                       If None, all strategies are applied.
        """
        self.schema = schema
        self.properties = schema.get("properties", {})
        self.required = set(schema.get("required", []))
        
        # Default: all strategies enabled
        self.strategies = strategies or [
            "missing_field",
            "type_error",
            "boundary",
            "format_error",
            "injection",
            "null_handling",
        ]

    def generate_all(
        self,
        valid_example: Dict[str, Any],
    ) -> List[MutationCase]:
        """
        Generate all mutation test cases.
        
        Args:
            valid_example: Valid request payload to mutate
        
        Returns:
            List of MutationCase objects
        """
        cases = []
        
        if "missing_field" in self.strategies:
            cases.extend(self._generate_missing_field_cases(valid_example))
        
        if "type_error" in self.strategies:
            cases.extend(self._generate_type_error_cases(valid_example))
        
        if "boundary" in self.strategies:
            cases.extend(self._generate_boundary_cases(valid_example))
        
        if "format_error" in self.strategies:
            cases.extend(self._generate_format_error_cases(valid_example))
        
        if "injection" in self.strategies:
            cases.extend(self._generate_injection_cases(valid_example))
        
        if "null_handling" in self.strategies:
            cases.extend(self._generate_null_handling_cases(valid_example))
        
        logger.info(
            f"Generated {len(cases)} mutation cases using strategies: "
            f"{self.strategies}"
        )
        
        return cases

    def _generate_missing_field_cases(
        self,
        valid_example: Dict[str, Any],
    ) -> List[MutationCase]:
        """Generate cases with required fields removed."""
        cases = []
        
        for field_name in self.required:
            if field_name in valid_example:
                payload = copy.deepcopy(valid_example)
                del payload[field_name]
                
                cases.append(MutationCase(
                    name=f"missing_required_field_{field_name}",
                    description=f"Required field '{field_name}' is missing",
                    strategy="missing_field",
                    field=field_name,
                    payload=payload,
                    expected_status=400,
                    expected_error="required",
                ))
        
        return cases

    def _generate_type_error_cases(
        self,
        valid_example: Dict[str, Any],
    ) -> List[MutationCase]:
        """Generate cases with wrong field types."""
        cases = []
        
        for field_name, field_schema in self.properties.items():
            if field_name not in valid_example:
                continue
            
            field_type = field_schema.get("type", "string")
            wrong_values = self.TYPE_CONFUSION.get(field_type, [])
            
            for wrong_value in wrong_values[:2]:  # Limit to 2 per field
                payload = copy.deepcopy(valid_example)
                payload[field_name] = wrong_value
                
                value_type = type(wrong_value).__name__
                cases.append(MutationCase(
                    name=f"type_error_{field_name}_{value_type}",
                    description=(
                        f"Field '{field_name}' expects {field_type}, "
                        f"received {value_type}"
                    ),
                    strategy="type_error",
                    field=field_name,
                    payload=payload,
                    expected_status=400,
                    expected_error="type",
                ))
        
        return cases

    def _generate_boundary_cases(
        self,
        valid_example: Dict[str, Any],
    ) -> List[MutationCase]:
        """Generate boundary value test cases."""
        cases = []
        
        for field_name, field_schema in self.properties.items():
            if field_name not in valid_example:
                continue
            
            field_type = field_schema.get("type", "string")
            
            if field_type == "string":
                cases.extend(
                    self._generate_string_boundary_cases(
                        field_name, field_schema, valid_example
                    )
                )
            elif field_type in ("integer", "number"):
                cases.extend(
                    self._generate_number_boundary_cases(
                        field_name, field_schema, valid_example
                    )
                )
            elif field_type == "array":
                cases.extend(
                    self._generate_array_boundary_cases(
                        field_name, field_schema, valid_example
                    )
                )
        
        return cases

    def _generate_string_boundary_cases(
        self,
        field_name: str,
        field_schema: Dict[str, Any],
        valid_example: Dict[str, Any],
    ) -> List[MutationCase]:
        """Generate string length boundary cases."""
        cases = []
        
        min_length = field_schema.get("minLength", 0)
        max_length = field_schema.get("maxLength")
        
        # Below minimum length
        if min_length > 0:
            payload = copy.deepcopy(valid_example)
            payload[field_name] = "a" * (min_length - 1) if min_length > 1 else ""
            
            cases.append(MutationCase(
                name=f"boundary_{field_name}_below_min_length",
                description=f"String length below minimum ({min_length})",
                strategy="boundary",
                field=field_name,
                payload=payload,
                expected_status=400,
            ))
        
        # Above maximum length
        if max_length:
            payload = copy.deepcopy(valid_example)
            payload[field_name] = "a" * (max_length + 1)
            
            cases.append(MutationCase(
                name=f"boundary_{field_name}_above_max_length",
                description=f"String length above maximum ({max_length})",
                strategy="boundary",
                field=field_name,
                payload=payload,
                expected_status=400,
            ))
        
        # Empty string
        payload = copy.deepcopy(valid_example)
        payload[field_name] = ""
        
        cases.append(MutationCase(
            name=f"boundary_{field_name}_empty_string",
            description="Empty string value",
            strategy="boundary",
            field=field_name,
            payload=payload,
            expected_status=400 if min_length > 0 else 200,
        ))
        
        return cases

    def _generate_number_boundary_cases(
        self,
        field_name: str,
        field_schema: Dict[str, Any],
        valid_example: Dict[str, Any],
    ) -> List[MutationCase]:
        """Generate numeric boundary cases."""
        cases = []
        
        minimum = field_schema.get("minimum")
        maximum = field_schema.get("maximum")
        
        # Below minimum
        if minimum is not None:
            payload = copy.deepcopy(valid_example)
            payload[field_name] = minimum - 1
            
            cases.append(MutationCase(
                name=f"boundary_{field_name}_below_minimum",
                description=f"Value below minimum ({minimum})",
                strategy="boundary",
                field=field_name,
                payload=payload,
                expected_status=400,
            ))
        
        # Above maximum
        if maximum is not None:
            payload = copy.deepcopy(valid_example)
            payload[field_name] = maximum + 1
            
            cases.append(MutationCase(
                name=f"boundary_{field_name}_above_maximum",
                description=f"Value above maximum ({maximum})",
                strategy="boundary",
                field=field_name,
                payload=payload,
                expected_status=400,
            ))
        
        # Negative value
        payload = copy.deepcopy(valid_example)
        payload[field_name] = -1
        
        cases.append(MutationCase(
            name=f"boundary_{field_name}_negative",
            description="Negative numeric value",
            strategy="boundary",
            field=field_name,
            payload=payload,
            expected_status=400 if minimum is not None and minimum >= 0 else 200,
        ))
        
        return cases

    def _generate_array_boundary_cases(
        self,
        field_name: str,
        field_schema: Dict[str, Any],
        valid_example: Dict[str, Any],
    ) -> List[MutationCase]:
        """Generate array length boundary cases."""
        cases = []
        
        max_items = field_schema.get("maxItems")
        
        # Empty array
        payload = copy.deepcopy(valid_example)
        payload[field_name] = []
        
        cases.append(MutationCase(
            name=f"boundary_{field_name}_empty_array",
            description="Empty array",
            strategy="boundary",
            field=field_name,
            payload=payload,
            expected_status=400,
        ))
        
        # Above max items
        if max_items:
            payload = copy.deepcopy(valid_example)
            payload[field_name] = ["item"] * (max_items + 1)
            
            cases.append(MutationCase(
                name=f"boundary_{field_name}_above_max_items",
                description=f"Array length above maximum ({max_items})",
                strategy="boundary",
                field=field_name,
                payload=payload,
                expected_status=400,
            ))
        
        return cases

    def _generate_format_error_cases(
        self,
        valid_example: Dict[str, Any],
    ) -> List[MutationCase]:
        """Generate format validation error cases."""
        cases = []
        
        for field_name, field_schema in self.properties.items():
            if field_name not in valid_example:
                continue
            
            field_format = field_schema.get("format")
            
            if field_format == "email":
                invalid_emails = [
                    "notanemail",
                    "missing@domain",
                    "@nodomain.com",
                    "spaces in@email.com",
                ]
                for invalid_email in invalid_emails[:2]:
                    payload = copy.deepcopy(valid_example)
                    payload[field_name] = invalid_email
                    
                    cases.append(MutationCase(
                        name=f"format_error_{field_name}_invalid_email",
                        description=f"Invalid email format: {invalid_email}",
                        strategy="format_error",
                        field=field_name,
                        payload=payload,
                        expected_status=400,
                    ))
            
            elif field_format == "uri":
                invalid_urls = [
                    "not-a-url",
                    "http//missing-colon.com",
                    "://no-scheme.com",
                ]
                for invalid_url in invalid_urls[:1]:
                    payload = copy.deepcopy(valid_example)
                    payload[field_name] = invalid_url
                    
                    cases.append(MutationCase(
                        name=f"format_error_{field_name}_invalid_url",
                        description=f"Invalid URL format: {invalid_url}",
                        strategy="format_error",
                        field=field_name,
                        payload=payload,
                        expected_status=400,
                    ))
            
            # Enum validation
            enum_values = field_schema.get("enum")
            if enum_values:
                payload = copy.deepcopy(valid_example)
                payload[field_name] = "INVALID_ENUM_VALUE"
                
                cases.append(MutationCase(
                    name=f"format_error_{field_name}_invalid_enum",
                    description=f"Invalid enum value (valid: {enum_values})",
                    strategy="format_error",
                    field=field_name,
                    payload=payload,
                    expected_status=400,
                ))
        
        return cases

    def _generate_injection_cases(
        self,
        valid_example: Dict[str, Any],
    ) -> List[MutationCase]:
        """Generate security injection test cases."""
        cases = []
        
        for field_name, field_schema in self.properties.items():
            if field_name not in valid_example:
                continue
            
            field_type = field_schema.get("type", "string")
            if field_type != "string":
                continue
            
            # SQL injection
            payload = copy.deepcopy(valid_example)
            payload[field_name] = random.choice(self.SQL_INJECTION_PAYLOADS)
            
            cases.append(MutationCase(
                name=f"injection_{field_name}_sql",
                description="SQL injection payload",
                strategy="injection",
                field=field_name,
                payload=payload,
                expected_status=400,  # Should be rejected or sanitized
            ))
            
            # XSS
            payload = copy.deepcopy(valid_example)
            payload[field_name] = random.choice(self.XSS_PAYLOADS)
            
            cases.append(MutationCase(
                name=f"injection_{field_name}_xss",
                description="XSS payload",
                strategy="injection",
                field=field_name,
                payload=payload,
                expected_status=400,  # Should be rejected or sanitized
            ))
        
        return cases

    def _generate_null_handling_cases(
        self,
        valid_example: Dict[str, Any],
    ) -> List[MutationCase]:
        """Generate null/empty value handling cases."""
        cases = []
        
        for field_name in self.required:
            if field_name not in valid_example:
                continue
            
            # null value
            payload = copy.deepcopy(valid_example)
            payload[field_name] = None
            
            cases.append(MutationCase(
                name=f"null_handling_{field_name}_null",
                description=f"Required field '{field_name}' is null",
                strategy="null_handling",
                field=field_name,
                payload=payload,
                expected_status=400,
            ))
        
        return cases


__all__ = [
    "MutationGenerator",
    "MutationCase",
]

