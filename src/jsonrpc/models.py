"""JSON-RPC 2.0 request/response models."""
from pydantic import BaseModel, Field
from typing import Any, Optional, Union, Literal


class JSONRPCRequest(BaseModel):
    """JSON-RPC 2.0 request model."""

    jsonrpc: Literal["2.0"] = "2.0"
    method: str
    params: Optional[dict] = None
    id: Optional[Union[str, int]] = None


class JSONRPCError(BaseModel):
    """JSON-RPC 2.0 error model."""

    code: int
    message: str
    data: Optional[Any] = None


class JSONRPCResponse(BaseModel):
    """JSON-RPC 2.0 response model."""

    jsonrpc: Literal["2.0"] = "2.0"
    id: Optional[Union[str, int]]
    result: Optional[Any] = None
    error: Optional[JSONRPCError] = None


class ErrorCode:
    """JSON-RPC 2.0 standard error codes and custom application codes."""

    # Standard JSON-RPC 2.0 error codes
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603

    # Custom application error codes
    TOOL_NOT_FOUND = -32001
    TOOL_EXECUTION_ERROR = -32002
    DATABASE_ERROR = -32003
