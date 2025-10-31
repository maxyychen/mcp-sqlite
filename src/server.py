"""FastAPI server with MCP Streamable HTTP transport support."""
import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict, Any, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from sse_starlette.sse import EventSourceResponse

from .mcp_handler import MCPHandler
from .database.connection import DatabaseManager
from .database.crud_operations import CRUDOperations
from .jsonrpc.handler import JSONRPCHandler
from .jsonrpc.models import JSONRPCRequest, JSONRPCResponse
from .mcp_transport import MCPTransport

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize components
mcp_handler = MCPHandler()
jsonrpc_handler = JSONRPCHandler()
mcp_transport = MCPTransport(jsonrpc_handler)

# Use DATABASE_PATH env var if set, otherwise default to ./data/database.db
db_path = os.getenv("DATABASE_PATH", "./data/database.db")
db_manager = DatabaseManager(db_path)
crud_ops = CRUDOperations(db_manager)


def register_all_tools():
    """Register all MCP tools."""

    # Tool 1: create_table
    mcp_handler.register_tool(
        name="create_table",
        description="Create a new table in the database",
        input_schema={
            "type": "object",
            "properties": {
                "table_name": {"type": "string", "description": "Name of the table"},
                "schema": {
                    "type": "object",
                    "description": "Column definitions with types (e.g., {'id': 'INTEGER', 'name': 'TEXT'})",
                },
                "primary_key": {
                    "type": "string",
                    "description": "Primary key column name (optional)",
                },
            },
            "required": ["table_name", "schema"],
        },
        handler=crud_ops.create_table,
    )

    # Tool 2: insert_record
    mcp_handler.register_tool(
        name="insert_record",
        description="Insert a new record into a table",
        input_schema={
            "type": "object",
            "properties": {
                "table_name": {"type": "string", "description": "Target table name"},
                "data": {
                    "type": "object",
                    "description": "Key-value pairs for the record",
                },
            },
            "required": ["table_name", "data"],
        },
        handler=crud_ops.insert_record,
    )

    # Tool 3: query_records
    mcp_handler.register_tool(
        name="query_records",
        description="Query/read records from a table",
        input_schema={
            "type": "object",
            "properties": {
                "table_name": {"type": "string", "description": "Target table name"},
                "filters": {
                    "type": "object",
                    "description": "WHERE clause conditions (optional)",
                },
                "limit": {"type": "integer", "description": "Maximum records to return"},
                "offset": {"type": "integer", "description": "Pagination offset"},
                "order_by": {"type": "string", "description": "Column to sort by"},
            },
            "required": ["table_name"],
        },
        handler=crud_ops.query_records,
    )

    # Tool 4: update_record
    mcp_handler.register_tool(
        name="update_record",
        description="Update existing record(s)",
        input_schema={
            "type": "object",
            "properties": {
                "table_name": {"type": "string", "description": "Target table name"},
                "filters": {
                    "type": "object",
                    "description": "WHERE clause conditions to match records",
                },
                "data": {"type": "object", "description": "Fields to update"},
            },
            "required": ["table_name", "filters", "data"],
        },
        handler=crud_ops.update_record,
    )

    # Tool 5: delete_record
    mcp_handler.register_tool(
        name="delete_record",
        description="Delete record(s) from a table",
        input_schema={
            "type": "object",
            "properties": {
                "table_name": {"type": "string", "description": "Target table name"},
                "filters": {
                    "type": "object",
                    "description": "WHERE clause conditions to match records",
                },
            },
            "required": ["table_name", "filters"],
        },
        handler=crud_ops.delete_record,
    )

    # Tool 6: list_tables
    mcp_handler.register_tool(
        name="list_tables",
        description="List all tables in the database",
        input_schema={"type": "object", "properties": {}, "required": []},
        handler=lambda: crud_ops.list_tables(),
    )

    # Tool 7: describe_table
    mcp_handler.register_tool(
        name="describe_table",
        description="Get detailed schema information for a table",
        input_schema={
            "type": "object",
            "properties": {
                "table_name": {"type": "string", "description": "Target table name"}
            },
            "required": ["table_name"],
        },
        handler=crud_ops.describe_table,
    )

    # Tool 8: execute_raw_query
    mcp_handler.register_tool(
        name="execute_raw_query",
        description="Execute custom SQL query (with safety controls)",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "SQL query to execute"},
                "params": {
                    "type": "array",
                    "items": {},
                    "description": "Parameterized query values (optional)",
                },
                "read_only": {
                    "type": "boolean",
                    "description": "Enforce read-only mode (default: true)",
                },
            },
            "required": ["query"],
        },
        handler=crud_ops.execute_raw_query,
    )


def register_jsonrpc_methods():
    """Register all JSON-RPC 2.0 methods."""

    # Method: initialize
    async def initialize(params: dict):
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {"listChanged": False},
                "logging": {}
            },
            "serverInfo": {
                "name": "mcp-sqlite-server",
                "version": "1.0.0"
            }
        }

    # Method: ping
    async def ping(params: dict):
        return {}

    # Method: tools/list
    async def tools_list(params: dict):
        tools = mcp_handler.list_tools()
        return {"tools": tools}

    # Method: tools/call
    async def tools_call(params: dict):
        name = params.get("name")
        arguments = params.get("arguments", {})

        if not name:
            raise ValueError("Tool name is required")

        result = await mcp_handler.execute_tool(name, arguments)
        return {
            "content": [{"type": "text", "text": str(result)}]
        }

    # Register methods
    jsonrpc_handler.register_method("initialize", initialize)
    jsonrpc_handler.register_method("ping", ping)
    jsonrpc_handler.register_method("tools/list", tools_list)
    jsonrpc_handler.register_method("tools/call", tools_call)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for FastAPI app."""
    logger.info("Starting MCP server with Streamable HTTP transport...")
    register_all_tools()
    register_jsonrpc_methods()
    mcp_transport.start_cleanup()
    logger.info(f"Registered {len(mcp_handler.tools)} MCP tools")
    logger.info(f"Registered {len(jsonrpc_handler.methods)} JSON-RPC methods")
    logger.info("MCP session cleanup task started")
    yield
    logger.info("Shutting down MCP server...")
    mcp_transport.stop_cleanup()


app = FastAPI(
    title="MCP SQLite Server",
    description="MCP server with Streamable HTTP transport for SQLite CRUD operations",
    version="2.1.0",
    lifespan=lifespan,
)


# MCP Streamable HTTP Endpoint (Unified POST + GET)
@app.post("/mcp")
async def mcp_post_endpoint(request: Request, jsonrpc_request: JSONRPCRequest):
    """MCP Streamable HTTP POST endpoint.

    Per MCP spec: Every JSON-RPC message from client MUST be a new HTTP POST.
    Handles MCP headers: Mcp-Session-Id, Mcp-Protocol-Version.
    """
    return await mcp_transport.handle_post_request(request, jsonrpc_request)


@app.get("/mcp")
async def mcp_get_endpoint(request: Request):
    """MCP Streamable HTTP GET endpoint.

    Per MCP spec: Opens an SSE stream allowing server to push messages.
    Supports resumption via Last-Event-Id header.
    """
    return await mcp_transport.handle_get_request(request)


# Legacy JSON-RPC 2.0 Endpoints (for backward compatibility)
@app.post("/")
@app.post("/rpc")
@app.post("/jsonrpc")
async def jsonrpc_endpoint(request: JSONRPCRequest):
    """Legacy JSON-RPC 2.0 endpoint (no MCP headers).

    Kept for backward compatibility with non-MCP clients.
    """
    response = await jsonrpc_handler.handle_request(request)
    return response.model_dump(exclude_none=True)


# Monitoring Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "mcp-sqlite-server",
        "version": "2.1.0",
        "transport": "MCP Streamable HTTP",
        "protocol_version": "2024-11-05"
    }


@app.get("/sse")
async def legacy_sse_endpoint():
    """Legacy SSE endpoint (deprecated).

    Use GET /mcp with Mcp-Session-Id header instead.
    """
    async def event_generator() -> AsyncGenerator[dict, None]:
        yield {
            "event": "message",
            "data": '{"type": "notification", "message": "Legacy SSE endpoint. Use GET /mcp instead."}',
        }

    return EventSourceResponse(event_generator())
