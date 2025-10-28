"""Unit tests for CRUD operations."""
import pytest
import tempfile
import os
from pathlib import Path

from src.database.connection import DatabaseManager
from src.database.crud_operations import CRUDOperations
from src.utils.errors import DatabaseError


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".db", delete=False) as f:
        db_path = f.name

    yield db_path

    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def db_manager(temp_db):
    """Create DatabaseManager instance with temp database."""
    return DatabaseManager(temp_db)


@pytest.fixture
def crud_ops(db_manager):
    """Create CRUDOperations instance."""
    return CRUDOperations(db_manager)


class TestCreateTable:
    """Test create_table functionality."""

    @pytest.mark.asyncio
    async def test_create_simple_table(self, crud_ops):
        """Test creating a simple table."""
        schema = {"id": "INTEGER", "name": "TEXT", "email": "TEXT"}
        result = await crud_ops.create_table("users", schema, "id")

        assert "created successfully" in result
        tables = await crud_ops.list_tables()
        assert "users" in tables

    @pytest.mark.asyncio
    async def test_create_table_with_compound_type(self, crud_ops):
        """Test creating table with compound type like 'INTEGER PRIMARY KEY'."""
        schema = {
            "id": "INTEGER PRIMARY KEY",
            "name": "TEXT",
            "email": "TEXT"
        }
        result = await crud_ops.create_table("users_compound", schema)

        assert "created successfully" in result
        tables = await crud_ops.list_tables()
        assert "users_compound" in tables

        # Verify schema
        description = await crud_ops.describe_table("users_compound")
        assert len(description) == 3
        # Check that primary key was applied
        id_col = next((col for col in description if col["name"] == "id"), None)
        assert id_col is not None
        assert id_col["pk"] == 1  # SQLite uses 1 for primary key columns

    @pytest.mark.asyncio
    async def test_create_table_without_primary_key(self, crud_ops):
        """Test creating table without primary key."""
        schema = {"name": "TEXT", "description": "TEXT"}
        result = await crud_ops.create_table("items", schema)

        assert "created successfully" in result
        tables = await crud_ops.list_tables()
        assert "items" in tables

    @pytest.mark.asyncio
    async def test_create_table_with_multiple_types(self, crud_ops):
        """Test creating table with multiple data types."""
        schema = {
            "id": "INTEGER",
            "name": "TEXT",
            "price": "REAL",
            "quantity": "INTEGER",
            "active": "BOOLEAN"
        }
        result = await crud_ops.create_table("products", schema, "id")

        assert "created successfully" in result
        description = await crud_ops.describe_table("products")
        assert len(description) == 5


class TestInsertRecord:
    """Test insert_record functionality."""

    @pytest.mark.asyncio
    async def test_insert_single_record(self, crud_ops):
        """Test inserting a single record."""
        # Create table first
        schema = {"id": "INTEGER", "name": "TEXT", "email": "TEXT"}
        await crud_ops.create_table("users", schema, "id")

        # Insert record
        data = {"id": 1, "name": "John Doe", "email": "john@example.com"}
        result = await crud_ops.insert_record("users", data)

        assert result["id"] == 1
        assert result["data"] == data

    @pytest.mark.asyncio
    async def test_insert_multiple_records(self, crud_ops):
        """Test inserting multiple records."""
        schema = {"id": "INTEGER", "name": "TEXT"}
        await crud_ops.create_table("items", schema, "id")

        # Insert multiple records
        for i in range(1, 4):
            data = {"id": i, "name": f"Item {i}"}
            result = await crud_ops.insert_record("items", data)
            assert result["id"] == i

        # Verify all inserted
        records = await crud_ops.query_records("items")
        assert len(records) == 3

    @pytest.mark.asyncio
    async def test_insert_with_null_values(self, crud_ops):
        """Test inserting records with null values."""
        schema = {"id": "INTEGER", "name": "TEXT", "description": "TEXT"}
        await crud_ops.create_table("tasks", schema, "id")

        data = {"id": 1, "name": "Task 1"}  # description is null
        result = await crud_ops.insert_record("tasks", data)
        assert result["id"] == 1


class TestQueryRecords:
    """Test query_records functionality."""

    @pytest.mark.asyncio
    async def test_query_all_records(self, crud_ops):
        """Test querying all records."""
        schema = {"id": "INTEGER", "name": "TEXT"}
        await crud_ops.create_table("users", schema, "id")

        # Insert test data
        for i in range(1, 6):
            await crud_ops.insert_record("users", {"id": i, "name": f"User {i}"})

        # Query all
        records = await crud_ops.query_records("users")
        assert len(records) == 5

    @pytest.mark.asyncio
    async def test_query_with_filters(self, crud_ops):
        """Test querying with filters."""
        schema = {"id": "INTEGER", "name": "TEXT", "age": "INTEGER"}
        await crud_ops.create_table("users", schema, "id")

        # Insert test data
        await crud_ops.insert_record("users", {"id": 1, "name": "Alice", "age": 25})
        await crud_ops.insert_record("users", {"id": 2, "name": "Bob", "age": 30})
        await crud_ops.insert_record("users", {"id": 3, "name": "Charlie", "age": 25})

        # Query with filter
        records = await crud_ops.query_records("users", filters={"age": 25})
        assert len(records) == 2
        assert all(r["age"] == 25 for r in records)

    @pytest.mark.asyncio
    async def test_query_with_limit(self, crud_ops):
        """Test querying with limit."""
        schema = {"id": "INTEGER", "name": "TEXT"}
        await crud_ops.create_table("items", schema, "id")

        # Insert test data
        for i in range(1, 11):
            await crud_ops.insert_record("items", {"id": i, "name": f"Item {i}"})

        # Query with limit
        records = await crud_ops.query_records("items", limit=5)
        assert len(records) == 5

    @pytest.mark.asyncio
    async def test_query_with_offset(self, crud_ops):
        """Test querying with offset."""
        schema = {"id": "INTEGER", "name": "TEXT"}
        await crud_ops.create_table("items", schema, "id")

        # Insert test data
        for i in range(1, 11):
            await crud_ops.insert_record("items", {"id": i, "name": f"Item {i}"})

        # Query with offset
        records = await crud_ops.query_records("items", limit=5, offset=5)
        assert len(records) == 5
        assert records[0]["id"] == 6

    @pytest.mark.asyncio
    async def test_query_with_order_by(self, crud_ops):
        """Test querying with order_by."""
        schema = {"id": "INTEGER", "name": "TEXT", "score": "INTEGER"}
        await crud_ops.create_table("scores", schema, "id")

        # Insert test data in random order
        await crud_ops.insert_record("scores", {"id": 1, "name": "Alice", "score": 85})
        await crud_ops.insert_record("scores", {"id": 2, "name": "Bob", "score": 92})
        await crud_ops.insert_record("scores", {"id": 3, "name": "Charlie", "score": 78})

        # Query ordered by score
        records = await crud_ops.query_records("scores", order_by="score")
        assert records[0]["score"] == 78
        assert records[1]["score"] == 85
        assert records[2]["score"] == 92


class TestUpdateRecord:
    """Test update_record functionality."""

    @pytest.mark.asyncio
    async def test_update_single_record(self, crud_ops):
        """Test updating a single record."""
        schema = {"id": "INTEGER", "name": "TEXT", "email": "TEXT"}
        await crud_ops.create_table("users", schema, "id")

        # Insert record
        await crud_ops.insert_record("users", {"id": 1, "name": "John", "email": "john@old.com"})

        # Update record
        rows_affected = await crud_ops.update_record(
            "users",
            filters={"id": 1},
            data={"email": "john@new.com"}
        )

        assert rows_affected == 1

        # Verify update
        records = await crud_ops.query_records("users", filters={"id": 1})
        assert records[0]["email"] == "john@new.com"

    @pytest.mark.asyncio
    async def test_update_multiple_records(self, crud_ops):
        """Test updating multiple records."""
        schema = {"id": "INTEGER", "status": "TEXT", "category": "TEXT"}
        await crud_ops.create_table("tasks", schema, "id")

        # Insert records
        await crud_ops.insert_record("tasks", {"id": 1, "status": "pending", "category": "work"})
        await crud_ops.insert_record("tasks", {"id": 2, "status": "pending", "category": "work"})
        await crud_ops.insert_record("tasks", {"id": 3, "status": "pending", "category": "personal"})

        # Update multiple records
        rows_affected = await crud_ops.update_record(
            "tasks",
            filters={"category": "work"},
            data={"status": "completed"}
        )

        assert rows_affected == 2

        # Verify updates
        completed = await crud_ops.query_records("tasks", filters={"status": "completed"})
        assert len(completed) == 2

    @pytest.mark.asyncio
    async def test_update_nonexistent_record(self, crud_ops):
        """Test updating a nonexistent record."""
        schema = {"id": "INTEGER", "name": "TEXT"}
        await crud_ops.create_table("users", schema, "id")

        # Try to update nonexistent record
        rows_affected = await crud_ops.update_record(
            "users",
            filters={"id": 999},
            data={"name": "Ghost"}
        )

        assert rows_affected == 0


class TestDeleteRecord:
    """Test delete_record functionality."""

    @pytest.mark.asyncio
    async def test_delete_single_record(self, crud_ops):
        """Test deleting a single record."""
        schema = {"id": "INTEGER", "name": "TEXT"}
        await crud_ops.create_table("users", schema, "id")

        # Insert records
        await crud_ops.insert_record("users", {"id": 1, "name": "User 1"})
        await crud_ops.insert_record("users", {"id": 2, "name": "User 2"})

        # Delete one record
        rows_affected = await crud_ops.delete_record("users", filters={"id": 1})

        assert rows_affected == 1

        # Verify deletion
        records = await crud_ops.query_records("users")
        assert len(records) == 1
        assert records[0]["id"] == 2

    @pytest.mark.asyncio
    async def test_delete_multiple_records(self, crud_ops):
        """Test deleting multiple records."""
        schema = {"id": "INTEGER", "category": "TEXT"}
        await crud_ops.create_table("items", schema, "id")

        # Insert records
        await crud_ops.insert_record("items", {"id": 1, "category": "A"})
        await crud_ops.insert_record("items", {"id": 2, "category": "A"})
        await crud_ops.insert_record("items", {"id": 3, "category": "B"})

        # Delete multiple records
        rows_affected = await crud_ops.delete_record("items", filters={"category": "A"})

        assert rows_affected == 2

        # Verify deletion
        records = await crud_ops.query_records("items")
        assert len(records) == 1
        assert records[0]["category"] == "B"

    @pytest.mark.asyncio
    async def test_delete_nonexistent_record(self, crud_ops):
        """Test deleting a nonexistent record."""
        schema = {"id": "INTEGER", "name": "TEXT"}
        await crud_ops.create_table("users", schema, "id")

        # Try to delete nonexistent record
        rows_affected = await crud_ops.delete_record("users", filters={"id": 999})

        assert rows_affected == 0


class TestListTables:
    """Test list_tables functionality."""

    @pytest.mark.asyncio
    async def test_list_empty_database(self, crud_ops):
        """Test listing tables in empty database."""
        tables = await crud_ops.list_tables()
        assert isinstance(tables, list)

    @pytest.mark.asyncio
    async def test_list_multiple_tables(self, crud_ops):
        """Test listing multiple tables."""
        # Create multiple tables
        await crud_ops.create_table("users", {"id": "INTEGER", "name": "TEXT"}, "id")
        await crud_ops.create_table("products", {"id": "INTEGER", "name": "TEXT"}, "id")
        await crud_ops.create_table("orders", {"id": "INTEGER", "total": "REAL"}, "id")

        # List tables
        tables = await crud_ops.list_tables()
        assert len(tables) == 3
        assert "users" in tables
        assert "products" in tables
        assert "orders" in tables


class TestDescribeTable:
    """Test describe_table functionality."""

    @pytest.mark.asyncio
    async def test_describe_table_structure(self, crud_ops):
        """Test describing table structure."""
        schema = {
            "id": "INTEGER",
            "name": "TEXT",
            "price": "REAL",
            "active": "BOOLEAN"
        }
        await crud_ops.create_table("products", schema, "id")

        # Describe table
        description = await crud_ops.describe_table("products")

        assert isinstance(description, list)
        assert len(description) == 4

        # Check that column names are present
        column_names = [col.get("name") for col in description]
        assert "id" in column_names
        assert "name" in column_names
        assert "price" in column_names
        assert "active" in column_names


class TestExecuteRawQuery:
    """Test execute_raw_query functionality."""

    @pytest.mark.asyncio
    async def test_execute_select_query(self, crud_ops):
        """Test executing a SELECT query."""
        schema = {"id": "INTEGER", "name": "TEXT"}
        await crud_ops.create_table("users", schema, "id")
        await crud_ops.insert_record("users", {"id": 1, "name": "Alice"})
        await crud_ops.insert_record("users", {"id": 2, "name": "Bob"})

        # Execute raw SELECT
        result = await crud_ops.execute_raw_query("SELECT * FROM users", read_only=True)

        assert "rows" in result
        assert len(result["rows"]) == 2
        assert result["count"] == 2

    @pytest.mark.asyncio
    async def test_execute_parameterized_query(self, crud_ops):
        """Test executing a parameterized query."""
        schema = {"id": "INTEGER", "name": "TEXT", "age": "INTEGER"}
        await crud_ops.create_table("users", schema, "id")
        await crud_ops.insert_record("users", {"id": 1, "name": "Alice", "age": 25})
        await crud_ops.insert_record("users", {"id": 2, "name": "Bob", "age": 30})

        # Execute parameterized query
        result = await crud_ops.execute_raw_query(
            "SELECT * FROM users WHERE age > ?",
            params=[26],
            read_only=True
        )

        assert len(result["rows"]) == 1
        assert result["rows"][0]["name"] == "Bob"

    @pytest.mark.asyncio
    async def test_execute_write_query_in_write_mode(self, crud_ops):
        """Test executing write query in write mode."""
        schema = {"id": "INTEGER", "name": "TEXT"}
        await crud_ops.create_table("users", schema, "id")

        # Execute INSERT in write mode
        result = await crud_ops.execute_raw_query(
            "INSERT INTO users (id, name) VALUES (1, 'Alice')",
            read_only=False
        )

        assert "rows_affected" in result
        assert result["rows_affected"] == 1

    @pytest.mark.asyncio
    async def test_execute_write_query_in_readonly_mode_fails(self, crud_ops):
        """Test that write queries fail in read-only mode."""
        schema = {"id": "INTEGER", "name": "TEXT"}
        await crud_ops.create_table("users", schema, "id")

        # Try to execute INSERT in read-only mode
        with pytest.raises(DatabaseError) as exc_info:
            await crud_ops.execute_raw_query(
                "INSERT INTO users (id, name) VALUES (1, 'Alice')",
                read_only=True
            )

        assert "read-only mode" in str(exc_info.value)


class TestCompleteWorkflow:
    """Test complete CRUD workflow."""

    @pytest.mark.asyncio
    async def test_full_crud_workflow(self, crud_ops):
        """Test a complete CRUD workflow."""
        # 1. Create table
        schema = {"id": "INTEGER", "name": "TEXT", "email": "TEXT", "active": "BOOLEAN"}
        await crud_ops.create_table("users", schema, "id")

        # 2. Insert records
        await crud_ops.insert_record("users", {"id": 1, "name": "Alice", "email": "alice@example.com", "active": 1})
        await crud_ops.insert_record("users", {"id": 2, "name": "Bob", "email": "bob@example.com", "active": 1})
        await crud_ops.insert_record("users", {"id": 3, "name": "Charlie", "email": "charlie@example.com", "active": 0})

        # 3. Query records
        all_users = await crud_ops.query_records("users")
        assert len(all_users) == 3

        active_users = await crud_ops.query_records("users", filters={"active": 1})
        assert len(active_users) == 2

        # 4. Update record
        await crud_ops.update_record("users", filters={"id": 3}, data={"active": 1})
        active_users = await crud_ops.query_records("users", filters={"active": 1})
        assert len(active_users) == 3

        # 5. Delete record
        await crud_ops.delete_record("users", filters={"id": 2})
        remaining = await crud_ops.query_records("users")
        assert len(remaining) == 2

        # 6. List tables
        tables = await crud_ops.list_tables()
        assert "users" in tables

        # 7. Describe table
        description = await crud_ops.describe_table("users")
        assert len(description) == 4
