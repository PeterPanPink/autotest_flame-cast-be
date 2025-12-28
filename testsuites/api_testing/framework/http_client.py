"""
================================================================================
Enterprise HTTP Client with Allure Integration
================================================================================

A production-ready HTTP client featuring:
    - Automatic retry with exponential backoff
    - Rate limit (429) handling with Retry-After parsing
    - Comprehensive Allure reporting with cURL command generation
    - Token management and auto-refresh
    - Network error resilience

Author: Automation Team
License: MIT
================================================================================
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, Optional

import allure
import httpx
from allure_commons.types import AttachmentType
from loguru import logger

from .config_loader import ConfigLoader
from .token_manager import TokenManager


# Maximum response length to include in Allure reports
MAX_RESPONSE_LENGTH = 3000

# Default retry settings
DEFAULT_RETRY_COUNT = 3
DEFAULT_RETRY_BACKOFF = 0.5
DEFAULT_RETRY_MAX_WAIT = 5.0


class HttpClientError(Exception):
    """Base exception for HTTP client errors."""
    pass


class RateLimitExceeded(HttpClientError):
    """Raised when rate limit is exceeded and all retries are exhausted."""
    pass


class HttpClient:
    """
    Enterprise HTTP client with built-in resilience and reporting.
    
    Features:
        - Automatic retry with exponential backoff for transient failures
        - Smart rate limit (429) handling with Retry-After header parsing
        - Full Allure reporting with request/response details
        - cURL command generation for easy reproduction
        - Token management and authentication handling
    
    Usage:
        >>> config = ConfigLoader()
        >>> with HttpClient(config) as client:
        ...     response = client.request("GET", "/api/v1/users")
        ...     print(response.json())
    """

    def __init__(self, config: Optional[ConfigLoader] = None) -> None:
        """
        Initialize HTTP client with configuration.
        
        Args:
            config: Configuration loader instance. Creates new one if None.
        """
        if config is None:
            config = ConfigLoader()

        self.config = config
        self.base_url = config.get("api.base_url", "http://localhost:8000")
        self.timeout = int(config.get("api.timeout", 30))
        self.retry_count = int(config.get("api.retry_count", DEFAULT_RETRY_COUNT))
        self.retry_backoff = float(config.get("api.retry_backoff", DEFAULT_RETRY_BACKOFF))
        self.retry_max_wait = float(config.get("api.retry_max_wait", DEFAULT_RETRY_MAX_WAIT))
        
        self.session: Optional[httpx.Client] = None
        self.token_manager = TokenManager.instance(config)

    def __enter__(self) -> "HttpClient":
        """Enter context manager - initialize HTTP session."""
        self.session = httpx.Client(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout),
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager - close HTTP session."""
        if self.session:
            self.session.close()
            self.session = None

    def request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """
        Execute HTTP request with automatic retry and Allure logging.
        
        All requests are automatically:
            - Retried on network errors with exponential backoff
            - Retried on 429 with Retry-After header parsing
            - Logged to Allure with full request/response details
            - Authenticated using TokenManager
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE, PATCH)
            url: Request URL (relative to base_url)
            **kwargs: Additional arguments passed to httpx.request
        
        Returns:
            httpx.Response object
        
        Raises:
            RateLimitExceeded: When rate limit retries are exhausted
            httpx.HTTPError: When network retries are exhausted
        """
        if self.session is None:
            raise HttpClientError(
                "HttpClient must be used within a context manager. "
                "Use 'with HttpClient() as client:'"
            )

        # Apply authentication headers
        headers = kwargs.pop("headers", {})
        headers = self.token_manager.apply(headers)
        kwargs["headers"] = headers

        last_exception: Optional[Exception] = None
        
        for attempt in range(self.retry_count):
            try:
                response = self.session.request(method, url, **kwargs)
                
                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = self._parse_retry_after(response)
                    logger.warning(
                        f"Rate limited (429). Waiting {retry_after}s before retry. "
                        f"Attempt {attempt + 1}/{self.retry_count}"
                    )
                    time.sleep(retry_after)
                    continue
                
                # Log successful request to Allure
                self._log_to_allure(method, url, kwargs, response)
                return response

            except (httpx.TimeoutException, httpx.NetworkError) as e:
                last_exception = e
                if attempt < self.retry_count - 1:
                    wait_time = self._calculate_backoff(attempt)
                    logger.warning(
                        f"Network error: {e}. Retrying in {wait_time}s. "
                        f"Attempt {attempt + 1}/{self.retry_count}"
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"All retries exhausted. Last error: {e}")
                    raise

        # If we get here, rate limit retries were exhausted
        raise RateLimitExceeded(
            f"Rate limit exceeded after {self.retry_count} retries"
        )

    def get(self, url: str, **kwargs: Any) -> httpx.Response:
        """Execute GET request."""
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> httpx.Response:
        """Execute POST request."""
        return self.request("POST", url, **kwargs)

    def put(self, url: str, **kwargs: Any) -> httpx.Response:
        """Execute PUT request."""
        return self.request("PUT", url, **kwargs)

    def patch(self, url: str, **kwargs: Any) -> httpx.Response:
        """Execute PATCH request."""
        return self.request("PATCH", url, **kwargs)

    def delete(self, url: str, **kwargs: Any) -> httpx.Response:
        """Execute DELETE request."""
        return self.request("DELETE", url, **kwargs)

    def _parse_retry_after(self, response: httpx.Response) -> float:
        """
        Parse Retry-After header from 429 response.
        
        Supports both:
            - Seconds: "60"
            - HTTP date: "Wed, 21 Oct 2024 07:28:00 GMT"
        
        Returns:
            Wait time in seconds (capped at retry_max_wait)
        """
        retry_after = response.headers.get("Retry-After", "")
        
        try:
            # Try parsing as seconds
            wait_time = float(retry_after)
        except ValueError:
            # Default if header is missing or invalid
            wait_time = self.retry_backoff
        
        # Cap at maximum wait time
        return min(wait_time, self.retry_max_wait)

    def _calculate_backoff(self, attempt: int) -> float:
        """
        Calculate exponential backoff wait time.
        
        Formula: base * (2 ^ attempt), capped at max_wait
        """
        wait_time = self.retry_backoff * (2 ** attempt)
        return min(wait_time, self.retry_max_wait)

    def _log_to_allure(
        self,
        method: str,
        url: str,
        kwargs: Dict[str, Any],
        response: httpx.Response,
    ) -> None:
        """
        Log HTTP request/response to Allure report.
        
        Attaches:
            - Request URL with query parameters
            - Request headers
            - Request body (if present)
            - cURL command for reproduction
            - Response status
            - Response body (truncated if too long)
        """
        # Build full URL with query parameters
        full_url = f"{self.base_url.rstrip('/')}/{url.lstrip('/')}"
        params = kwargs.get("params")
        if params:
            query_string = "&".join(
                f"{k}={v}" for k, v in params.items() if v is not None
            )
            if query_string:
                full_url = f"{full_url}?{query_string}"

        # Determine status emoji
        status_emoji = "✅" if response.status_code < 400 else "❌"
        step_title = f"{status_emoji} {method} {url} → {response.status_code}"

        with allure.step(step_title):
            # 1. Request URL
            allure.attach(
                full_url,
                name="🔗 Request URL",
                attachment_type=AttachmentType.TEXT
            )

            # 2. Request Headers
            headers = kwargs.get("headers", {})
            safe_headers = self._redact_headers(headers)
            if safe_headers:
                allure.attach(
                    json.dumps(safe_headers, ensure_ascii=False, indent=2),
                    name="📤 Request Headers",
                    attachment_type=AttachmentType.JSON
                )

            # 3. Request Body
            body = kwargs.get("json")
            safe_body = self._redact_body(body)
            if safe_body:
                allure.attach(
                    json.dumps(safe_body, ensure_ascii=False, indent=2),
                    name="📤 Request Body",
                    attachment_type=AttachmentType.JSON
                )

            # 4. Query Parameters
            if params:
                allure.attach(
                    json.dumps(params, ensure_ascii=False, indent=2),
                    name="📤 Query Params",
                    attachment_type=AttachmentType.JSON
                )

            # 5. cURL Command
            curl_cmd = self._build_curl(method, full_url, safe_headers, safe_body)
            allure.attach(
                curl_cmd,
                name="🔧 cURL Command",
                attachment_type=AttachmentType.TEXT
            )

            # 6. Response Status
            allure.attach(
                f"{status_emoji} {response.status_code}",
                name="📥 Response Status",
                attachment_type=AttachmentType.TEXT
            )

            # 7. Response Body (with truncation)
            try:
                response_body = response.json()
                response_content = json.dumps(
                    response_body, ensure_ascii=False, indent=2
                )
            except (json.JSONDecodeError, ValueError):
                response_content = response.text or "<empty>"

            # Truncate long responses
            if len(response_content) > MAX_RESPONSE_LENGTH:
                response_content = (
                    f"{response_content[:MAX_RESPONSE_LENGTH]}\n\n"
                    f"... [Truncated, full length: {len(response_content)} chars] ..."
                )

            allure.attach(
                response_content,
                name="📥 Response Body",
                attachment_type=AttachmentType.JSON
            )

    def _redact_headers(self, headers: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mask sensitive header values before logging.
        """
        sensitive_keys = {"authorization", "x-api-key", "x-app-auth", "cookie", "set-cookie"}
        masked = {}
        for key, value in headers.items():
            if key.lower() in sensitive_keys:
                masked[key] = "***MASKED***"
            else:
                masked[key] = value
        return masked

    def _redact_body(self, payload: Any) -> Any:
        """
        Recursively mask sensitive fields in request bodies.
        """
        if isinstance(payload, dict):
            redacted = {}
            for key, value in payload.items():
                if any(token in key.lower() for token in [
                    "password", "secret", "token", "api_key", "authorization", "session"
                ]):
                    redacted[key] = "***MASKED***"
                else:
                    redacted[key] = self._redact_body(value)
            return redacted
        if isinstance(payload, list):
            return [self._redact_body(item) for item in payload]
        return payload

    def _build_curl(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        body: Optional[Dict[str, Any]],
    ) -> str:
        """
        Build cURL command for request reproduction.
        
        Generates a copy-paste ready cURL command with:
            - HTTP method
            - Headers
            - JSON body (if present)
        """
        parts = [f"curl -X {method}"]
        
        # Add headers
        for key, value in headers.items():
            # Mask sensitive headers
            if key.lower() in ("authorization", "x-api-key"):
                value = value[:20] + "..." if len(value) > 20 else "***"
            parts.append(f"-H '{key}: {value}'")
        
        # Add body
        if body:
            body_json = json.dumps(body, ensure_ascii=False)
            parts.append(f"-d '{body_json}'")
        
        # Add URL
        parts.append(f"'{url}'")
        
        return " \\\n  ".join(parts)


__all__ = [
    "HttpClient",
    "HttpClientError",
    "RateLimitExceeded",
]

