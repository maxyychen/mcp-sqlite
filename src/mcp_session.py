"""MCP Session Management for Streamable HTTP transport."""
import asyncio
import uuid
import logging
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class MCPMessage:
    """Represents a message in the SSE stream."""
    id: str
    data: str
    event: Optional[str] = None


@dataclass
class MCPSession:
    """Represents an active MCP session."""
    session_id: str
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    message_queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    messages_sent: List[MCPMessage] = field(default_factory=list)
    last_event_id: int = 0

    def get_next_event_id(self) -> str:
        """Generate next event ID for SSE."""
        self.last_event_id += 1
        return str(self.last_event_id)

    async def queue_message(self, data: str, event: Optional[str] = None):
        """Queue a message to be sent via SSE."""
        event_id = self.get_next_event_id()
        message = MCPMessage(id=event_id, data=data, event=event)
        self.messages_sent.append(message)
        await self.message_queue.put(message)
        self.last_activity = datetime.now()

    def get_messages_after(self, last_event_id: str) -> List[MCPMessage]:
        """Get messages after a specific event ID for resumption."""
        try:
            last_id = int(last_event_id)
            return [msg for msg in self.messages_sent if int(msg.id) > last_id]
        except (ValueError, AttributeError):
            return []


class MCPSessionManager:
    """Manages MCP sessions for Streamable HTTP transport."""

    def __init__(self, session_timeout_minutes: int = 30):
        self.sessions: Dict[str, MCPSession] = {}
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
        self._cleanup_task: Optional[asyncio.Task] = None

    def create_session(self) -> MCPSession:
        """Create a new MCP session."""
        session_id = str(uuid.uuid4())
        session = MCPSession(session_id=session_id)
        self.sessions[session_id] = session
        logger.info(f"Created MCP session: {session_id}")
        return session

    def get_session(self, session_id: str) -> Optional[MCPSession]:
        """Get an existing session by ID."""
        session = self.sessions.get(session_id)
        if session:
            session.last_activity = datetime.now()
        return session

    def delete_session(self, session_id: str):
        """Delete a session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Deleted MCP session: {session_id}")

    async def cleanup_expired_sessions(self):
        """Remove sessions that have been inactive for too long."""
        now = datetime.now()
        expired = [
            sid for sid, session in self.sessions.items()
            if now - session.last_activity > self.session_timeout
        ]
        for session_id in expired:
            self.delete_session(session_id)
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired sessions")

    async def start_cleanup_task(self):
        """Start background task to clean up expired sessions."""
        while True:
            await asyncio.sleep(300)  # Every 5 minutes
            await self.cleanup_expired_sessions()

    def start_background_cleanup(self):
        """Start cleanup task in background."""
        if not self._cleanup_task:
            self._cleanup_task = asyncio.create_task(self.start_cleanup_task())

    def stop_background_cleanup(self):
        """Stop cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            self._cleanup_task = None
