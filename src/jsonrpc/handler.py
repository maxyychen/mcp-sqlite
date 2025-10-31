"""JSON-RPC 2.0 request handler."""
from typing import Any, Dict, Callable
import logging
from .models import (
    JSONRPCRequest,
    JSONRPCResponse,
    JSONRPCError,
    ErrorCode
)

logger = logging.getLogger(__name__)


class JSONRPCHandler:
    """Handles JSON-RPC 2.0 requests and routes to registered methods."""

    def __init__(self):
        self.methods: Dict[str, Callable] = {}

    def register_method(self, method_name: str, handler: Callable):
        """Register a JSON-RPC method handler.

        Args:
            method_name: Name of the JSON-RPC method (e.g., "tools/list")
            handler: Async callable that handles the method
        """
        self.methods[method_name] = handler
        logger.info(f"Registered JSON-RPC method: {method_name}")

    async def handle_request(
        self,
        request: JSONRPCRequest
    ) -> JSONRPCResponse:
        """Handle a JSON-RPC 2.0 request.

        Args:
            request: JSONRPCRequest object

        Returns:
            JSONRPCResponse with result or error
        """
        try:
            # Validate method exists
            if request.method not in self.methods:
                return JSONRPCResponse(
                    id=request.id,
                    error=JSONRPCError(
                        code=ErrorCode.METHOD_NOT_FOUND,
                        message=f"Method not found: {request.method}"
                    )
                )

            # Execute method
            handler = self.methods[request.method]
            result = await handler(request.params or {})

            # Return success response
            return JSONRPCResponse(
                id=request.id,
                result=result
            )

        except ValueError as e:
            # Invalid parameters
            return JSONRPCResponse(
                id=request.id,
                error=JSONRPCError(
                    code=ErrorCode.INVALID_PARAMS,
                    message=str(e)
                )
            )
        except Exception as e:
            # Internal error
            logger.error(f"Internal error handling {request.method}: {e}", exc_info=True)
            return JSONRPCResponse(
                id=request.id,
                error=JSONRPCError(
                    code=ErrorCode.INTERNAL_ERROR,
                    message="Internal error",
                    data={"details": str(e)}
                )
            )
