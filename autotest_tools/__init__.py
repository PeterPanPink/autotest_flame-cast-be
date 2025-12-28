"""
================================================================================
Autotest Tools
================================================================================

A collection of automation utilities for test infrastructure management.

Modules:
    - common: Shared configuration and logging utilities
    - log_analyzer: Elasticsearch log search and analysis
    - notion_integration: Notion API client for documentation fetching
    - mongo_tools: MongoDB utilities for test data management

Example:
    from autotest_tools.log_analyzer import LogAnalyzer
    from autotest_tools.notion_integration import NotionFetcher
    from autotest_tools.mongo_tools import MongoDBClient
    
    # Analyze logs for errors
    analyzer = LogAnalyzer()
    report = analyzer.quick_health_check(lookback_minutes=60)
    
    # Fetch Notion documentation
    fetcher = NotionFetcher()
    page = fetcher.fetch_page("page_id")
    
    # Manage test data
    with MongoDBClient() as client:
        client.insert_one("test_collection", {"name": "test_item"})

================================================================================
"""

__version__ = "1.0.0"

__all__ = [
    "common",
    "log_analyzer",
    "notion_integration",
    "mongo_tools",
]

