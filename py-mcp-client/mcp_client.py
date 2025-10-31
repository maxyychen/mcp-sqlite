"""MCP Client for connecting to MCP SQLite Server via JSON-RPC 2.0."""
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
    """Client for interacting with MCP server via JSON-RPC 2.0."""

    def __init__(self, base_url: str, timeout: int = 30):
        """Initialize MCP client.

        Args:
            base_url: Base URL of the MCP server (e.g., http://localhost:8080)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.request_id = 0
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

    def _get_next_id(self) -> int:
        """Get next request ID for JSON-RPC."""
        self.request_id += 1
        return self.request_id

    def _jsonrpc_request(self, method: str, params: Optional[Dict] = None) -> Dict:
        """Make a JSON-RPC 2.0 request.

        Args:
            method: JSON-RPC method name (e.g., "tools/list")
            params: Method parameters

        Returns:
            Response result dictionary

        Raises:
            Exception: If JSON-RPC error occurs or HTTP error
        """
        request_payload = {
            "jsonrpc": "2.0",
            "id": self._get_next_id(),
            "method": method,
            "params": params or {}
        }

        try:
            response = self.client.post(
                f"{self.base_url}/",
                json=request_payload
            )
            response.raise_for_status()
            result = response.json()

            # Check for JSON-RPC error
            if "error" in result:
                error = result["error"]
                raise Exception(
                    f"JSON-RPC Error {error['code']}: {error['message']}"
                )

            return result.get("result", {})

        except httpx.HTTPError as e:
            logger.error(f"HTTP error during JSON-RPC request: {e}")
            raise

    def initialize(self) -> Dict[str, Any]:
        """Initialize MCP session with the server.

        Returns:
            Server capabilities and info

        Example:
            >>> client = MCPClient("http://localhost:8080")
            >>> info = client.initialize()
            >>> print(info['serverInfo']['name'])
        """
        return self._jsonrpc_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "roots": {"listChanged": False}
                },
                "clientInfo": {
                    "name": "mcp-python-client",
                    "version": "2.0.0"
                }
            }
        )

    def ping(self) -> Dict[str, Any]:
        """Ping the server to keep connection alive.

        Returns:
            Empty dictionary on success
        """
        return self._jsonrpc_request("ping")

    def list_tools(self) -> List[MCPTool]:
        """List all available tools from the MCP server.

        Returns:
            List of MCPTool objects

        Example:
            >>> client = MCPClient("http://localhost:8080")
            >>> tools = client.list_tools()
            >>> print([tool.name for tool in tools])
        """
        data = self._jsonrpc_request("tools/list")

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

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the MCP server.

        Args:
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool

        Returns:
            Dictionary with 'success' (bool) and 'result' or 'error' (str)

        Example:
            >>> client = MCPClient("http://localhost:8080")
            >>> result = client.call_tool("list_tables", {})
            >>> if result['success']:
            ...     print(result['result'])
        """
        try:
            result = self._jsonrpc_request(
                "tools/call",
                {"name": tool_name, "arguments": arguments}
            )

            # Extract result from MCP response
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
                "result": "Tool executed successfully"
            }

        except Exception as e:
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

        Note:
            This uses the /health endpoint which is not part of JSON-RPC.
        """
        try:
            response = self.client.get(f"{self.base_url}/health")
            response.raise_for_status()
            data = response.json()
            is_healthy = data.get("status") == "healthy"
            if is_healthy:
                logger.info(f"Server healthy, version: {data.get('version', 'unknown')}")
            return is_healthy
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
