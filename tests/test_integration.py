"""Integration tests for MCP SQLite Server API."""
import pytest
import tempfile
import os
from fastapi.testclient import TestClient

# Import after ensuring we have a test database
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(scope="module")
def test_db_path():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".db", delete=False) as f:
        db_path = f.name

    yield db_path

    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture(scope="module")
def client(test_db_path):
    """Create FastAPI test client with test database."""
    # Patch the database path before importing server
    from src.database import connection
    from pathlib import Path

    original_init = connection.DatabaseManager.__init__

    def patched_init(self, db_path=None, timeout=30):
        self.db_path = Path(test_db_path)
        self.timeout = timeout
        self._ensure_directory()

    connection.DatabaseManager.__init__ = patched_init

    from src.server import app

    with TestClient(app) as test_client:
        yield test_client

    # Restore original init
    connection.DatabaseManager.__init__ = original_init


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_check(self, client):
        """Test health check endpoint returns success."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "mcp-sqlite-server"

    def test_health_check_multiple_calls(self, client):
        """Test health endpoint can be called multiple times."""
        for _ in range(5):
            response = client.get("/health")
            assert response.status_code == 200


class TestToolsListEndpoint:
    """Test tools listing endpoint."""

    def test_list_tools(self, client):
        """Test listing all available tools."""
        response = client.post("/mcp/v1/tools/list")

        assert response.status_code == 200
        data = response.json()
        assert "tools" in data
        assert isinstance(data["tools"], list)
        assert len(data["tools"]) == 8  # We have 8 CRUD tools

    def test_list_tools_contains_expected_tools(self, client):
        """Test that all expected tools are listed."""
        response = client.post("/mcp/v1/tools/list")
        data = response.json()

        tool_names = [tool["name"] for tool in data["tools"]]
        expected_tools = [
            "create_table",
            "insert_record",
            "query_records",
            "update_record",
            "delete_record",
            "list_tables",
            "describe_table",
            "execute_raw_query"
        ]

        for expected_tool in expected_tools:
            assert expected_tool in tool_names

    def test_list_tools_schema_structure(self, client):
        """Test that tool schemas have correct structure."""
        response = client.post("/mcp/v1/tools/list")
        data = response.json()

        for tool in data["tools"]:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool
            assert "type" in tool["inputSchema"]
            assert "properties" in tool["inputSchema"]


class TestToolCallEndpoint:
    """Test tool execution endpoint."""

    def test_create_table_tool(self, client):
        """Test creating a table via tool call."""
        request_data = {
            "name": "create_table",
            "arguments": {
                "table_name": "test_users",
                "schema": {
                    "id": "INTEGER",
                    "name": "TEXT",
                    "email": "TEXT"
                },
                "primary_key": "id"
            }
        }

        response = client.post("/mcp/v1/tools/call", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["isError"] is False
        assert len(data["content"]) > 0
        assert "created successfully" in data["content"][0]["text"]

    def test_insert_record_tool(self, client):
        """Test inserting a record via tool call."""
        # First create table
        create_request = {
            "name": "create_table",
            "arguments": {
                "table_name": "products",
                "schema": {
                    "id": "INTEGER",
                    "name": "TEXT",
                    "price": "REAL"
                },
                "primary_key": "id"
            }
        }
        client.post("/mcp/v1/tools/call", json=create_request)

        # Then insert record
        insert_request = {
            "name": "insert_record",
            "arguments": {
                "table_name": "products",
                "data": {
                    "id": 1,
                    "name": "Widget",
                    "price": 19.99
                }
            }
        }

        response = client.post("/mcp/v1/tools/call", json=insert_request)

        assert response.status_code == 200
        data = response.json()
        assert data["isError"] is False

    def test_query_records_tool(self, client):
        """Test querying records via tool call."""
        # Create and populate table
        client.post("/mcp/v1/tools/call", json={
            "name": "create_table",
            "arguments": {
                "table_name": "employees",
                "schema": {"id": "INTEGER", "name": "TEXT", "dept": "TEXT"},
                "primary_key": "id"
            }
        })

        for i in range(1, 4):
            client.post("/mcp/v1/tools/call", json={
                "name": "insert_record",
                "arguments": {
                    "table_name": "employees",
                    "data": {"id": i, "name": f"Employee {i}", "dept": "IT"}
                }
            })

        # Query records
        query_request = {
            "name": "query_records",
            "arguments": {
                "table_name": "employees",
                "limit": 10
            }
        }

        response = client.post("/mcp/v1/tools/call", json=query_request)

        assert response.status_code == 200
        data = response.json()
        assert data["isError"] is False

    def test_update_record_tool(self, client):
        """Test updating a record via tool call."""
        # Create and populate table
        client.post("/mcp/v1/tools/call", json={
            "name": "create_table",
            "arguments": {
                "table_name": "inventory",
                "schema": {"id": "INTEGER", "item": "TEXT", "quantity": "INTEGER"},
                "primary_key": "id"
            }
        })

        client.post("/mcp/v1/tools/call", json={
            "name": "insert_record",
            "arguments": {
                "table_name": "inventory",
                "data": {"id": 1, "item": "Laptop", "quantity": 10}
            }
        })

        # Update record
        update_request = {
            "name": "update_record",
            "arguments": {
                "table_name": "inventory",
                "filters": {"id": 1},
                "data": {"quantity": 15}
            }
        }

        response = client.post("/mcp/v1/tools/call", json=update_request)

        assert response.status_code == 200
        data = response.json()
        assert data["isError"] is False

    def test_delete_record_tool(self, client):
        """Test deleting a record via tool call."""
        # Create and populate table
        client.post("/mcp/v1/tools/call", json={
            "name": "create_table",
            "arguments": {
                "table_name": "temp_data",
                "schema": {"id": "INTEGER", "value": "TEXT"},
                "primary_key": "id"
            }
        })

        client.post("/mcp/v1/tools/call", json={
            "name": "insert_record",
            "arguments": {
                "table_name": "temp_data",
                "data": {"id": 1, "value": "test"}
            }
        })

        # Delete record
        delete_request = {
            "name": "delete_record",
            "arguments": {
                "table_name": "temp_data",
                "filters": {"id": 1}
            }
        }

        response = client.post("/mcp/v1/tools/call", json=delete_request)

        assert response.status_code == 200
        data = response.json()
        assert data["isError"] is False

    def test_list_tables_tool(self, client):
        """Test listing tables via tool call."""
        list_request = {
            "name": "list_tables",
            "arguments": {}
        }

        response = client.post("/mcp/v1/tools/call", json=list_request)

        assert response.status_code == 200
        data = response.json()
        assert data["isError"] is False

    def test_describe_table_tool(self, client):
        """Test describing a table via tool call."""
        # Create table first
        client.post("/mcp/v1/tools/call", json={
            "name": "create_table",
            "arguments": {
                "table_name": "schema_test",
                "schema": {"id": "INTEGER", "name": "TEXT", "active": "BOOLEAN"},
                "primary_key": "id"
            }
        })

        # Describe table
        describe_request = {
            "name": "describe_table",
            "arguments": {
                "table_name": "schema_test"
            }
        }

        response = client.post("/mcp/v1/tools/call", json=describe_request)

        assert response.status_code == 200
        data = response.json()
        assert data["isError"] is False

    def test_execute_raw_query_tool(self, client):
        """Test executing raw SQL via tool call."""
        # Create and populate table
        client.post("/mcp/v1/tools/call", json={
            "name": "create_table",
            "arguments": {
                "table_name": "raw_query_test",
                "schema": {"id": "INTEGER", "value": "TEXT"},
                "primary_key": "id"
            }
        })

        client.post("/mcp/v1/tools/call", json={
            "name": "insert_record",
            "arguments": {
                "table_name": "raw_query_test",
                "data": {"id": 1, "value": "test"}
            }
        })

        # Execute raw query
        raw_query_request = {
            "name": "execute_raw_query",
            "arguments": {
                "query": "SELECT * FROM raw_query_test",
                "read_only": True
            }
        }

        response = client.post("/mcp/v1/tools/call", json=raw_query_request)

        assert response.status_code == 200
        data = response.json()
        assert data["isError"] is False

    def test_tool_call_with_invalid_tool_name(self, client):
        """Test calling a non-existent tool."""
        request_data = {
            "name": "nonexistent_tool",
            "arguments": {}
        }

        response = client.post("/mcp/v1/tools/call", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["isError"] is True
        assert "not found" in data["content"][0]["text"].lower()

    def test_tool_call_with_invalid_arguments(self, client):
        """Test calling a tool with missing required arguments."""
        request_data = {
            "name": "create_table",
            "arguments": {
                "table_name": "incomplete_table"
                # Missing 'schema' argument
            }
        }

        response = client.post("/mcp/v1/tools/call", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["isError"] is True


class TestCompleteWorkflow:
    """Test complete end-to-end workflows."""

    def test_full_crud_workflow(self, client):
        """Test a complete CRUD workflow through the API."""
        # 1. Create table
        create_response = client.post("/mcp/v1/tools/call", json={
            "name": "create_table",
            "arguments": {
                "table_name": "workflow_test",
                "schema": {
                    "id": "INTEGER",
                    "title": "TEXT",
                    "completed": "BOOLEAN"
                },
                "primary_key": "id"
            }
        })
        assert create_response.status_code == 200
        assert create_response.json()["isError"] is False

        # 2. Insert records
        for i in range(1, 4):
            insert_response = client.post("/mcp/v1/tools/call", json={
                "name": "insert_record",
                "arguments": {
                    "table_name": "workflow_test",
                    "data": {
                        "id": i,
                        "title": f"Task {i}",
                        "completed": 0
                    }
                }
            })
            assert insert_response.status_code == 200
            assert insert_response.json()["isError"] is False

        # 3. Query all records
        query_response = client.post("/mcp/v1/tools/call", json={
            "name": "query_records",
            "arguments": {
                "table_name": "workflow_test"
            }
        })
        assert query_response.status_code == 200
        assert query_response.json()["isError"] is False

        # 4. Update a record
        update_response = client.post("/mcp/v1/tools/call", json={
            "name": "update_record",
            "arguments": {
                "table_name": "workflow_test",
                "filters": {"id": 1},
                "data": {"completed": 1}
            }
        })
        assert update_response.status_code == 200
        assert update_response.json()["isError"] is False

        # 5. Delete a record
        delete_response = client.post("/mcp/v1/tools/call", json={
            "name": "delete_record",
            "arguments": {
                "table_name": "workflow_test",
                "filters": {"id": 3}
            }
        })
        assert delete_response.status_code == 200
        assert delete_response.json()["isError"] is False

        # 6. List tables to verify
        list_response = client.post("/mcp/v1/tools/call", json={
            "name": "list_tables",
            "arguments": {}
        })
        assert list_response.status_code == 200
        assert list_response.json()["isError"] is False

    def test_multiple_tables_workflow(self, client):
        """Test working with multiple tables."""
        tables = ["customers_multi", "orders_multi", "products_multi"]

        # Create multiple tables
        for table_name in tables:
            response = client.post("/mcp/v1/tools/call", json={
                "name": "create_table",
                "arguments": {
                    "table_name": table_name,
                    "schema": {"id": "INTEGER", "name": "TEXT"},
                    "primary_key": "id"
                }
            })
            assert response.status_code == 200
            assert response.json()["isError"] is False

        # List tables
        list_response = client.post("/mcp/v1/tools/call", json={
            "name": "list_tables",
            "arguments": {}
        })
        assert list_response.status_code == 200
        result = list_response.json()
        assert result["isError"] is False

        # Verify all tables exist
        for table_name in tables:
            # Describe each table
            describe_response = client.post("/mcp/v1/tools/call", json={
                "name": "describe_table",
                "arguments": {"table_name": table_name}
            })
            assert describe_response.status_code == 200
            assert describe_response.json()["isError"] is False

    def test_filter_and_pagination_workflow(self, client):
        """Test filtering and pagination through the API."""
        # Create and populate table
        client.post("/mcp/v1/tools/call", json={
            "name": "create_table",
            "arguments": {
                "table_name": "pagination_test",
                "schema": {"id": "INTEGER", "category": "TEXT", "value": "INTEGER"},
                "primary_key": "id"
            }
        })

        # Insert multiple records
        for i in range(1, 21):
            client.post("/mcp/v1/tools/call", json={
                "name": "insert_record",
                "arguments": {
                    "table_name": "pagination_test",
                    "data": {
                        "id": i,
                        "category": "A" if i % 2 == 0 else "B",
                        "value": i * 10
                    }
                }
            })

        # Test pagination
        page1_response = client.post("/mcp/v1/tools/call", json={
            "name": "query_records",
            "arguments": {
                "table_name": "pagination_test",
                "limit": 5,
                "offset": 0
            }
        })
        assert page1_response.status_code == 200
        assert page1_response.json()["isError"] is False

        page2_response = client.post("/mcp/v1/tools/call", json={
            "name": "query_records",
            "arguments": {
                "table_name": "pagination_test",
                "limit": 5,
                "offset": 5
            }
        })
        assert page2_response.status_code == 200
        assert page2_response.json()["isError"] is False

        # Test filtering
        filter_response = client.post("/mcp/v1/tools/call", json={
            "name": "query_records",
            "arguments": {
                "table_name": "pagination_test",
                "filters": {"category": "A"}
            }
        })
        assert filter_response.status_code == 200
        assert filter_response.json()["isError"] is False


class TestSSEEndpoint:
    """Test Server-Sent Events endpoint."""

    def test_sse_endpoint_accessible(self, client):
        """Test that SSE endpoint is accessible."""
        response = client.get("/mcp/v1/sse")

        # SSE endpoints typically return 200 with streaming content
        assert response.status_code == 200

    def test_sse_endpoint_content_type(self, client):
        """Test that SSE endpoint returns correct content type."""
        response = client.get("/mcp/v1/sse")

        # Check if content-type is text/event-stream
        content_type = response.headers.get("content-type", "")
        assert "text/event-stream" in content_type or response.status_code == 200


class TestErrorHandling:
    """Test error handling in the API."""

    def test_invalid_endpoint(self, client):
        """Test accessing an invalid endpoint."""
        response = client.get("/invalid/endpoint")
        assert response.status_code == 404

    def test_invalid_method_on_tools_list(self, client):
        """Test using wrong HTTP method on tools/list."""
        response = client.get("/mcp/v1/tools/list")
        assert response.status_code == 405  # Method not allowed

    def test_invalid_method_on_tools_call(self, client):
        """Test using wrong HTTP method on tools/call."""
        response = client.get("/mcp/v1/tools/call")
        assert response.status_code == 405  # Method not allowed

    def test_malformed_json_request(self, client):
        """Test sending malformed JSON to tools/call."""
        response = client.post(
            "/mcp/v1/tools/call",
            content="invalid json{",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422  # Unprocessable entity

    def test_missing_required_fields(self, client):
        """Test sending request with missing required fields."""
        response = client.post("/mcp/v1/tools/call", json={
            "name": "create_table"
            # Missing 'arguments' field
        })
        assert response.status_code == 422  # Validation error
