"""Unit tests for JSON-RPC handler."""
import pytest
from src.jsonrpc.handler import JSONRPCHandler
from src.jsonrpc.models import JSONRPCRequest, JSONRPCResponse, ErrorCode


@pytest.mark.asyncio
async def test_jsonrpc_method_not_found():
    """Test that non-existent methods return METHOD_NOT_FOUND error."""
    handler = JSONRPCHandler()

    request = JSONRPCRequest(
        method="nonexistent_method",
        params={},
        id=1
    )

    response = await handler.handle_request(request)

    assert response.error is not None
    assert response.error.code == ErrorCode.METHOD_NOT_FOUND
    assert "nonexistent_method" in response.error.message
    assert response.result is None


@pytest.mark.asyncio
async def test_jsonrpc_successful_call():
    """Test successful method execution."""
    handler = JSONRPCHandler()

    # Register a test method
    async def test_method(params):
        return {"result": "success", "input": params}

    handler.register_method("test", test_method)

    request = JSONRPCRequest(
        method="test",
        params={"key": "value"},
        id=1
    )

    response = await handler.handle_request(request)

    assert response.error is None
    assert response.result == {"result": "success", "input": {"key": "value"}}
    assert response.id == 1


@pytest.mark.asyncio
async def test_jsonrpc_value_error():
    """Test that ValueError returns INVALID_PARAMS error."""
    handler = JSONRPCHandler()

    async def error_method(params):
        raise ValueError("Invalid parameter provided")

    handler.register_method("error_test", error_method)

    request = JSONRPCRequest(
        method="error_test",
        params={},
        id=2
    )

    response = await handler.handle_request(request)

    assert response.error is not None
    assert response.error.code == ErrorCode.INVALID_PARAMS
    assert "Invalid parameter" in response.error.message


@pytest.mark.asyncio
async def test_jsonrpc_internal_error():
    """Test that unexpected exceptions return INTERNAL_ERROR."""
    handler = JSONRPCHandler()

    async def crash_method(params):
        raise RuntimeError("Something went wrong")

    handler.register_method("crash", crash_method)

    request = JSONRPCRequest(
        method="crash",
        params={},
        id=3
    )

    response = await handler.handle_request(request)

    assert response.error is not None
    assert response.error.code == ErrorCode.INTERNAL_ERROR
    assert response.error.data is not None


@pytest.mark.asyncio
async def test_jsonrpc_no_params():
    """Test method call with no params (None)."""
    handler = JSONRPCHandler()

    async def no_params_method(params):
        assert params == {}
        return {"status": "ok"}

    handler.register_method("no_params", no_params_method)

    request = JSONRPCRequest(
        method="no_params",
        params=None,
        id=4
    )

    response = await handler.handle_request(request)

    assert response.error is None
    assert response.result == {"status": "ok"}


@pytest.mark.asyncio
async def test_jsonrpc_notification():
    """Test notification (no id)."""
    handler = JSONRPCHandler()

    async def notification_method(params):
        return {"received": True}

    handler.register_method("notify", notification_method)

    request = JSONRPCRequest(
        method="notify",
        params={},
        id=None  # Notification
    )

    response = await handler.handle_request(request)

    assert response.id is None
    assert response.result == {"received": True}


def test_error_codes():
    """Test that error codes are correctly defined."""
    assert ErrorCode.PARSE_ERROR == -32700
    assert ErrorCode.INVALID_REQUEST == -32600
    assert ErrorCode.METHOD_NOT_FOUND == -32601
    assert ErrorCode.INVALID_PARAMS == -32602
    assert ErrorCode.INTERNAL_ERROR == -32603
    assert ErrorCode.TOOL_NOT_FOUND == -32001
    assert ErrorCode.TOOL_EXECUTION_ERROR == -32002
    assert ErrorCode.DATABASE_ERROR == -32003
