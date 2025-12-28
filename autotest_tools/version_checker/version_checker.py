"""
================================================================================
Version Checker Tool
================================================================================

This module provides utilities for checking and comparing versions of
frontend and backend applications. Ensures test execution against compatible
versions and prevents running tests against mismatched deployments.

Features:
- Frontend version detection (from meta tags or API)
- Backend version detection (from health endpoints)
- Version compatibility validation
- CI/CD integration for version gates

================================================================================
"""

import re
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import asyncio

import httpx
from loguru import logger


# ================================================================================
# Version Models
# ================================================================================

class VersionComparisonResult(Enum):
    """Result of version comparison."""
    EQUAL = "equal"
    COMPATIBLE = "compatible"
    INCOMPATIBLE = "incompatible"
    UNKNOWN = "unknown"


@dataclass
class SemanticVersion:
    """
    Represents a semantic version (major.minor.patch).
    
    Attributes:
        major: Major version number
        minor: Minor version number
        patch: Patch version number
        prerelease: Optional prerelease identifier
        build: Optional build metadata
    """
    major: int
    minor: int
    patch: int
    prerelease: Optional[str] = None
    build: Optional[str] = None
    
    @classmethod
    def parse(cls, version_string: str) -> "SemanticVersion":
        """
        Parse version string to SemanticVersion.
        
        Args:
            version_string: Version string (e.g., "1.2.3", "v1.2.3-beta+build")
            
        Returns:
            SemanticVersion instance
            
        Raises:
            ValueError: If version string is invalid
        """
        # Remove 'v' prefix if present
        version_string = version_string.lstrip('v')
        
        # Regex for semantic versioning
        pattern = r'^(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9.-]+))?(?:\+([a-zA-Z0-9.-]+))?$'
        match = re.match(pattern, version_string)
        
        if not match:
            raise ValueError(f"Invalid version string: {version_string}")
        
        return cls(
            major=int(match.group(1)),
            minor=int(match.group(2)),
            patch=int(match.group(3)),
            prerelease=match.group(4),
            build=match.group(5),
        )
    
    def __str__(self) -> str:
        """Convert to version string."""
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            version += f"-{self.prerelease}"
        if self.build:
            version += f"+{self.build}"
        return version
    
    def __eq__(self, other: "SemanticVersion") -> bool:
        """Check equality (ignores build metadata)."""
        return (
            self.major == other.major and
            self.minor == other.minor and
            self.patch == other.patch and
            self.prerelease == other.prerelease
        )
    
    def __lt__(self, other: "SemanticVersion") -> bool:
        """Check if less than other version."""
        if self.major != other.major:
            return self.major < other.major
        if self.minor != other.minor:
            return self.minor < other.minor
        if self.patch != other.patch:
            return self.patch < other.patch
        # Prerelease versions are less than release
        if self.prerelease and not other.prerelease:
            return True
        if not self.prerelease and other.prerelease:
            return False
        return (self.prerelease or "") < (other.prerelease or "")
    
    def is_compatible_with(self, other: "SemanticVersion") -> bool:
        """
        Check if versions are compatible (same major, minor >= other).
        
        Args:
            other: Version to compare against
            
        Returns:
            True if compatible
        """
        return self.major == other.major and self.minor >= other.minor


@dataclass
class VersionInfo:
    """
    Complete version information for a service.
    
    Attributes:
        service_name: Name of the service
        version: Parsed semantic version
        version_string: Original version string
        commit_hash: Optional git commit hash
        build_date: Optional build date
        environment: Optional environment identifier
    """
    service_name: str
    version: SemanticVersion
    version_string: str
    commit_hash: Optional[str] = None
    build_date: Optional[str] = None
    environment: Optional[str] = None


# ================================================================================
# Version Detectors
# ================================================================================

class BackendVersionDetector:
    """
    Detects backend application version.
    
    Supports multiple detection methods:
    - Health endpoint (/health, /api/health)
    - Version endpoint (/version, /api/version)
    - Custom endpoints
    """
    
    DEFAULT_ENDPOINTS = [
        "/health",
        "/api/health",
        "/version",
        "/api/version",
        "/api/v1/system/version",
    ]
    
    def __init__(self, base_url: str, timeout: int = 10):
        """
        Initialize detector.
        
        Args:
            base_url: Backend base URL
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
    
    async def detect(self) -> Optional[VersionInfo]:
        """
        Detect backend version.
        
        Returns:
            VersionInfo if detected, None otherwise
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for endpoint in self.DEFAULT_ENDPOINTS:
                try:
                    response = await client.get(f"{self.base_url}{endpoint}")
                    if response.status_code == 200:
                        version_info = self._parse_response(response.json())
                        if version_info:
                            logger.info(f"Backend version detected: {version_info.version}")
                            return version_info
                except Exception as e:
                    logger.debug(f"Failed to detect from {endpoint}: {e}")
                    continue
        
        logger.warning("Could not detect backend version")
        return None
    
    def _parse_response(self, data: Dict[str, Any]) -> Optional[VersionInfo]:
        """Parse version from response data."""
        # Try common version field names
        version_fields = ["version", "app_version", "api_version", "v"]
        
        version_string = None
        for field in version_fields:
            if field in data:
                version_string = str(data[field])
                break
        
        if not version_string:
            return None
        
        try:
            version = SemanticVersion.parse(version_string)
        except ValueError:
            # If not semantic, create basic version
            version = SemanticVersion(0, 0, 0)
        
        return VersionInfo(
            service_name="backend",
            version=version,
            version_string=version_string,
            commit_hash=data.get("commit") or data.get("git_commit"),
            build_date=data.get("build_date") or data.get("built_at"),
            environment=data.get("environment") or data.get("env"),
        )


class FrontendVersionDetector:
    """
    Detects frontend application version.
    
    Supports multiple detection methods:
    - Meta tags in HTML
    - JavaScript build info
    - Version API endpoints
    """
    
    VERSION_META_PATTERNS = [
        r'<meta\s+name=["\']version["\']\s+content=["\']([^"\']+)["\']',
        r'<meta\s+name=["\']app-version["\']\s+content=["\']([^"\']+)["\']',
        r'window\.__VERSION__\s*=\s*["\']([^"\']+)["\']',
        r'"version":\s*"([^"]+)"',
    ]
    
    def __init__(self, base_url: str, timeout: int = 10):
        """
        Initialize detector.
        
        Args:
            base_url: Frontend base URL
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
    
    async def detect(self) -> Optional[VersionInfo]:
        """
        Detect frontend version.
        
        Returns:
            VersionInfo if detected, None otherwise
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                # Try to get main page
                response = await client.get(self.base_url)
                if response.status_code == 200:
                    version_string = self._extract_version(response.text)
                    if version_string:
                        try:
                            version = SemanticVersion.parse(version_string)
                        except ValueError:
                            version = SemanticVersion(0, 0, 0)
                        
                        logger.info(f"Frontend version detected: {version}")
                        return VersionInfo(
                            service_name="frontend",
                            version=version,
                            version_string=version_string,
                        )
            except Exception as e:
                logger.error(f"Failed to detect frontend version: {e}")
        
        logger.warning("Could not detect frontend version")
        return None
    
    def _extract_version(self, html: str) -> Optional[str]:
        """Extract version from HTML content."""
        for pattern in self.VERSION_META_PATTERNS:
            match = re.search(pattern, html)
            if match:
                return match.group(1)
        return None


# ================================================================================
# Version Validator
# ================================================================================

class VersionValidator:
    """
    Validates version compatibility between services.
    
    Ensures frontend and backend versions are compatible before
    running tests.
    """
    
    def __init__(
        self,
        backend_url: str,
        frontend_url: Optional[str] = None,
        expected_version: Optional[str] = None
    ):
        """
        Initialize validator.
        
        Args:
            backend_url: Backend API URL
            frontend_url: Optional frontend URL
            expected_version: Optional expected version string
        """
        self.backend_detector = BackendVersionDetector(backend_url)
        self.frontend_detector = FrontendVersionDetector(frontend_url) if frontend_url else None
        self.expected_version = SemanticVersion.parse(expected_version) if expected_version else None
    
    async def validate(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate version compatibility.
        
        Returns:
            Tuple of (is_valid, details_dict)
        """
        result = {
            "valid": True,
            "backend": None,
            "frontend": None,
            "expected": str(self.expected_version) if self.expected_version else None,
            "issues": [],
        }
        
        # Check backend version
        backend_info = await self.backend_detector.detect()
        if backend_info:
            result["backend"] = str(backend_info.version)
            
            # Check against expected
            if self.expected_version:
                if not backend_info.version.is_compatible_with(self.expected_version):
                    result["valid"] = False
                    result["issues"].append(
                        f"Backend version {backend_info.version} is not compatible with expected {self.expected_version}"
                    )
        else:
            result["valid"] = False
            result["issues"].append("Could not detect backend version")
        
        # Check frontend version if configured
        if self.frontend_detector:
            frontend_info = await self.frontend_detector.detect()
            if frontend_info:
                result["frontend"] = str(frontend_info.version)
                
                # Check frontend/backend compatibility
                if backend_info and frontend_info:
                    if frontend_info.version.major != backend_info.version.major:
                        result["valid"] = False
                        result["issues"].append(
                            f"Frontend {frontend_info.version} and Backend {backend_info.version} major versions don't match"
                        )
            else:
                result["issues"].append("Could not detect frontend version (non-blocking)")
        
        return result["valid"], result
    
    async def check_and_log(self) -> bool:
        """
        Check versions and log results.
        
        Returns:
            True if valid
        """
        is_valid, details = await self.validate()
        
        if is_valid:
            logger.info("✅ Version check passed")
            logger.info(f"   Backend: {details['backend']}")
            if details['frontend']:
                logger.info(f"   Frontend: {details['frontend']}")
        else:
            logger.error("❌ Version check failed")
            for issue in details['issues']:
                logger.error(f"   - {issue}")
        
        return is_valid


# ================================================================================
# Convenience Functions
# ================================================================================

async def check_versions(
    backend_url: str,
    frontend_url: Optional[str] = None,
    expected_version: Optional[str] = None
) -> bool:
    """
    Quick helper to check version compatibility.
    
    Args:
        backend_url: Backend API URL
        frontend_url: Optional frontend URL
        expected_version: Optional expected version
        
    Returns:
        True if versions are compatible
    """
    validator = VersionValidator(backend_url, frontend_url, expected_version)
    return await validator.check_and_log()


def compare_versions(version1: str, version2: str) -> VersionComparisonResult:
    """
    Compare two version strings.
    
    Args:
        version1: First version string
        version2: Second version string
        
    Returns:
        Comparison result
    """
    try:
        v1 = SemanticVersion.parse(version1)
        v2 = SemanticVersion.parse(version2)
        
        if v1 == v2:
            return VersionComparisonResult.EQUAL
        elif v1.is_compatible_with(v2) or v2.is_compatible_with(v1):
            return VersionComparisonResult.COMPATIBLE
        else:
            return VersionComparisonResult.INCOMPATIBLE
    except ValueError:
        return VersionComparisonResult.UNKNOWN


# ================================================================================
# CLI Entry Point (for standalone use)
# ================================================================================

async def main():
    """CLI entry point for version checking."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Version Checker")
    parser.add_argument("--backend-url", required=True, help="Backend API URL")
    parser.add_argument("--frontend-url", help="Frontend URL")
    parser.add_argument("--expected", help="Expected version")
    
    args = parser.parse_args()
    
    is_valid = await check_versions(
        backend_url=args.backend_url,
        frontend_url=args.frontend_url,
        expected_version=args.expected
    )
    
    exit(0 if is_valid else 1)


if __name__ == "__main__":
    asyncio.run(main())

