# ================================================================================
# Wait Helpers Module
# ================================================================================
#
# This module provides utilities for implementing wait strategies in API testing.
# It includes exponential backoff, polling mechanisms, and status waiting utilities.
#
# Key Features:
#   - Exponential backoff with jitter
#   - Configurable polling intervals
#   - Status-based waiting
#   - Timeout management
#   - Allure integration for step reporting
#
# Usage:
#   wait_for_status(client, session_id, "LIVE", timeout=60)
#   result = wait_with_backoff(check_function, max_attempts=5)
#
# ================================================================================

import time
import random
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, Union
from dataclasses import dataclass, field

import allure
from loguru import logger


T = TypeVar('T')


@dataclass
class WaitConfig:
    """
    Configuration for wait operations.
    
    Attributes:
        initial_interval: Initial wait interval in seconds
        multiplier: Multiplier for exponential backoff
        max_interval: Maximum interval between attempts
        timeout: Total timeout in seconds
        jitter: Add random jitter to prevent thundering herd
    """
    initial_interval: float = 1.0
    multiplier: float = 2.0
    max_interval: float = 30.0
    timeout: float = 120.0
    jitter: bool = True


# Pre-configured wait strategies for common scenarios
WAIT_SCENARIOS: Dict[str, WaitConfig] = {
    # Default configuration
    "default": WaitConfig(),
    
    # Fast operations (internal API responses)
    "fast": WaitConfig(
        initial_interval=0.5,
        multiplier=1.5,
        max_interval=5.0,
        timeout=30.0
    ),
    
    # Room operations (LiveKit)
    "create_room": WaitConfig(
        initial_interval=1.0,
        multiplier=2.0,
        max_interval=10.0,
        timeout=30.0
    ),
    "delete_room": WaitConfig(
        initial_interval=1.0,
        multiplier=2.0,
        max_interval=10.0,
        timeout=30.0
    ),
    
    # Stream operations (Mux)
    "start_live_stream": WaitConfig(
        initial_interval=2.0,
        multiplier=1.5,
        max_interval=15.0,
        timeout=90.0
    ),
    "end_live_stream": WaitConfig(
        initial_interval=2.0,
        multiplier=1.5,
        max_interval=15.0,
        timeout=90.0
    ),
    
    # Status waits
    "wait_for_ready": WaitConfig(
        initial_interval=1.0,
        multiplier=2.0,
        max_interval=10.0,
        timeout=60.0
    ),
    "wait_for_publishing": WaitConfig(
        initial_interval=2.0,
        multiplier=1.5,
        max_interval=10.0,
        timeout=90.0
    ),
    "wait_for_live": WaitConfig(
        initial_interval=2.0,
        multiplier=1.5,
        max_interval=15.0,
        timeout=180.0
    ),
    "wait_for_stopped": WaitConfig(
        initial_interval=3.0,
        multiplier=1.5,
        max_interval=20.0,
        timeout=300.0
    ),
    
    # Async data waits
    "wait_for_webhook": WaitConfig(
        initial_interval=2.0,
        multiplier=1.5,
        max_interval=10.0,
        timeout=120.0
    ),
    "wait_for_vod": WaitConfig(
        initial_interval=5.0,
        multiplier=1.5,
        max_interval=30.0,
        timeout=300.0
    ),
}


class WaitTimeoutError(Exception):
    """Raised when a wait operation times out."""
    pass


def get_wait_config(scenario: str) -> WaitConfig:
    """
    Get wait configuration for a specific scenario.
    
    Args:
        scenario: Scenario name (e.g., "wait_for_live", "create_room")
        
    Returns:
        WaitConfig for the scenario, or default if not found
    """
    return WAIT_SCENARIOS.get(scenario, WAIT_SCENARIOS["default"])


def calculate_next_interval(
    current_interval: float,
    config: WaitConfig
) -> float:
    """
    Calculate the next wait interval with exponential backoff and jitter.
    
    Args:
        current_interval: Current interval in seconds
        config: Wait configuration
        
    Returns:
        Next interval in seconds
    """
    next_interval = min(
        current_interval * config.multiplier,
        config.max_interval
    )
    
    if config.jitter:
        # Add +/- 25% jitter
        jitter_factor = 0.75 + (random.random() * 0.5)
        next_interval = next_interval * jitter_factor
    
    return next_interval


@allure.step("Waiting with backoff: {description}")
def wait_with_backoff(
    check_fn: Callable[[], Tuple[bool, T]],
    scenario: str = "default",
    description: str = "Waiting for condition",
    config: WaitConfig = None
) -> T:
    """
    Wait for a condition with exponential backoff.
    
    Args:
        check_fn: Function that returns (success: bool, result: T)
        scenario: Predefined scenario name for configuration
        description: Human-readable description for logging
        config: Optional custom WaitConfig (overrides scenario)
        
    Returns:
        Result from check_fn when successful
        
    Raises:
        WaitTimeoutError: If timeout is reached without success
        
    Example:
        def check_status():
            response = client.get_session(session_id)
            status = response.json()["results"]["status"]
            return status == "LIVE", status
        
        final_status = wait_with_backoff(
            check_status,
            scenario="wait_for_live",
            description="Waiting for session to go LIVE"
        )
    """
    if config is None:
        config = get_wait_config(scenario)
    
    start_time = time.time()
    current_interval = config.initial_interval
    attempt = 0
    last_result = None
    last_error = None
    
    logger.info(
        f"Starting wait: {description} "
        f"(timeout={config.timeout}s, scenario={scenario})"
    )
    
    while True:
        elapsed = time.time() - start_time
        
        if elapsed >= config.timeout:
            error_msg = (
                f"Timeout after {elapsed:.1f}s waiting for: {description}. "
                f"Last result: {last_result}, Last error: {last_error}"
            )
            logger.error(error_msg)
            raise WaitTimeoutError(error_msg)
        
        attempt += 1
        
        try:
            success, result = check_fn()
            last_result = result
            
            if success:
                logger.info(
                    f"Wait successful after {attempt} attempts "
                    f"({elapsed:.1f}s): {description}"
                )
                return result
            
            logger.debug(
                f"Attempt {attempt}: condition not met. "
                f"Result: {result}. Waiting {current_interval:.1f}s..."
            )
            
        except Exception as e:
            last_error = str(e)
            logger.warning(
                f"Attempt {attempt} failed with error: {e}. "
                f"Waiting {current_interval:.1f}s..."
            )
        
        # Wait before next attempt
        time.sleep(current_interval)
        current_interval = calculate_next_interval(current_interval, config)


def wait_for_session_status(
    http_client,
    session_id: str,
    expected_statuses: List[str],
    scenario: str = "default",
    fail_statuses: List[str] = None
) -> str:
    """
    Wait for a session to reach one of the expected statuses.
    
    Args:
        http_client: HTTP client for making API requests
        session_id: Session ID to check
        expected_statuses: List of acceptable target statuses
        scenario: Wait scenario name
        fail_statuses: List of statuses that should cause immediate failure
        
    Returns:
        The final status when it matches expected
        
    Raises:
        WaitTimeoutError: If timeout is reached
        ValueError: If session reaches a fail status
    """
    fail_statuses = fail_statuses or ["ABORTED", "CANCELLED"]
    
    def check_status() -> Tuple[bool, str]:
        response = http_client.get(f"/api/v1/session/{session_id}")
        
        if response.status_code != 200:
            raise Exception(f"Failed to get session: {response.status_code}")
        
        status = response.json().get("results", {}).get("status", "UNKNOWN")
        
        if status in fail_statuses:
            raise ValueError(
                f"Session reached fail status: {status}. "
                f"Expected one of: {expected_statuses}"
            )
        
        return status in expected_statuses, status
    
    with allure.step(f"Waiting for session {session_id} to reach {expected_statuses}"):
        return wait_with_backoff(
            check_fn=check_status,
            scenario=scenario,
            description=f"Session {session_id} -> {expected_statuses}"
        )


def wait_for_field_not_null(
    http_client,
    url: str,
    field_path: str,
    scenario: str = "default"
) -> Any:
    """
    Wait for a specific field in an API response to become non-null.
    
    Args:
        http_client: HTTP client for making API requests
        url: API endpoint URL
        field_path: Dot-notation path to the field (e.g., "results.post_id")
        scenario: Wait scenario name
        
    Returns:
        The field value when it becomes non-null
    """
    def get_nested_value(data: dict, path: str) -> Any:
        current = data
        for key in path.split('.'):
            if current is None:
                return None
            current = current.get(key)
        return current
    
    def check_field() -> Tuple[bool, Any]:
        response = http_client.get(url)
        
        if response.status_code != 200:
            raise Exception(f"Failed to get resource: {response.status_code}")
        
        value = get_nested_value(response.json(), field_path)
        return value is not None, value
    
    with allure.step(f"Waiting for {field_path} to be non-null"):
        return wait_with_backoff(
            check_fn=check_field,
            scenario=scenario,
            description=f"Field {field_path} != null"
        )


def wait_for_resource_exists(
    http_client,
    url: str,
    scenario: str = "fast"
) -> dict:
    """
    Wait for a resource to exist (return 200).
    
    Args:
        http_client: HTTP client for making API requests
        url: API endpoint URL
        scenario: Wait scenario name
        
    Returns:
        The response JSON when resource exists
    """
    def check_exists() -> Tuple[bool, dict]:
        response = http_client.get(url)
        
        if response.status_code == 200:
            return True, response.json()
        elif response.status_code == 404:
            return False, None
        else:
            raise Exception(f"Unexpected status code: {response.status_code}")
    
    with allure.step(f"Waiting for resource to exist: {url}"):
        return wait_with_backoff(
            check_fn=check_exists,
            scenario=scenario,
            description=f"Resource exists: {url}"
        )


def wait_for_resource_deleted(
    http_client,
    url: str,
    scenario: str = "fast"
) -> bool:
    """
    Wait for a resource to be deleted (return 404).
    
    Args:
        http_client: HTTP client for making API requests
        url: API endpoint URL
        scenario: Wait scenario name
        
    Returns:
        True when resource is deleted
    """
    def check_deleted() -> Tuple[bool, bool]:
        response = http_client.get(url)
        return response.status_code == 404, response.status_code == 404
    
    with allure.step(f"Waiting for resource to be deleted: {url}"):
        return wait_with_backoff(
            check_fn=check_deleted,
            scenario=scenario,
            description=f"Resource deleted: {url}"
        )


class AsyncWaiter:
    """
    Async-compatible waiter for concurrent test scenarios.
    
    This class provides async versions of the wait functions for use
    with asyncio-based test frameworks.
    """
    
    def __init__(self, config: WaitConfig = None):
        """
        Initialize async waiter.
        
        Args:
            config: Default wait configuration
        """
        self.config = config or WaitConfig()
    
    async def wait(
        self,
        check_fn: Callable[[], Tuple[bool, T]],
        description: str = "Waiting for condition"
    ) -> T:
        """
        Async wait for a condition.
        
        Args:
            check_fn: Async or sync function that returns (success, result)
            description: Description for logging
            
        Returns:
            Result from check_fn when successful
        """
        import asyncio
        
        start_time = time.time()
        current_interval = self.config.initial_interval
        
        while True:
            elapsed = time.time() - start_time
            
            if elapsed >= self.config.timeout:
                raise WaitTimeoutError(
                    f"Timeout after {elapsed:.1f}s: {description}"
                )
            
            try:
                # Support both sync and async check functions
                if asyncio.iscoroutinefunction(check_fn):
                    success, result = await check_fn()
                else:
                    success, result = check_fn()
                
                if success:
                    return result
                    
            except Exception as e:
                logger.warning(f"Wait check failed: {e}")
            
            await asyncio.sleep(current_interval)
            current_interval = calculate_next_interval(
                current_interval, 
                self.config
            )
