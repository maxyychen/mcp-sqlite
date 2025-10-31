# MCP SQLite Server

A Model Context Protocol (MCP) server with **Streamable HTTP transport** for SQLite database CRUD operations.

## Features

- ✅ **MCP Streamable HTTP** - Full MCP specification compliance (2024-11-05)
- ✅ **Stateful Sessions** - Session management with automatic cleanup
- ✅ **Bidirectional Communication** - SSE for server-to-client messaging
- ✅ **Stream Resumability** - Reconnect and resume from last event
- ✅ **8 CRUD Tools** - Complete database operations
- ✅ **Security First** - SQL injection prevention, input validation
- ✅ **Docker Ready** - Multi-stage build, production-optimized (~150-200MB)
- ✅ **Type Safe** - Full Python type hints and Pydantic models
- ✅ **Async Support** - FastAPI async/await patterns
- ✅ **Backward Compatible** - Legacy JSON-RPC 2.0 endpoints still work

## Quick Start

### Option 1: Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run server
uvicorn src.server:app --reload --port 8080
```

### Option 2: Docker

```bash
# Build and run with Docker
docker build -t mcp-sqlite-server:latest .
docker run -d -p 8080:8080 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  --name mcp-server \
  mcp-sqlite-server:latest
```

### Option 3: Docker Compose (Recommended)

```bash
# Start services
docker-compose up -d  
or  
docker compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Testing the Server

### MCP Streamable HTTP (Recommended)

```bash
# Check health
curl http://localhost:8080/health

# Initialize MCP session (note the /mcp endpoint)
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
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

# Save the Mcp-Session-Id from response headers!
# Example: Mcp-Session-Id: 318a19a9-b757-4c0b-9ddb-a8dc1b40d240

# Ping server (use your session ID)
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -H "Mcp-Session-Id: YOUR_SESSION_ID_HERE" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "ping",
    "params": {}
  }'

# List available tools
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -H "Mcp-Session-Id: YOUR_SESSION_ID_HERE" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/list",
    "params": {}
  }'

# Open SSE stream for server notifications
curl -N http://localhost:8080/mcp \
  -H "Mcp-Session-Id: YOUR_SESSION_ID_HERE"

# Create a table
curl -X POST http://localhost:8080/mcp \
  -H "Mcp-Session-Id: YOUR_SESSION_ID_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 4,
    "method": "tools/call",
    "params": {
      "name": "create_table",
      "arguments": {
        "table_name": "users",
        "schema": {
          "id": "INTEGER",
          "name": "TEXT",
          "email": "TEXT"
        },
        "primary_key": "id"
      }
    }
  }'

# Insert a record
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -H "Mcp-Session-Id: YOUR_SESSION_ID_HERE" \
  -d '{
    "jsonrpc": "2.0",
    "id": 5,
    "method": "tools/call",
    "params": {
      "name": "insert_record",
      "arguments": {
        "table_name": "users",
        "data": {
          "id": 1,
          "name": "John Doe",
          "email": "john@example.com"
        }
      }
    }
  }'

# Query records
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -H "Mcp-Session-Id: YOUR_SESSION_ID_HERE" \
  -d '{
    "jsonrpc": "2.0",
    "id": 6,
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

### Legacy JSON-RPC 2.0 (Still Supported)

For backward compatibility, the old endpoints still work:

```bash
# These work without session management
curl -X POST http://localhost:8080/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"ping","params":{}}'
```

## Available MCP Tools

### 1. `create_table`
Create a new table in the database.

**Parameters:**
- `table_name` (string, required): Name of the table
- `schema` (object, required): Column definitions with types
- `primary_key` (string, optional): Primary key column name

**Example:**
```json
{
  "table_name": "products",
  "schema": {
    "id": "INTEGER",
    "name": "TEXT",
    "price": "REAL"
  },
  "primary_key": "id"
}
```

### 2. `insert_record`
Insert a new record into a table.

**Parameters:**
- `table_name` (string, required): Target table
- `data` (object, required): Key-value pairs for the record

**Example:**
```json
{
  "table_name": "products",
  "data": {
    "id": 1,
    "name": "Widget",
    "price": 19.99
  }
}
```

### 3. `query_records`
Query/read records from a table.

**Parameters:**
- `table_name` (string, required): Target table
- `filters` (object, optional): WHERE clause conditions
- `limit` (integer, optional): Maximum records to return
- `offset` (integer, optional): Pagination offset
- `order_by` (string, optional): Column to sort by

**Example:**
```json
{
  "table_name": "products",
  "filters": {"price": 19.99},
  "limit": 10,
  "order_by": "name"
}
```

### 4. `update_record`
Update existing record(s).

**Parameters:**
- `table_name` (string, required): Target table
- `filters` (object, required): WHERE clause conditions
- `data` (object, required): Fields to update

**Example:**
```json
{
  "table_name": "products",
  "filters": {"id": 1},
  "data": {"price": 24.99}
}
```

### 5. `delete_record`
Delete record(s) from a table.

**Parameters:**
- `table_name` (string, required): Target table
- `filters` (object, required): WHERE clause conditions

**Example:**
```json
{
  "table_name": "products",
  "filters": {"id": 1}
}
```

### 6. `list_tables`
List all tables in the database.

**Parameters:** None

### 7. `describe_table`
Get detailed schema information for a table.

**Parameters:**
- `table_name` (string, required): Target table

**Example:**
```json
{
  "table_name": "products"
}
```

### 8. `execute_raw_query`
Execute custom SQL query (with safety controls).

**Parameters:**
- `query` (string, required): SQL query to execute
- `params` (array, optional): Parameterized query values
- `read_only` (boolean, optional): Enforce read-only mode (default: true)

**Example:**
```json
{
  "query": "SELECT * FROM products WHERE price > ?",
  "params": [10.0],
  "read_only": true
}
```

## API Endpoints

### MCP Streamable HTTP (Primary)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/mcp` | MCP requests with session management |
| GET | `/mcp` | Open SSE stream for server notifications |
| GET | `/health` | Health check |

**Required Headers:**
- `Mcp-Session-Id`: Session ID (after initialize)
- `Mcp-Protocol-Version`: `2024-11-05`
- `Accept`: `application/json, text/event-stream`

### Legacy Endpoints (Backward Compatible)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/`, `/rpc`, `/jsonrpc` | Plain JSON-RPC 2.0 (no sessions) |
| GET | `/sse` | Legacy SSE (deprecated) |

### JSON-RPC Methods

| Method | Description |
|--------|-------------|
| `initialize` | Initialize MCP session (returns session ID) |
| `ping` | Keep-alive ping |
| `tools/list` | List available tools |
| `tools/call` | Execute a tool |

## Configuration

Edit `config/config.yaml`:

```yaml
server:
  host: "0.0.0.0"
  port: 8080
  debug: true

database:
  path: "./data/database.db"
  connection_timeout: 30
  max_connections: 5

security:
  enable_auth: false
  max_query_results: 1000
  allow_raw_queries: true
  read_only_mode: false
```

## Project Structure

```
mcp_template/
├── src/
│   ├── server.py              # FastAPI server with tool registration
│   ├── mcp_handler.py         # MCP protocol implementation
│   ├── database/
│   │   ├── connection.py      # Database connection manager
│   │   ├── crud_operations.py # CRUD implementation
│   │   └── query_builder.py   # Safe SQL query builder
│   └── utils/
│       ├── errors.py          # Custom exceptions
│       ├── validation.py      # Input validation
│       └── security.py        # SQL injection prevention
├── tests/                     # Test suite
├── config/                    # Configuration files
├── data/                      # SQLite database storage
├── logs/                      # Application logs
├── Dockerfile                 # Docker image definition
├── docker-compose.yml         # Docker Compose setup
└── requirements.txt           # Python dependencies
```

## Security Features

- **SQL Injection Prevention**: Parameterized queries exclusively
- **Input Validation**: Regex-based identifier validation
- **Identifier Sanitization**: All table/column names validated
- **Read-only Mode**: Optional enforcement for raw queries
- **Non-root User**: Docker runs as `mcpuser` (UID 1000)

## Development

```bash
# Install dev dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Type checking
mypy src/

# Linting
ruff check src/

# Code formatting
black src/
```

## Docker Image Details

- **Base Image**: `python:3.11-slim`
- **Size**: ~150-200MB (optimized with multi-stage build)
- **User**: Non-root `mcpuser`
- **Health Checks**: Built-in
- **Volumes**: `/app/data` (database), `/app/logs` (logs)

## License

MIT License

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## Support

For issues and questions, please open an issue on GitHub.
