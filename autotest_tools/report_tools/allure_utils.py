"""
================================================================================
Allure Report Utilities
================================================================================

This module provides utilities for enhancing Allure test reports with
additional information, custom attachments, and report processing.

Features:
- Custom attachment helpers
- Report post-processing
- History management
- Summary generation

================================================================================
"""

import json
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import subprocess

import allure
from loguru import logger


# ================================================================================
# Attachment Helpers
# ================================================================================

def attach_json(data: Any, name: str = "Data"):
    """
    Attach JSON data to Allure report.
    
    Args:
        data: Data to attach (will be JSON serialized)
        name: Attachment name
    """
    json_str = json.dumps(data, indent=2, default=str)
    allure.attach(
        json_str,
        name=name,
        attachment_type=allure.attachment_type.JSON
    )


def attach_text(text: str, name: str = "Text"):
    """
    Attach text content to Allure report.
    
    Args:
        text: Text to attach
        name: Attachment name
    """
    allure.attach(
        text,
        name=name,
        attachment_type=allure.attachment_type.TEXT
    )


def attach_html(html: str, name: str = "HTML"):
    """
    Attach HTML content to Allure report.
    
    Args:
        html: HTML to attach
        name: Attachment name
    """
    allure.attach(
        html,
        name=name,
        attachment_type=allure.attachment_type.HTML
    )


def attach_curl_command(
    method: str,
    url: str,
    headers: Optional[Dict[str, str]] = None,
    body: Optional[Any] = None
):
    """
    Attach cURL command for API request reproduction.
    
    Args:
        method: HTTP method
        url: Request URL
        headers: Request headers
        body: Request body
    """
    cmd_parts = [f"curl -X {method}"]
    
    if headers:
        for key, value in headers.items():
            # Mask sensitive headers
            if key.lower() in ["authorization", "x-api-key"]:
                value = "***MASKED***"
            cmd_parts.append(f"-H '{key}: {value}'")
    
    if body:
        body_str = json.dumps(body) if isinstance(body, (dict, list)) else str(body)
        cmd_parts.append(f"-d '{body_str}'")
    
    cmd_parts.append(f"'{url}'")
    
    curl_cmd = " \\\n  ".join(cmd_parts)
    attach_text(curl_cmd, name="cURL Command")


def attach_request_response(
    request_url: str,
    request_method: str,
    request_headers: Dict[str, str],
    request_body: Optional[Any],
    response_status: int,
    response_body: Any,
    response_time_ms: Optional[float] = None
):
    """
    Attach complete request/response details.
    
    Args:
        request_url: Request URL
        request_method: HTTP method
        request_headers: Request headers
        request_body: Request body
        response_status: Response status code
        response_body: Response body
        response_time_ms: Response time in milliseconds
    """
    with allure.step(f"📤 Request: {request_method} {request_url}"):
        attach_text(request_url, name="🔗 Request URL")
        
        # Mask sensitive headers
        safe_headers = {
            k: "***MASKED***" if k.lower() in ["authorization", "x-api-key"] else v
            for k, v in request_headers.items()
        }
        attach_json(safe_headers, name="📤 Request Headers")
        
        if request_body:
            attach_json(request_body, name="📤 Request Body")
        
        attach_curl_command(request_method, request_url, request_headers, request_body)
    
    with allure.step(f"📥 Response: {response_status}"):
        status_emoji = "✅" if 200 <= response_status < 300 else "❌"
        attach_text(f"{status_emoji} {response_status}", name="📥 Response Status")
        
        if response_time_ms:
            attach_text(f"{response_time_ms:.2f}ms", name="⏱️ Response Time")
        
        attach_json(response_body, name="📥 Response Body")


# ================================================================================
# Report Processing
# ================================================================================

@dataclass
class TestResultSummary:
    """Summary of test execution results."""
    total: int = 0
    passed: int = 0
    failed: int = 0
    broken: int = 0
    skipped: int = 0
    unknown: int = 0
    duration_ms: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    @property
    def pass_rate(self) -> float:
        """Calculate pass rate percentage."""
        if self.total == 0:
            return 0.0
        return (self.passed / self.total) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "broken": self.broken,
            "skipped": self.skipped,
            "unknown": self.unknown,
            "pass_rate": f"{self.pass_rate:.2f}%",
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp,
        }


class AllureReportProcessor:
    """
    Processes Allure results and generates reports.
    
    Provides methods for analyzing results, generating summaries,
    and managing report history.
    """
    
    def __init__(
        self,
        results_dir: Path,
        report_dir: Optional[Path] = None,
        history_dir: Optional[Path] = None
    ):
        """
        Initialize processor.
        
        Args:
            results_dir: Allure results directory
            report_dir: Output report directory
            history_dir: History data directory
        """
        self.results_dir = Path(results_dir)
        self.report_dir = Path(report_dir or results_dir.parent / "allure-report")
        self.history_dir = Path(history_dir or results_dir.parent / "allure-history")
    
    def parse_results(self) -> List[Dict[str, Any]]:
        """
        Parse Allure result files.
        
        Returns:
            List of test result dictionaries
        """
        results = []
        
        for result_file in self.results_dir.glob("*-result.json"):
            try:
                with open(result_file) as f:
                    results.append(json.load(f))
            except Exception as e:
                logger.warning(f"Failed to parse {result_file}: {e}")
        
        return results
    
    def generate_summary(self) -> TestResultSummary:
        """
        Generate summary from results.
        
        Returns:
            TestResultSummary object
        """
        results = self.parse_results()
        summary = TestResultSummary()
        summary.total = len(results)
        
        for result in results:
            status = result.get("status", "unknown")
            if status == "passed":
                summary.passed += 1
            elif status == "failed":
                summary.failed += 1
            elif status == "broken":
                summary.broken += 1
            elif status == "skipped":
                summary.skipped += 1
            else:
                summary.unknown += 1
            
            # Add duration
            start = result.get("start", 0)
            stop = result.get("stop", 0)
            summary.duration_ms += (stop - start)
        
        return summary
    
    def copy_history(self):
        """Copy history from previous report to results."""
        history_source = self.report_dir / "history"
        history_dest = self.results_dir / "history"
        
        if history_source.exists():
            if history_dest.exists():
                shutil.rmtree(history_dest)
            shutil.copytree(history_source, history_dest)
            logger.info("Copied history from previous report")
    
    def generate_report(self) -> bool:
        """
        Generate Allure HTML report.
        
        Returns:
            True if successful
        """
        try:
            # Copy history first
            self.copy_history()
            
            # Generate report
            cmd = [
                "allure", "generate",
                str(self.results_dir),
                "-o", str(self.report_dir),
                "--clean"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"Report generated at {self.report_dir}")
                return True
            else:
                logger.error(f"Report generation failed: {result.stderr}")
                return False
                
        except FileNotFoundError:
            logger.error("Allure command not found. Install allure-commandline.")
            return False
        except Exception as e:
            logger.error(f"Report generation error: {e}")
            return False
    
    def save_history(self):
        """Save current history for future reports."""
        history_source = self.report_dir / "history"
        
        if history_source.exists():
            self.history_dir.mkdir(parents=True, exist_ok=True)
            
            # Create timestamped backup
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = self.history_dir / timestamp
            shutil.copytree(history_source, backup_dir)
            
            # Keep latest as "current"
            current_dir = self.history_dir / "current"
            if current_dir.exists():
                shutil.rmtree(current_dir)
            shutil.copytree(history_source, current_dir)
            
            logger.info(f"History saved to {self.history_dir}")
    
    def print_summary(self):
        """Print summary to console."""
        summary = self.generate_summary()
        
        print("\n" + "=" * 60)
        print("TEST EXECUTION SUMMARY")
        print("=" * 60)
        print(f"Total Tests:    {summary.total}")
        print(f"Passed:         {summary.passed} ✅")
        print(f"Failed:         {summary.failed} ❌")
        print(f"Broken:         {summary.broken} ⚠️")
        print(f"Skipped:        {summary.skipped} ⏭️")
        print(f"Pass Rate:      {summary.pass_rate:.2f}%")
        print(f"Duration:       {summary.duration_ms / 1000:.2f}s")
        print("=" * 60 + "\n")


# ================================================================================
# Decorators
# ================================================================================

def allure_step(step_name: str):
    """
    Decorator to wrap function as Allure step.
    
    Args:
        step_name: Step name for report
    """
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            with allure.step(step_name):
                return await func(*args, **kwargs)
        
        def sync_wrapper(*args, **kwargs):
            with allure.step(step_name):
                return func(*args, **kwargs)
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def allure_feature(feature_name: str):
    """
    Decorator to mark test class/function with Allure feature.
    
    Args:
        feature_name: Feature name
    """
    return allure.feature(feature_name)


def allure_story(story_name: str):
    """
    Decorator to mark test with Allure story.
    
    Args:
        story_name: Story name
    """
    return allure.story(story_name)


# ================================================================================
# Convenience Functions
# ================================================================================

def generate_allure_report(
    results_dir: str,
    output_dir: Optional[str] = None,
    open_report: bool = False
) -> bool:
    """
    Generate Allure report from results.
    
    Args:
        results_dir: Path to allure-results directory
        output_dir: Optional output directory
        open_report: Whether to open report in browser
        
    Returns:
        True if successful
    """
    processor = AllureReportProcessor(
        Path(results_dir),
        Path(output_dir) if output_dir else None
    )
    
    success = processor.generate_report()
    
    if success:
        processor.print_summary()
        processor.save_history()
        
        if open_report:
            subprocess.run(["allure", "open", str(processor.report_dir)])
    
    return success

