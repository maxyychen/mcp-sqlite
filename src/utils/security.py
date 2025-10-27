"""Security utilities for SQL injection prevention."""
from typing import Any, Dict, List
from .validation import validate_table_name, validate_column_name
from .errors import SecurityError


def sanitize_identifier(identifier: str, identifier_type: str = "table") -> str:
    """Sanitize and validate SQL identifiers."""
    validator = validate_table_name if identifier_type == "table" else validate_column_name

    if not validator(identifier):
        raise SecurityError(f"Invalid {identifier_type} name: {identifier}")

    return identifier


def build_parameterized_query(
    base_query: str, params: Dict[str, Any]
) -> tuple[str, List[Any]]:
    """Build parameterized query safely."""
    # Implementation for safe parameterized queries
    param_values = []
    # Convert dict params to positional params for sqlite3
    for key, value in params.items():
        param_values.append(value)
    return base_query, param_values
