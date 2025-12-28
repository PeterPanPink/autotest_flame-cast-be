"""
================================================================================
MongoDB Client and Data Management Tools
================================================================================

This module provides MongoDB utilities for test automation, including:
- Connection management with SSH tunneling support
- Test data seeding from JSON files
- Automated test data cleanup
- Direct database queries for test validation

Key Features:
    - Context manager for safe connection handling
    - SSH tunnel support for remote databases
    - Bulk insert/update/delete operations
    - Query builder for common test patterns
    - Cleanup tracking to avoid accidental data loss

Usage:
    from autotest_tools.mongo_tools import MongoDBClient, DataSeeder
    
    with MongoDBClient() as client:
        db = client.get_database("test_db")
        seeder = DataSeeder(db)
        seeder.seed_from_file("baseline_data.json")

Author: Automation Team
License: MIT
================================================================================
"""

import json
import os
import re
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from loguru import logger

from autotest_tools.common import get_config, init_logger, ensure_directory


# Initialize logger
init_logger()


# ============================================================
# Data Models
# ============================================================

@dataclass
class CleanupRecord:
    """
    Tracks data that needs to be cleaned up after tests.
    """
    collection: str
    document_ids: Set[str] = field(default_factory=set)
    query_patterns: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SeedResult:
    """
    Results of a data seeding operation.
    """
    collection: str
    inserted_count: int
    inserted_ids: List[str]
    errors: List[str] = field(default_factory=list)
    
    @property
    def success(self) -> bool:
        return len(self.errors) == 0


# ============================================================
# MongoDB Client
# ============================================================

class MongoDBClient:
    """
    MongoDB client wrapper with connection management.
    
    Supports:
        - Direct connection
        - SSH tunnel connection (for remote databases)
        - Connection pooling
        - Automatic reconnection
    """
    
    def __init__(
        self,
        uri: str = None,
        database: str = None,
        ssh_host: str = None,
        ssh_user: str = None,
        ssh_key_file: str = None,
        ssh_port: int = 22,
        local_bind_port: int = 27018
    ):
        """
        Initializes the MongoDB client.
        
        Args:
            uri: MongoDB connection URI. Defaults to config value.
            database: Default database name. Defaults to config value.
            ssh_host: SSH jump host for tunneling (optional).
            ssh_user: SSH username (optional).
            ssh_key_file: Path to SSH private key (optional).
            ssh_port: SSH port (default: 22).
            local_bind_port: Local port for SSH tunnel (default: 27018).
        """
        self.uri = uri or get_config("mongodb.uri", "mongodb://localhost:27017")
        self.default_database = database or get_config("mongodb.database", "test")
        
        # SSH tunnel settings (obfuscated for demo)
        self.ssh_config = {
            "host": ssh_host or get_config("mongodb.ssh.host", ""),
            "user": ssh_user or get_config("mongodb.ssh.user", ""),
            "key_file": ssh_key_file or get_config("mongodb.ssh.key_file", ""),
            "port": ssh_port,
            "local_bind_port": local_bind_port,
        }
        
        self._client = None
        self._tunnel = None
        self._connected = False
        
        # Track created data for cleanup
        self._cleanup_records: List[CleanupRecord] = []
    
    def connect(self) -> "MongoDBClient":
        """
        Establishes connection to MongoDB.
        
        Returns:
            Self for method chaining.
        """
        try:
            # Import pymongo here to make it optional
            from pymongo import MongoClient
            
            # Setup SSH tunnel if configured
            if self.ssh_config["host"]:
                self._setup_ssh_tunnel()
                effective_uri = f"mongodb://localhost:{self.ssh_config['local_bind_port']}"
            else:
                effective_uri = self.uri
            
            self._client = MongoClient(effective_uri)
            
            # Verify connection
            self._client.admin.command("ping")
            self._connected = True
            logger.info(f"Connected to MongoDB: {self._mask_uri(effective_uri)}")
            
        except ImportError:
            logger.error("pymongo not installed. Run: pip install pymongo")
            raise
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
        
        return self
    
    def _setup_ssh_tunnel(self) -> None:
        """
        Sets up SSH tunnel for remote database access.
        """
        try:
            from sshtunnel import SSHTunnelForwarder
            
            logger.info(f"Setting up SSH tunnel via {self.ssh_config['host']}")
            
            self._tunnel = SSHTunnelForwarder(
                (self.ssh_config["host"], self.ssh_config["port"]),
                ssh_username=self.ssh_config["user"],
                ssh_pkey=self.ssh_config["key_file"],
                remote_bind_address=("localhost", 27017),
                local_bind_address=("localhost", self.ssh_config["local_bind_port"]),
            )
            self._tunnel.start()
            logger.info("SSH tunnel established")
            
        except ImportError:
            logger.error("sshtunnel not installed. Run: pip install sshtunnel")
            raise
    
    def disconnect(self) -> None:
        """
        Closes the MongoDB connection and any SSH tunnel.
        """
        if self._client:
            self._client.close()
            self._client = None
        
        if self._tunnel:
            self._tunnel.stop()
            self._tunnel = None
        
        self._connected = False
        logger.info("Disconnected from MongoDB")
    
    def get_database(self, name: str = None):
        """
        Gets a database instance.
        
        Args:
            name: Database name. Uses default if not provided.
        
        Returns:
            pymongo.database.Database instance.
        """
        if not self._connected:
            self.connect()
        
        db_name = name or self.default_database
        return self._client[db_name]
    
    def get_collection(self, collection: str, database: str = None):
        """
        Gets a collection instance.
        
        Args:
            collection: Collection name.
            database: Database name. Uses default if not provided.
        
        Returns:
            pymongo.collection.Collection instance.
        """
        db = self.get_database(database)
        return db[collection]
    
    def find_one(
        self,
        collection: str,
        query: Dict[str, Any],
        database: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Finds a single document.
        """
        coll = self.get_collection(collection, database)
        return coll.find_one(query)
    
    def find_many(
        self,
        collection: str,
        query: Dict[str, Any],
        limit: int = 100,
        database: str = None
    ) -> List[Dict[str, Any]]:
        """
        Finds multiple documents.
        """
        coll = self.get_collection(collection, database)
        return list(coll.find(query).limit(limit))
    
    def insert_one(
        self,
        collection: str,
        document: Dict[str, Any],
        database: str = None,
        track_for_cleanup: bool = True
    ) -> str:
        """
        Inserts a single document.
        
        Returns:
            Inserted document ID.
        """
        coll = self.get_collection(collection, database)
        result = coll.insert_one(document)
        inserted_id = str(result.inserted_id)
        
        if track_for_cleanup:
            self._track_for_cleanup(collection, [inserted_id])
        
        logger.debug(f"Inserted document into {collection}: {inserted_id}")
        return inserted_id
    
    def insert_many(
        self,
        collection: str,
        documents: List[Dict[str, Any]],
        database: str = None,
        track_for_cleanup: bool = True
    ) -> List[str]:
        """
        Inserts multiple documents.
        
        Returns:
            List of inserted document IDs.
        """
        coll = self.get_collection(collection, database)
        result = coll.insert_many(documents)
        inserted_ids = [str(id) for id in result.inserted_ids]
        
        if track_for_cleanup:
            self._track_for_cleanup(collection, inserted_ids)
        
        logger.debug(f"Inserted {len(inserted_ids)} documents into {collection}")
        return inserted_ids
    
    def delete_many(
        self,
        collection: str,
        query: Dict[str, Any],
        database: str = None
    ) -> int:
        """
        Deletes multiple documents.
        
        Returns:
            Number of deleted documents.
        """
        coll = self.get_collection(collection, database)
        result = coll.delete_many(query)
        logger.debug(f"Deleted {result.deleted_count} documents from {collection}")
        return result.deleted_count
    
    def _track_for_cleanup(self, collection: str, document_ids: List[str]) -> None:
        """
        Tracks inserted documents for later cleanup.
        """
        # Find or create cleanup record for this collection
        record = None
        for r in self._cleanup_records:
            if r.collection == collection:
                record = r
                break
        
        if record is None:
            record = CleanupRecord(collection=collection)
            self._cleanup_records.append(record)
        
        record.document_ids.update(document_ids)
    
    def cleanup_tracked_data(self) -> Dict[str, int]:
        """
        Cleans up all tracked test data.
        
        Returns:
            Dictionary of collection -> deleted count.
        """
        from bson import ObjectId
        
        results = {}
        
        for record in self._cleanup_records:
            if record.document_ids:
                coll = self.get_collection(record.collection)
                ids = [ObjectId(id) for id in record.document_ids if ObjectId.is_valid(id)]
                
                if ids:
                    result = coll.delete_many({"_id": {"$in": ids}})
                    results[record.collection] = result.deleted_count
                    logger.info(f"Cleaned up {result.deleted_count} documents from {record.collection}")
        
        self._cleanup_records.clear()
        return results
    
    def _mask_uri(self, uri: str) -> str:
        """
        Masks sensitive parts of the MongoDB URI.
        """
        return re.sub(r"://[^@]+@", "://****:****@", uri)
    
    def __enter__(self) -> "MongoDBClient":
        return self.connect()
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.cleanup_tracked_data()
        self.disconnect()


# ============================================================
# Data Seeder
# ============================================================

class DataSeeder:
    """
    Seeds test data into MongoDB collections.
    """
    
    def __init__(self, client: MongoDBClient):
        """
        Initializes the seeder.
        
        Args:
            client: MongoDBClient instance.
        """
        self.client = client
    
    def seed_from_file(
        self,
        filepath: str,
        collection: str = None,
        clear_existing: bool = False
    ) -> SeedResult:
        """
        Seeds data from a JSON file.
        
        Args:
            filepath: Path to JSON file with seed data.
            collection: Target collection. Defaults to filename without extension.
            clear_existing: Whether to clear existing data first.
        
        Returns:
            SeedResult with operation details.
        """
        path = Path(filepath)
        
        if not path.exists():
            return SeedResult(
                collection=collection or "",
                inserted_count=0,
                inserted_ids=[],
                errors=[f"File not found: {filepath}"]
            )
        
        collection = collection or path.stem
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Handle both single document and array
            if isinstance(data, dict):
                data = [data]
            
            if clear_existing:
                self.client.delete_many(collection, {})
            
            inserted_ids = self.client.insert_many(collection, data)
            
            return SeedResult(
                collection=collection,
                inserted_count=len(inserted_ids),
                inserted_ids=inserted_ids,
            )
            
        except Exception as e:
            logger.error(f"Failed to seed from {filepath}: {e}")
            return SeedResult(
                collection=collection,
                inserted_count=0,
                inserted_ids=[],
                errors=[str(e)]
            )
    
    def seed_from_directory(
        self,
        directory: str,
        file_pattern: str = "*.json"
    ) -> List[SeedResult]:
        """
        Seeds data from all JSON files in a directory.
        
        Args:
            directory: Directory containing JSON files.
            file_pattern: Glob pattern for files to seed.
        
        Returns:
            List of SeedResult for each file.
        """
        results = []
        path = Path(directory)
        
        for file in path.glob(file_pattern):
            result = self.seed_from_file(str(file))
            results.append(result)
        
        total_inserted = sum(r.inserted_count for r in results)
        logger.info(f"Seeded {total_inserted} documents from {len(results)} files")
        
        return results


# ============================================================
# Data Cleaner
# ============================================================

class DataCleaner:
    """
    Cleans up test data from MongoDB.
    """
    
    # Default patterns for test data identification
    TEST_DATA_PATTERNS = {
        "prefix": ["test_", "autotest_", "e2e_"],
        "suffix": ["_test", "_autotest"],
    }
    
    def __init__(self, client: MongoDBClient):
        """
        Initializes the cleaner.
        
        Args:
            client: MongoDBClient instance.
        """
        self.client = client
    
    def clean_by_pattern(
        self,
        collection: str,
        field: str,
        patterns: List[str] = None,
        dry_run: bool = True
    ) -> int:
        """
        Cleans documents matching test data patterns.
        
        Args:
            collection: Collection to clean.
            field: Field to match patterns against.
            patterns: List of regex patterns. Defaults to test data patterns.
            dry_run: If True, only count matches without deleting.
        
        Returns:
            Number of documents matched/deleted.
        """
        if patterns is None:
            patterns = [
                f"^{p}" for p in self.TEST_DATA_PATTERNS["prefix"]
            ] + [
                f"{s}$" for s in self.TEST_DATA_PATTERNS["suffix"]
            ]
        
        # Build regex query
        regex_conditions = [
            {field: {"$regex": pattern, "$options": "i"}}
            for pattern in patterns
        ]
        query = {"$or": regex_conditions}
        
        coll = self.client.get_collection(collection)
        count = coll.count_documents(query)
        
        if dry_run:
            logger.info(f"[DRY RUN] Would delete {count} documents from {collection}")
        else:
            result = coll.delete_many(query)
            logger.info(f"Deleted {result.deleted_count} documents from {collection}")
            return result.deleted_count
        
        return count
    
    def clean_by_age(
        self,
        collection: str,
        timestamp_field: str = "created_at",
        max_age_hours: int = 24,
        additional_filter: Dict[str, Any] = None,
        dry_run: bool = True
    ) -> int:
        """
        Cleans documents older than specified age.
        
        Args:
            collection: Collection to clean.
            timestamp_field: Field containing timestamp.
            max_age_hours: Maximum age in hours.
            additional_filter: Additional query filter.
            dry_run: If True, only count matches without deleting.
        
        Returns:
            Number of documents matched/deleted.
        """
        from datetime import timedelta
        
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        query = {timestamp_field: {"$lt": cutoff_time}}
        
        if additional_filter:
            query.update(additional_filter)
        
        coll = self.client.get_collection(collection)
        count = coll.count_documents(query)
        
        if dry_run:
            logger.info(f"[DRY RUN] Would delete {count} old documents from {collection}")
        else:
            result = coll.delete_many(query)
            logger.info(f"Deleted {result.deleted_count} old documents from {collection}")
            return result.deleted_count
        
        return count


# ============================================================
# CLI Interface
# ============================================================

def main():
    """
    CLI entry point for MongoDB tools.
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="MongoDB Test Data Tools")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Seed command
    seed_parser = subparsers.add_parser("seed", help="Seed data from file")
    seed_parser.add_argument("file", help="JSON file to seed")
    seed_parser.add_argument("--collection", help="Target collection")
    seed_parser.add_argument("--clear", action="store_true", help="Clear existing data")
    
    # Clean command
    clean_parser = subparsers.add_parser("clean", help="Clean test data")
    clean_parser.add_argument("collection", help="Collection to clean")
    clean_parser.add_argument("--field", default="name", help="Field to match patterns")
    clean_parser.add_argument("--dry-run", action="store_true", help="Preview only")
    
    args = parser.parse_args()
    
    with MongoDBClient() as client:
        if args.command == "seed":
            seeder = DataSeeder(client)
            result = seeder.seed_from_file(
                args.file,
                collection=args.collection,
                clear_existing=args.clear
            )
            logger.info(f"Seeded {result.inserted_count} documents")
            
        elif args.command == "clean":
            cleaner = DataCleaner(client)
            count = cleaner.clean_by_pattern(
                args.collection,
                args.field,
                dry_run=args.dry_run
            )
            logger.info(f"{'Would delete' if args.dry_run else 'Deleted'} {count} documents")


if __name__ == "__main__":
    main()

