"""FastAPI server with HTTP+SSE support for MCP protocol."""
import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict, Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel

from .mcp_handler import MCPHandler
from .database.connection import DatabaseManager
from .database.crud_operations import CRUDOperations

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize components
mcp_handler = MCPHandler()
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for FastAPI app."""
    logger.info("Starting MCP server...")
    register_all_tools()
    logger.info(f"Registered {len(mcp_handler.tools)} tools")
    yield
    logger.info("Shutting down MCP server...")


app = FastAPI(
    title="MCP SQLite Server",
    description="MCP server with HTTP+SSE for SQLite CRUD operations",
    version="1.0.0",
    lifespan=lifespan,
)


# Request/Response models
class ToolCallRequest(BaseModel):
    name: str
    arguments: dict


class MCPResponse(BaseModel):
    content: list[dict]
    isError: bool = False


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "mcp-sqlite-server"}


@app.post("/mcp/v1/tools/list")
async def list_tools():
    """List all available MCP tools."""
    tools = mcp_handler.list_tools()
    return {"tools": tools}


@app.post("/mcp/v1/tools/call")
async def call_tool(request: ToolCallRequest):
    """Execute an MCP tool."""
    try:
        result = await mcp_handler.execute_tool(request.name, request.arguments)
        return MCPResponse(
            content=[{"type": "text", "text": str(result)}], isError=False
        )
    except Exception as e:
        logger.error(f"Tool execution error: {e}")
        return MCPResponse(content=[{"type": "text", "text": str(e)}], isError=True)


@app.get("/mcp/v1/sse")
async def sse_endpoint():
    """SSE endpoint for real-time notifications."""

    async def event_generator() -> AsyncGenerator[dict, None]:
        # Yield SSE events
        yield {
            "event": "message",
            "data": '{"type": "notification", "message": "Connected to MCP server"}',
        }

    return EventSourceResponse(event_generator())
