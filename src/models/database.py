"""Database connection and management for Anime Tracker"""

import logging
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


class Database:
    """Manages SQLite database access with one connection per thread.

    sqlite3 connections cannot be shared across threads. Each thread that
    touches this Database transparently gets its own connection, so services
    can be called from worker threads without per-call-site workarounds.
    """

    SCHEMA_VERSION = 2

    def __init__(self, db_path: Path):
        """Initialize database

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self._local = threading.local()

    @property
    def connection(self) -> Optional[sqlite3.Connection]:
        """The current thread's connection, or None if not connected"""
        return getattr(self._local, "connection", None)

    def connect(self):
        """Establish a database connection for the current thread"""
        try:
            connection = sqlite3.connect(
                str(self.db_path), detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
            )
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            self._local.connection = connection
            logger.info(
                f"Connected to database: {self.db_path} "
                f"(thread {threading.current_thread().name})"
            )
        except sqlite3.Error as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def disconnect(self):
        """Close the current thread's database connection.

        Connections belonging to other threads close when their thread's
        Database usage is released (sqlite3 forbids cross-thread close).
        """
        if self.connection:
            self.connection.close()
            self._local.connection = None
            logger.info("Disconnected from database")

    @contextmanager
    def get_cursor(self):
        """Context manager for a cursor on the current thread's connection

        Yields:
            sqlite3.Cursor: Database cursor
        """
        if not self.connection:
            self.connect()

        connection = self.connection
        cursor = connection.cursor()
        try:
            yield cursor
            connection.commit()
        except sqlite3.Error as e:
            connection.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            cursor.close()

    def initialize(self):
        """Initialize database with schema"""
        if not self.connection:
            self.connect()

        # Check if database needs initialization
        if self._needs_initialization():
            self._create_schema()
            # The base schema predates v2: sync_status/last_mal_sync and the
            # sync_queue table only exist in the v2 migration. Run it (it is
            # idempotent) so fresh installs match upgraded ones.
            self._migrate_to_v2()
            self._set_schema_version()
            logger.info("Database initialized with schema")
        else:
            # Check for migrations
            current_version = self._get_schema_version()
            if current_version < self.SCHEMA_VERSION:
                self._migrate_schema(current_version)

    def _needs_initialization(self) -> bool:
        """Check if database needs initialization

        Returns:
            bool: True if database needs initialization
        """
        with self.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='anime'
            """
            )
            return cursor.fetchone() is None

    def _create_schema(self):
        """Create database schema"""
        schema_sql = """
        -- Main anime table
        CREATE TABLE IF NOT EXISTS anime (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mal_id INTEGER UNIQUE,
            title TEXT NOT NULL,
            title_english TEXT,
            title_japanese TEXT,
            image_url TEXT,
            image_cached BLOB,
            episodes_watched INTEGER DEFAULT 0 CHECK(episodes_watched >= 0),
            total_episodes INTEGER CHECK(total_episodes > 0 OR total_episodes IS NULL),
            status TEXT NOT NULL DEFAULT 'Plan to Watch'
                CHECK(status IN ('Watching', 'Completed', 'On Hold', 'Dropped', 'Plan to Watch')),
            score INTEGER CHECK(score >= 0 AND score <= 10),
            synopsis TEXT,
            genres TEXT,  -- JSON array
            studio TEXT,
            aired_from DATE,
            aired_to DATE,
            season TEXT,
            year INTEGER,
            source TEXT,
            rating TEXT,  -- TV-14, R, etc.
            notes TEXT,
            date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            date_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            mal_sync_date TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Create indexes for frequently queried columns
        CREATE INDEX IF NOT EXISTS idx_anime_status ON anime(status);
        CREATE INDEX IF NOT EXISTS idx_anime_title ON anime(title);
        CREATE INDEX IF NOT EXISTS idx_anime_mal_id ON anime(mal_id);

        -- Sync history table
        CREATE TABLE IF NOT EXISTS sync_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sync_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sync_type TEXT CHECK(sync_type IN ('manual', 'auto', 'import')),
            items_synced INTEGER DEFAULT 0,
            items_failed INTEGER DEFAULT 0,
            status TEXT,
            error_message TEXT
        );

        -- Settings table
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Watch history table (optional feature)
        CREATE TABLE IF NOT EXISTS watch_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            anime_id INTEGER NOT NULL,
            episodes_watched INTEGER NOT NULL,
            date_watched DATE DEFAULT CURRENT_DATE,
            FOREIGN KEY (anime_id) REFERENCES anime(id) ON DELETE CASCADE
        );

        -- Schema version table
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Trigger to update the updated_at timestamp
        CREATE TRIGGER IF NOT EXISTS update_anime_timestamp
        AFTER UPDATE ON anime
        BEGIN
            UPDATE anime SET updated_at = CURRENT_TIMESTAMP
            WHERE id = NEW.id;
        END;
        """

        with self.get_cursor() as cursor:
            cursor.executescript(schema_sql)

    def _get_schema_version(self) -> int:
        """Get current schema version

        Returns:
            int: Current schema version
        """
        with self.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT MAX(version) as version FROM schema_version
            """
            )
            result = cursor.fetchone()
            return result["version"] if result and result["version"] else 0

    def _set_schema_version(self):
        """Set current schema version"""
        with self.get_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO schema_version (version) VALUES (?)
            """,
                (self.SCHEMA_VERSION,),
            )

    def _migrate_schema(self, from_version: int):
        """Migrate database schema

        Args:
            from_version: Current schema version
        """
        logger.info(f"Migrating schema from version {from_version} to {self.SCHEMA_VERSION}")

        # Add migration logic here for future versions
        if from_version < 2:
            self._migrate_to_v2()

        self._set_schema_version()

    def _migrate_to_v2(self):
        """Migrate to schema version 2 - Add sync support fields"""
        logger.info("Applying migration to schema v2: Adding sync support")

        with self.get_cursor() as cursor:
            # Add sync_status to anime table if it doesn't exist
            cursor.execute(
                """
                SELECT COUNT(*) as count FROM pragma_table_info('anime')
                WHERE name='sync_status'
            """
            )

            if cursor.fetchone()["count"] == 0:
                cursor.execute(
                    """
                    ALTER TABLE anime
                    ADD COLUMN sync_status TEXT DEFAULT 'local_only'
                    CHECK(sync_status IN ('local_only', 'synced', 'pending_upload', 'pending_download', 'conflict'))
                """
                )
                logger.info("Added sync_status column to anime table")

            # Add last_mal_sync column if it doesn't exist
            cursor.execute(
                """
                SELECT COUNT(*) as count FROM pragma_table_info('anime')
                WHERE name='last_mal_sync'
            """
            )

            if cursor.fetchone()["count"] == 0:
                cursor.execute(
                    """
                    ALTER TABLE anime
                    ADD COLUMN last_mal_sync TIMESTAMP
                """
                )
                logger.info("Added last_mal_sync column to anime table")

            # Create sync_queue table for offline operations
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS sync_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    anime_id INTEGER NOT NULL,
                    operation TEXT NOT NULL CHECK(operation IN ('create', 'update', 'delete')),
                    data TEXT,  -- JSON data for the operation
                    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'processing', 'completed', 'failed')),
                    retry_count INTEGER DEFAULT 0,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed_at TIMESTAMP,
                    FOREIGN KEY (anime_id) REFERENCES anime(id) ON DELETE CASCADE
                )
            """
            )

            # Create index for sync_queue
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_sync_queue_status
                ON sync_queue(status)
            """
            )

            logger.info("Schema migration to v2 completed")

    def fetchone(self, query: str, params: Optional[Tuple] = None) -> Optional[sqlite3.Row]:
        """Fetch one result

        Args:
            query: SQL query to execute
            params: Query parameters

        Returns:
            Optional[sqlite3.Row]: Query result or None
        """
        with self.get_cursor() as cursor:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.fetchone()

    def fetchall(self, query: str, params: Optional[Tuple] = None) -> List[sqlite3.Row]:
        """Fetch all results

        Args:
            query: SQL query to execute
            params: Query parameters

        Returns:
            List[sqlite3.Row]: Query results
        """
        with self.get_cursor() as cursor:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.fetchall()

    def backup(self, backup_path: Path):
        """Create database backup

        Args:
            backup_path: Path for backup file
        """
        if not self.connection:
            self.connect()

        backup_conn = sqlite3.connect(str(backup_path))
        with backup_conn:
            self.connection.backup(backup_conn)
        backup_conn.close()
        logger.info(f"Database backed up to: {backup_path}")

    def vacuum(self):
        """Optimize database file size"""
        if not self.connection:
            self.connect()

        self.connection.execute("VACUUM")
        logger.info("Database vacuumed")

    def get_stats(self) -> dict:
        """Get database statistics

        Returns:
            dict: Database statistics
        """
        stats = {}

        with self.get_cursor() as cursor:
            # Get anime count
            cursor.execute("SELECT COUNT(*) as count FROM anime")
            stats["total_anime"] = cursor.fetchone()["count"]

            # Get anime by status
            cursor.execute(
                """
                SELECT status, COUNT(*) as count
                FROM anime
                GROUP BY status
            """
            )
            stats["by_status"] = {row["status"]: row["count"] for row in cursor.fetchall()}

            # Get database size
            cursor.execute(
                "SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()"
            )
            stats["db_size"] = cursor.fetchone()["size"]

        return stats
