"""
================================================================================
Log Parser Module
================================================================================

This module provides utilities for parsing and analyzing application logs
from various sources. It supports structured log parsing, pattern detection,
and error categorization for CI/CD integration.

Key Features:
- Parse structured JSON logs
- Detect error patterns and anomalies
- Categorize errors by type and severity
- Generate analysis reports

================================================================================
"""

import re
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import Counter

from loguru import logger


# ================================================================================
# Data Models
# ================================================================================

class LogLevel(str, Enum):
    """Log level enumeration."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ErrorCategory(str, Enum):
    """Error categorization for analysis."""
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATABASE = "database"
    NETWORK = "network"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    INTERNAL = "internal"
    UNKNOWN = "unknown"


@dataclass
class LogEntry:
    """Parsed log entry."""
    timestamp: datetime
    level: LogLevel
    message: str
    service: str = ""
    trace_id: str = ""
    span_id: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)
    raw: str = ""
    
    @property
    def is_error(self) -> bool:
        """Check if this is an error level log."""
        return self.level in [LogLevel.ERROR, LogLevel.CRITICAL]


@dataclass
class ErrorPattern:
    """Pattern for identifying specific error types."""
    name: str
    pattern: str
    category: ErrorCategory
    severity: int = 1  # 1-5, higher is more severe
    description: str = ""
    
    def matches(self, text: str) -> bool:
        """Check if the pattern matches the given text."""
        return bool(re.search(self.pattern, text, re.IGNORECASE))


@dataclass
class AnalysisResult:
    """Result of log analysis."""
    total_entries: int = 0
    error_count: int = 0
    warning_count: int = 0
    entries_by_level: Dict[str, int] = field(default_factory=dict)
    errors_by_category: Dict[str, int] = field(default_factory=dict)
    top_errors: List[Tuple[str, int]] = field(default_factory=list)
    anomalies: List[str] = field(default_factory=list)
    time_range: Optional[Tuple[datetime, datetime]] = None


# ================================================================================
# Log Parser
# ================================================================================

class LogParser:
    """
    Parser for structured application logs.
    
    This class handles parsing of JSON-formatted logs and provides
    methods for extracting structured information.
    
    Example:
        parser = LogParser()
        entries = parser.parse_file("app.log")
        errors = parser.get_errors(entries)
    """
    
    # Standard log format patterns
    PATTERNS = {
        "json": r'^\{.*\}$',
        "standard": r'^(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})\s*\|\s*(\w+)\s*\|\s*(.+)$',
        "with_service": r'^(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})\s*\|\s*(\w+)\s*\|\s*\[(\w+)\]\s*(.+)$'
    }
    
    def __init__(self):
        """Initialize the log parser."""
        self.entries: List[LogEntry] = []
    
    def parse_line(self, line: str) -> Optional[LogEntry]:
        """
        Parse a single log line.
        
        Args:
            line: Raw log line
            
        Returns:
            Parsed LogEntry or None if parsing fails
        """
        line = line.strip()
        if not line:
            return None
        
        # Try JSON format first
        if line.startswith('{'):
            return self._parse_json_log(line)
        
        # Try standard formats
        return self._parse_standard_log(line)
    
    def _parse_json_log(self, line: str) -> Optional[LogEntry]:
        """Parse JSON-formatted log line."""
        try:
            data = json.loads(line)
            
            # Handle various JSON log formats
            timestamp = self._parse_timestamp(
                data.get('timestamp') or data.get('time') or data.get('@timestamp', '')
            )
            
            level = self._parse_level(
                data.get('level') or data.get('severity') or 'INFO'
            )
            
            message = data.get('message') or data.get('msg') or str(data)
            
            return LogEntry(
                timestamp=timestamp or datetime.now(),
                level=level,
                message=message,
                service=data.get('service', ''),
                trace_id=data.get('trace_id', ''),
                span_id=data.get('span_id', ''),
                extra={k: v for k, v in data.items() 
                       if k not in ['timestamp', 'time', 'level', 'message', 'service']},
                raw=line
            )
        except json.JSONDecodeError:
            return None
    
    def _parse_standard_log(self, line: str) -> Optional[LogEntry]:
        """Parse standard text format log line."""
        # Try with service pattern
        match = re.match(self.PATTERNS['with_service'], line)
        if match:
            timestamp_str, level_str, service, message = match.groups()
            return LogEntry(
                timestamp=self._parse_timestamp(timestamp_str) or datetime.now(),
                level=self._parse_level(level_str),
                message=message,
                service=service,
                raw=line
            )
        
        # Try standard pattern
        match = re.match(self.PATTERNS['standard'], line)
        if match:
            timestamp_str, level_str, message = match.groups()
            return LogEntry(
                timestamp=self._parse_timestamp(timestamp_str) or datetime.now(),
                level=self._parse_level(level_str),
                message=message,
                raw=line
            )
        
        # Fallback: treat entire line as message
        return LogEntry(
            timestamp=datetime.now(),
            level=LogLevel.INFO,
            message=line,
            raw=line
        )
    
    def _parse_timestamp(self, value: str) -> Optional[datetime]:
        """Parse timestamp from various formats."""
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%d %H:%M:%S.%f"
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(value.replace('Z', ''), fmt)
            except ValueError:
                continue
        
        return None
    
    def _parse_level(self, value: str) -> LogLevel:
        """Parse log level string to enum."""
        value = value.upper().strip()
        
        try:
            return LogLevel(value)
        except ValueError:
            # Handle common variations
            if value in ['WARN']:
                return LogLevel.WARNING
            elif value in ['ERR', 'FATAL']:
                return LogLevel.ERROR
            return LogLevel.INFO
    
    def parse_file(self, file_path: str) -> List[LogEntry]:
        """
        Parse all log entries from a file.
        
        Args:
            file_path: Path to the log file
            
        Returns:
            List of parsed LogEntry objects
        """
        entries = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    entry = self.parse_line(line)
                    if entry:
                        entries.append(entry)
        except IOError as e:
            logger.error(f"Error reading log file {file_path}: {e}")
        
        self.entries = entries
        logger.info(f"Parsed {len(entries)} log entries from {file_path}")
        
        return entries
    
    def parse_text(self, text: str) -> List[LogEntry]:
        """
        Parse log entries from text content.
        
        Args:
            text: Log content as string
            
        Returns:
            List of parsed LogEntry objects
        """
        entries = []
        
        for line in text.split('\n'):
            entry = self.parse_line(line)
            if entry:
                entries.append(entry)
        
        self.entries = entries
        return entries
    
    def get_errors(self, entries: List[LogEntry] = None) -> List[LogEntry]:
        """Get all error-level entries."""
        entries = entries or self.entries
        return [e for e in entries if e.is_error]
    
    def get_by_level(self, level: LogLevel, entries: List[LogEntry] = None) -> List[LogEntry]:
        """Get entries by log level."""
        entries = entries or self.entries
        return [e for e in entries if e.level == level]


# ================================================================================
# Log Analyzer
# ================================================================================

class LogAnalyzer:
    """
    Analyzer for detecting patterns and anomalies in logs.
    
    This class provides methods for categorizing errors, detecting
    anomalies, and generating analysis reports.
    
    Example:
        analyzer = LogAnalyzer()
        analyzer.add_pattern(ErrorPattern(...))
        result = analyzer.analyze(entries)
    """
    
    # Built-in error patterns
    DEFAULT_PATTERNS = [
        ErrorPattern(
            name="Validation Error",
            pattern=r"(validation|invalid|malformed|missing required)",
            category=ErrorCategory.VALIDATION,
            severity=2
        ),
        ErrorPattern(
            name="Authentication Error",
            pattern=r"(unauthorized|authentication failed|invalid token|jwt expired)",
            category=ErrorCategory.AUTHENTICATION,
            severity=3
        ),
        ErrorPattern(
            name="Authorization Error",
            pattern=r"(forbidden|permission denied|access denied|not allowed)",
            category=ErrorCategory.AUTHORIZATION,
            severity=3
        ),
        ErrorPattern(
            name="Database Error",
            pattern=r"(database|db error|connection refused|query failed|deadlock)",
            category=ErrorCategory.DATABASE,
            severity=4
        ),
        ErrorPattern(
            name="Network Error",
            pattern=r"(connection error|network unreachable|dns|socket error)",
            category=ErrorCategory.NETWORK,
            severity=3
        ),
        ErrorPattern(
            name="Timeout Error",
            pattern=r"(timeout|timed out|deadline exceeded)",
            category=ErrorCategory.TIMEOUT,
            severity=3
        ),
        ErrorPattern(
            name="Rate Limit Error",
            pattern=r"(rate limit|too many requests|throttled|429)",
            category=ErrorCategory.RATE_LIMIT,
            severity=2
        ),
        ErrorPattern(
            name="Internal Error",
            pattern=r"(internal error|500|unhandled exception|stack trace)",
            category=ErrorCategory.INTERNAL,
            severity=5
        )
    ]
    
    def __init__(self, include_defaults: bool = True):
        """
        Initialize the analyzer.
        
        Args:
            include_defaults: Whether to include default error patterns
        """
        self.patterns: List[ErrorPattern] = []
        
        if include_defaults:
            self.patterns.extend(self.DEFAULT_PATTERNS)
    
    def add_pattern(self, pattern: ErrorPattern) -> None:
        """Add a custom error pattern."""
        self.patterns.append(pattern)
    
    def categorize_error(self, entry: LogEntry) -> ErrorCategory:
        """
        Categorize an error entry.
        
        Args:
            entry: Log entry to categorize
            
        Returns:
            Error category
        """
        text = f"{entry.message} {str(entry.extra)}"
        
        for pattern in self.patterns:
            if pattern.matches(text):
                return pattern.category
        
        return ErrorCategory.UNKNOWN
    
    def analyze(self, entries: List[LogEntry]) -> AnalysisResult:
        """
        Perform comprehensive log analysis.
        
        Args:
            entries: List of log entries to analyze
            
        Returns:
            AnalysisResult with statistics and insights
        """
        result = AnalysisResult()
        result.total_entries = len(entries)
        
        if not entries:
            return result
        
        # Count by level
        level_counter = Counter(e.level.value for e in entries)
        result.entries_by_level = dict(level_counter)
        result.error_count = level_counter.get(LogLevel.ERROR.value, 0) + \
                            level_counter.get(LogLevel.CRITICAL.value, 0)
        result.warning_count = level_counter.get(LogLevel.WARNING.value, 0)
        
        # Categorize errors
        errors = [e for e in entries if e.is_error]
        category_counter = Counter()
        
        for error in errors:
            category = self.categorize_error(error)
            category_counter[category.value] += 1
        
        result.errors_by_category = dict(category_counter)
        
        # Find top error messages
        error_messages = [e.message[:100] for e in errors]  # Truncate for grouping
        message_counter = Counter(error_messages)
        result.top_errors = message_counter.most_common(10)
        
        # Time range
        timestamps = [e.timestamp for e in entries if e.timestamp]
        if timestamps:
            result.time_range = (min(timestamps), max(timestamps))
        
        # Detect anomalies
        result.anomalies = self._detect_anomalies(entries)
        
        return result
    
    def _detect_anomalies(self, entries: List[LogEntry]) -> List[str]:
        """Detect anomalies in log patterns."""
        anomalies = []
        
        if not entries:
            return anomalies
        
        # High error rate
        error_rate = sum(1 for e in entries if e.is_error) / len(entries)
        if error_rate > 0.1:  # More than 10% errors
            anomalies.append(f"High error rate detected: {error_rate:.1%}")
        
        # Burst of errors in short time
        errors = sorted([e for e in entries if e.is_error], key=lambda x: x.timestamp)
        if len(errors) > 10:
            # Check for 10+ errors within 1 minute
            for i in range(len(errors) - 10):
                time_diff = (errors[i + 10].timestamp - errors[i].timestamp).total_seconds()
                if time_diff < 60:
                    anomalies.append("Error burst detected: 10+ errors within 1 minute")
                    break
        
        # Check for critical internal errors
        internal_errors = sum(
            1 for e in entries 
            if e.is_error and self.categorize_error(e) == ErrorCategory.INTERNAL
        )
        if internal_errors > 0:
            anomalies.append(f"Internal errors detected: {internal_errors}")
        
        return anomalies
    
    def generate_report(self, result: AnalysisResult) -> str:
        """
        Generate a human-readable analysis report.
        
        Args:
            result: Analysis result
            
        Returns:
            Formatted report string
        """
        lines = [
            "=" * 60,
            "LOG ANALYSIS REPORT",
            "=" * 60,
            "",
            f"Total Entries: {result.total_entries}",
            f"Error Count: {result.error_count}",
            f"Warning Count: {result.warning_count}",
            ""
        ]
        
        if result.time_range:
            start, end = result.time_range
            lines.append(f"Time Range: {start} to {end}")
            lines.append("")
        
        lines.append("Entries by Level:")
        for level, count in sorted(result.entries_by_level.items()):
            lines.append(f"  {level}: {count}")
        lines.append("")
        
        if result.errors_by_category:
            lines.append("Errors by Category:")
            for category, count in sorted(result.errors_by_category.items()):
                lines.append(f"  {category}: {count}")
            lines.append("")
        
        if result.top_errors:
            lines.append("Top Error Messages:")
            for msg, count in result.top_errors[:5]:
                lines.append(f"  [{count}x] {msg[:60]}...")
            lines.append("")
        
        if result.anomalies:
            lines.append("⚠️ ANOMALIES DETECTED:")
            for anomaly in result.anomalies:
                lines.append(f"  - {anomaly}")
            lines.append("")
        
        lines.append("=" * 60)
        
        return "\n".join(lines)

