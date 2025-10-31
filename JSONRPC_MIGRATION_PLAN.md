# JSON-RPC 2.0 Migration Plan

## Executive Summary

This document outlines the plan to migrate the MCP SQLite Server from REST-like HTTP endpoints to full JSON-RPC 2.0 compliance per the MCP specification.

**Migration Effort**: Low-Medium (1-2 days)
**Risk Level**: Medium (breaking change - no backward compatibility)
**Benefits**: Full MCP compliance, broader client compatibility, standardized error handling, cleaner codebase

---

## 1. Current State Analysis

### Current Architecture
```
REST-like Endpoints:
- GET  /health                    # Health check
- POST /mcp/v1/tools/list         # List tools
- POST /mcp/v1/tools/call         # Execute tool
- GET  /mcp/v1/sse                # SSE stream
```

### Current Request/Response Format
```json
// Request
POST /mcp/v1/tools/call
{
  "name": "query_records",
  "arguments": {
    "table_name": "users"
  }
}

// Response
{
  "content": [
    {"type": "text", "text": "result"}
  ],
  "isError": false
}
```

---

## 2. Target State (JSON-RPC 2.0)

### Target Architecture
```
Unified JSON-RPC Endpoint:
- POST /                          # Main JSON-RPC endpoint (or /rpc, /jsonrpc)
- GET  /health                    # Keep for monitoring
- GET  /sse                       # SSE stream for notifications
```

### JSON-RPC 2.0 Request Format
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "query_records",
    "arguments": {
      "table_name": "users"
    }
  }
}
```

### JSON-RPC 2.0 Response Format
```json
// Success
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {"type": "text", "text": "result"}
    ]
  }
}

// Error
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32602,
    "message": "Invalid params",
    "data": {
      "details": "table_name is required"
    }
  }
}
```

---

## 3. MCP Methods to Implement

According to MCP specification, we need to support these JSON-RPC methods:

### 3.1 Core Methods
```
initialize              # Initialize MCP session
ping                    # Keep-alive
tools/list              # List available tools
tools/call              # Execute a tool
```

### 3.2 Optional Methods (Future)
```
resources/list          # List available resources
prompts/list            # List available prompts
logging/setLevel        # Configure logging
```

---

## 4. Implementation Plan

### Phase 1: Add JSON-RPC Handler (Day 1)

#### 1.1 Create JSON-RPC Models
**File**: `src/jsonrpc/models.py` (NEW)

```python
from pydantic import BaseModel, Field
from typing import Any, Optional, Union, Literal

class JSONRPCRequest(BaseModel):
    jsonrpc: Literal["2.0"] = "2.0"
    method: str
    params: Optional[dict] = None
    id: Optional[Union[str, int]] = None

class JSONRPCError(BaseModel):
    code: int
    message: str
    data: Optional[Any] = None

class JSONRPCResponse(BaseModel):
    jsonrpc: Literal["2.0"] = "2.0"
    id: Optional[Union[str, int]]
    result: Optional[Any] = None
    error: Optional[JSONRPCError] = None

# Error codes per JSON-RPC spec
class ErrorCode:
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    # Custom application errors
    TOOL_NOT_FOUND = -32001
    TOOL_EXECUTION_ERROR = -32002
    DATABASE_ERROR = -32003
```

#### 1.2 Create JSON-RPC Handler
**File**: `src/jsonrpc/handler.py` (NEW)

```python
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
    def __init__(self):
        self.methods: Dict[str, Callable] = {}

    def register_method(self, method_name: str, handler: Callable):
        """Register a JSON-RPC method handler."""
        self.methods[method_name] = handler
        logger.info(f"Registered JSON-RPC method: {method_name}")

    async def handle_request(
        self,
        request: JSONRPCRequest
    ) -> JSONRPCResponse:
        """Handle a JSON-RPC request."""
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
            return JSONRPCResponse(
                id=request.id,
                error=JSONRPCError(
                    code=ErrorCode.INVALID_PARAMS,
                    message=str(e)
                )
            )
        except Exception as e:
            logger.error(f"Internal error: {e}", exc_info=True)
            return JSONRPCResponse(
                id=request.id,
                error=JSONRPCError(
                    code=ErrorCode.INTERNAL_ERROR,
                    message="Internal error",
                    data={"details": str(e)}
                )
            )
```

#### 1.3 Replace Server Endpoints with JSON-RPC
**File**: `src/server.py` (MAJOR UPDATE)

```python
from .jsonrpc.handler import JSONRPCHandler
from .jsonrpc.models import JSONRPCRequest, JSONRPCResponse

# Initialize JSON-RPC handler
jsonrpc_handler = JSONRPCHandler()

# Register JSON-RPC methods
def register_jsonrpc_methods():
    """Register all JSON-RPC methods."""

    # Method: initialize
    async def initialize(params: dict):
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {"listChanged": False},
                "logging": {}
            },
            "serverInfo": {
                "name": "mcp-sqlite-server",
                "version": "1.0.0"
            }
        }

    # Method: ping
    async def ping(params: dict):
        return {}

    # Method: tools/list
    async def tools_list(params: dict):
        tools = mcp_handler.list_tools()
        return {"tools": tools}

    # Method: tools/call
    async def tools_call(params: dict):
        name = params.get("name")
        arguments = params.get("arguments", {})

        if not name:
            raise ValueError("Tool name is required")

        result = await mcp_handler.execute_tool(name, arguments)
        return {
            "content": [{"type": "text", "text": str(result)}]
        }

    # Register methods
    jsonrpc_handler.register_method("initialize", initialize)
    jsonrpc_handler.register_method("ping", ping)
    jsonrpc_handler.register_method("tools/list", tools_list)
    jsonrpc_handler.register_method("tools/call", tools_call)

# Update lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting MCP server...")
    register_all_tools()
    register_jsonrpc_methods()
    logger.info(f"Registered {len(mcp_handler.tools)} MCP tools")
    yield
    logger.info("Shutting down MCP server...")

# REMOVE old endpoints and models (ToolCallRequest, MCPResponse)
# REPLACE with JSON-RPC endpoint only

# JSON-RPC endpoint
@app.post("/")
@app.post("/rpc")
@app.post("/jsonrpc")
async def jsonrpc_endpoint(request: JSONRPCRequest):
    """Main JSON-RPC 2.0 endpoint."""
    response = await jsonrpc_handler.handle_request(request)
    return response.model_dump(exclude_none=True)

# Keep health check and SSE
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "mcp-sqlite-server"}

@app.get("/sse")
async def sse_endpoint():
    """SSE endpoint for real-time notifications."""
    async def event_generator() -> AsyncGenerator[dict, None]:
        yield {
            "event": "message",
            "data": '{"type": "notification", "message": "Connected to MCP server"}',
        }
    return EventSourceResponse(event_generator())
```

### Phase 2: Update Client Library (Day 1)

#### 2.1 Rewrite MCPClient for JSON-RPC Only
**File**: `py-mcp-client/mcp_client.py` (MAJOR UPDATE)

```python
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

    def _get_next_id(self) -> int:
        """Get next request ID."""
        self.request_id += 1
        return self.request_id

    def _jsonrpc_request(self, method: str, params: Optional[Dict] = None) -> Dict:
        """Make a JSON-RPC 2.0 request.

        Args:
            method: JSON-RPC method name
            params: Method parameters

        Returns:
            Response result

        Raises:
            Exception: If JSON-RPC error occurs
        """
        request_payload = {
            "jsonrpc": "2.0",
            "id": self._get_next_id(),
            "method": method,
            "params": params or {}
        }

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

    def initialize(self) -> Dict[str, Any]:
        """Initialize MCP session.

        Returns:
            Server capabilities and info
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
                    "version": "1.0.0"
                }
            }
        )

    def ping(self) -> Dict[str, Any]:
        """Ping the server to keep connection alive."""
        return self._jsonrpc_request("ping")

    def list_tools(self) -> List[MCPTool]:
        """List all available tools."""
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
        """Call a tool.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            Dictionary with success status and result/error
        """
        try:
            result = self._jsonrpc_request(
                "tools/call",
                {"name": tool_name, "arguments": arguments}
            )
            content = result.get("content", [])
            if content:
                return {
                    "success": True,
                    "result": content[0].get("text", "")
                }
            return {
                "success": True,
                "result": "Tool executed successfully"
            }

        except Exception as e:
            logger.error(f"Failed to call tool {tool_name}: {e}")
            return {"success": False, "error": str(e)}
```

### Phase 3: Testing (Day 1-2)

#### 3.1 Unit Tests
**File**: `tests/test_jsonrpc.py` (NEW)

```python
import pytest
from src.jsonrpc.handler import JSONRPCHandler
from src.jsonrpc.models import JSONRPCRequest, ErrorCode

@pytest.mark.asyncio
async def test_jsonrpc_method_not_found():
    handler = JSONRPCHandler()
    request = JSONRPCRequest(
        method="nonexistent",
        params={},
        id=1
    )
    response = await handler.handle_request(request)
    assert response.error is not None
    assert response.error.code == ErrorCode.METHOD_NOT_FOUND

@pytest.mark.asyncio
async def test_jsonrpc_success():
    handler = JSONRPCHandler()

    async def test_method(params):
        return {"result": "success"}

    handler.register_method("test", test_method)

    request = JSONRPCRequest(
        method="test",
        params={},
        id=1
    )
    response = await handler.handle_request(request)
    assert response.error is None
    assert response.result == {"result": "success"}
```

#### 3.2 Integration Tests
**File**: `tests/test_jsonrpc_integration.py` (NEW)

```python
import pytest
from httpx import AsyncClient
from src.server import app

@pytest.mark.asyncio
async def test_jsonrpc_initialize():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1.0"}
                }
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert "result" in data
        assert "serverInfo" in data["result"]

@pytest.mark.asyncio
async def test_jsonrpc_tools_list():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/",
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {}
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        assert "tools" in data["result"]
        assert len(data["result"]["tools"]) == 8

@pytest.mark.asyncio
async def test_jsonrpc_tools_call():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/",
            json={
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "list_tables",
                    "arguments": {}
                }
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
```

### Phase 4: Documentation Updates (Day 2)

#### 4.1 Update README.md

```markdown
## Testing the Server (JSON-RPC 2.0)

### Initialize Session
curl -X POST http://localhost:8080/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2024-11-05",
      "capabilities": {},
      "clientInfo": {"name": "curl-client", "version": "1.0"}
    }
  }'

### List Tools
curl -X POST http://localhost:8080/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list",
    "params": {}
  }'

### Call a Tool
curl -X POST http://localhost:8080/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "query_records",
      "arguments": {
        "table_name": "users",
        "limit": 10
      }
    }
  }'
```

---

## 5. File Changes Summary

### New Files
```
src/jsonrpc/
├── __init__.py
├── models.py           # JSON-RPC request/response models
└── handler.py          # JSON-RPC request handler

tests/test_jsonrpc.py                    # Unit tests
tests/test_jsonrpc_integration.py        # Integration tests
MIGRATION_GUIDE.md                       # Client migration guide
```

### Modified Files
```
src/server.py                            # Replace REST with JSON-RPC endpoints
py-mcp-client/mcp_client.py             # Rewrite for JSON-RPC only
README.md                                # Update all examples
requirements.txt                         # (no changes needed)
```

---

## 6. Migration Timeline

| Day | Phase | Tasks | Deliverables |
|-----|-------|-------|--------------|
| 1 | Implementation | Create JSON-RPC handler, models, replace server endpoints | Working JSON-RPC endpoint |
| 1 | Client Update | Rewrite client library for JSON-RPC only | Pure JSON-RPC client |
| 1-2 | Testing | Write and run comprehensive tests | 100% test coverage |
| 2 | Documentation | Update README, examples, create migration guide | Complete docs |

**Total Time**: 1-2 days

---

## 7. Testing Strategy

### 7.1 Manual Testing Checklist
- [ ] JSON-RPC initialize method works
- [ ] JSON-RPC ping method works
- [ ] JSON-RPC tools/list returns all 8 tools
- [ ] JSON-RPC tools/call executes each tool successfully
- [ ] Error responses follow JSON-RPC spec
- [ ] Old REST endpoints return 404 (removed)
- [ ] SSE stream still functional at /sse
- [ ] Health check still works at /health

### 7.2 Automated Testing
```bash
# Run unit tests
pytest tests/test_jsonrpc.py -v

# Run integration tests
pytest tests/test_jsonrpc_integration.py -v

# Run all tests with coverage
pytest tests/ -v --cov=src --cov-report=html
```

### 7.3 Load Testing
```bash
# Test JSON-RPC endpoint performance
ab -n 1000 -c 10 -p request.json -T application/json \
  http://localhost:8080/
```

---

## 8. Rollback Plan

If critical issues arise during migration:

### Quick Rollback
```bash
# Revert to previous version
git revert HEAD
docker-compose down
docker-compose up -d --build
```

### Full Rollback
```bash
# Checkout previous commit
git checkout <previous-commit>
docker-compose down
docker-compose up -d --build

# Notify clients to revert to old client version
```

**Important**: Since this is a breaking change, ensure you have:
- Backup of current working code
- Tested rollback procedure before migration
- Communication plan for all API consumers

---

## 9. Success Criteria

- ✅ All JSON-RPC 2.0 methods implemented (initialize, ping, tools/list, tools/call)
- ✅ Legacy REST endpoints completely removed
- ✅ 100% test coverage for JSON-RPC handler
- ✅ Documentation updated with JSON-RPC examples only
- ✅ Client library fully rewritten for JSON-RPC 2.0
- ✅ No performance degradation
- ✅ Error handling follows JSON-RPC spec
- ✅ All existing clients updated to use new protocol

---

## 10. Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Breaking existing clients | High | **High** | **Communicate migration plan, coordinate client updates** |
| Performance issues | Medium | Low | Comprehensive load testing |
| Incomplete spec implementation | Medium | Medium | Reference MCP spec closely, test with real MCP clients |
| Client library bugs | High | Medium | Thorough testing, provide migration examples |
| Rollback complexity | High | Low | Test rollback procedure before migration |

**⚠️ Critical Risk**: This is a breaking change. All existing API consumers must be updated simultaneously or during a planned maintenance window.

---

## 11. Pre-Migration Checklist

Before starting the migration:

- [ ] Identify all API consumers (internal and external)
- [ ] Communicate breaking change with timeline
- [ ] Prepare updated client code for all consumers
- [ ] Schedule maintenance window if needed
- [ ] Create backup of current production code
- [ ] Test rollback procedure in staging
- [ ] Prepare monitoring and alerting
- [ ] Document all changes for stakeholders

---

## 12. Next Steps

1. **⚠️ Identify all API consumers** and notify them of breaking change
2. **Review and approve this plan** with all stakeholders
3. **Schedule maintenance window** for production deployment
4. **Create feature branch**: `git checkout -b feature/jsonrpc-2.0`
5. **Phase 1**: Implement JSON-RPC handler and update server
6. **Phase 2**: Update client library
7. **Phase 3**: Comprehensive testing (unit, integration, manual)
8. **Phase 4**: Update all documentation
9. **Deploy to staging**: Test thoroughly in staging environment
10. **Update all client applications** to use new client library
11. **Production deployment**: Deploy during maintenance window
12. **Monitor**: Watch for errors and performance issues post-deployment

---

## 13. References

- [JSON-RPC 2.0 Specification](https://www.jsonrpc.org/specification)
- [MCP Specification](https://modelcontextprotocol.io/docs/specification)
- [FastAPI JSON-RPC](https://fastapi.tiangolo.com/)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)

