
# Database Chatbot with FastAPI

A complete Database Chatbot that connects to your local databases (PostgreSQL, MySQL, MongoDB) with natural language to SQL/MongoDB query translation, streaming responses, and an intelligent caching system.

## Features
- **🌐 Web UI**: Modern, responsive interface at `/ui` for easy testing and demos
- **🔌 Smart Connection**: Just use `localhost` - automatically handles Docker networking
- **🤖 Dual AI Modes**: ReAct Agent (advanced reasoning) + Direct LLM (fast + conversational)
- **💬 Real-time Streaming**: Server-Sent Events with newline-delimited JSON responses
- **🗃️ Session Management**: Persistent chat sessions with SQLite storage
- **⚡ Smart Caching**: Similarity-based caching for faster repeat queries
- **📚 OpenAPI Docs**: Complete API documentation at `/docs`
- **🐳 Docker Ready**: Containerized deployment with local database support

## Project Structure
```
app/
  main.py
  config.py
  routers/
    database.py
    chat.py
   services/
     connections.py
     llm_agent.py
     direct_llm.py
     cache.py
   (LLM-based only; no rule-based translator)
    cache.py
   static/
    app.js
    index.html
    style.css
  models/
    db_models.py
    schemas.py
data/
  postgres/
    init.sql
docker/
  Dockerfile
  docker-compose.yml
var/
  (created at runtime for local SQLite)
```

## 🚀 Quick Start

### Prerequisites
1. **Local Databases**: Ensure you have at least one of these running:
   - PostgreSQL (port 5432)
   - MySQL (port 3306) 
   - MongoDB (port 27017)

2. **OpenAI API Key**: Required for LLM functionality

### Step 1: Setup Local Databases

### Step 2: Configure OpenAI API Key
Create `.env` and copy `.env.exapmle` then set your API key:
```yaml
OPENAI_API_KEY: your_actual_openai_key_here
```

### Step 3: Run the Application
```bash
# Start the containerized application
docker-compose -f docker/docker-compose.yml up --build
```

### Step 4: Access the Application
- **🌐 Web UI**: http://localhost:8000/ui
- **📚 API Docs**: http://localhost:8000/docs

### Step 5: Connect to Your Database
In the Web UI, simply use:
- **Host**: `localhost` (works automatically whether running locally or in Docker)
- **Port**: Your database's standard port (5432, 3306, 27017)
- **Database**: `sampledb` (if using the setup script)
- **Credentials**: As configured in your local database

## 💡 Connection Examples

### PostgreSQL
```json
{
  "host": "localhost",
  "port": 5432,
  "database": "sampledb",
  "username": "postgres",
  "password": "postgres",
  "db_type": "postgresql"
}
```

### MySQL
```json
{
  "host": "localhost",
  "port": 3306,
  "database": "sampledb",
  "username": "root",
  "password": "password",
  "db_type": "mysql"
}
```

### MongoDB
```json
{
  "host": "localhost",
  "port": 27017,
  "database": "sampledb",
  "username": "",
  "password": "",
  "db_type": "mongodb"
}
```

> **🔧 Smart Networking**: The application automatically detects if it's running in Docker and converts `localhost` to `host.docker.internal` when needed. You always use `localhost` in the UI!

## 🤖 AI Query Modes

The application offers two powerful AI modes for interacting with your databases:

### ReAct Agent Mode (Advanced)
POST `/api/chat/query`
```json
{
  "connection_id": "<from connect>",
  "message": "Show me all users from last month",
  "session_id": "<from created session>"
}
```

### Direct LLM Mode (Fast + Conversational)
POST `/api/chat/query-direct`
```json
{
  "connection_id": "<from connect>",
  "message": "Hello, show me all users",
  "session_id": "<from created session>"
}
```

Both endpoints stream responses as newline-delimited JSON events:
```json
{"event":"start","session_id":"...","mode":"direct_llm"}
{"event":"llm_processing","message":"Generating SQL..."}
{"event":"generated_sql","sql":"SELECT * FROM users LIMIT 100","explanation":"Retrieving all user records"}
{"event":"executing_sql","message":"Executing query..."}
{"event":"result","data":{"columns":["id","name","email"],"rows":[...]}}
{"event":"end"}
```

**Direct LLM Benefits:**
- **Conversational**: Handles both database queries and general conversation
- **Faster**: Direct SQL generation without tool-based reasoning
- **Explanations**: Provides context for generated queries
- **Mixed Mode**: Seamlessly switches between data queries and chat

## 📝 Example Queries

### Database Queries
- "Show me all users from last month"
- "How many orders were placed today?"
- "List users in the Engineering department"
- "What are the top 5 products by sales?"
- "Count active users"

### Conversational
- "Hello, how can you help me?"
- "What databases can you connect to?"
- "Explain what you found in the data"

## 🔧 API Endpoints

### Database Management
- `POST /api/database/connect` - Connect to database
- `GET /api/database/validate/{connection_id}` - Validate connection
- `DELETE /api/database/disconnect/{connection_id}` - Disconnect

### Chat Sessions
- `POST /api/chat/sessions` - Create new session
- `GET /api/chat/sessions` - List all sessions
- `GET /api/chat/sessions/{session_id}/messages` - Get session messages
- `DELETE /api/chat/sessions/{session_id}` - Delete session

### Query Processing
- `POST /api/chat/query` - ReAct Agent mode (advanced reasoning)
- `POST /api/chat/query-direct` - Direct LLM mode (fast + conversational)

## 🏗️ Technical Features

- **Smart Caching**: Jaccard similarity-based caching with TTL for faster repeat queries
- **Session Persistence**: SQLite storage for chat sessions, messages, and cache
- **Connection Pooling**: Efficient database connection management with timeouts
- **Streaming Responses**: Real-time Server-Sent Events with newline-delimited JSON
- **Auto-Detection**: Automatic Docker networking with localhost conversion
- **LLM Integration**: Powered by LangChain + LangGraph with OpenAI models

---

**🎉 Ready to chat with your databases! Just use `localhost` and let the AI handle the rest.**
