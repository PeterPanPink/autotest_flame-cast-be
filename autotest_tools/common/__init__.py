"""
================================================================================
Autotest Tools Common Utilities
================================================================================

This module provides shared utilities, configuration management, and logging
setup for all autotest tools.

Exports:
    - GlobalConfig: Singleton configuration manager
    - get_config: Convenience function to get configuration values
    - init_logger: Function to initialize loguru logger with standard settings

Usage:
    from autotest_tools.common import get_config, init_logger
    
    init_logger()
    es_host = get_config("elasticsearch.url", "http://localhost:9200")

================================================================================
"""

import os
import sys
from typing import Any, Dict, Optional
import yaml
from loguru import logger

# ============================================================
# Configuration Management
# ============================================================

class GlobalConfig:
    """
    Singleton class to manage global configurations for autotest_tools.
    
    Loads settings from environment variables and YAML configuration files.
    Environment variables take precedence over file-based configuration.
    """
    _instance: Optional["GlobalConfig"] = None
    _config: Dict[str, Any] = {}
    _initialized: bool = False

    def __new__(cls) -> "GlobalConfig":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._load_configs()
        self._initialized = True

    def _load_configs(self) -> None:
        """
        Loads configurations from YAML files and environment variables.
        """
        # Look for config in multiple locations
        config_paths = [
            "config/tools_config.yaml",
            "autotest_tools/config/tools_config.yaml",
            os.path.join(os.path.dirname(__file__), "..", "config", "tools_config.yaml"),
        ]
        
        for config_path in config_paths:
            if os.path.exists(config_path):
                try:
                    with open(config_path, "r", encoding="utf-8") as f:
                        file_config = yaml.safe_load(f) or {}
                        self._config.update(file_config)
                    logger.debug(f"Loaded configuration from {config_path}")
                    break
                except Exception as e:
                    logger.warning(f"Failed to load config from {config_path}: {e}")
        
        # Override with environment variables
        env_mapping = {
            "ELASTICSEARCH_URL": "elasticsearch.url",
            "ELASTICSEARCH_USERNAME": "elasticsearch.username",
            "ELASTICSEARCH_PASSWORD": "elasticsearch.password",
            "NOTION_TOKEN": "notion.token",
            "MONGO_URI": "mongodb.uri",
            "LOG_LEVEL": "logging.level",
        }
        
        for env_key, config_key in env_mapping.items():
            if env_key in os.environ:
                self._set_nested(config_key, os.environ[env_key])

    def _set_nested(self, key: str, value: Any) -> None:
        """
        Sets a nested configuration value using dot notation.
        """
        keys = key.split(".")
        current = self._config
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        current[keys[-1]] = value

    def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieves a configuration value using dot notation.
        
        Args:
            key: Configuration key (e.g., "elasticsearch.url")
            default: Default value if key is not found
        
        Returns:
            Configuration value or default
        """
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def set(self, key: str, value: Any) -> None:
        """
        Sets a configuration value.
        
        Args:
            key: Configuration key (e.g., "elasticsearch.url")
            value: Value to set
        """
        self._set_nested(key, value)

    def get_all(self) -> Dict[str, Any]:
        """
        Returns the entire configuration dictionary.
        """
        return self._config.copy()


# Global config instance
_global_config: Optional[GlobalConfig] = None


def get_config(key: str, default: Any = None) -> Any:
    """
    Convenience function to get a configuration value.
    
    Args:
        key: Configuration key using dot notation
        default: Default value if not found
    
    Returns:
        Configuration value or default
    
    Example:
        es_host = get_config("elasticsearch.url", "http://localhost:9200")
    """
    global _global_config
    if _global_config is None:
        _global_config = GlobalConfig()
    return _global_config.get(key, default)


def set_config(key: str, value: Any) -> None:
    """
    Convenience function to set a configuration value.
    
    Args:
        key: Configuration key using dot notation
        value: Value to set
    """
    global _global_config
    if _global_config is None:
        _global_config = GlobalConfig()
    _global_config.set(key, value)


# ============================================================
# Logging Setup
# ============================================================

_logger_initialized = False


def init_logger(
    level: str = None,
    format_string: str = None,
    log_file: str = None
) -> None:
    """
    Initializes the loguru logger with standard settings.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR). Defaults to config value.
        format_string: Log format string. Uses default if not provided.
        log_file: Optional file path to write logs to.
    
    Example:
        init_logger()  # Use defaults
        init_logger(level="DEBUG", log_file="logs/tools.log")
    """
    global _logger_initialized
    
    if _logger_initialized:
        return
    
    # Remove default handler
    logger.remove()
    
    # Get settings from config or use defaults
    level = level or get_config("logging.level", "INFO")
    format_string = format_string or get_config(
        "logging.format",
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    
    # Add console handler
    logger.add(
        sys.stderr,
        format=format_string,
        level=level,
        colorize=True,
    )
    
    # Add file handler if specified
    log_file = log_file or get_config("logging.file")
    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        
        logger.add(
            log_file,
            format=format_string,
            level=level,
            rotation=get_config("logging.rotation", "10 MB"),
            retention=get_config("logging.retention", "7 days"),
        )
    
    _logger_initialized = True
    logger.debug("Logger initialized successfully")


# ============================================================
# Common Utilities
# ============================================================

def ensure_directory(path: str) -> str:
    """
    Ensures a directory exists, creating it if necessary.
    
    Args:
        path: Directory path
    
    Returns:
        The path (for chaining)
    """
    os.makedirs(path, exist_ok=True)
    return path


def safe_json_serialize(obj: Any) -> Any:
    """
    Safely serializes an object to JSON-compatible format.
    
    Handles common non-serializable types like datetime, bytes, etc.
    """
    from datetime import datetime, date
    import json
    
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")
    elif hasattr(obj, "__dict__"):
        return obj.__dict__
    else:
        return str(obj)


# Export public API
__all__ = [
    "GlobalConfig",
    "get_config",
    "set_config",
    "init_logger",
    "ensure_directory",
    "safe_json_serialize",
]
