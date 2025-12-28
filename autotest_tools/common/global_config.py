"""
================================================================================
Global Configuration for Automation Tools
================================================================================

This module provides centralized configuration management for all automation
tools, including logging setup and configuration file loading.

Features:
    - Singleton pattern for global configuration
    - YAML-based configuration loading
    - Environment variable support
    - Centralized Loguru logging configuration

Author: Automation Team
License: MIT
================================================================================
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional
import yaml
from loguru import logger

# Global configuration storage
_config: Dict[str, Any] = {}
_logger_initialized: bool = False


def init_logger(level: str = None, format_str: str = None) -> None:
    """
    Initializes the global Loguru logger with consistent configuration.
    
    This function should be called at the start of any tool to ensure
    consistent logging across all automation tools.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR). Defaults to config value.
        format_str: Custom log format string. Defaults to config value.
    """
    global _logger_initialized
    
    if _logger_initialized:
        return
    
    # Load config first to get logging settings
    _ensure_config_loaded()
    
    # Get logging configuration with defaults
    log_level = level or get_config("logging.level", "INFO")
    log_format = format_str or get_config(
        "logging.format",
        "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}"
    )
    
    # Remove default logger and add configured one
    logger.remove()
    logger.add(
        sys.stderr,
        level=log_level.upper(),
        format=log_format,
        colorize=True,
        backtrace=True,
        diagnose=True,
    )
    
    # Optional: Add file logging
    log_file = get_config("logging.file", None)
    if log_file:
        log_dir = Path(log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        logger.add(
            log_file,
            level=log_level.upper(),
            format=log_format.replace("{level: <8}", "{level}"),  # Remove padding for file
            rotation=get_config("logging.rotation", "10 MB"),
            retention=get_config("logging.retention", "7 days"),
            compression="zip",
        )
    
    _logger_initialized = True
    logger.debug(f"Logger initialized with level: {log_level}")


def get_logger():
    """
    Returns the configured Loguru logger instance.
    
    Ensures the logger is initialized before returning.
    
    Returns:
        The Loguru logger instance.
    """
    if not _logger_initialized:
        init_logger()
    return logger


def _ensure_config_loaded() -> None:
    """
    Ensures the configuration is loaded.
    """
    global _config
    if not _config:
        _load_config()


def _load_config() -> None:
    """
    Loads configuration from YAML files and environment variables.
    
    Configuration loading order:
        1. Default configuration file (config/config.yaml)
        2. Environment-specific configuration (config/{ENV}.yaml)
        3. Environment variables (override YAML settings)
    """
    global _config
    
    # Determine config directory
    # Try multiple possible locations for flexibility
    possible_config_dirs = [
        Path("config"),
        Path(__file__).parent.parent.parent / "config",
        Path(__file__).parent.parent.parent / "testsuites" / "config",
    ]
    
    config_dir = None
    for dir_path in possible_config_dirs:
        if dir_path.exists():
            config_dir = dir_path
            break
    
    if not config_dir:
        logger.warning("No configuration directory found. Using defaults.")
        _config = _get_defaults()
        return
    
    # Load default config
    default_config_path = config_dir / "config.yaml"
    if default_config_path.exists():
        with open(default_config_path, "r", encoding="utf-8") as f:
            _config = yaml.safe_load(f) or {}
        logger.debug(f"Loaded configuration from {default_config_path}")
    else:
        _config = _get_defaults()
    
    # Load environment-specific config (optional)
    env = os.getenv("ENVIRONMENT", os.getenv("ENV", "dev"))
    env_config_path = config_dir / f"{env}.yaml"
    if env_config_path.exists():
        with open(env_config_path, "r", encoding="utf-8") as f:
            env_config = yaml.safe_load(f) or {}
        _config = _deep_merge(_config, env_config)
        logger.debug(f"Merged environment config: {env_config_path}")
    
    # Override with environment variables
    _apply_env_overrides()


def _get_defaults() -> Dict[str, Any]:
    """
    Returns default configuration values.
    """
    return {
        "logging": {
            "level": "INFO",
            "format": "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        },
        "api": {
            "base_url": "http://localhost:8000",
            "timeout": 30,
            "retry_count": 3,
        },
        "elasticsearch": {
            "url": "http://localhost:9200",
            "index_pattern": "logs-*",
            "timeout": 10,
        },
        "notion": {
            "version": "2022-06-28",
        },
    }


def _deep_merge(base: Dict, override: Dict) -> Dict:
    """
    Deep merges two dictionaries, with override taking precedence.
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _apply_env_overrides() -> None:
    """
    Applies environment variable overrides to the configuration.
    
    Environment variable naming convention:
        - Use double underscore to separate nested keys
        - Example: LOGGING__LEVEL=DEBUG overrides logging.level
    """
    global _config
    
    for key, value in os.environ.items():
        if "__" in key:
            # Convert LOGGING__LEVEL to ["logging", "level"]
            parts = [p.lower() for p in key.split("__")]
            _set_nested(_config, parts, value)


def _set_nested(d: Dict, keys: list, value: Any) -> None:
    """
    Sets a nested dictionary value using a list of keys.
    """
    for key in keys[:-1]:
        d = d.setdefault(key, {})
    d[keys[-1]] = value


def get_config(key: str, default: Any = None) -> Any:
    """
    Retrieves a configuration value using a dot-separated key path.
    
    Args:
        key: Dot-separated key path (e.g., "logging.level", "api.base_url").
        default: Default value to return if key is not found.
    
    Returns:
        The configuration value, or the default if not found.
    
    Examples:
        >>> get_config("logging.level", "INFO")
        "DEBUG"
        >>> get_config("api.timeout", 30)
        60
    """
    _ensure_config_loaded()
    
    keys = key.split(".")
    value = _config
    
    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            return default
    
    return value


def set_config(key: str, value: Any) -> None:
    """
    Sets a configuration value at runtime.
    
    Args:
        key: Dot-separated key path.
        value: Value to set.
    """
    _ensure_config_loaded()
    
    keys = key.split(".")
    _set_nested(_config, keys, value)


def reload_config() -> None:
    """
    Reloads the configuration from files.
    """
    global _config, _logger_initialized
    _config = {}
    _logger_initialized = False
    _load_config()
    init_logger()
    logger.info("Configuration reloaded.")

