"""
================================================================================
AI-Powered API Test Data Generator
================================================================================

This module provides AI-enhanced test data generation capabilities for API
testing. It can analyze API schemas (OpenAPI/Swagger) and generate appropriate
test data for various scenarios.

Features:
- OpenAPI/Swagger schema parsing
- Intelligent data generation based on field types and constraints
- Boundary value generation
- Invalid data generation for negative testing
- Customizable data patterns

================================================================================
"""

import json
import random
import string
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import uuid

from loguru import logger


# ================================================================================
# Enums and Constants
# ================================================================================

class DataGenerationType(Enum):
    """Types of data generation strategies."""
    VALID = "valid"
    BOUNDARY_MIN = "boundary_min"
    BOUNDARY_MAX = "boundary_max"
    INVALID_TYPE = "invalid_type"
    INVALID_FORMAT = "invalid_format"
    NULL = "null"
    EMPTY = "empty"
    INJECTION = "injection"
    RANDOM = "random"


class FieldType(Enum):
    """Supported field types."""
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    ENUM = "enum"
    DATE = "date"
    DATETIME = "datetime"
    EMAIL = "email"
    URL = "url"
    UUID = "uuid"


# ================================================================================
# Schema Models
# ================================================================================

@dataclass
class FieldSchema:
    """
    Represents a field's schema definition.
    
    Attributes:
        name: Field name
        field_type: Type of the field
        required: Whether field is required
        min_length: Minimum length (strings/arrays)
        max_length: Maximum length (strings/arrays)
        minimum: Minimum value (numbers)
        maximum: Maximum value (numbers)
        pattern: Regex pattern for validation
        enum_values: Allowed values for enum fields
        format: Format hint (email, date, etc.)
        description: Field description
    """
    name: str
    field_type: FieldType
    required: bool = True
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    pattern: Optional[str] = None
    enum_values: List[Any] = field(default_factory=list)
    format: Optional[str] = None
    description: Optional[str] = None
    default: Optional[Any] = None
    
    @classmethod
    def from_openapi(cls, name: str, schema: Dict[str, Any], required: bool = True) -> "FieldSchema":
        """
        Create FieldSchema from OpenAPI schema definition.
        
        Args:
            name: Field name
            schema: OpenAPI schema dict
            required: Whether field is required
            
        Returns:
            FieldSchema instance
        """
        field_type = cls._parse_type(schema)
        
        return cls(
            name=name,
            field_type=field_type,
            required=required,
            min_length=schema.get("minLength"),
            max_length=schema.get("maxLength"),
            minimum=schema.get("minimum"),
            maximum=schema.get("maximum"),
            pattern=schema.get("pattern"),
            enum_values=schema.get("enum", []),
            format=schema.get("format"),
            description=schema.get("description"),
            default=schema.get("default"),
        )
    
    @staticmethod
    def _parse_type(schema: Dict[str, Any]) -> FieldType:
        """Parse OpenAPI type to FieldType."""
        type_str = schema.get("type", "string")
        format_str = schema.get("format", "")
        
        # Check format first
        if format_str == "email":
            return FieldType.EMAIL
        elif format_str == "uri" or format_str == "url":
            return FieldType.URL
        elif format_str == "uuid":
            return FieldType.UUID
        elif format_str == "date":
            return FieldType.DATE
        elif format_str == "date-time":
            return FieldType.DATETIME
        
        # Check enum
        if "enum" in schema:
            return FieldType.ENUM
        
        # Map type
        type_map = {
            "string": FieldType.STRING,
            "integer": FieldType.INTEGER,
            "number": FieldType.NUMBER,
            "boolean": FieldType.BOOLEAN,
            "array": FieldType.ARRAY,
            "object": FieldType.OBJECT,
        }
        
        return type_map.get(type_str, FieldType.STRING)


@dataclass
class EndpointSchema:
    """
    Represents an API endpoint's schema.
    
    Attributes:
        path: API path (e.g., "/api/v1/users")
        method: HTTP method
        request_fields: List of request field schemas
        response_fields: List of response field schemas
        description: Endpoint description
    """
    path: str
    method: str
    request_fields: List[FieldSchema] = field(default_factory=list)
    response_fields: List[FieldSchema] = field(default_factory=list)
    description: Optional[str] = None
    
    @classmethod
    def from_openapi(cls, path: str, method: str, spec: Dict[str, Any]) -> "EndpointSchema":
        """
        Create EndpointSchema from OpenAPI specification.
        
        Args:
            path: API path
            method: HTTP method
            spec: OpenAPI operation spec
            
        Returns:
            EndpointSchema instance
        """
        request_fields = []
        
        # Parse request body
        request_body = spec.get("requestBody", {})
        content = request_body.get("content", {})
        json_content = content.get("application/json", {})
        schema = json_content.get("schema", {})
        
        if schema.get("type") == "object":
            required_fields = schema.get("required", [])
            properties = schema.get("properties", {})
            
            for name, prop_schema in properties.items():
                is_required = name in required_fields
                field = FieldSchema.from_openapi(name, prop_schema, is_required)
                request_fields.append(field)
        
        return cls(
            path=path,
            method=method.upper(),
            request_fields=request_fields,
            description=spec.get("description") or spec.get("summary"),
        )


# ================================================================================
# Data Generators
# ================================================================================

class BaseGenerator:
    """Base class for data generators."""
    
    def generate(self, field: FieldSchema, generation_type: DataGenerationType) -> Any:
        """
        Generate data for a field.
        
        Args:
            field: Field schema
            generation_type: Type of generation
            
        Returns:
            Generated value
        """
        raise NotImplementedError


class StringGenerator(BaseGenerator):
    """Generator for string fields."""
    
    INJECTION_PAYLOADS = [
        "'; DROP TABLE users; --",
        "<script>alert('XSS')</script>",
        "${7*7}",
        "{{constructor.constructor('return this')()}}",
        "../../../etc/passwd",
        "| cat /etc/passwd",
    ]
    
    def generate(self, field: FieldSchema, generation_type: DataGenerationType) -> Any:
        """Generate string data."""
        if generation_type == DataGenerationType.VALID:
            return self._generate_valid(field)
        elif generation_type == DataGenerationType.BOUNDARY_MIN:
            return self._generate_min_length(field)
        elif generation_type == DataGenerationType.BOUNDARY_MAX:
            return self._generate_max_length(field)
        elif generation_type == DataGenerationType.INVALID_TYPE:
            return random.randint(1, 100)  # Return number instead of string
        elif generation_type == DataGenerationType.NULL:
            return None
        elif generation_type == DataGenerationType.EMPTY:
            return ""
        elif generation_type == DataGenerationType.INJECTION:
            return random.choice(self.INJECTION_PAYLOADS)
        else:
            return self._generate_random()
    
    def _generate_valid(self, field: FieldSchema) -> str:
        """Generate valid string."""
        if field.enum_values:
            return random.choice(field.enum_values)
        
        length = 10
        if field.min_length and field.max_length:
            length = (field.min_length + field.max_length) // 2
        elif field.min_length:
            length = field.min_length + 5
        elif field.max_length:
            length = min(field.max_length, 20)
        
        return "".join(random.choices(string.ascii_letters + string.digits, k=length))
    
    def _generate_min_length(self, field: FieldSchema) -> str:
        """Generate minimum length string."""
        length = field.min_length or 1
        return "".join(random.choices(string.ascii_letters, k=length))
    
    def _generate_max_length(self, field: FieldSchema) -> str:
        """Generate maximum length string."""
        length = field.max_length or 255
        return "".join(random.choices(string.ascii_letters, k=length))
    
    def _generate_random(self) -> str:
        """Generate random string."""
        length = random.randint(1, 50)
        return "".join(random.choices(string.ascii_letters + string.digits, k=length))


class NumberGenerator(BaseGenerator):
    """Generator for numeric fields."""
    
    def generate(self, field: FieldSchema, generation_type: DataGenerationType) -> Any:
        """Generate numeric data."""
        is_integer = field.field_type == FieldType.INTEGER
        
        if generation_type == DataGenerationType.VALID:
            return self._generate_valid(field, is_integer)
        elif generation_type == DataGenerationType.BOUNDARY_MIN:
            return self._generate_min_value(field, is_integer)
        elif generation_type == DataGenerationType.BOUNDARY_MAX:
            return self._generate_max_value(field, is_integer)
        elif generation_type == DataGenerationType.INVALID_TYPE:
            return "not_a_number"
        elif generation_type == DataGenerationType.NULL:
            return None
        else:
            return self._generate_random(is_integer)
    
    def _generate_valid(self, field: FieldSchema, is_integer: bool) -> Any:
        """Generate valid number."""
        minimum = field.minimum or 0
        maximum = field.maximum or 100
        
        if is_integer:
            return random.randint(int(minimum), int(maximum))
        else:
            return round(random.uniform(minimum, maximum), 2)
    
    def _generate_min_value(self, field: FieldSchema, is_integer: bool) -> Any:
        """Generate minimum value."""
        return int(field.minimum) if is_integer else field.minimum
    
    def _generate_max_value(self, field: FieldSchema, is_integer: bool) -> Any:
        """Generate maximum value."""
        return int(field.maximum) if is_integer else field.maximum
    
    def _generate_random(self, is_integer: bool) -> Any:
        """Generate random number."""
        if is_integer:
            return random.randint(-1000, 1000)
        else:
            return round(random.uniform(-1000, 1000), 2)


class EmailGenerator(BaseGenerator):
    """Generator for email fields."""
    
    VALID_DOMAINS = ["example.com", "test.org", "demo.net", "sample.io"]
    INVALID_EMAILS = [
        "not_an_email",
        "@no_local_part.com",
        "no_domain@",
        "spaces in@email.com",
        "double@@at.com",
    ]
    
    def generate(self, field: FieldSchema, generation_type: DataGenerationType) -> Any:
        """Generate email data."""
        if generation_type == DataGenerationType.VALID:
            return self._generate_valid()
        elif generation_type == DataGenerationType.INVALID_FORMAT:
            return random.choice(self.INVALID_EMAILS)
        elif generation_type == DataGenerationType.NULL:
            return None
        elif generation_type == DataGenerationType.EMPTY:
            return ""
        else:
            return self._generate_valid()
    
    def _generate_valid(self) -> str:
        """Generate valid email."""
        local = "".join(random.choices(string.ascii_lowercase, k=8))
        domain = random.choice(self.VALID_DOMAINS)
        return f"{local}@{domain}"


class UUIDGenerator(BaseGenerator):
    """Generator for UUID fields."""
    
    def generate(self, field: FieldSchema, generation_type: DataGenerationType) -> Any:
        """Generate UUID data."""
        if generation_type == DataGenerationType.VALID:
            return str(uuid.uuid4())
        elif generation_type == DataGenerationType.INVALID_FORMAT:
            return "not-a-valid-uuid"
        elif generation_type == DataGenerationType.NULL:
            return None
        elif generation_type == DataGenerationType.EMPTY:
            return ""
        else:
            return str(uuid.uuid4())


class DateTimeGenerator(BaseGenerator):
    """Generator for date/datetime fields."""
    
    def generate(self, field: FieldSchema, generation_type: DataGenerationType) -> Any:
        """Generate date/datetime data."""
        is_date = field.field_type == FieldType.DATE
        
        if generation_type == DataGenerationType.VALID:
            return self._generate_valid(is_date)
        elif generation_type == DataGenerationType.INVALID_FORMAT:
            return "not-a-date"
        elif generation_type == DataGenerationType.NULL:
            return None
        elif generation_type == DataGenerationType.EMPTY:
            return ""
        elif generation_type == DataGenerationType.BOUNDARY_MIN:
            return "1970-01-01" if is_date else "1970-01-01T00:00:00Z"
        elif generation_type == DataGenerationType.BOUNDARY_MAX:
            return "2099-12-31" if is_date else "2099-12-31T23:59:59Z"
        else:
            return self._generate_valid(is_date)
    
    def _generate_valid(self, is_date: bool) -> str:
        """Generate valid date/datetime."""
        days_offset = random.randint(-365, 365)
        dt = datetime.now() + timedelta(days=days_offset)
        
        if is_date:
            return dt.strftime("%Y-%m-%d")
        else:
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class BooleanGenerator(BaseGenerator):
    """Generator for boolean fields."""
    
    def generate(self, field: FieldSchema, generation_type: DataGenerationType) -> Any:
        """Generate boolean data."""
        if generation_type == DataGenerationType.VALID:
            return random.choice([True, False])
        elif generation_type == DataGenerationType.INVALID_TYPE:
            return "not_a_boolean"
        elif generation_type == DataGenerationType.NULL:
            return None
        else:
            return random.choice([True, False])


class ArrayGenerator(BaseGenerator):
    """Generator for array fields."""
    
    def __init__(self, item_generator: BaseGenerator):
        """
        Initialize array generator.
        
        Args:
            item_generator: Generator for array items
        """
        self.item_generator = item_generator
    
    def generate(self, field: FieldSchema, generation_type: DataGenerationType) -> Any:
        """Generate array data."""
        if generation_type == DataGenerationType.VALID:
            return self._generate_valid(field)
        elif generation_type == DataGenerationType.BOUNDARY_MIN:
            min_items = field.min_length or 1
            return [self._generate_item(field) for _ in range(min_items)]
        elif generation_type == DataGenerationType.BOUNDARY_MAX:
            max_items = field.max_length or 10
            return [self._generate_item(field) for _ in range(max_items)]
        elif generation_type == DataGenerationType.INVALID_TYPE:
            return "not_an_array"
        elif generation_type == DataGenerationType.NULL:
            return None
        elif generation_type == DataGenerationType.EMPTY:
            return []
        else:
            return self._generate_valid(field)
    
    def _generate_valid(self, field: FieldSchema) -> List[Any]:
        """Generate valid array."""
        min_items = field.min_length or 1
        max_items = field.max_length or 5
        count = random.randint(min_items, max_items)
        return [self._generate_item(field) for _ in range(count)]
    
    def _generate_item(self, field: FieldSchema) -> Any:
        """Generate single array item."""
        # Create a simple string item by default
        return "".join(random.choices(string.ascii_letters, k=5))


# ================================================================================
# Main Data Generator
# ================================================================================

class APIDataGenerator:
    """
    Main class for generating API test data.
    
    Coordinates field-specific generators to create complete request payloads.
    """
    
    def __init__(self):
        """Initialize generators."""
        self.generators: Dict[FieldType, BaseGenerator] = {
            FieldType.STRING: StringGenerator(),
            FieldType.INTEGER: NumberGenerator(),
            FieldType.NUMBER: NumberGenerator(),
            FieldType.BOOLEAN: BooleanGenerator(),
            FieldType.EMAIL: EmailGenerator(),
            FieldType.UUID: UUIDGenerator(),
            FieldType.DATE: DateTimeGenerator(),
            FieldType.DATETIME: DateTimeGenerator(),
            FieldType.ARRAY: ArrayGenerator(StringGenerator()),
            FieldType.ENUM: StringGenerator(),  # Uses enum values from field
        }
    
    def generate_request(
        self,
        endpoint: EndpointSchema,
        generation_type: DataGenerationType = DataGenerationType.VALID,
        target_field: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a complete request payload.
        
        Args:
            endpoint: Endpoint schema
            generation_type: Type of data to generate
            target_field: If specified, only this field uses generation_type,
                         others use VALID
                         
        Returns:
            Request payload dict
        """
        payload = {}
        
        for field in endpoint.request_fields:
            if target_field and field.name != target_field:
                # Use valid data for non-target fields
                value = self._generate_field_value(field, DataGenerationType.VALID)
            else:
                value = self._generate_field_value(field, generation_type)
            
            # Skip None for required fields in VALID generation
            if value is None and field.required and generation_type == DataGenerationType.VALID:
                value = self._generate_field_value(field, DataGenerationType.VALID)
            
            payload[field.name] = value
        
        return payload
    
    def generate_mutation_cases(
        self, 
        endpoint: EndpointSchema
    ) -> List[Tuple[str, Dict[str, Any], str]]:
        """
        Generate mutation test cases for an endpoint.
        
        Args:
            endpoint: Endpoint schema
            
        Returns:
            List of (case_name, payload, expected_behavior) tuples
        """
        cases = []
        
        for field in endpoint.request_fields:
            # Missing required field
            if field.required:
                payload = self.generate_request(endpoint)
                del payload[field.name]
                cases.append((
                    f"missing_required_{field.name}",
                    payload,
                    "should_fail_400"
                ))
            
            # Invalid type
            payload = self.generate_request(
                endpoint,
                DataGenerationType.INVALID_TYPE,
                field.name
            )
            cases.append((
                f"invalid_type_{field.name}",
                payload,
                "should_fail_400"
            ))
            
            # Null value
            if field.required:
                payload = self.generate_request(
                    endpoint,
                    DataGenerationType.NULL,
                    field.name
                )
                cases.append((
                    f"null_required_{field.name}",
                    payload,
                    "should_fail_400"
                ))
            
            # Empty string for non-optional strings
            if field.field_type == FieldType.STRING and field.required:
                payload = self.generate_request(
                    endpoint,
                    DataGenerationType.EMPTY,
                    field.name
                )
                cases.append((
                    f"empty_string_{field.name}",
                    payload,
                    "should_fail_400"
                ))
            
            # Injection payloads
            if field.field_type == FieldType.STRING:
                payload = self.generate_request(
                    endpoint,
                    DataGenerationType.INJECTION,
                    field.name
                )
                cases.append((
                    f"injection_{field.name}",
                    payload,
                    "should_sanitize_or_reject"
                ))
        
        return cases
    
    def _generate_field_value(
        self, 
        field: FieldSchema, 
        generation_type: DataGenerationType
    ) -> Any:
        """Generate value for a single field."""
        generator = self.generators.get(field.field_type, StringGenerator())
        return generator.generate(field, generation_type)


# ================================================================================
# Convenience Functions
# ================================================================================

def generate_valid_payload(
    path: str,
    method: str,
    openapi_spec: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Quick helper to generate valid payload from OpenAPI spec.
    
    Args:
        path: API path
        method: HTTP method
        openapi_spec: OpenAPI specification dict
        
    Returns:
        Valid request payload
    """
    # Find the operation
    paths = openapi_spec.get("paths", {})
    path_item = paths.get(path, {})
    operation = path_item.get(method.lower(), {})
    
    if not operation:
        logger.warning(f"Operation not found: {method} {path}")
        return {}
    
    endpoint = EndpointSchema.from_openapi(path, method, operation)
    generator = APIDataGenerator()
    
    return generator.generate_request(endpoint, DataGenerationType.VALID)


def generate_mutation_tests(
    path: str,
    method: str,
    openapi_spec: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Generate mutation test cases from OpenAPI spec.
    
    Args:
        path: API path
        method: HTTP method
        openapi_spec: OpenAPI specification dict
        
    Returns:
        List of mutation test case dicts
    """
    paths = openapi_spec.get("paths", {})
    path_item = paths.get(path, {})
    operation = path_item.get(method.lower(), {})
    
    if not operation:
        logger.warning(f"Operation not found: {method} {path}")
        return []
    
    endpoint = EndpointSchema.from_openapi(path, method, operation)
    generator = APIDataGenerator()
    
    mutations = generator.generate_mutation_cases(endpoint)
    
    return [
        {
            "name": name,
            "payload": payload,
            "expected": expected,
        }
        for name, payload, expected in mutations
    ]

