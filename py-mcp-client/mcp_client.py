"""MCP Client for connecting to MCP SQLite Server."""
import httpx
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MCPTool:
    """Represents an MCP tool."""
    name: str
    description: str
    input_schema: Dict[str, Any]


class MCPClient:
    """Client for interacting with MCP server."""

    def __init__(self, base_url: str, timeout: int = 30):
        """Initialize MCP client.

        Args:
            base_url: Base URL of the MCP server
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.tools: Dict[str, MCPTool] = {}
        self.client = httpx.Client(timeout=timeout)

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def close(self):
        """Close the HTTP client."""
        self.client.close()

    def list_tools(self) -> List[MCPTool]:
        """List all available tools from the MCP server.

        Returns:
            List of MCPTool objects
        """
        try:
            response = self.client.post(f"{self.base_url}/mcp/v1/tools/list")
            response.raise_for_status()
            data = response.json()

            tools = []
            for tool_data in data.get("tools", []):
                tool = MCPTool(
                    name=tool_data["name"],
                    description=tool_data["description"],
                    input_schema=tool_data["inputSchema"]
                )
                tools.append(tool)
                self.tools[tool.name] = tool

            logger.info(f"Loaded {len(tools)} tools from MCP server")
            return tools

        except httpx.HTTPError as e:
            logger.error(f"Failed to list tools: {e}")
            raise

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the MCP server.

        Args:
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool

        Returns:
            Tool execution result
        """
        try:
            payload = {
                "name": tool_name,
                "arguments": arguments
            }

            response = self.client.post(
                f"{self.base_url}/mcp/v1/tools/call",
                json=payload
            )
            response.raise_for_status()
            result = response.json()

            if result.get("isError", False):
                error_msg = result.get("content", [{}])[0].get("text", "Unknown error")
                logger.error(f"Tool execution error: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg
                }

            # Extract result text
            content = result.get("content", [])
            if content:
                result_text = content[0].get("text", "")
                logger.info(f"Tool {tool_name} executed successfully")
                return {
                    "success": True,
                    "result": result_text
                }

            return {
                "success": True,
                "result": "Tool executed successfully (no output)"
            }

        except httpx.HTTPError as e:
            logger.error(f"Failed to call tool {tool_name}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_tool_descriptions(self) -> List[Dict[str, str]]:
        """Get formatted tool descriptions for the LLM.

        Returns:
            List of tool descriptions with name, description, and parameters
        """
        descriptions = []
        for tool in self.tools.values():
            properties = tool.input_schema.get("properties", {})
            required = tool.input_schema.get("required", [])

            params = []
            for param_name, param_info in properties.items():
                param_type = param_info.get("type", "string")
                param_desc = param_info.get("description", "")
                is_required = param_name in required
                params.append(
                    f"  - {param_name} ({param_type}){' [required]' if is_required else ''}: {param_desc}"
                )

            desc = {
                "name": tool.name,
                "description": tool.description,
                "parameters": "\n".join(params) if params else "  No parameters"
            }
            descriptions.append(desc)

        return descriptions

    def format_tools_for_prompt(self) -> str:
        """Format tools information for inclusion in LLM prompt.

        Returns:
            Formatted string describing all available tools
        """
        if not self.tools:
            self.list_tools()

        tool_descriptions = self.get_tool_descriptions()

        formatted = "Available MCP Tools:\n\n"
        for tool_desc in tool_descriptions:
            formatted += f"Tool: {tool_desc['name']}\n"
            formatted += f"Description: {tool_desc['description']}\n"
            formatted += f"Parameters:\n{tool_desc['parameters']}\n\n"

        formatted += (
            "To use a tool, respond with a JSON object in the following format:\n"
            '{"tool": "tool_name", "arguments": {"param1": "value1", "param2": "value2"}}\n\n'
            "After using a tool, I will show you the result and you can continue the conversation."
        )

        return formatted

    def format_tools_for_ollama(self) -> List[Dict[str, Any]]:
        """Format tools for Ollama's native function calling format.

        Returns:
            List of tools in Ollama format
        """
        if not self.tools:
            self.list_tools()

        ollama_tools = []
        for tool in self.tools.values():
            ollama_tool = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.input_schema
                }
            }
            ollama_tools.append(ollama_tool)

        return ollama_tools

    def health_check(self) -> bool:
        """Check if the MCP server is healthy.

        Returns:
            True if server is healthy, False otherwise
        """
        try:
            response = self.client.get(f"{self.base_url}/health")
            response.raise_for_status()
            data = response.json()
            return data.get("status") == "healthy"
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
