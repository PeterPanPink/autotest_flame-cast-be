"""
================================================================================
Token Manager with Auto-Refresh and Caching
================================================================================

Manages API authentication tokens with:
    - Automatic token refresh before expiration
    - Cross-process token caching using filelock
    - Support for multiple authentication schemes
    - Thread-safe singleton pattern

Author: Automation Team
License: MIT
================================================================================
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

from loguru import logger
try:
    from filelock import FileLock  # type: ignore
except Exception:  # pragma: no cover
    FileLock = None  # type: ignore
    logger.warning(
        "filelock is not installed. Token cache will run without cross-process locking "
        "(safe for demo; install requirements.txt for full behavior)."
    )


# Token cache configuration
TOKEN_CACHE_DIR = Path(__file__).parent.parent.parent / ".token_cache"
TOKEN_CACHE_FILE = TOKEN_CACHE_DIR / "cache.json"
TOKEN_LOCK_FILE = TOKEN_CACHE_DIR / "cache.lock"

# Default token TTL (1 hour in seconds)
DEFAULT_TOKEN_TTL = 3600

# Refresh token when less than this many seconds remain
TOKEN_REFRESH_BUFFER = 300  # 5 minutes


class TokenError(Exception):
    """Raised when token operations fail."""
    pass


class TokenManager:
    """
    Token manager with automatic refresh and cross-process caching.
    
    Features:
        - Automatic token acquisition and refresh
        - Cross-process token sharing using file-based cache
        - Thread-safe singleton pattern
        - Multiple authentication header support
    
    Authentication Headers Applied:
        - Authorization: Bearer {token}
        - x-api-key: {api_key}
        - x-app-auth: {json_encoded_auth}
    
    Usage:
        >>> token_manager = TokenManager.instance(config)
        >>> headers = token_manager.apply({})
        >>> # headers now contains all authentication headers
    """

    _instance: Optional["TokenManager"] = None
    _lock = None

    def __new__(cls, config=None) -> "TokenManager":
        """Singleton pattern - return existing instance if available."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, config=None) -> None:
        """
        Initialize token manager.
        
        Args:
            config: ConfigLoader instance for configuration access
        """
        if getattr(self, "_initialized", False):
            return
        
        self.config = config
        self._token: Optional[str] = None
        self._user: Optional[str] = None
        self._expires_at: float = 0
        
        # Ensure cache directory exists
        TOKEN_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        
        self._initialized = True

    @classmethod
    def instance(cls, config=None) -> "TokenManager":
        """
        Get singleton instance of TokenManager.
        
        Args:
            config: ConfigLoader instance (required on first call)
        
        Returns:
            TokenManager singleton instance
        """
        if cls._instance is None:
            cls._instance = cls(config)
        return cls._instance

    def apply(self, headers: Dict[str, str]) -> Dict[str, str]:
        """
        Apply authentication headers to request.
        
        Automatically refreshes token if expired or about to expire.
        
        Args:
            headers: Existing headers dictionary
        
        Returns:
            Headers with authentication added
        """
        self._ensure_valid_token()
        
        # Apply authentication headers
        result = dict(headers)
        
        # API Key header
        api_key = self._get_api_key()
        if api_key:
            result["x-api-key"] = api_key
        
        # Bearer token
        if self._token:
            result["Authorization"] = f"Bearer {self._token}"
            
            # App auth header (JSON encoded)
            if self._user:
                result["x-app-auth"] = json.dumps({
                    "token": self._token,
                    "user": self._user
                })
        
        return result

    def _ensure_valid_token(self) -> None:
        """
        Ensure token is valid, refreshing if necessary.
        
        Checks:
            1. In-memory token validity
            2. Cached token from file (cross-process sharing)
            3. Fetches new token if neither is valid
        """
        current_time = time.time()
        
        # Check if current token is still valid
        if self._token and self._expires_at > current_time + TOKEN_REFRESH_BUFFER:
            return
        
        # Try loading from cache (other process may have refreshed)
        cached = self._load_cached_token()
        if cached and cached["expires_at"] > current_time + TOKEN_REFRESH_BUFFER:
            self._token = cached["token"]
            self._user = cached.get("user")
            self._expires_at = cached["expires_at"]
            return
        
        # Fetch new token
        self._fetch_token()

    def _fetch_token(self) -> None:
        """
        Fetch new authentication token from API.
        
        This method acquires a file lock to prevent multiple processes
        from fetching tokens simultaneously.
        """
        from contextlib import nullcontext

        lock_ctx = FileLock(TOKEN_LOCK_FILE) if FileLock is not None else nullcontext()
        with lock_ctx:
            # Double-check cache after acquiring lock
            cached = self._load_cached_token()
            if cached and cached["expires_at"] > time.time() + TOKEN_REFRESH_BUFFER:
                self._token = cached["token"]
                self._user = cached.get("user")
                self._expires_at = cached["expires_at"]
                return
            
            # Fetch new token from API
            token_data = self._request_new_token()
            
            self._token = token_data["token"]
            self._user = token_data.get("user")
            
            # Calculate expiration
            ttl = token_data.get("ttl", DEFAULT_TOKEN_TTL)
            self._expires_at = time.time() + ttl
            
            # Save to cache
            self._save_token_to_cache()
            
            logger.info("Token refreshed and cached")

    def _request_new_token(self) -> Dict[str, Any]:
        """
        Request new token from authentication API.
        
        Returns:
            Dictionary with token, user, and optional ttl
        """
        import httpx
        
        base_url = self.config.get("api.base_url") if self.config else ""
        auth_endpoint = "/api/v1/auth/token"  # Example endpoint
        
        # Get authentication parameters
        auth_params = {
            "user_id": self.config.get("auth.user_id", "demo_user"),
            "username": self.config.get("auth.username", "demo_user"),
            "ttl": self.config.get("auth.ttl", DEFAULT_TOKEN_TTL),
        }
        
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(
                    f"{base_url}{auth_endpoint}",
                    params=auth_params
                )
                response.raise_for_status()
                
                result = response.json()
                return result.get("result", result)
                
        except httpx.HTTPError as e:
            raise TokenError(f"Failed to fetch token: {e}") from e

    def _load_cached_token(self) -> Optional[Dict[str, Any]]:
        """Load token from file cache."""
        try:
            if TOKEN_CACHE_FILE.exists():
                with open(TOKEN_CACHE_FILE, "r") as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
        return None

    def _save_token_to_cache(self) -> None:
        """Save current token to file cache."""
        cache_data = {
            "token": self._token,
            "user": self._user,
            "expires_at": self._expires_at,
        }
        
        try:
            with open(TOKEN_CACHE_FILE, "w") as f:
                json.dump(cache_data, f)
        except IOError as e:
            logger.warning(f"Failed to cache token: {e}")

    def _get_api_key(self) -> Optional[str]:
        """Get API key from configuration."""
        if self.config:
            return self.config.get("security.api_key")
        return None

    def invalidate(self) -> None:
        """
        Invalidate current token.
        
        Forces next request to fetch a new token.
        """
        self._token = None
        self._user = None
        self._expires_at = 0
        
        # Remove cached token
        if TOKEN_CACHE_FILE.exists():
            TOKEN_CACHE_FILE.unlink()

    @classmethod
    def reset(cls) -> None:
        """Reset singleton instance (for testing)."""
        if cls._instance:
            cls._instance.invalidate()
        cls._instance = None


__all__ = [
    "TokenManager",
    "TokenError",
]

