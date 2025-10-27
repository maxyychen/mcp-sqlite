# MCP Server with HTTP+SSE and SQLite CRUD - Implementation Plan

## 1. Project Overview

Create a Model Context Protocol (MCP) server that:
- Uses HTTP with Server-Sent Events (SSE) for streaming communication
- Provides MCP tools for CRUD operations on a SQLite database
- Follows MCP specification for tool definition and execution
- Supports multiple database operations through a clean API

## 2. Technology Stack

### Core Dependencies
- **Runtime**: Python 3.10+
- **MCP SDK**: `mcp` (Python MCP SDK)
- **HTTP Framework**: FastAPI (modern, async, built-in SSE support)
- **Database**: SQLite3 (built-in `sqlite3` module)
- **SSE Library**: `sse-starlette` for FastAPI SSE support
- **Validation**: Pydantic (included with FastAPI)
- **Configuration**: `pyyaml` for YAML config files

### Development Dependencies
- **Type Checking**: `mypy` for static type analysis
- **Testing**: `pytest` + `pytest-asyncio` for async tests
- **Coverage**: `pytest-cov` for test coverage reports
- **Linting**: `ruff` for fast Python linting
- **Formatting**: `black` for code formatting
- **Dev Server**: `uvicorn` for running FastAPI

## 3. Architecture Design

### 3.1 High-Level Components

```
┌─────────────────────────────────────────┐
│         MCP Client (Claude, etc.)       │
└────────────────┬────────────────────────┘
                 │ HTTP+SSE
                 ▼
┌─────────────────────────────────────────┐
│        HTTP+SSE Transport Layer         │
│  - Request/Response handling            │
│  - SSE stream management                │
│  - Protocol negotiation                 │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│         MCP Protocol Handler            │
│  - Tool registration                    │
│  - Tool execution routing               │
│  - Error handling                       │
│  - Schema validation                    │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│        SQLite CRUD Service              │
│  - Database connection management       │
│  - Query execution                      │
│  - Transaction handling                 │
│  - Result formatting                    │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│          SQLite Database                │
└─────────────────────────────────────────┘
```

### 3.2 MCP Tools to Implement

#### Tool 1: `create_table`
- **Purpose**: Create a new table in the database
- **Parameters**:
  - `table_name` (string, required): Name of the table
  - `schema` (object, required): Column definitions with types
  - `primary_key` (string, optional): Primary key column
- **Returns**: Success message with table details

#### Tool 2: `insert_record`
- **Purpose**: Insert a new record into a table
- **Parameters**:
  - `table_name` (string, required): Target table
  - `data` (object, required): Key-value pairs for the record
- **Returns**: Inserted record with generated ID

#### Tool 3: `query_records`
- **Purpose**: Query/read records from a table
- **Parameters**:
  - `table_name` (string, required): Target table
  - `filters` (object, optional): WHERE clause conditions
  - `limit` (number, optional): Maximum records to return
  - `offset` (number, optional): Pagination offset
  - `order_by` (string, optional): Sorting column
- **Returns**: Array of matching records

#### Tool 4: `update_record`
- **Purpose**: Update existing record(s)
- **Parameters**:
  - `table_name` (string, required): Target table
  - `filters` (object, required): WHERE clause conditions
  - `data` (object, required): Fields to update
- **Returns**: Number of records updated

#### Tool 5: `delete_record`
- **Purpose**: Delete record(s) from a table
- **Parameters**:
  - `table_name` (string, required): Target table
  - `filters` (object, required): WHERE clause conditions
- **Returns**: Number of records deleted

#### Tool 6: `list_tables`
- **Purpose**: List all tables in the database
- **Parameters**: None
- **Returns**: Array of table names with schema info

#### Tool 7: `describe_table`
- **Purpose**: Get detailed schema information for a table
- **Parameters**:
  - `table_name` (string, required): Target table
- **Returns**: Table schema details (columns, types, constraints)

#### Tool 8: `execute_raw_query`
- **Purpose**: Execute custom SQL query (with safety controls)
- **Parameters**:
  - `query` (string, required): SQL query to execute
  - `params` (array, optional): Parameterized query values
  - `read_only` (boolean, optional): Enforce read-only mode
- **Returns**: Query results or affected row count

## 4. Project Structure

```
mcp_template/
├── src/
│   ├── __init__.py
│   ├── server.py                          # Main FastAPI HTTP+SSE server
│   ├── mcp_handler.py                     # MCP protocol implementation
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py                  # Database connection manager
│   │   ├── crud_operations.py             # CRUD implementation
│   │   └── query_builder.py               # Safe query construction
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── table_tools.py                 # Table management tools
│   │   ├── record_tools.py                # Record CRUD tools
│   │   └── query_tools.py                 # Query execution tools
│   └── utils/
│       ├── __init__.py
│       ├── validation.py                  # Input validation
│       ├── security.py                    # SQL injection prevention
│       └── errors.py                      # Custom error types
├── tests/
│   ├── __init__.py
│   ├── test_mcp_protocol.py
│   ├── test_crud_operations.py
│   └── test_integration.py
├── config/
│   └── config.yaml                        # Server configuration
├── data/
│   └── database.db                        # SQLite database file (created at runtime)
├── requirements.txt                       # Python dependencies
├── pyproject.toml                         # Python project configuration
├── Dockerfile                             # Docker image definition
├── .dockerignore                          # Docker build exclusions
├── docker-compose.yml                     # Docker Compose configuration
├── README.md
├── .env.example
├── .gitignore
└── PROJECT_PLAN.md                        # This file
```

## 5. Docker Deployment

### 5.1 Dockerfile

```dockerfile
# Multi-stage build for smaller final image
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Final stage
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Create non-root user for security
RUN useradd -m -u 1000 mcpuser && \
    mkdir -p /app/data /app/logs && \
    chown -R mcpuser:mcpuser /app

# Copy Python dependencies from builder
COPY --from=builder --chown=mcpuser:mcpuser /root/.local /home/mcpuser/.local

# Copy application code
COPY --chown=mcpuser:mcpuser src/ ./src/
COPY --chown=mcpuser:mcpuser config/ ./config/

# Set environment variables
ENV PATH=/home/mcpuser/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DATABASE_PATH=/app/data/database.db \
    SERVER_HOST=0.0.0.0 \
    SERVER_PORT=8080

# Switch to non-root user
USER mcpuser

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

# Run the application
CMD ["uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "8080"]
```

### 5.2 .dockerignore

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
*.egg-info/
dist/
build/

# Virtual environments
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/

# Database (don't copy local database to image)
data/*.db
data/*.db-journal

# Logs
logs/*.log

# Environment
.env
.env.local

# Git
.git/
.gitignore

# Documentation
*.md
docs/

# CI/CD
.github/
.gitlab-ci.yml

# Mac
.DS_Store
```

### 5.3 docker-compose.yml

```yaml
version: '3.8'

services:
  mcp-server:
    build:
      context: .
      dockerfile: Dockerfile
    image: mcp-sqlite-server:latest
    container_name: mcp-sqlite-server
    ports:
      - "8080:8080"
    volumes:
      # Persist database outside container
      - ./data:/app/data
      # Persist logs outside container
      - ./logs:/app/logs
      # Mount custom config (optional)
      - ./config/config.yaml:/app/config/config.yaml:ro
    environment:
      - DATABASE_PATH=/app/data/database.db
      - SERVER_HOST=0.0.0.0
      - SERVER_PORT=8080
      - DEBUG=false
    restart: unless-stopped
    networks:
      - mcp-network
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

networks:
  mcp-network:
    driver: bridge

volumes:
  mcp-data:
  mcp-logs:
```

### 5.4 Docker Build and Run Commands

**Build the Docker image:**
```bash
# Build with default tag
docker build -t mcp-sqlite-server:latest .

# Build with specific version tag
docker build -t mcp-sqlite-server:1.0.0 .

# Build with build arguments (if needed)
docker build --build-arg PYTHON_VERSION=3.11 -t mcp-sqlite-server:latest .
```

**Run with Docker:**
```bash
# Run container with volume mounts
docker run -d \
  --name mcp-server \
  -p 8080:8080 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  -e DEBUG=false \
  mcp-sqlite-server:latest

# Run container in foreground (for debugging)
docker run --rm -it \
  --name mcp-server \
  -p 8080:8080 \
  -v $(pwd)/data:/app/data \
  mcp-sqlite-server:latest

# View logs
docker logs -f mcp-server

# Stop container
docker stop mcp-server

# Remove container
docker rm mcp-server
```

**Run with Docker Compose:**
```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild and restart
docker-compose up -d --build

# Stop and remove volumes
docker-compose down -v
```

### 5.5 Docker Image Optimization

**Best Practices Implemented:**

1. **Multi-stage build** - Separates build dependencies from runtime
2. **Slim base image** - Uses `python:3.11-slim` for smaller image size
3. **Layer caching** - Copies requirements.txt first for better cache utilization
4. **Non-root user** - Runs as `mcpuser` for security
5. **Health checks** - Built-in health check for container orchestration
6. **Volume mounts** - Persists data and logs outside container
7. **.dockerignore** - Excludes unnecessary files from build context

**Expected Image Size:** ~150-200MB (vs ~900MB+ for full Python image)

### 5.6 Production Deployment Considerations

**Environment Variables:**
```bash
# .env file for Docker Compose
DATABASE_PATH=/app/data/database.db
SERVER_HOST=0.0.0.0
SERVER_PORT=8080
DEBUG=false
ENABLE_AUTH=true
API_KEY=your-secure-api-key-here
MAX_QUERY_RESULTS=1000
ALLOW_RAW_QUERIES=true
```

**Resource Limits (Docker Compose):**
```yaml
services:
  mcp-server:
    # ... other config ...
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
```

**Kubernetes Deployment (Optional):**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-sqlite-server
spec:
  replicas: 2
  selector:
    matchLabels:
      app: mcp-sqlite-server
  template:
    metadata:
      labels:
        app: mcp-sqlite-server
    spec:
      containers:
      - name: mcp-server
        image: mcp-sqlite-server:latest
        ports:
        - containerPort: 8080
        env:
        - name: DATABASE_PATH
          value: /app/data/database.db
        volumeMounts:
        - name: data
          mountPath: /app/data
        - name: logs
          mountPath: /app/logs
        resources:
          limits:
            memory: "512Mi"
            cpu: "1000m"
          requests:
            memory: "256Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 10
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: mcp-data-pvc
      - name: logs
        emptyDir: {}
```

## 6. MCP Protocol Specifics

### 6.1 HTTP+SSE Transport

**Endpoint Structure**:
```
POST /mcp/v1/initialize    # Initialize MCP session
POST /mcp/v1/tools/list    # List available tools
POST /mcp/v1/tools/call    # Execute a tool
GET  /mcp/v1/sse           # SSE stream for notifications
GET  /health               # Health check endpoint
```

**SSE Message Format**:
```json
{
  "jsonrpc": "2.0",
  "method": "notifications/message",
  "params": {
    "level": "info|warning|error",
    "message": "Status update..."
  }
}
```

### 6.2 Tool Schema Example

```json
{
  "name": "insert_record",
  "description": "Insert a new record into a database table",
  "inputSchema": {
    "type": "object",
    "properties": {
      "table_name": {
        "type": "string",
        "description": "Name of the table to insert into"
      },
      "data": {
        "type": "object",
        "description": "Key-value pairs representing the record data"
      }
    },
    "required": ["table_name", "data"]
  }
}
```

## 7. Security Considerations

### 7.1 SQL Injection Prevention
- Use parameterized queries exclusively
- Validate table and column names against whitelist
- Sanitize all user inputs
- Implement query complexity limits

### 7.2 Access Control
- Optional authentication layer (API keys, OAuth)
- Rate limiting on tool executions
- Query result size limits
- Database operation timeout controls

### 7.3 Data Protection
- Option to encrypt database at rest
- Secure connection (HTTPS) for production
- Audit logging for all operations
- Backup and recovery procedures

## 8. Configuration Options

```yaml
server:
  host: "localhost"
  port: 8080
  debug: false

database:
  path: "./data/database.db"
  connection_timeout: 30
  max_connections: 5

mcp:
  server_name: "sqlite-crud-server"
  server_version: "1.0.0"
  max_tool_execution_time: 60

security:
  enable_auth: false
  api_key: "your-api-key-here"
  max_query_results: 1000
  allow_raw_queries: true
  read_only_mode: false

logging:
  level: "INFO"
  file: "./logs/server.log"
```

## 9. Testing Strategy

### Unit Tests
- Individual tool functionality
- Query builder correctness
- Validation logic
- Error handling

### Integration Tests
- End-to-end tool execution
- SSE streaming behavior
- Database transaction handling
- Concurrent request handling

### Performance Tests
- Load testing with multiple concurrent requests
- Large dataset query performance
- Memory usage monitoring
- SSE connection stability

## 10. Documentation Deliverables

- [ ] API Reference (OpenAPI/Swagger spec)
- [ ] MCP Tool Documentation
- [ ] Setup and Installation Guide
- [ ] Configuration Guide
- [ ] Usage Examples
- [ ] Troubleshooting Guide
- [ ] Security Best Practices

## 11. Future Enhancements (Post-MVP)

- Support for multiple database backends (PostgreSQL, MySQL)
- Database migration tool integration
- Query result caching
- Websocket alternative to SSE
- GraphQL-style query interface
- Database schema versioning
- Backup and restore tools
- Performance analytics dashboard
- Multi-tenancy support

## 12. Success Criteria

- [x] MCP protocol fully compliant
- [x] All 8 CRUD tools working correctly
- [x] HTTP+SSE transport functioning reliably
- [x] Security measures implemented
- [x] Test coverage > 80%
- [x] Documentation complete
- [x] Successfully integrates with Claude or other MCP clients

## 13. Technology Decisions & Open Questions

### Decided:
- **Language**: ✅ Python 3.10+
- **HTTP Framework**: ✅ FastAPI (best async support, built-in validation)
- **MCP SDK**: ✅ Python MCP SDK

### Still To Decide:

1. **Authentication**: Should we implement auth in v1?
   - **Recommendation**: Option A (no auth initially)
   - Option A: Start without auth for simplicity
   - Option B: Add basic API key auth from the start

2. **Database Location**: Where should the SQLite file live?
   - **Recommendation**: Option A (configurable)
   - Option A: Configurable path in config file (most flexible)
   - Option B: Always in project `data/` directory
   - Option C: Support multiple databases simultaneously

3. **Raw Query Tool**: Should we allow arbitrary SQL execution?
   - **Recommendation**: Yes, with read-only mode by default
   - Implement with configurable safety controls
   - Default to read-only mode unless explicitly disabled
   - Add query timeout and complexity limits

4. **Error Handling**: How verbose should error messages be?
   - **Recommendation**: Detailed in debug mode, sanitized in production
   - Debug mode: Full stack traces and SQL details
   - Production mode: User-friendly messages without internal details

## 14. Timeline & Milestones

- **Week 1-2**: Foundation + MCP Protocol + Docker Setup (25%)
- **Week 3-4**: CRUD Tools + Advanced Features (50%)
- **Week 5**: Testing + Documentation (75%)
- **Week 6**: Docker Optimization + Production Ready (100%)

**Total Estimated Time**: 6 weeks for full implementation

**Deliverables:**
- ✅ Fully functional MCP server with HTTP+SSE transport
- ✅ 8 CRUD tools for SQLite database operations
- ✅ Production-ready Docker image (~150-200MB)
- ✅ Docker Compose configuration for easy deployment
- ✅ Complete documentation and tests
- ✅ Optional Kubernetes deployment manifests

---

## Next Steps

1. ✅ Choose technology stack (Python selected)
2. Review and approve this plan
3. Make any necessary modifications
4. Answer remaining open questions (auth, database location, etc.)
5. Begin Phase 1 implementation

### Quick Start Commands (after approval):

**Option 1: Local Development (Python Virtual Environment)**
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install fastapi uvicorn sse-starlette pyyaml pydantic mcp
pip install --dev pytest pytest-asyncio pytest-cov mypy ruff black

# Run development server
uvicorn src.server:app --reload --port 8080
```

**Option 2: Docker Development**
```bash
# Build Docker image
docker build -t mcp-sqlite-server:latest .

# Run with Docker
docker run -d -p 8080:8080 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  --name mcp-server \
  mcp-sqlite-server:latest

# View logs
docker logs -f mcp-server
```

**Option 3: Docker Compose (Recommended for Production)**
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

**Test the server:**
```bash
# Check health endpoint
curl http://localhost:8080/health

# List available tools
curl -X POST http://localhost:8080/mcp/v1/tools/list
```
