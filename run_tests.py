#!/usr/bin/env python3
# ================================================================================
# Test Runner Script
# ================================================================================
#
# This is the main entry point for executing test suites.
# It provides a unified interface for running different types of tests
# with various configurations.
#
# Features:
#   - Run API tests (mutations, business, e2e)
#   - Run UI tests
#   - Generate Allure reports
#   - Version compatibility checking
#   - Log analysis integration
#   - CI/CD pipeline support
#
# Usage:
#   python run_tests.py --suite api --tags P0 smoke
#   python run_tests.py --suite ui --browser chromium
#   python run_tests.py --suite all --parallel 4 --allure
#
# ================================================================================

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from loguru import logger


# Configure logging
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
    level="INFO"
)


class TestRunner:
    """
    Main test runner class for orchestrating test execution.
    
    This class handles:
    - Test suite selection and execution
    - Parallel execution configuration
    - Report generation
    - Environment validation
    """
    
    def __init__(
        self,
        suite: str = "all",
        tags: List[str] = None,
        parallel: int = 1,
        browser: str = "chromium",
        headless: bool = True,
        allure_report: bool = True,
        verbose: bool = False
    ):
        """
        Initialize test runner.
        
        Args:
            suite: Test suite to run - "api", "ui", "all"
            tags: List of pytest markers to filter tests
            parallel: Number of parallel workers
            browser: Browser for UI tests - "chromium", "firefox", "webkit"
            headless: Run browser in headless mode
            allure_report: Generate Allure report
            verbose: Enable verbose output
        """
        self.suite = suite
        self.tags = tags or []
        self.parallel = parallel
        self.browser = browser
        self.headless = headless
        self.allure_report = allure_report
        self.verbose = verbose
        
        # Paths
        self.root_dir = Path(__file__).parent
        self.reports_dir = self.root_dir / "reports"
        self.allure_results = self.reports_dir / "allure-results"
        self.allure_report_dir = self.reports_dir / "allure-report"
    
    def run(self) -> int:
        """
        Execute the test run.
        
        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        logger.info("=" * 60)
        logger.info("Starting Test Execution")
        logger.info("=" * 60)
        logger.info(f"Suite: {self.suite}")
        logger.info(f"Tags: {self.tags or 'All'}")
        logger.info(f"Parallel Workers: {self.parallel}")
        if self.suite in ["ui", "all"]:
            logger.info(f"Browser: {self.browser}")
            logger.info(f"Headless: {self.headless}")
        logger.info("=" * 60)
        
        # Prepare environment
        self._prepare_environment()
        
        # Check version compatibility
        if not self._check_version_compatibility():
            logger.warning("Version compatibility check failed, continuing anyway...")
        
        # Build pytest command
        cmd = self._build_pytest_command()
        
        logger.info(f"Executing: {' '.join(cmd)}")
        
        # Execute tests
        try:
            result = subprocess.run(cmd, cwd=str(self.root_dir))
            exit_code = result.returncode
        except Exception as e:
            logger.error(f"Test execution failed: {e}")
            exit_code = 1
        
        # Generate report
        if self.allure_report:
            self._generate_allure_report()
        
        # Log analysis
        self._analyze_logs()
        
        # Print summary
        self._print_summary(exit_code)
        
        return exit_code
    
    def _prepare_environment(self) -> None:
        """Prepare test environment."""
        # Create reports directory
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.allure_results.mkdir(parents=True, exist_ok=True)
        
        # Clean previous results if needed
        logger.debug("Environment prepared")
    
    def _check_version_compatibility(self) -> bool:
        """
        Check version compatibility between test framework and target application.
        
        Returns:
            True if versions are compatible
        """
        logger.info("Checking version compatibility...")
        
        # This is a placeholder for actual version checking logic
        # In a real implementation, this would:
        # 1. Fetch frontend version from deployment
        # 2. Fetch backend version from API
        # 3. Compare with expected versions
        
        try:
            # Example version check (placeholder)
            expected_api_version = os.getenv("EXPECTED_API_VERSION", "1.0.0")
            expected_ui_version = os.getenv("EXPECTED_UI_VERSION", "1.0.0")
            
            logger.info(f"Expected API Version: {expected_api_version}")
            logger.info(f"Expected UI Version: {expected_ui_version}")
            
            return True
        except Exception as e:
            logger.warning(f"Version check failed: {e}")
            return False
    
    def _build_pytest_command(self) -> List[str]:
        """Build the pytest command with all options."""
        cmd = ["python", "-m", "pytest"]
        
        # Add test paths based on suite
        if self.suite == "api":
            cmd.append("testsuites/api_testing/tests")
        elif self.suite == "ui":
            cmd.append("testsuites/ui_testing/tests")
        else:  # all
            cmd.append("testsuites/")
        
        # Add tags filter
        if self.tags:
            marker_expr = " or ".join(self.tags)
            cmd.extend(["-m", marker_expr])
        
        # Add parallel execution
        if self.parallel > 1:
            cmd.extend(["-n", str(self.parallel)])
        
        # Add Allure
        if self.allure_report:
            cmd.extend(["--alluredir", str(self.allure_results)])
        
        # Add verbosity
        if self.verbose:
            cmd.append("-v")
        else:
            cmd.append("-q")
        
        # Add UI-specific options
        if self.suite in ["ui", "all"]:
            cmd.extend([
                f"--browser={self.browser}",
                f"--headed" if not self.headless else ""
            ])
            # Remove empty strings
            cmd = [c for c in cmd if c]
        
        return cmd
    
    def _generate_allure_report(self) -> None:
        """Generate Allure HTML report."""
        logger.info("Generating Allure report...")
        
        try:
            # Create timestamp for report
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = self.reports_dir / f"allure-report-{timestamp}"
            
            # Generate report
            subprocess.run([
                "allure", "generate",
                str(self.allure_results),
                "-o", str(report_path),
                "--clean"
            ], check=True)
            
            # Create/update latest symlink
            latest_link = self.allure_report_dir
            if latest_link.is_symlink():
                latest_link.unlink()
            elif latest_link.exists():
                import shutil
                shutil.rmtree(latest_link)
            
            latest_link.symlink_to(report_path.name)
            
            logger.info(f"Report generated: {report_path}")
            logger.info(f"Latest report: {self.allure_report_dir}")
            
        except FileNotFoundError:
            logger.warning("Allure CLI not found. Please install Allure to generate reports.")
        except Exception as e:
            logger.error(f"Failed to generate Allure report: {e}")
    
    def _analyze_logs(self) -> None:
        """Analyze test logs for insights."""
        logger.info("Analyzing test logs...")
        
        # This is a placeholder for log analysis integration
        # In a real implementation, this would:
        # 1. Fetch logs from Elasticsearch
        # 2. Analyze error patterns
        # 3. Correlate with test failures
        
        try:
            from autotest_tools.log_analyzer.es_log_search import search_logs
            
            # Example: Search for errors during test window
            # errors = search_logs(
            #     index="app-logs-*",
            #     level="ERROR",
            #     time_range="15m"
            # )
            # logger.info(f"Found {len(errors)} errors in logs")
            
            logger.debug("Log analysis complete")
        except ImportError:
            logger.debug("Log analyzer not available")
        except Exception as e:
            logger.warning(f"Log analysis failed: {e}")
    
    def _print_summary(self, exit_code: int) -> None:
        """Print test execution summary."""
        logger.info("=" * 60)
        if exit_code == 0:
            logger.info("✅ TEST EXECUTION COMPLETED SUCCESSFULLY")
        else:
            logger.error(f"❌ TEST EXECUTION FAILED (exit code: {exit_code})")
        
        if self.allure_report:
            logger.info(f"📊 Report available at: {self.allure_report_dir}")
        
        logger.info("=" * 60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Flame-Cast Automation Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all API tests
  python run_tests.py --suite api

  # Run P0 smoke tests in parallel
  python run_tests.py --suite all --tags P0 smoke --parallel 4

  # Run UI tests with visible browser
  python run_tests.py --suite ui --no-headless --browser firefox

  # Run with verbose output and generate report
  python run_tests.py --suite api --verbose --allure
        """
    )
    
    parser.add_argument(
        "--suite",
        choices=["api", "ui", "all"],
        default="all",
        help="Test suite to run (default: all)"
    )
    
    parser.add_argument(
        "--tags",
        nargs="+",
        default=[],
        help="Pytest markers to filter tests (e.g., P0 smoke regression)"
    )
    
    parser.add_argument(
        "--parallel", "-n",
        type=int,
        default=1,
        help="Number of parallel workers (default: 1)"
    )
    
    parser.add_argument(
        "--browser",
        choices=["chromium", "firefox", "webkit"],
        default="chromium",
        help="Browser for UI tests (default: chromium)"
    )
    
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Run browser in headed mode (visible)"
    )
    
    parser.add_argument(
        "--allure",
        action="store_true",
        default=True,
        help="Generate Allure report (default: True)"
    )
    
    parser.add_argument(
        "--no-allure",
        action="store_true",
        help="Disable Allure report generation"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    # Create and run test runner
    runner = TestRunner(
        suite=args.suite,
        tags=args.tags,
        parallel=args.parallel,
        browser=args.browser,
        headless=not args.no_headless,
        allure_report=not args.no_allure,
        verbose=args.verbose
    )
    
    exit_code = runner.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
