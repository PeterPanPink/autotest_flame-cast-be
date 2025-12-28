"""
================================================================================
Configuration Loader
================================================================================

YAML-based configuration management with environment variable override support.

Features:
    - Hierarchical YAML configuration loading
    - Environment variable override (API_BASE_URL overrides api.base_url)
    - Dot notation path access
    - Default value support
    - Multiple environment support (dev, test, staging, prod)

Author: Automation Team
License: MIT
================================================================================
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from loguru import logger


# Default configuration file paths
DEFAULT_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "config.yaml"


class ConfigurationError(Exception):
    """Raised when configuration loading or access fails."""
    pass


class ConfigLoader:
    """
    Configuration loader with YAML and environment variable support.
    
    Configuration hierarchy (highest to lowest priority):
        1. Environment variables (API_BASE_URL)
        2. YAML configuration file
        3. Default values
    
    Usage:
        >>> config = ConfigLoader()
        >>> config.get("api.base_url", "http://localhost:8000")
        'https://api.example.com'  # From YAML or env var
        
        >>> config.get("api.timeout", 30)
        30  # Default value if not configured
    
    Environment Variable Mapping:
        - api.base_url -> API_BASE_URL
        - api.timeout -> API_TIMEOUT
        - security.api_key -> SECURITY_API_KEY
    """

    _instance: Optional["ConfigLoader"] = None
    _config: Dict[str, Any] = {}

    def __new__(cls, config_path: Optional[Path] = None) -> "ConfigLoader":
        """
        Singleton pattern - return existing instance if available.
        
        This ensures configuration is loaded only once per process,
        improving performance and ensuring consistency.
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, config_path: Optional[Path] = None) -> None:
        """
        Initialize configuration loader.
        
        Args:
            config_path: Path to YAML configuration file.
                        Uses DEFAULT_CONFIG_PATH if not specified.
        """
        if getattr(self, "_initialized", False):
            return
        
        self._config_path = config_path or DEFAULT_CONFIG_PATH
        self._load_config()
        self._initialized = True

    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        if not self._config_path.exists():
            logger.warning(
                f"Configuration file not found: {self._config_path}. "
                f"Using defaults and environment variables only."
            )
            self._config = {}
            return

        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f) or {}
            logger.debug(f"Loaded configuration from: {self._config_path}")
        except yaml.YAMLError as e:
            raise ConfigurationError(
                f"Invalid YAML in configuration file: {e}"
            ) from e

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-notation path.
        
        First checks environment variables, then YAML config, then default.
        
        Args:
            key: Dot-notation path (e.g., "api.base_url")
            default: Default value if key not found
        
        Returns:
            Configuration value or default
        
        Examples:
            >>> config.get("api.base_url")
            'https://api.example.com'
            
            >>> config.get("api.retry_count", 3)
            3
        """
        # Check environment variable first
        env_key = key.upper().replace(".", "_")
        env_value = os.environ.get(env_key)
        if env_value is not None:
            return self._convert_type(env_value, default)

        # Navigate YAML config by dot notation
        value = self._config
        for part in key.split("."):
            if isinstance(value, dict):
                value = value.get(part)
            else:
                value = None
            
            if value is None:
                return default

        return value

    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get entire configuration section.
        
        Args:
            section: Section name (e.g., "api", "security")
        
        Returns:
            Section dictionary or empty dict if not found
        """
        return self._config.get(section, {})

    def reload(self) -> None:
        """
        Reload configuration from file.
        
        Useful when configuration file has been updated during runtime.
        """
        self._load_config()
        logger.info(f"Configuration reloaded from: {self._config_path}")

    def _convert_type(self, value: str, reference: Any) -> Any:
        """
        Convert string value to match reference type.
        
        Used for environment variables which are always strings.
        """
        if reference is None:
            return value
        
        if isinstance(reference, bool):
            return value.lower() in ("true", "1", "yes", "on")
        if isinstance(reference, int):
            try:
                return int(value)
            except ValueError:
                return value
        if isinstance(reference, float):
            try:
                return float(value)
            except ValueError:
                return value
        
        return value

    @classmethod
    def reset(cls) -> None:
        """
        Reset singleton instance.
        
        Useful for testing when configuration needs to be reloaded
        with different settings.
        """
        cls._instance = None
        cls._config = {}


__all__ = [
    "ConfigLoader",
    "ConfigurationError",
]

