"""
================================================================================
Elasticsearch Log Analyzer
================================================================================

This module provides tools for searching, analyzing, and reporting on 
application logs stored in Elasticsearch.

Features:
    - Time-range based log search
    - Log level filtering (ERROR, WARNING, INFO, DEBUG)
    - Pattern matching and highlighting
    - Automated error detection and categorization
    - Report generation for CI/CD integration

Author: Automation Team
License: MIT
================================================================================
"""

from .es_log_search import (
    ElasticsearchClient,
    LogSearcher,
    LogAnalyzer,
    AnalysisReport,
)

__all__ = [
    "ElasticsearchClient",
    "LogSearcher",
    "LogAnalyzer",
    "AnalysisReport",
]

