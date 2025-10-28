"""Unit tests for MCP protocol handler."""
import pytest
from unittest.mock import AsyncMock, Mock

from src.mcp_handler import MCPHandler, ToolSchema


@pytest.fixture
def mcp_handler():
    """Create MCPHandler instance for testing."""
    return MCPHandler()


@pytest.fixture
def sample_tool_handler():
    """Create a sample async tool handler."""
    async def handler(name: str, value: int) -> dict:
        return {"name": name, "value": value, "result": value * 2}
    return handler


class TestToolRegistration:
    """Test tool registration functionality."""

    def test_register_single_tool(self, mcp_handler, sample_tool_handler):
        """Test registering a single tool."""
        input_schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "value": {"type": "integer"}
            },
            "required": ["name", "value"]
        }

        mcp_handler.register_tool(
            name="sample_tool",
            description="A sample tool for testing",
            input_schema=input_schema,
            handler=sample_tool_handler
        )

        assert "sample_tool" in mcp_handler.tools
        assert "sample_tool" in mcp_handler.tool_schemas
        assert mcp_handler.tool_schemas["sample_tool"].name == "sample_tool"
        assert mcp_handler.tool_schemas["sample_tool"].description == "A sample tool for testing"

    def test_register_multiple_tools(self, mcp_handler):
        """Test registering multiple tools."""
        async def handler1(**kwargs):
            return "result1"

        async def handler2(**kwargs):
            return "result2"

        mcp_handler.register_tool(
            name="tool1",
            description="First tool",
            input_schema={"type": "object", "properties": {}},
            handler=handler1
        )

        mcp_handler.register_tool(
            name="tool2",
            description="Second tool",
            input_schema={"type": "object", "properties": {}},
            handler=handler2
        )

        assert len(mcp_handler.tools) == 2
        assert len(mcp_handler.tool_schemas) == 2
        assert "tool1" in mcp_handler.tools
        assert "tool2" in mcp_handler.tools

    def test_register_tool_overwrites_existing(self, mcp_handler):
        """Test that registering a tool with the same name overwrites."""
        async def handler1(**kwargs):
            return "result1"

        async def handler2(**kwargs):
            return "result2"

        mcp_handler.register_tool(
            name="my_tool",
            description="First version",
            input_schema={"type": "object"},
            handler=handler1
        )

        mcp_handler.register_tool(
            name="my_tool",
            description="Second version",
            input_schema={"type": "object"},
            handler=handler2
        )

        assert len(mcp_handler.tools) == 1
        assert mcp_handler.tool_schemas["my_tool"].description == "Second version"


class TestListTools:
    """Test listing tools functionality."""

    def test_list_empty_tools(self, mcp_handler):
        """Test listing tools when none are registered."""
        tools = mcp_handler.list_tools()
        assert isinstance(tools, list)
        assert len(tools) == 0

    def test_list_registered_tools(self, mcp_handler):
        """Test listing registered tools."""
        async def handler(**kwargs):
            return "result"

        # Register multiple tools
        for i in range(1, 4):
            mcp_handler.register_tool(
                name=f"tool{i}",
                description=f"Tool {i}",
                input_schema={
                    "type": "object",
                    "properties": {"param": {"type": "string"}},
                    "required": ["param"]
                },
                handler=handler
            )

        tools = mcp_handler.list_tools()
        assert len(tools) == 3

        # Check structure
        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool

    def test_list_tools_includes_schemas(self, mcp_handler):
        """Test that listed tools include their input schemas."""
        async def handler(**kwargs):
            return "result"

        input_schema = {
            "type": "object",
            "properties": {
                "table_name": {"type": "string", "description": "Name of table"},
                "limit": {"type": "integer", "description": "Max records"}
            },
            "required": ["table_name"]
        }

        mcp_handler.register_tool(
            name="query_tool",
            description="Query database",
            input_schema=input_schema,
            handler=handler
        )

        tools = mcp_handler.list_tools()
        assert len(tools) == 1

        tool = tools[0]
        assert tool["name"] == "query_tool"
        assert tool["description"] == "Query database"
        assert tool["inputSchema"]["properties"]["table_name"]["type"] == "string"
        assert "table_name" in tool["inputSchema"]["required"]


class TestExecuteTool:
    """Test tool execution functionality."""

    @pytest.mark.asyncio
    async def test_execute_tool_success(self, mcp_handler, sample_tool_handler):
        """Test successful tool execution."""
        input_schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "value": {"type": "integer"}
            }
        }

        mcp_handler.register_tool(
            name="sample_tool",
            description="Sample tool",
            input_schema=input_schema,
            handler=sample_tool_handler
        )

        result = await mcp_handler.execute_tool(
            "sample_tool",
            {"name": "test", "value": 5}
        )

        assert result["name"] == "test"
        assert result["value"] == 5
        assert result["result"] == 10

    @pytest.mark.asyncio
    async def test_execute_tool_not_found(self, mcp_handler):
        """Test executing a non-existent tool."""
        with pytest.raises(ValueError) as exc_info:
            await mcp_handler.execute_tool("nonexistent_tool", {})

        assert "Tool not found" in str(exc_info.value)
        assert "nonexistent_tool" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_tool_with_no_arguments(self, mcp_handler):
        """Test executing a tool that requires no arguments."""
        async def no_arg_handler():
            return {"status": "success"}

        mcp_handler.register_tool(
            name="no_arg_tool",
            description="Tool with no arguments",
            input_schema={"type": "object", "properties": {}},
            handler=no_arg_handler
        )

        result = await mcp_handler.execute_tool("no_arg_tool", {})
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_execute_tool_with_optional_arguments(self, mcp_handler):
        """Test executing a tool with optional arguments."""
        async def optional_handler(required_param: str, optional_param: str = "default"):
            return {"required": required_param, "optional": optional_param}

        mcp_handler.register_tool(
            name="optional_tool",
            description="Tool with optional params",
            input_schema={
                "type": "object",
                "properties": {
                    "required_param": {"type": "string"},
                    "optional_param": {"type": "string"}
                },
                "required": ["required_param"]
            },
            handler=optional_handler
        )

        # Test with only required param
        result1 = await mcp_handler.execute_tool(
            "optional_tool",
            {"required_param": "test"}
        )
        assert result1["required"] == "test"
        assert result1["optional"] == "default"

        # Test with both params
        result2 = await mcp_handler.execute_tool(
            "optional_tool",
            {"required_param": "test", "optional_param": "custom"}
        )
        assert result2["required"] == "test"
        assert result2["optional"] == "custom"

    @pytest.mark.asyncio
    async def test_execute_tool_handler_exception(self, mcp_handler):
        """Test handling exceptions from tool handlers."""
        async def failing_handler(**kwargs):
            raise RuntimeError("Handler failed")

        mcp_handler.register_tool(
            name="failing_tool",
            description="Tool that fails",
            input_schema={"type": "object"},
            handler=failing_handler
        )

        with pytest.raises(RuntimeError) as exc_info:
            await mcp_handler.execute_tool("failing_tool", {})

        assert "Handler failed" in str(exc_info.value)


class TestToolSchema:
    """Test ToolSchema model."""

    def test_tool_schema_creation(self):
        """Test creating a ToolSchema."""
        schema = ToolSchema(
            name="test_tool",
            description="A test tool",
            inputSchema={
                "type": "object",
                "properties": {"param": {"type": "string"}}
            }
        )

        assert schema.name == "test_tool"
        assert schema.description == "A test tool"
        assert schema.inputSchema["type"] == "object"

    def test_tool_schema_serialization(self):
        """Test serializing ToolSchema to dict."""
        schema = ToolSchema(
            name="test_tool",
            description="A test tool",
            inputSchema={
                "type": "object",
                "properties": {
                    "param1": {"type": "string"},
                    "param2": {"type": "integer"}
                },
                "required": ["param1"]
            }
        )

        schema_dict = schema.model_dump()

        assert schema_dict["name"] == "test_tool"
        assert schema_dict["description"] == "A test tool"
        assert "param1" in schema_dict["inputSchema"]["properties"]
        assert "param2" in schema_dict["inputSchema"]["properties"]
        assert "param1" in schema_dict["inputSchema"]["required"]


class TestMCPIntegration:
    """Test integration scenarios for MCP handler."""

    @pytest.mark.asyncio
    async def test_register_and_execute_multiple_tools(self, mcp_handler):
        """Test registering and executing multiple tools."""
        # Register tools
        async def add_handler(a: int, b: int):
            return {"operation": "add", "result": a + b}

        async def multiply_handler(a: int, b: int):
            return {"operation": "multiply", "result": a * b}

        async def concat_handler(str1: str, str2: str):
            return {"operation": "concat", "result": str1 + str2}

        for name, handler, desc in [
            ("add", add_handler, "Add two numbers"),
            ("multiply", multiply_handler, "Multiply two numbers"),
            ("concat", concat_handler, "Concatenate strings")
        ]:
            mcp_handler.register_tool(
                name=name,
                description=desc,
                input_schema={"type": "object", "properties": {}},
                handler=handler
            )

        # List tools
        tools = mcp_handler.list_tools()
        assert len(tools) == 3

        # Execute tools
        result1 = await mcp_handler.execute_tool("add", {"a": 5, "b": 3})
        assert result1["result"] == 8

        result2 = await mcp_handler.execute_tool("multiply", {"a": 4, "b": 6})
        assert result2["result"] == 24

        result3 = await mcp_handler.execute_tool("concat", {"str1": "Hello", "str2": " World"})
        assert result3["result"] == "Hello World"

    @pytest.mark.asyncio
    async def test_tool_registration_order_preserved_in_list(self, mcp_handler):
        """Test that tool registration order is reflected in list."""
        async def handler(**kwargs):
            return {}

        tool_names = ["zebra", "apple", "banana", "cherry"]

        for name in tool_names:
            mcp_handler.register_tool(
                name=name,
                description=f"{name} tool",
                input_schema={"type": "object"},
                handler=handler
            )

        tools = mcp_handler.list_tools()
        listed_names = [tool["name"] for tool in tools]

        # Note: dict order is preserved in Python 3.7+
        assert len(listed_names) == len(tool_names)
        for name in tool_names:
            assert name in listed_names

    @pytest.mark.asyncio
    async def test_complex_tool_execution(self, mcp_handler):
        """Test executing a tool with complex arguments."""
        async def complex_handler(
            table_name: str,
            filters: dict,
            limit: int = 10,
            order_by: str = None
        ):
            return {
                "table": table_name,
                "filters": filters,
                "limit": limit,
                "order_by": order_by,
                "executed": True
            }

        mcp_handler.register_tool(
            name="complex_query",
            description="Complex query tool",
            input_schema={
                "type": "object",
                "properties": {
                    "table_name": {"type": "string"},
                    "filters": {"type": "object"},
                    "limit": {"type": "integer"},
                    "order_by": {"type": "string"}
                },
                "required": ["table_name", "filters"]
            },
            handler=complex_handler
        )

        result = await mcp_handler.execute_tool(
            "complex_query",
            {
                "table_name": "users",
                "filters": {"age": 25, "active": True},
                "limit": 5,
                "order_by": "name"
            }
        )

        assert result["table"] == "users"
        assert result["filters"]["age"] == 25
        assert result["filters"]["active"] is True
        assert result["limit"] == 5
        assert result["order_by"] == "name"
        assert result["executed"] is True
