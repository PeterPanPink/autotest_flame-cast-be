"""
================================================================================
Notion API Client and Content Converter
================================================================================

This module provides comprehensive tools for interacting with the Notion API.
It supports fetching pages, databases, and child content, then converting
Notion blocks to various formats (Markdown, JSON).

Key Features:
    - API client with retry mechanism
    - Page and database content fetching
    - Recursive child page fetching
    - Block-to-Markdown conversion
    - Image downloading and caching
    - Rate limit handling

Usage:
    from autotest_tools.notion_integration import NotionFetcher
    
    fetcher = NotionFetcher(token="your_notion_token")
    content = fetcher.fetch_page("page_id")
    markdown = content.to_markdown()
    content.save("output/my_page.md")

Author: Automation Team
License: MIT
================================================================================
"""

import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse

import httpx
from loguru import logger

from autotest_tools.common import get_config, init_logger, ensure_directory


# Initialize logger
init_logger()


# ============================================================
# Data Models
# ============================================================

@dataclass
class NotionBlock:
    """
    Represents a Notion block (paragraph, heading, list, etc.).
    """
    id: str
    type: str
    content: Dict[str, Any]
    children: List["NotionBlock"] = field(default_factory=list)
    has_children: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Converts block to dictionary."""
        return {
            "id": self.id,
            "type": self.type,
            "content": self.content,
            "children": [c.to_dict() for c in self.children],
        }


@dataclass
class NotionPage:
    """
    Represents a Notion page with its content.
    """
    id: str
    title: str
    url: str
    properties: Dict[str, Any]
    blocks: List[NotionBlock] = field(default_factory=list)
    created_time: str = ""
    last_edited_time: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Converts page to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "url": self.url,
            "properties": self.properties,
            "blocks": [b.to_dict() for b in self.blocks],
            "created_time": self.created_time,
            "last_edited_time": self.last_edited_time,
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Converts page to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
    
    def save(self, filepath: str) -> None:
        """
        Saves the page content to a file.
        
        Args:
            filepath: Output file path. Format determined by extension.
        """
        path = Path(filepath)
        ensure_directory(str(path.parent))
        
        if path.suffix in (".md", ".markdown"):
            converter = NotionContentConverter()
            content = converter.page_to_markdown(self)
        elif path.suffix == ".json":
            content = self.to_json()
        else:
            content = self.to_json()
        
        path.write_text(content, encoding="utf-8")
        logger.info(f"Page saved to: {filepath}")


# ============================================================
# Notion API Client
# ============================================================

class NotionClient:
    """
    Low-level client for Notion API interactions.
    """
    
    BASE_URL = "https://api.notion.com/v1"
    NOTION_VERSION = "2022-06-28"
    
    def __init__(
        self,
        token: str = None,
        timeout: int = 30,
        max_retries: int = 3
    ):
        """
        Initializes the Notion API client.
        
        Args:
            token: Notion integration token. Defaults to config value.
            timeout: Request timeout in seconds.
            max_retries: Maximum number of retry attempts.
        """
        self.token = token or get_config("notion.token", "")
        if not self.token:
            logger.warning("Notion token not configured. API calls will fail.")
        
        self.timeout = timeout
        self.max_retries = max_retries
        
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": self.NOTION_VERSION,
            "Content-Type": "application/json",
        }
    
    def _request(
        self,
        method: str,
        endpoint: str,
        params: Dict[str, Any] = None,
        json_body: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Makes an API request with retry logic.
        """
        url = f"{self.BASE_URL}/{endpoint}"
        
        for attempt in range(self.max_retries):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.request(
                        method=method,
                        url=url,
                        headers=self.headers,
                        params=params,
                        json=json_body,
                    )
                    
                    # Handle rate limiting
                    if response.status_code == 429:
                        retry_after = int(response.headers.get("Retry-After", 5))
                        logger.warning(f"Rate limited. Waiting {retry_after}s...")
                        time.sleep(retry_after)
                        continue
                    
                    response.raise_for_status()
                    return response.json()
                    
            except httpx.HTTPError as e:
                logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(2 ** attempt)  # Exponential backoff
        
        return {}
    
    def get_page(self, page_id: str) -> Dict[str, Any]:
        """
        Retrieves a page by ID.
        """
        return self._request("GET", f"pages/{page_id}")
    
    def get_block_children(
        self,
        block_id: str,
        start_cursor: str = None
    ) -> Dict[str, Any]:
        """
        Retrieves children of a block.
        """
        params = {}
        if start_cursor:
            params["start_cursor"] = start_cursor
        return self._request("GET", f"blocks/{block_id}/children", params=params)
    
    def query_database(
        self,
        database_id: str,
        filter_obj: Dict[str, Any] = None,
        sorts: List[Dict[str, str]] = None,
        start_cursor: str = None
    ) -> Dict[str, Any]:
        """
        Queries a database with optional filters and sorting.
        """
        body = {}
        if filter_obj:
            body["filter"] = filter_obj
        if sorts:
            body["sorts"] = sorts
        if start_cursor:
            body["start_cursor"] = start_cursor
        
        return self._request("POST", f"databases/{database_id}/query", json_body=body)
    
    def search(self, query: str, filter_type: str = None) -> Dict[str, Any]:
        """
        Searches for pages and databases.
        """
        body = {"query": query}
        if filter_type:
            body["filter"] = {"value": filter_type, "property": "object"}
        return self._request("POST", "search", json_body=body)


# ============================================================
# Content Converter
# ============================================================

class NotionContentConverter:
    """
    Converts Notion blocks to Markdown and other formats.
    """
    
    def __init__(self, download_images: bool = False, image_dir: str = "images"):
        """
        Initializes the converter.
        
        Args:
            download_images: Whether to download images locally.
            image_dir: Directory to save downloaded images.
        """
        self.download_images = download_images
        self.image_dir = image_dir
    
    def page_to_markdown(self, page: NotionPage) -> str:
        """
        Converts a NotionPage to Markdown format.
        """
        lines = []
        
        # Add title as H1
        lines.append(f"# {page.title}")
        lines.append("")
        
        # Add metadata
        lines.append(f"> Last edited: {page.last_edited_time}")
        lines.append("")
        
        # Convert blocks
        for block in page.blocks:
            block_md = self.block_to_markdown(block)
            if block_md:
                lines.append(block_md)
        
        return "\n".join(lines)
    
    def block_to_markdown(self, block: NotionBlock, indent_level: int = 0) -> str:
        """
        Converts a single block to Markdown.
        """
        block_type = block.type
        content = block.content
        indent = "    " * indent_level
        
        converter_method = getattr(self, f"_convert_{block_type}", None)
        if converter_method:
            result = converter_method(content, indent)
        else:
            # Default: try to extract text
            result = self._extract_rich_text(content)
        
        # Handle children
        if block.children:
            child_lines = []
            for child in block.children:
                child_md = self.block_to_markdown(child, indent_level + 1)
                if child_md:
                    child_lines.append(child_md)
            if child_lines:
                result += "\n" + "\n".join(child_lines)
        
        return result
    
    def _extract_rich_text(self, content: Dict[str, Any]) -> str:
        """
        Extracts and formats rich text content.
        """
        rich_text = content.get("rich_text", content.get("text", []))
        if not rich_text:
            return ""
        
        parts = []
        for text_obj in rich_text:
            text = text_obj.get("plain_text", "")
            annotations = text_obj.get("annotations", {})
            
            # Apply formatting
            if annotations.get("bold"):
                text = f"**{text}**"
            if annotations.get("italic"):
                text = f"*{text}*"
            if annotations.get("code"):
                text = f"`{text}`"
            if annotations.get("strikethrough"):
                text = f"~~{text}~~"
            
            # Handle links
            href = text_obj.get("href")
            if href:
                text = f"[{text}]({href})"
            
            parts.append(text)
        
        return "".join(parts)
    
    # Block type converters
    
    def _convert_paragraph(self, content: Dict, indent: str) -> str:
        return indent + self._extract_rich_text(content) + "\n"
    
    def _convert_heading_1(self, content: Dict, indent: str) -> str:
        return f"# {self._extract_rich_text(content)}\n"
    
    def _convert_heading_2(self, content: Dict, indent: str) -> str:
        return f"## {self._extract_rich_text(content)}\n"
    
    def _convert_heading_3(self, content: Dict, indent: str) -> str:
        return f"### {self._extract_rich_text(content)}\n"
    
    def _convert_bulleted_list_item(self, content: Dict, indent: str) -> str:
        return f"{indent}- {self._extract_rich_text(content)}"
    
    def _convert_numbered_list_item(self, content: Dict, indent: str) -> str:
        return f"{indent}1. {self._extract_rich_text(content)}"
    
    def _convert_to_do(self, content: Dict, indent: str) -> str:
        checked = content.get("checked", False)
        checkbox = "[x]" if checked else "[ ]"
        return f"{indent}- {checkbox} {self._extract_rich_text(content)}"
    
    def _convert_code(self, content: Dict, indent: str) -> str:
        language = content.get("language", "")
        text = self._extract_rich_text(content)
        return f"```{language}\n{text}\n```\n"
    
    def _convert_quote(self, content: Dict, indent: str) -> str:
        text = self._extract_rich_text(content)
        return f"> {text}\n"
    
    def _convert_divider(self, content: Dict, indent: str) -> str:
        return "---\n"
    
    def _convert_callout(self, content: Dict, indent: str) -> str:
        icon = content.get("icon", {}).get("emoji", "💡")
        text = self._extract_rich_text(content)
        return f"> {icon} {text}\n"
    
    def _convert_image(self, content: Dict, indent: str) -> str:
        image_type = content.get("type", "external")
        
        if image_type == "external":
            url = content.get("external", {}).get("url", "")
        else:
            url = content.get("file", {}).get("url", "")
        
        caption = ""
        if "caption" in content:
            caption = self._extract_rich_text({"rich_text": content["caption"]})
        
        alt_text = caption or "image"
        return f"![{alt_text}]({url})\n"
    
    def _convert_table(self, content: Dict, indent: str) -> str:
        return "[Table content - see original page]\n"
    
    def _convert_toggle(self, content: Dict, indent: str) -> str:
        text = self._extract_rich_text(content)
        return f"<details>\n<summary>{text}</summary>\n\n</details>\n"


# ============================================================
# High-Level Fetcher
# ============================================================

class NotionFetcher:
    """
    High-level interface for fetching Notion content.
    """
    
    def __init__(
        self,
        token: str = None,
        download_images: bool = False,
        image_dir: str = "images"
    ):
        """
        Initializes the fetcher.
        
        Args:
            token: Notion integration token.
            download_images: Whether to download images.
            image_dir: Directory for downloaded images.
        """
        self.client = NotionClient(token=token)
        self.converter = NotionContentConverter(
            download_images=download_images,
            image_dir=image_dir
        )
    
    def fetch_page(
        self,
        page_id: str,
        include_children: bool = True,
        max_depth: int = 3
    ) -> NotionPage:
        """
        Fetches a Notion page with all its content.
        
        Args:
            page_id: The page ID or URL.
            include_children: Whether to fetch nested content.
            max_depth: Maximum nesting depth for child pages.
        
        Returns:
            NotionPage object with content.
        """
        # Clean page ID if URL was provided
        page_id = self._extract_page_id(page_id)
        
        logger.info(f"Fetching page: {page_id}")
        
        # Get page metadata
        page_data = self.client.get_page(page_id)
        
        # Extract title
        title = self._extract_title(page_data.get("properties", {}))
        
        # Fetch blocks
        blocks = []
        if include_children:
            blocks = self._fetch_blocks_recursive(page_id, max_depth)
        
        return NotionPage(
            id=page_id,
            title=title,
            url=page_data.get("url", ""),
            properties=page_data.get("properties", {}),
            blocks=blocks,
            created_time=page_data.get("created_time", ""),
            last_edited_time=page_data.get("last_edited_time", ""),
        )
    
    def fetch_database(
        self,
        database_id: str,
        filter_obj: Dict[str, Any] = None,
        sorts: List[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetches all items from a Notion database.
        
        Args:
            database_id: The database ID.
            filter_obj: Optional filter criteria.
            sorts: Optional sort criteria.
        
        Returns:
            List of database items.
        """
        database_id = self._extract_page_id(database_id)
        logger.info(f"Fetching database: {database_id}")
        
        items = []
        cursor = None
        
        while True:
            result = self.client.query_database(
                database_id=database_id,
                filter_obj=filter_obj,
                sorts=sorts,
                start_cursor=cursor,
            )
            
            items.extend(result.get("results", []))
            
            if not result.get("has_more"):
                break
            cursor = result.get("next_cursor")
        
        logger.info(f"Fetched {len(items)} items from database")
        return items
    
    def _fetch_blocks_recursive(
        self,
        block_id: str,
        max_depth: int,
        current_depth: int = 0
    ) -> List[NotionBlock]:
        """
        Recursively fetches all blocks under a parent block.
        """
        if current_depth >= max_depth:
            return []
        
        blocks = []
        cursor = None
        
        while True:
            result = self.client.get_block_children(block_id, cursor)
            
            for block_data in result.get("results", []):
                block = NotionBlock(
                    id=block_data["id"],
                    type=block_data["type"],
                    content=block_data.get(block_data["type"], {}),
                    has_children=block_data.get("has_children", False),
                )
                
                # Fetch children recursively
                if block.has_children:
                    block.children = self._fetch_blocks_recursive(
                        block.id, max_depth, current_depth + 1
                    )
                
                blocks.append(block)
            
            if not result.get("has_more"):
                break
            cursor = result.get("next_cursor")
        
        return blocks
    
    def _extract_page_id(self, id_or_url: str) -> str:
        """
        Extracts page ID from a URL or returns the ID as-is.
        """
        # If it looks like a URL
        if "notion.so" in id_or_url or "notion.site" in id_or_url:
            # Extract ID from URL (last segment after removing query params)
            parsed = urlparse(id_or_url)
            path = parsed.path.rstrip("/")
            last_segment = path.split("/")[-1]
            # Handle URLs with title-id format
            if "-" in last_segment:
                last_segment = last_segment.split("-")[-1]
            return last_segment
        
        # Remove any dashes from the ID (Notion IDs are sometimes formatted with dashes)
        return id_or_url.replace("-", "")
    
    def _extract_title(self, properties: Dict[str, Any]) -> str:
        """
        Extracts the title from page properties.
        """
        for prop_name, prop_value in properties.items():
            if prop_value.get("type") == "title":
                title_array = prop_value.get("title", [])
                if title_array:
                    return title_array[0].get("plain_text", "Untitled")
        return "Untitled"


# ============================================================
# CLI Interface
# ============================================================

def main():
    """
    CLI entry point for Notion fetcher.
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="Notion Content Fetcher")
    parser.add_argument("page_id", help="Notion page ID or URL")
    parser.add_argument("--output", "-o", default="output/page.md", help="Output file path")
    parser.add_argument("--format", choices=["md", "json"], default="md", help="Output format")
    parser.add_argument("--download-images", action="store_true", help="Download images locally")
    
    args = parser.parse_args()
    
    fetcher = NotionFetcher(download_images=args.download_images)
    page = fetcher.fetch_page(args.page_id)
    
    output_path = args.output
    if args.format == "json" and not output_path.endswith(".json"):
        output_path = output_path.rsplit(".", 1)[0] + ".json"
    
    page.save(output_path)
    logger.success(f"Page saved to: {output_path}")


if __name__ == "__main__":
    main()

