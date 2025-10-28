"""Safe SQL query builder."""
from typing import Dict, Any, List, Optional
from ..utils.security import sanitize_identifier
from ..utils.validation import validate_sql_type


class QueryBuilder:
    @staticmethod
    def build_create_table(
        table_name: str, schema: Dict[str, str], primary_key: Optional[str] = None
    ) -> str:
        """Build CREATE TABLE query."""
        table_name = sanitize_identifier(table_name, "table")

        columns = []
        for col_name, col_type in schema.items():
            col_name = sanitize_identifier(col_name, "column")
            if not validate_sql_type(col_type):
                raise ValueError(f"Invalid SQL type: {col_type}")

            col_def = f"{col_name} {col_type.upper()}"
            # Only add PRIMARY KEY if not already in the type string
            if col_name == primary_key and "PRIMARY KEY" not in col_type.upper():
                col_def += " PRIMARY KEY"
            columns.append(col_def)

        return f"CREATE TABLE {table_name} ({', '.join(columns)})"

    @staticmethod
    def build_insert(table_name: str, data: Dict[str, Any]) -> tuple[str, List[Any]]:
        """Build INSERT query with parameters."""
        table_name = sanitize_identifier(table_name, "table")

        columns = [sanitize_identifier(col, "column") for col in data.keys()]
        placeholders = ["?" for _ in columns]
        values = list(data.values())

        query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
        return query, values

    @staticmethod
    def build_select(
        table_name: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: Optional[str] = None,
    ) -> tuple[str, List[Any]]:
        """Build SELECT query with parameters."""
        table_name = sanitize_identifier(table_name, "table")
        query = f"SELECT * FROM {table_name}"
        params = []

        if filters:
            where_clauses = []
            for col, val in filters.items():
                col = sanitize_identifier(col, "column")
                where_clauses.append(f"{col} = ?")
                params.append(val)
            query += f" WHERE {' AND '.join(where_clauses)}"

        if order_by:
            order_by = sanitize_identifier(order_by, "column")
            query += f" ORDER BY {order_by}"

        if limit:
            query += f" LIMIT {int(limit)}"

        if offset:
            query += f" OFFSET {int(offset)}"

        return query, params

    @staticmethod
    def build_update(
        table_name: str, filters: Dict[str, Any], data: Dict[str, Any]
    ) -> tuple[str, List[Any]]:
        """Build UPDATE query with parameters."""
        table_name = sanitize_identifier(table_name, "table")

        set_clauses = []
        params = []

        for col, val in data.items():
            col = sanitize_identifier(col, "column")
            set_clauses.append(f"{col} = ?")
            params.append(val)

        query = f"UPDATE {table_name} SET {', '.join(set_clauses)}"

        if filters:
            where_clauses = []
            for col, val in filters.items():
                col = sanitize_identifier(col, "column")
                where_clauses.append(f"{col} = ?")
                params.append(val)
            query += f" WHERE {' AND '.join(where_clauses)}"

        return query, params

    @staticmethod
    def build_delete(table_name: str, filters: Dict[str, Any]) -> tuple[str, List[Any]]:
        """Build DELETE query with parameters."""
        table_name = sanitize_identifier(table_name, "table")

        query = f"DELETE FROM {table_name}"
        params = []

        if filters:
            where_clauses = []
            for col, val in filters.items():
                col = sanitize_identifier(col, "column")
                where_clauses.append(f"{col} = ?")
                params.append(val)
            query += f" WHERE {' AND '.join(where_clauses)}"

        return query, params

    @staticmethod
    def build_list_tables() -> str:
        """Build query to list all tables."""
        return "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"

    @staticmethod
    def build_describe_table(table_name: str) -> str:
        """Build query to describe table schema."""
        table_name = sanitize_identifier(table_name, "table")
        return f"PRAGMA table_info({table_name})"
