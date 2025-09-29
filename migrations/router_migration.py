"""
Database migration script for adding router-related columns.
This script is idempotent and can be run multiple times safely.
Adapted to the existing schema used in this project.
"""

import sqlite3
import logging
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class RouterDatabaseMigration:
    """Handles database schema migrations for router functionality."""

    def __init__(self, db_path: str = "kem_validator.db"):
        self.db_path = db_path
        self.logger = logger.getChild(self.__class__.__name__)

    def migrate(self) -> bool:
        """Run all migrations. Returns True if successful."""
        try:
            self._ensure_database_exists()
            self._add_router_columns()
            self._add_idempotency_table()
            self._create_indexes()
            self.logger.info("Database migration completed successfully")
            return True
        except Exception as e:
            self.logger.error(f"Migration failed: {e}")
            return False

    def _ensure_database_exists(self):
        """Ensure the database and base tables exist (align with current schema)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Check if processing_history table exists
            cursor.execute(
                """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='processing_history'
                """
            )
            if not cursor.fetchone():
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS processing_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        file_name TEXT NOT NULL,
                        processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        validation_status TEXT,
                        total_lines INTEGER,
                        kem_lines INTEGER,
                        valid_lines INTEGER,
                        failed_lines INTEGER,
                        success_rate REAL,
                        csv_path TEXT,
                        file_hash TEXT,
                        court_code TEXT DEFAULT 'KEM'
                    )
                    """
                )
                conn.commit()
                self.logger.info("Created processing_history table (project schema)")

    def _add_router_columns(self):
        """Add router-related columns to processing_history table."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Get existing columns
            cursor.execute("PRAGMA table_info(processing_history)")
            existing_columns = {row[1] for row in cursor.fetchall()}

            # Define new columns to add
            new_columns = [
                ("routed_court_code", "TEXT"),
                ("routing_confidence", "INTEGER"),
                ("routing_explanation", "TEXT"),
                ("router_scores_json", "TEXT"),
                ("idempotency_key", "TEXT"),
                ("router_mode", "TEXT"),
                ("quarantined", "INTEGER DEFAULT 0"),
            ]

            for column_name, column_type in new_columns:
                if column_name not in existing_columns:
                    try:
                        cursor.execute(
                            f"ALTER TABLE processing_history ADD COLUMN {column_name} {column_type}"
                        )
                        conn.commit()
                        self.logger.info(f"Added column: {column_name}")
                    except sqlite3.OperationalError as e:
                        if "duplicate column name" not in str(e).lower():
                            raise

    def _add_idempotency_table(self):
        """Create table for tracking processed files (idempotency)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS processed_ledger (
                    idempotency_key TEXT PRIMARY KEY,
                    remote_path TEXT NOT NULL,
                    file_size INTEGER,
                    file_mtime TEXT,
                    court_code TEXT,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processing_status TEXT,
                    processing_id INTEGER,
                    FOREIGN KEY (processing_id) REFERENCES processing_history(id)
                )
                """
            )
            conn.commit()
            self.logger.info("Ensured processed_ledger table exists")

    def _create_indexes(self):
        """Create indexes for better query performance (resilient to column names)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Determine which timestamp column exists in processing_history
            cursor.execute("PRAGMA table_info(processing_history)")
            ph_cols = {row[1] for row in cursor.fetchall()}
            ts_col = "processed_at" if "processed_at" in ph_cols else (
                "processing_timestamp" if "processing_timestamp" in ph_cols else None
            )

            # Define indexes to create
            indexes = [
                ("idx_processing_history_court", "processing_history", "court_code"),
                ("idx_processing_history_routed", "processing_history", "routed_court_code"),
                ("idx_processing_history_idempotency", "processing_history", "idempotency_key"),
                ("idx_processed_ledger_path", "processed_ledger", "remote_path"),
            ]

            if ts_col:
                indexes.append(("idx_processing_history_ts", "processing_history", ts_col))

            # processed_ledger timestamp column is 'processed_at' here
            indexes.append(("idx_processed_ledger_ts", "processed_ledger", "processed_at"))

            for index_name, table_name, column_name in indexes:
                try:
                    cursor.execute(
                        f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({column_name})"
                    )
                except sqlite3.OperationalError:
                    # Index might already exist or column missing (skip quietly)
                    pass

            conn.commit()
            self.logger.info("Indexes created/verified")

    def check_migration_status(self) -> dict:
        """Check the current migration status of the database."""
        status = {
            'database_exists': Path(self.db_path).exists(),
            'tables': {},
            'router_columns': {},
            'indexes': []
        }

        if not status['database_exists']:
            return status

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Tables
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                status['tables'] = {t[0]: True for t in tables}

                # Router columns
                if 'processing_history' in status['tables']:
                    cursor.execute("PRAGMA table_info(processing_history)")
                    columns = cursor.fetchall()
                    column_names = {c[1] for c in columns}
                    router_columns = [
                        'routed_court_code', 'routing_confidence', 'routing_explanation',
                        'router_scores_json', 'idempotency_key', 'router_mode', 'quarantined'
                    ]
                    for col in router_columns:
                        status['router_columns'][col] = col in column_names

                # Indexes
                cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
                indexes = cursor.fetchall()
                status['indexes'] = [idx[0] for idx in indexes]

        except Exception as e:
            status['error'] = str(e)

        return status


def run_migration(db_path: str = "kem_validator.db") -> bool:
    """Convenience function to run the migration."""
    migration = RouterDatabaseMigration(db_path)
    return migration.migrate()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    if run_migration():
        print("Migration completed successfully")
        mig = RouterDatabaseMigration()
        status = mig.check_migration_status()
        print("\nMigration Status:")
        print(f"Database exists: {status['database_exists']}")
        print(f"Tables: {list(status['tables'].keys())}")
        print(f"Router columns: {sum(status['router_columns'].values())}/{len(status['router_columns'])}")
    else:
        print("Migration failed - check logs for details")

