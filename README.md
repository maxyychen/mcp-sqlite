# MCP SQLite Server

A Model Context Protocol (MCP) server with HTTP+SSE transport for SQLite database CRUD operations.

## Features

- ✅ **MCP Protocol Compliant** - Full HTTP+SSE implementation
- ✅ **8 CRUD Tools** - Complete database operations
- ✅ **Security First** - SQL injection prevention, input validation
- ✅ **Docker Ready** - Multi-stage build, production-optimized (~150-200MB)
- ✅ **Type Safe** - Full Python type hints and Pydantic models
- ✅ **Async Support** - FastAPI async/await patterns

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

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Testing the Server

```bash
# Check health
curl http://localhost:8080/health

# List available tools
curl -X POST http://localhost:8080/mcp/v1/tools/list

# Create a table
curl -X POST http://localhost:8080/mcp/v1/tools/call \
  -H "Content-Type: application/json" \
  -d '{
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
  }'

# Insert a record
curl -X POST http://localhost:8080/mcp/v1/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "name": "insert_record",
    "arguments": {
      "table_name": "users",
      "data": {
        "id": 1,
        "name": "John Doe",
        "email": "john@example.com"
      }
    }
  }'

# Query records
curl -X POST http://localhost:8080/mcp/v1/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "name": "query_records",
    "arguments": {
      "table_name": "users",
      "limit": 10
    }
  }'
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

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/mcp/v1/tools/list` | List available tools |
| POST | `/mcp/v1/tools/call` | Execute a tool |
| GET | `/mcp/v1/sse` | SSE stream for notifications |

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
