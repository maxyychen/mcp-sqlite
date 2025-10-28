"""Input validation utilities."""
import re
from typing import Any, Dict

VALID_TABLE_NAME = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
VALID_COLUMN_NAME = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def validate_table_name(name: str) -> bool:
    """Validate table name against SQL identifier rules."""
    return bool(VALID_TABLE_NAME.match(name))


def validate_column_name(name: str) -> bool:
    """Validate column name against SQL identifier rules."""
    return bool(VALID_COLUMN_NAME.match(name))


def validate_sql_type(sql_type: str) -> bool:
    """Validate SQLite data type.

    Supports base types and compound types like 'INTEGER PRIMARY KEY'.
    Extracts the base type and validates it.
    """
    valid_types = {
        "INTEGER",
        "TEXT",
        "REAL",
        "BLOB",
        "NUMERIC",
        "BOOLEAN",
        "DATE",
        "DATETIME",
    }

    # Extract base type (first word) to handle compound types like "INTEGER PRIMARY KEY"
    base_type = sql_type.strip().split()[0].upper()
    return base_type in valid_types
