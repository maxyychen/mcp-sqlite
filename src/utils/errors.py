"""Custom exception classes for the MCP server."""


class MCPError(Exception):
    """Base exception for MCP-related errors."""

    pass


class DatabaseError(MCPError):
    """Database operation errors."""

    pass


class ValidationError(MCPError):
    """Input validation errors."""

    pass


class SecurityError(MCPError):
    """Security-related errors (SQL injection, etc.)."""

    pass


class ToolExecutionError(MCPError):
    """Tool execution errors."""

    pass
