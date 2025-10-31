"""Integration tests for JSON-RPC MCP server."""
import pytest
from fastapi.testclient import TestClient
from src.server import app, register_all_tools, register_jsonrpc_methods


@pytest.fixture(scope="module")
def client():
    """Create a test client with all tools registered."""
    register_all_tools()
    register_jsonrpc_methods()
    with TestClient(app) as c:
        yield c


def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "mcp-sqlite-server"
    assert "version" in data


def test_jsonrpc_initialize(client):
    """Test JSON-RPC initialize method."""
    response = client.post("/", json={
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0.0"}
        }
    })

    assert response.status_code == 200
    data = response.json()
    assert data["jsonrpc"] == "2.0"
    assert data["id"] == 1
    assert "result" in data
    assert "serverInfo" in data["result"]
    assert data["result"]["serverInfo"]["name"] == "mcp-sqlite-server"
    assert "protocolVersion" in data["result"]
    assert "capabilities" in data["result"]


def test_jsonrpc_ping(client):
    """Test JSON-RPC ping method."""
    response = client.post("/", json={
        "jsonrpc": "2.0",
        "id": 2,
        "method": "ping",
        "params": {}
    })

    assert response.status_code == 200
    data = response.json()
    assert data["jsonrpc"] == "2.0"
    assert data["id"] == 2
    assert data["result"] == {}


def test_jsonrpc_tools_list(client):
    """Test JSON-RPC tools/list method."""
    response = client.post("/", json={
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/list",
        "params": {}
    })

    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    assert "tools" in data["result"]
    tools = data["result"]["tools"]
    assert len(tools) == 8  # Should have 8 CRUD tools

    # Verify tool structure
    tool_names = [tool["name"] for tool in tools]
    assert "create_table" in tool_names
    assert "insert_record" in tool_names
    assert "query_records" in tool_names
    assert "update_record" in tool_names
    assert "delete_record" in tool_names
    assert "list_tables" in tool_names
    assert "describe_table" in tool_names
    assert "execute_raw_query" in tool_names

    # Verify each tool has required fields
    for tool in tools:
        assert "name" in tool
        assert "description" in tool
        assert "inputSchema" in tool


def test_jsonrpc_tools_call_list_tables(client):
    """Test JSON-RPC tools/call method with list_tables."""
    response = client.post("/", json={
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
            "name": "list_tables",
            "arguments": {}
        }
    })

    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    assert "content" in data["result"]
    assert len(data["result"]["content"]) > 0
    assert data["result"]["content"][0]["type"] == "text"


def test_jsonrpc_tools_call_invalid_tool(client):
    """Test JSON-RPC tools/call with non-existent tool."""
    response = client.post("/", json={
        "jsonrpc": "2.0",
        "id": 5,
        "method": "tools/call",
        "params": {
            "name": "nonexistent_tool",
            "arguments": {}
        }
    })

    assert response.status_code == 200
    data = response.json()
    # Should return an error from the tool execution
    assert "error" in data or ("result" in data and "error" in str(data["result"]))


def test_jsonrpc_tools_call_missing_name(client):
    """Test JSON-RPC tools/call without tool name."""
    response = client.post("/", json={
        "jsonrpc": "2.0",
        "id": 6,
        "method": "tools/call",
        "params": {
            "arguments": {}
        }
    })

    assert response.status_code == 200
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == -32602  # INVALID_PARAMS


def test_jsonrpc_method_not_found(client):
    """Test JSON-RPC with non-existent method."""
    response = client.post("/", json={
        "jsonrpc": "2.0",
        "id": 7,
        "method": "nonexistent_method",
        "params": {}
    })

    assert response.status_code == 200
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == -32601  # METHOD_NOT_FOUND


def test_jsonrpc_multiple_endpoints(client):
    """Test that JSON-RPC works on multiple endpoint paths."""
    payloads = [
        ("/", {"jsonrpc": "2.0", "id": 1, "method": "ping", "params": {}}),
        ("/rpc", {"jsonrpc": "2.0", "id": 2, "method": "ping", "params": {}}),
        ("/jsonrpc", {"jsonrpc": "2.0", "id": 3, "method": "ping", "params": {}}),
    ]

    for endpoint, payload in payloads:
        response = client.post(endpoint, json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["result"] == {}


def test_sse_endpoint(client):
    """Test SSE endpoint exists."""
    response = client.get("/sse")
    assert response.status_code == 200
    # SSE returns text/event-stream content type
    assert "text/event-stream" in response.headers.get("content-type", "")


def test_old_rest_endpoints_removed(client):
    """Test that old REST endpoints are removed (return 404)."""
    # Old endpoints should not exist
    response = client.post("/mcp/v1/tools/list")
    assert response.status_code == 404

    response = client.post("/mcp/v1/tools/call", json={"name": "list_tables", "arguments": {}})
    assert response.status_code == 404

    response = client.get("/mcp/v1/sse")
    assert response.status_code == 404
