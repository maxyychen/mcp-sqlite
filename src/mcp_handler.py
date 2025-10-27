"""MCP protocol handler with tool registration and execution."""
from typing import Dict, Any, Callable, List
import logging
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ToolSchema(BaseModel):
    name: str
    description: str
    inputSchema: Dict[str, Any]


class MCPHandler:
    def __init__(self):
        self.tools: Dict[str, Callable] = {}
        self.tool_schemas: Dict[str, ToolSchema] = {}

    def register_tool(
        self, name: str, description: str, input_schema: Dict[str, Any], handler: Callable
    ) -> None:
        """Register an MCP tool."""
        self.tools[name] = handler
        self.tool_schemas[name] = ToolSchema(
            name=name, description=description, inputSchema=input_schema
        )
        logger.info(f"Registered tool: {name}")

    def list_tools(self) -> List[Dict[str, Any]]:
        """List all registered tools."""
        return [schema.model_dump() for schema in self.tool_schemas.values()]

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a registered tool."""
        if tool_name not in self.tools:
            raise ValueError(f"Tool not found: {tool_name}")

        handler = self.tools[tool_name]
        return await handler(**arguments)
