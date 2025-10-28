# MCP SQLite Chatbot

A Python chatbot that integrates with the MCP SQLite Server using local Ollama API. This chatbot can interact with SQLite databases through natural language using the Model Context Protocol (MCP).

## Features

- 🤖 **Local LLM**: Uses Ollama with gpt-oss:20b model (configurable)
- 🔧 **MCP Integration**: Full access to 8 SQLite CRUD tools via MCP protocol
- 💬 **Interactive Chat**: Rich terminal interface with history
- 🛠️ **Tool Calling**: Automatic tool detection and execution
- 📝 **Smart Context**: Maintains conversation history with context management
- 🎨 **Rich UI**: Beautiful terminal UI with syntax highlighting

## Architecture

```
┌─────────────┐      ┌─────────────┐      ┌──────────────────┐
│   Chatbot   │─────▶│   Ollama    │      │   MCP Server     │
│  (Python)   │      │    API      │      │  (SQLite CRUD)   │
│             │◀─────│  gpt-oss    │      │                  │
└─────────────┘      └─────────────┘      └──────────────────┘
       │                                            ▲
       │                                            │
       └────────────── Tool Calls ─────────────────┘
```

## Prerequisites

1. **MCP SQLite Server** running on `http://localhost:8080`
   - See parent directory README for setup instructions
   - Start server: `uvicorn src.server:app --reload --port 8080`

2. **Ollama** installed and running
   ```bash
   # Install Ollama (see https://ollama.ai)
   curl https://ollama.ai/install.sh | sh

   # Pull the model
   ollama pull gpt-oss:20b
   ```

3. **Python 3.10+**

## Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Copy environment file (optional):
   ```bash
   cp .env.example .env
   ```

3. Review and customize `config.yaml` if needed

## Configuration

### config.yaml

The main configuration file controls all aspects of the chatbot:

```yaml
mcp_server:
  url: "http://localhost:8080"  # MCP server URL
  timeout: 30

ollama:
  base_url: "http://localhost:11434"  # Ollama API URL
  model: "gpt-oss:20b"                # Model to use
  temperature: 0.7
  num_ctx: 4096

chatbot:
  name: "MCP Assistant"
  max_history: 10                     # Number of message pairs to keep
  show_tool_calls: true               # Display tool executions
```

## Usage

### Quick Start

```bash
# Terminal 1: Start MCP Server
cd ..
uvicorn src.server:app --reload --port 8080

# Terminal 2: Start Chatbot
cd py-mcp-client
python chatbot.py
```

### Chat Commands

- **General chat**: Just type your message
- **quit/exit**: Exit the chatbot
- **clear**: Clear conversation history
- **tools**: List all available MCP tools

### Example Conversations

#### Example 1: Creating a Table

```
You: Create a table called users with id, name, and email columns