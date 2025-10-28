"""Database connection management."""
import sqlite3
import logging
from contextlib import contextmanager
from typing import Generator
from pathlib import Path

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self, db_path: str, timeout: int = 30):
        self.db_path = Path(db_path)
        self.timeout = timeout
        self._ensure_directory()

    def _ensure_directory(self) -> None:
        """Ensure database directory exists."""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            logger.info(f"Database directory ensured: {self.db_path.parent}")
        except Exception as e:
            logger.error(f"Failed to create database directory {self.db_path.parent}: {e}")
            raise

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Get database connection with context manager."""
        try:
            conn = sqlite3.connect(str(self.db_path), timeout=self.timeout)
            conn.row_factory = sqlite3.Row  # Enable column access by name
        except Exception as e:
            logger.error(f"Failed to open database file at {self.db_path}: {e}")
            logger.error(f"Database directory exists: {self.db_path.parent.exists()}")
            logger.error(f"Database file exists: {self.db_path.exists()}")
            raise
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database operation error: {e}")
            raise
        finally:
            conn.close()
