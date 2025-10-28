# Test Suite for MCP SQLite Server

This directory contains comprehensive test coverage for the MCP SQLite Server project.

## Test Files

### 1. test_crud_operations.py (25 tests)
Unit tests for database CRUD operations.

**Test Classes:**
- `TestCreateTable` - Table creation with various schemas and constraints
- `TestInsertRecord` - Record insertion with different data types
- `TestQueryRecords` - Querying with filters, pagination, and ordering
- `TestUpdateRecord` - Single and bulk update operations
- `TestDeleteRecord` - Record deletion with various filters
- `TestListTables` - Database table listing
- `TestDescribeTable` - Table schema information retrieval
- `TestExecuteRawQuery` - Raw SQL execution with safety controls
- `TestCompleteWorkflow` - End-to-end CRUD workflow

**Coverage:** Tests all CRUD operations with edge cases and error conditions.

### 2. test_mcp_protocol.py (16 tests)
Unit tests for the MCP protocol handler.

**Test Classes:**
- `TestToolRegistration` - Tool registration and management
- `TestListTools` - Tool listing and schema validation
- `TestExecuteTool` - Tool execution with various argument patterns
- `TestToolSchema` - Pydantic model validation
- `TestMCPIntegration` - Multi-tool integration scenarios

**Coverage:** Tests MCP protocol implementation, tool registration, and execution.

### 3. test_integration.py (25 tests)
End-to-end integration tests for the FastAPI server.

**Test Classes:**
- `TestHealthEndpoint` - Health check endpoint
- `TestToolsListEndpoint` - Tool listing API
- `TestToolCallEndpoint` - All 8 CRUD tool endpoints
- `TestCompleteWorkflow` - Complete workflows (CRUD, pagination, filtering)
- `TestSSEEndpoint` - Server-Sent Events endpoint
- `TestErrorHandling` - Error handling and validation

**Coverage:** Tests the complete HTTP API with real FastAPI test client.

## Running Tests

### Run all tests
```bash
pytest tests/ -v
```

### Run specific test file
```bash
pytest tests/test_crud_operations.py -v
pytest tests/test_mcp_protocol.py -v
pytest tests/test_integration.py -v
```

### Run with coverage
```bash
pytest tests/ --cov=src --cov-report=html
pytest tests/ --cov=src --cov-report=term-missing
```

### Run specific test class or method
```bash
pytest tests/test_crud_operations.py::TestCreateTable -v
pytest tests/test_crud_operations.py::TestCreateTable::test_create_simple_table -v
```

## Test Results Summary

**Total Tests:** 66
**Passing:** 66 (100%)
**Code Coverage:** 96%

### Coverage by Module
- `crud_operations.py`: 100%
- `mcp_handler.py`: 100%
- `server.py`: 100%
- `query_builder.py`: 99%
- `connection.py`: 84%
- `validation.py`: 100%
- `errors.py`: 100%
- `security.py`: 62%

## Test Fixtures

### For CRUD Tests
- `temp_db` - Temporary SQLite database (auto-cleanup)
- `db_manager` - DatabaseManager instance
- `crud_ops` - CRUDOperations instance

### For Integration Tests
- `test_db_path` - Temporary database path
- `client` - FastAPI TestClient with patched database

### For MCP Protocol Tests
- `mcp_handler` - MCPHandler instance
- `sample_tool_handler` - Sample async tool for testing

## Dependencies

Required packages (from requirements.txt):
- pytest>=7.4.3
- pytest-asyncio>=0.21.1
- pytest-cov>=4.1.0
- httpx>=0.25.0
- fastapi>=0.104.0
- All other project dependencies

## Notes

- All async tests use `@pytest.mark.asyncio` decorator
- Integration tests use module-scoped fixtures for performance
- Database fixtures ensure automatic cleanup after tests
- Tests are isolated and can run in any order
- SSE endpoint tests verify connection and content-type only (not full streaming)

## Continuous Integration

These tests are designed to run in CI/CD pipelines. Example GitHub Actions workflow:

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - run: pip install -r requirements.txt
      - run: pytest tests/ -v --cov=src
```
