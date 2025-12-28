"""
================================================================================
Elasticsearch Log Search and Analysis Tool
================================================================================

This module provides tools for searching and analyzing application logs
stored in Elasticsearch. It supports various search patterns, time ranges,
and log level filtering.

Features:
- Log search by level, time range, and keywords
- Automatic log categorization
- Error pattern detection
- Report generation
- Integration with CI/CD pipelines

================================================================================
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
import json
import re

from loguru import logger


# ================================================================================
# Configuration
# ================================================================================

@dataclass
class ElasticsearchConfig:
    """
    Configuration for Elasticsearch connection.
    
    Attributes:
        host: Elasticsearch host URL
        index_pattern: Index pattern to search (e.g., "logs-*")
        username: Optional username for authentication
        password: Optional password for authentication
        use_ssl: Whether to use SSL connection
        verify_certs: Whether to verify SSL certificates
    """
    host: str = "http://localhost:9200"
    index_pattern: str = "logs-*"
    username: Optional[str] = None
    password: Optional[str] = None
    use_ssl: bool = True
    verify_certs: bool = True
    timeout: int = 30
    
    def to_client_config(self) -> Dict[str, Any]:
        """Convert to Elasticsearch client configuration."""
        config = {
            "hosts": [self.host],
            "timeout": self.timeout,
        }
        
        if self.username and self.password:
            config["basic_auth"] = (self.username, self.password)
        
        if self.use_ssl:
            config["use_ssl"] = True
            config["verify_certs"] = self.verify_certs
        
        return config


# ================================================================================
# Search Query Builder
# ================================================================================

class LogQueryBuilder:
    """
    Builder for Elasticsearch log queries.
    
    Provides a fluent interface for constructing complex log queries.
    """
    
    def __init__(self):
        """Initialize empty query."""
        self._must: List[Dict] = []
        self._filter: List[Dict] = []
        self._should: List[Dict] = []
        self._must_not: List[Dict] = []
        self._sort: List[Dict] = [{"@timestamp": {"order": "desc"}}]
        self._size: int = 100
        self._source: Optional[List[str]] = None
    
    def with_level(self, level: str) -> "LogQueryBuilder":
        """
        Filter by log level.
        
        Args:
            level: Log level (ERROR, WARN, INFO, DEBUG)
        """
        self._must.append({"term": {"level": level.upper()}})
        return self
    
    def with_levels(self, levels: List[str]) -> "LogQueryBuilder":
        """
        Filter by multiple log levels.
        
        Args:
            levels: List of log levels
        """
        self._filter.append({
            "terms": {"level": [l.upper() for l in levels]}
        })
        return self
    
    def with_time_range(
        self, 
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        last_minutes: Optional[int] = None
    ) -> "LogQueryBuilder":
        """
        Filter by time range.
        
        Args:
            start: Start time
            end: End time
            last_minutes: Alternative - last N minutes
        """
        if last_minutes:
            start = datetime.now() - timedelta(minutes=last_minutes)
            end = datetime.now()
        
        time_range = {}
        if start:
            time_range["gte"] = start.isoformat()
        if end:
            time_range["lte"] = end.isoformat()
        
        if time_range:
            self._filter.append({"range": {"@timestamp": time_range}})
        
        return self
    
    def with_message_contains(self, text: str) -> "LogQueryBuilder":
        """
        Filter by message content.
        
        Args:
            text: Text to search for in message
        """
        self._must.append({"match_phrase": {"message": text}})
        return self
    
    def with_message_regex(self, pattern: str) -> "LogQueryBuilder":
        """
        Filter by message regex pattern.
        
        Args:
            pattern: Regex pattern for message
        """
        self._must.append({"regexp": {"message": pattern}})
        return self
    
    def with_service(self, service_name: str) -> "LogQueryBuilder":
        """
        Filter by service name.
        
        Args:
            service_name: Name of the service
        """
        self._must.append({"term": {"service.name": service_name}})
        return self
    
    def with_trace_id(self, trace_id: str) -> "LogQueryBuilder":
        """
        Filter by trace ID for distributed tracing.
        
        Args:
            trace_id: The trace ID to search for
        """
        self._must.append({"term": {"trace.id": trace_id}})
        return self
    
    def exclude_message(self, text: str) -> "LogQueryBuilder":
        """
        Exclude logs containing specific text.
        
        Args:
            text: Text to exclude
        """
        self._must_not.append({"match_phrase": {"message": text}})
        return self
    
    def with_size(self, size: int) -> "LogQueryBuilder":
        """
        Set maximum number of results.
        
        Args:
            size: Maximum results to return
        """
        self._size = size
        return self
    
    def with_fields(self, fields: List[str]) -> "LogQueryBuilder":
        """
        Specify which fields to return.
        
        Args:
            fields: List of field names
        """
        self._source = fields
        return self
    
    def sort_by(self, field: str, order: str = "desc") -> "LogQueryBuilder":
        """
        Set sort order.
        
        Args:
            field: Field to sort by
            order: Sort order (asc/desc)
        """
        self._sort = [{field: {"order": order}}]
        return self
    
    def build(self) -> Dict[str, Any]:
        """Build the final Elasticsearch query."""
        query = {"bool": {}}
        
        if self._must:
            query["bool"]["must"] = self._must
        if self._filter:
            query["bool"]["filter"] = self._filter
        if self._should:
            query["bool"]["should"] = self._should
        if self._must_not:
            query["bool"]["must_not"] = self._must_not
        
        body = {
            "query": query,
            "sort": self._sort,
            "size": self._size
        }
        
        if self._source:
            body["_source"] = self._source
        
        return body


# ================================================================================
# Log Entry Model
# ================================================================================

@dataclass
class LogEntry:
    """
    Represents a single log entry.
    
    Attributes:
        timestamp: Log timestamp
        level: Log level (ERROR, WARN, INFO, DEBUG)
        message: Log message
        service: Service name
        trace_id: Optional trace ID
        extra: Additional fields
    """
    timestamp: datetime
    level: str
    message: str
    service: str = ""
    trace_id: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_es_hit(cls, hit: Dict[str, Any]) -> "LogEntry":
        """Create LogEntry from Elasticsearch hit."""
        source = hit.get("_source", {})
        
        # Parse timestamp
        ts_str = source.get("@timestamp", "")
        try:
            timestamp = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except ValueError:
            timestamp = datetime.now()
        
        return cls(
            timestamp=timestamp,
            level=source.get("level", "INFO"),
            message=source.get("message", ""),
            service=source.get("service", {}).get("name", ""),
            trace_id=source.get("trace", {}).get("id"),
            extra={k: v for k, v in source.items() 
                   if k not in ["@timestamp", "level", "message", "service", "trace"]}
        )
    
    def is_error(self) -> bool:
        """Check if this is an error log."""
        return self.level.upper() in ["ERROR", "FATAL", "CRITICAL"]
    
    def is_warning(self) -> bool:
        """Check if this is a warning log."""
        return self.level.upper() in ["WARN", "WARNING"]


# ================================================================================
# Log Analyzer
# ================================================================================

class LogAnalyzer:
    """
    Analyzes log entries to identify patterns and issues.
    
    Provides methods for categorizing logs, detecting error patterns,
    and generating analysis reports.
    """
    
    # Known error patterns
    ERROR_PATTERNS = [
        (r"E_INTERNAL_ERROR", "Internal Server Error"),
        (r"E_DATABASE_ERROR", "Database Error"),
        (r"E_TIMEOUT", "Timeout Error"),
        (r"E_AUTH_FAILED", "Authentication Failed"),
        (r"E_PERMISSION_DENIED", "Permission Denied"),
        (r"E_NOT_FOUND", "Resource Not Found"),
        (r"E_VALIDATION_ERROR", "Validation Error"),
        (r"E_RATE_LIMITED", "Rate Limited"),
        (r"Exception|Traceback", "Unhandled Exception"),
        (r"OutOfMemory|OOM", "Memory Error"),
        (r"ConnectionRefused|ConnectionError", "Connection Error"),
    ]
    
    # Expected errors (from mutation testing, etc.)
    EXPECTED_ERRORS = [
        r"E_INVALID_PARAMS",
        r"E_CHANNEL_NOT_FOUND",
        r"E_SESSION_NOT_FOUND",
        r"Invalid cursor format",
        r"Validation error",
    ]
    
    def __init__(self, logs: List[LogEntry]):
        """
        Initialize analyzer with log entries.
        
        Args:
            logs: List of log entries to analyze
        """
        self.logs = logs
        self._categorized = None
    
    def categorize_by_level(self) -> Dict[str, List[LogEntry]]:
        """Categorize logs by level."""
        result: Dict[str, List[LogEntry]] = {}
        for log in self.logs:
            level = log.level.upper()
            if level not in result:
                result[level] = []
            result[level].append(log)
        return result
    
    def categorize_by_service(self) -> Dict[str, List[LogEntry]]:
        """Categorize logs by service."""
        result: Dict[str, List[LogEntry]] = {}
        for log in self.logs:
            service = log.service or "unknown"
            if service not in result:
                result[service] = []
            result[service].append(log)
        return result
    
    def find_error_patterns(self) -> Dict[str, List[LogEntry]]:
        """
        Find logs matching known error patterns.
        
        Returns:
            Dictionary mapping pattern names to matching logs
        """
        result: Dict[str, List[LogEntry]] = {}
        
        for log in self.logs:
            if not log.is_error():
                continue
            
            for pattern, name in self.ERROR_PATTERNS:
                if re.search(pattern, log.message, re.IGNORECASE):
                    if name not in result:
                        result[name] = []
                    result[name].append(log)
                    break
        
        return result
    
    def filter_unexpected_errors(self) -> List[LogEntry]:
        """
        Filter out expected errors, returning only unexpected ones.
        
        Returns:
            List of unexpected error logs
        """
        unexpected = []
        
        for log in self.logs:
            if not log.is_error():
                continue
            
            is_expected = False
            for pattern in self.EXPECTED_ERRORS:
                if re.search(pattern, log.message, re.IGNORECASE):
                    is_expected = True
                    break
            
            if not is_expected:
                unexpected.append(log)
        
        return unexpected
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get analysis summary.
        
        Returns:
            Dictionary with analysis summary
        """
        by_level = self.categorize_by_level()
        error_patterns = self.find_error_patterns()
        unexpected = self.filter_unexpected_errors()
        
        return {
            "total_logs": len(self.logs),
            "by_level": {level: len(logs) for level, logs in by_level.items()},
            "error_patterns": {name: len(logs) for name, logs in error_patterns.items()},
            "unexpected_errors": len(unexpected),
            "time_range": {
                "start": min(log.timestamp for log in self.logs).isoformat() if self.logs else None,
                "end": max(log.timestamp for log in self.logs).isoformat() if self.logs else None,
            }
        }
    
    def generate_report(self, output_path: Optional[Path] = None) -> str:
        """
        Generate a detailed analysis report.
        
        Args:
            output_path: Optional path to save report
            
        Returns:
            Report content as string
        """
        summary = self.get_summary()
        unexpected = self.filter_unexpected_errors()
        
        lines = [
            "=" * 80,
            "LOG ANALYSIS REPORT",
            "=" * 80,
            "",
            f"Analysis Time: {datetime.now().isoformat()}",
            f"Total Logs Analyzed: {summary['total_logs']}",
            "",
            "LOG LEVELS:",
            "-" * 40,
        ]
        
        for level, count in summary["by_level"].items():
            lines.append(f"  {level}: {count}")
        
        lines.extend([
            "",
            "ERROR PATTERNS DETECTED:",
            "-" * 40,
        ])
        
        if summary["error_patterns"]:
            for pattern, count in summary["error_patterns"].items():
                lines.append(f"  {pattern}: {count}")
        else:
            lines.append("  No known error patterns detected")
        
        lines.extend([
            "",
            "UNEXPECTED ERRORS:",
            "-" * 40,
        ])
        
        if unexpected:
            for log in unexpected[:10]:  # Show first 10
                lines.append(f"  [{log.timestamp}] {log.message[:100]}...")
            if len(unexpected) > 10:
                lines.append(f"  ... and {len(unexpected) - 10} more")
        else:
            lines.append("  No unexpected errors found")
        
        lines.extend([
            "",
            "=" * 80,
        ])
        
        report = "\n".join(lines)
        
        if output_path:
            output_path.write_text(report)
            logger.info(f"Report saved to {output_path}")
        
        return report


# ================================================================================
# Main Search Client
# ================================================================================

class ElasticsearchLogClient:
    """
    Main client for Elasticsearch log operations.
    
    Provides high-level methods for searching and analyzing logs.
    """
    
    def __init__(self, config: Optional[ElasticsearchConfig] = None):
        """
        Initialize client with configuration.
        
        Args:
            config: Elasticsearch configuration
        """
        self.config = config or ElasticsearchConfig()
        self._client = None
    
    def _get_client(self):
        """Get or create Elasticsearch client."""
        if self._client is None:
            try:
                from elasticsearch import Elasticsearch
                self._client = Elasticsearch(**self.config.to_client_config())
            except ImportError:
                logger.warning("elasticsearch package not installed")
                return None
        return self._client
    
    def search(
        self, 
        query: Optional[Dict[str, Any]] = None,
        builder: Optional[LogQueryBuilder] = None
    ) -> List[LogEntry]:
        """
        Search logs with query.
        
        Args:
            query: Raw Elasticsearch query
            builder: LogQueryBuilder instance
            
        Returns:
            List of LogEntry objects
        """
        client = self._get_client()
        if client is None:
            logger.warning("Elasticsearch client not available")
            return []
        
        if builder:
            query = builder.build()
        elif query is None:
            query = LogQueryBuilder().with_time_range(last_minutes=60).build()
        
        try:
            response = client.search(
                index=self.config.index_pattern,
                body=query
            )
            
            hits = response.get("hits", {}).get("hits", [])
            return [LogEntry.from_es_hit(hit) for hit in hits]
            
        except Exception as e:
            logger.error(f"Elasticsearch search failed: {e}")
            return []
    
    def search_errors(
        self, 
        last_minutes: int = 60,
        exclude_expected: bool = True
    ) -> List[LogEntry]:
        """
        Search for error logs.
        
        Args:
            last_minutes: Time range in minutes
            exclude_expected: Whether to exclude expected errors
            
        Returns:
            List of error logs
        """
        builder = (
            LogQueryBuilder()
            .with_levels(["ERROR", "FATAL", "CRITICAL"])
            .with_time_range(last_minutes=last_minutes)
            .with_size(500)
        )
        
        logs = self.search(builder=builder)
        
        if exclude_expected:
            analyzer = LogAnalyzer(logs)
            return analyzer.filter_unexpected_errors()
        
        return logs
    
    def analyze_recent(
        self, 
        last_minutes: int = 60,
        output_path: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Analyze recent logs and optionally save report.
        
        Args:
            last_minutes: Time range in minutes
            output_path: Optional path for report
            
        Returns:
            Analysis summary
        """
        builder = (
            LogQueryBuilder()
            .with_time_range(last_minutes=last_minutes)
            .with_size(1000)
        )
        
        logs = self.search(builder=builder)
        analyzer = LogAnalyzer(logs)
        
        if output_path:
            analyzer.generate_report(output_path)
        
        return analyzer.get_summary()


# ================================================================================
# Convenience Functions
# ================================================================================

def search_recent_errors(
    minutes: int = 60,
    config: Optional[ElasticsearchConfig] = None
) -> List[LogEntry]:
    """
    Quick helper to search recent error logs.
    
    Args:
        minutes: Time range in minutes
        config: Optional ES configuration
        
    Returns:
        List of error logs
    """
    client = ElasticsearchLogClient(config)
    return client.search_errors(last_minutes=minutes)


def analyze_test_run_logs(
    start_time: datetime,
    end_time: datetime,
    output_dir: Path,
    config: Optional[ElasticsearchConfig] = None
) -> Dict[str, Any]:
    """
    Analyze logs from a specific test run.
    
    Args:
        start_time: Test run start time
        end_time: Test run end time
        output_dir: Directory for output files
        config: Optional ES configuration
        
    Returns:
        Analysis summary
    """
    client = ElasticsearchLogClient(config)
    
    builder = (
        LogQueryBuilder()
        .with_time_range(start=start_time, end=end_time)
        .with_size(5000)
    )
    
    logs = client.search(builder=builder)
    analyzer = LogAnalyzer(logs)
    
    # Generate reports
    output_dir.mkdir(parents=True, exist_ok=True)
    
    report_path = output_dir / f"log_analysis_{datetime.now():%Y%m%d_%H%M%S}.txt"
    analyzer.generate_report(report_path)
    
    # Save raw logs
    logs_path = output_dir / f"raw_logs_{datetime.now():%Y%m%d_%H%M%S}.json"
    logs_data = [
        {
            "timestamp": log.timestamp.isoformat(),
            "level": log.level,
            "message": log.message,
            "service": log.service,
        }
        for log in logs
    ]
    logs_path.write_text(json.dumps(logs_data, indent=2))
    
    return analyzer.get_summary()
