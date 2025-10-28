"""CRUD operations for SQLite database."""
from typing import Dict, Any, List, Optional
from .connection import DatabaseManager
from .query_builder import QueryBuilder
from ..utils.errors import DatabaseError


class CRUDOperations:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.query_builder = QueryBuilder()

    async def create_table(
        self, table_name: str, schema: Dict[str, str], primary_key: Optional[str] = None
    ) -> str:
        """Create a new table."""
        query = self.query_builder.build_create_table(table_name, schema, primary_key)

        with self.db_manager.get_connection() as conn:
            conn.execute(query)

        return f"Table '{table_name}' created successfully"

    async def insert_record(self, table_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a record into table."""
        query, params = self.query_builder.build_insert(table_name, data)

        with self.db_manager.get_connection() as conn:
            cursor = conn.execute(query, params)
            row_id = cursor.lastrowid

        return {"id": row_id, "data": data}

    async def query_records(
        self,
        table_name: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Query records from table."""
        query, params = self.query_builder.build_select(
            table_name, filters, limit, offset, order_by
        )

        with self.db_manager.get_connection() as conn:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

        return [dict(row) for row in rows]

    async def update_record(
        self, table_name: str, filters: Dict[str, Any], data: Dict[str, Any]
    ) -> int:
        """Update existing record(s)."""
        query, params = self.query_builder.build_update(table_name, filters, data)

        with self.db_manager.get_connection() as conn:
            cursor = conn.execute(query, params)
            rows_affected = cursor.rowcount

        return rows_affected

    async def delete_record(self, table_name: str, filters: Dict[str, Any]) -> int:
        """Delete record(s) from table."""
        query, params = self.query_builder.build_delete(table_name, filters)

        with self.db_manager.get_connection() as conn:
            cursor = conn.execute(query, params)
            rows_affected = cursor.rowcount

        return rows_affected

    async def list_tables(self) -> List[str]:
        """List all tables in the database."""
        query = self.query_builder.build_list_tables()

        with self.db_manager.get_connection() as conn:
            cursor = conn.execute(query)
            rows = cursor.fetchall()

        return [row[0] for row in rows]

    async def describe_table(self, table_name: str) -> List[Dict[str, Any]]:
        """Get detailed schema information for a table."""
        query = self.query_builder.build_describe_table(table_name)

        with self.db_manager.get_connection() as conn:
            cursor = conn.execute(query)
            rows = cursor.fetchall()

        return [dict(row) for row in rows]

    async def execute_raw_query(
        self, query: str, params: Optional[List[Any]] = None, read_only: bool = True
    ) -> Dict[str, Any]:
        """Execute custom SQL query (with safety controls)."""
        if read_only and not query.strip().upper().startswith("SELECT"):
            raise DatabaseError(
                "Only SELECT queries allowed in read-only mode. "
                "To execute write operations, set read_only=False in the arguments."
            )

        params = params or []

        with self.db_manager.get_connection() as conn:
            cursor = conn.execute(query, params)

            if query.strip().upper().startswith("SELECT"):
                rows = cursor.fetchall()
                return {"rows": [dict(row) for row in rows], "count": len(rows)}
            else:
                return {"rows_affected": cursor.rowcount}
