"""
================================================================================
Test Data Factory
================================================================================

This module provides factory classes for generating test data.
It supports creating valid, invalid, and edge-case data for testing.

Features:
- Random data generation with reproducible seeds
- Template-based data creation
- Relationship-aware data generation (e.g., session requires channel)
- Cleanup tracking for automatic teardown

================================================================================
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from uuid import uuid4
from datetime import datetime, timedelta
import random
import string


# ================================================================================
# Data Models
# ================================================================================

@dataclass
class GeneratedData:
    """Container for generated test data with metadata."""
    data: Dict[str, Any]
    data_type: str
    created_at: datetime = field(default_factory=datetime.now)
    cleanup_handler: Optional[Callable] = None
    
    def __post_init__(self):
        """Add unique identifier for tracking."""
        self.tracking_id = uuid4().hex[:8]


# ================================================================================
# Factory Base
# ================================================================================

class DataFactoryBase:
    """
    Base class for test data factories.
    
    Provides common functionality for generating test data
    with automatic tracking and cleanup support.
    """
    
    # Prefix for all auto-generated test data
    PREFIX = "autotest_"
    
    def __init__(self, seed: Optional[int] = None):
        """
        Initialize factory with optional random seed.
        
        Args:
            seed: Random seed for reproducible data generation
        """
        if seed is not None:
            random.seed(seed)
        
        self._generated_items: List[GeneratedData] = []
    
    def _generate_unique_id(self, prefix: str = "") -> str:
        """Generate a unique identifier."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_part = uuid4().hex[:8]
        return f"{self.PREFIX}{prefix}{timestamp}_{random_part}"
    
    def _random_string(self, length: int = 10) -> str:
        """Generate random alphanumeric string."""
        chars = string.ascii_lowercase + string.digits
        return ''.join(random.choice(chars) for _ in range(length))
    
    def _random_email(self) -> str:
        """Generate random email address."""
        return f"{self._random_string(8)}@test.example.com"
    
    def _random_url(self, path: str = "") -> str:
        """Generate random URL."""
        domain = self._random_string(8)
        return f"https://{domain}.example.com/{path}"
    
    def _random_choice(self, options: List[Any]) -> Any:
        """Select random item from list."""
        return random.choice(options)
    
    def track(self, data: Dict[str, Any], data_type: str, 
              cleanup_handler: Optional[Callable] = None) -> GeneratedData:
        """
        Track generated data for later cleanup.
        
        Args:
            data: The generated data dictionary
            data_type: Type of data (e.g., "channel", "session")
            cleanup_handler: Optional function to clean up this data
            
        Returns:
            GeneratedData object with tracking info
        """
        generated = GeneratedData(
            data=data,
            data_type=data_type,
            cleanup_handler=cleanup_handler
        )
        self._generated_items.append(generated)
        return generated
    
    def cleanup_all(self):
        """Clean up all tracked data in reverse order."""
        for item in reversed(self._generated_items):
            if item.cleanup_handler:
                try:
                    item.cleanup_handler(item.data)
                except Exception as e:
                    print(f"Cleanup failed for {item.data_type}: {e}")
        
        self._generated_items.clear()
    
    @property
    def generated_count(self) -> int:
        """Return count of generated items."""
        return len(self._generated_items)


# ================================================================================
# Channel Factory
# ================================================================================

class ChannelFactory(DataFactoryBase):
    """
    Factory for generating channel test data.
    
    Supports creating channels with various configurations
    for positive, negative, and edge case testing.
    """
    
    # Valid options for channel fields
    LOCATIONS = ["US", "SG", "DE", "JP", "GB", "FR", "AU", "CA"]
    LANGUAGES = ["en", "zh", "es", "fr", "de", "ja", "ko"]
    CATEGORIES = ["cat_001", "cat_002", "cat_003", "cat_004", "cat_005"]
    
    def create_valid(
        self,
        title: Optional[str] = None,
        location: Optional[str] = None,
        **overrides
    ) -> Dict[str, Any]:
        """
        Create valid channel data.
        
        Args:
            title: Optional custom title
            location: Optional location code
            **overrides: Additional field overrides
            
        Returns:
            Valid channel data dictionary
        """
        data = {
            "title": title or self._generate_unique_id("channel_"),
            "location": location or self._random_choice(self.LOCATIONS),
            "description": f"Auto-generated test channel at {datetime.now()}",
            "lang": self._random_choice(self.LANGUAGES),
            "category_ids": random.sample(self.CATEGORIES, k=random.randint(1, 3)),
            "cover": self._random_url("covers/default.jpg")
        }
        
        data.update(overrides)
        return data
    
    def create_minimal(self) -> Dict[str, Any]:
        """Create channel with only required fields."""
        return {
            "title": self._generate_unique_id("minimal_"),
            "location": self._random_choice(self.LOCATIONS)
        }
    
    def create_with_missing_required(self, missing_field: str) -> Dict[str, Any]:
        """
        Create channel data with a required field missing.
        
        Args:
            missing_field: Name of required field to omit
            
        Returns:
            Invalid channel data for negative testing
        """
        data = self.create_minimal()
        if missing_field in data:
            del data[missing_field]
        return data
    
    def create_with_invalid_type(
        self, 
        field: str, 
        invalid_value: Any
    ) -> Dict[str, Any]:
        """
        Create channel data with wrong type for a field.
        
        Args:
            field: Field name to set with wrong type
            invalid_value: Invalid value to use
            
        Returns:
            Invalid channel data for type testing
        """
        data = self.create_valid()
        data[field] = invalid_value
        return data
    
    def create_boundary_title(self, length: int) -> Dict[str, Any]:
        """
        Create channel with specific title length.
        
        Args:
            length: Desired title length
            
        Returns:
            Channel data with boundary title length
        """
        title = self._random_string(length)
        return self.create_valid(title=title)


# ================================================================================
# Session Factory
# ================================================================================

class SessionFactory(DataFactoryBase):
    """
    Factory for generating session test data.
    
    Sessions are always associated with a channel.
    """
    
    def create_valid(
        self,
        channel_id: str,
        title: Optional[str] = None,
        **overrides
    ) -> Dict[str, Any]:
        """
        Create valid session data.
        
        Args:
            channel_id: Parent channel ID (required)
            title: Optional custom title
            **overrides: Additional field overrides
            
        Returns:
            Valid session data dictionary
        """
        data = {
            "channel_id": channel_id,
            "title": title or self._generate_unique_id("session_"),
            "description": f"Auto-generated test session at {datetime.now()}",
            "scheduled_start": (datetime.now() + timedelta(hours=1)).isoformat()
        }
        
        data.update(overrides)
        return data
    
    def create_minimal(self, channel_id: str) -> Dict[str, Any]:
        """Create session with only required fields."""
        return {"channel_id": channel_id}
    
    def create_for_streaming(self, channel_id: str) -> Dict[str, Any]:
        """Create session data suitable for streaming tests."""
        return self.create_valid(
            channel_id=channel_id,
            title=self._generate_unique_id("stream_"),
            enable_recording=True,
            enable_captions=True
        )


# ================================================================================
# User Factory
# ================================================================================

class UserFactory(DataFactoryBase):
    """
    Factory for generating user test data.
    
    Used for authentication and permission testing.
    """
    
    ROLES = ["admin", "host", "viewer", "moderator"]
    LEVELS = [1, 2, 3, 4, 5]
    
    def create_valid(
        self,
        role: Optional[str] = None,
        **overrides
    ) -> Dict[str, Any]:
        """
        Create valid user data.
        
        Args:
            role: Optional user role
            **overrides: Additional field overrides
            
        Returns:
            Valid user data dictionary
        """
        user_id = self._generate_unique_id("user_")
        
        data = {
            "user_id": user_id,
            "username": f"test_{self._random_string(6)}",
            "email": self._random_email(),
            "role": role or self._random_choice(self.ROLES),
            "level": self._random_choice(self.LEVELS),
            "display_name": f"Test User {self._random_string(4).upper()}"
        }
        
        data.update(overrides)
        return data
    
    def create_host(self) -> Dict[str, Any]:
        """Create a host user for streaming tests."""
        return self.create_valid(role="host", level=5)
    
    def create_viewer(self) -> Dict[str, Any]:
        """Create a viewer user."""
        return self.create_valid(role="viewer", level=1)
    
    def create_admin(self) -> Dict[str, Any]:
        """Create an admin user for permission tests."""
        return self.create_valid(role="admin", level=5)


# ================================================================================
# Composite Factory
# ================================================================================

class TestDataFactory:
    """
    Composite factory providing access to all data factories.
    
    Usage:
        factory = TestDataFactory()
        channel = factory.channel.create_valid()
        session = factory.session.create_valid(channel["channel_id"])
    """
    
    def __init__(self, seed: Optional[int] = None):
        """
        Initialize all factories.
        
        Args:
            seed: Optional random seed for reproducibility
        """
        self.channel = ChannelFactory(seed)
        self.session = SessionFactory(seed)
        self.user = UserFactory(seed)
        
        self._all_factories = [self.channel, self.session, self.user]
    
    def cleanup_all(self):
        """Clean up all generated data from all factories."""
        for factory in self._all_factories:
            factory.cleanup_all()
    
    @property
    def total_generated(self) -> int:
        """Return total count of generated items across all factories."""
        return sum(f.generated_count for f in self._all_factories)


# ================================================================================
# Convenience Functions
# ================================================================================

def create_test_channel(**kwargs) -> Dict[str, Any]:
    """Quick helper to create valid channel data."""
    return ChannelFactory().create_valid(**kwargs)


def create_test_session(channel_id: str, **kwargs) -> Dict[str, Any]:
    """Quick helper to create valid session data."""
    return SessionFactory().create_valid(channel_id, **kwargs)


def create_test_user(**kwargs) -> Dict[str, Any]:
    """Quick helper to create valid user data."""
    return UserFactory().create_valid(**kwargs)

