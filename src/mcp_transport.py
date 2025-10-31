"""MCP Streamable HTTP transport implementation."""
import json
import asyncio
import logging
from typing import AsyncGenerator, Optional, Dict, Any
from fastapi import Request, Response
from sse_starlette.sse import EventSourceResponse

from .mcp_session import MCPSessionManager, MCPSession
from .jsonrpc.handler import JSONRPCHandler
from .jsonrpc.models import JSONRPCRequest, JSONRPCResponse

logger = logging.getLogger(__name__)

# MCP Protocol Version
MCP_PROTOCOL_VERSION = "2024-11-05"


class MCPTransport:
    """Handles MCP Streamable HTTP transport."""

    def __init__(self, jsonrpc_handler: JSONRPCHandler):
        self.jsonrpc_handler = jsonrpc_handler
        self.session_manager = MCPSessionManager()

    async def handle_post_request(
        self,
        request: Request,
        jsonrpc_request: JSONRPCRequest
    ) -> Response:
        """Handle POST request from client.

        Per MCP spec: Every JSON-RPC message from client MUST be a new HTTP POST.
        Server may respond with either JSON or initiate an SSE stream.
        """
        # Extract session ID from header
        session_id = request.headers.get("Mcp-Session-Id")

        # Validate protocol version
        protocol_version = request.headers.get("Mcp-Protocol-Version")
        if protocol_version and protocol_version != MCP_PROTOCOL_VERSION:
            logger.warning(f"Client protocol version mismatch: {protocol_version}")

        # Get or create session
        if session_id:
            session = self.session_manager.get_session(session_id)
            if not session:
                logger.warning(f"Session not found: {session_id}, creating new one")
                session = self.session_manager.create_session()
        else:
            # First request - create new session
            session = self.session_manager.create_session()

        # Handle the JSON-RPC request
        jsonrpc_response = await self.jsonrpc_handler.handle_request(jsonrpc_request)

        # Check Accept header to determine response type
        accept = request.headers.get("Accept", "application/json")
        wants_sse = "text/event-stream" in accept

        # For initialize method, always return JSON with session header
        if jsonrpc_request.method == "initialize":
            response_data = jsonrpc_response.model_dump(exclude_none=True)
            return Response(
                content=json.dumps(response_data),
                media_type="application/json",
                headers={
                    "Mcp-Session-Id": session.session_id,
                    "Mcp-Protocol-Version": MCP_PROTOCOL_VERSION
                }
            )

        # For requests (has id), return JSON response
        if jsonrpc_request.id is not None:
            response_data = jsonrpc_response.model_dump(exclude_none=True)
            return Response(
                content=json.dumps(response_data),
                media_type="application/json",
                headers={
                    "Mcp-Session-Id": session.session_id,
                    "Mcp-Protocol-Version": MCP_PROTOCOL_VERSION
                }
            )

        # For notifications (no id), return 202 Accepted
        return Response(
            status_code=202,
            headers={
                "Mcp-Session-Id": session.session_id,
                "Mcp-Protocol-Version": MCP_PROTOCOL_VERSION
            }
        )

    async def handle_get_request(self, request: Request) -> EventSourceResponse:
        """Handle GET request to open SSE stream.

        Per MCP spec: Clients may issue HTTP GET requests to open an SSE stream,
        allowing the server to push messages without waiting for client requests.
        """
        # Get session ID from header
        session_id = request.headers.get("Mcp-Session-Id")

        if not session_id:
            # No session ID - client should initialize first
            return Response(
                content=json.dumps({"error": "No session ID provided. Initialize first."}),
                status_code=400,
                media_type="application/json"
            )

        session = self.session_manager.get_session(session_id)
        if not session:
            return Response(
                content=json.dumps({"error": "Invalid session ID"}),
                status_code=404,
                media_type="application/json"
            )

        # Check for resumption
        last_event_id = request.headers.get("Last-Event-Id")

        async def event_generator() -> AsyncGenerator[dict, None]:
            """Generate SSE events."""
            try:
                # If resuming, send missed messages first
                if last_event_id:
                    missed_messages = session.get_messages_after(last_event_id)
                    for msg in missed_messages:
                        yield {
                            "data": msg.data,
                            "event": msg.event or "message",
                            "id": msg.id
                        }

                # Send a connection confirmation
                event_id = session.get_next_event_id()
                yield {
                    "data": json.dumps({
                        "type": "connection",
                        "message": "SSE stream established"
                    }),
                    "event": "message",
                    "id": event_id
                }

                # Stream messages from queue
                while True:
                    try:
                        # Wait for messages with timeout
                        message = await asyncio.wait_for(
                            session.message_queue.get(),
                            timeout=30.0
                        )
                        yield {
                            "data": message.data,
                            "event": message.event or "message",
                            "id": message.id
                        }
                    except asyncio.TimeoutError:
                        # Send keepalive comment every 30s
                        yield {"comment": "keepalive"}
                        continue

            except asyncio.CancelledError:
                logger.info(f"SSE stream cancelled for session {session_id}")
                raise
            except Exception as e:
                logger.error(f"Error in SSE stream: {e}", exc_info=True)
                raise

        return EventSourceResponse(
            event_generator(),
            headers={
                "Mcp-Session-Id": session.session_id,
                "Mcp-Protocol-Version": MCP_PROTOCOL_VERSION
            }
        )

    async def send_notification(
        self,
        session_id: str,
        method: str,
        params: Optional[Dict[str, Any]] = None
    ):
        """Send a notification to a client via SSE.

        This allows the server to push messages to the client.
        """
        session = self.session_manager.get_session(session_id)
        if not session:
            logger.warning(f"Cannot send notification: session {session_id} not found")
            return

        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {}
        }

        await session.queue_message(
            data=json.dumps(notification),
            event="message"
        )
        logger.debug(f"Queued notification for session {session_id}: {method}")

    def start_cleanup(self):
        """Start background cleanup of expired sessions."""
        self.session_manager.start_background_cleanup()

    def stop_cleanup(self):
        """Stop background cleanup."""
        self.session_manager.stop_background_cleanup()
