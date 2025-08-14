# Database Chatbot Development Task with FastAPI Integration

This project implements a complete Database Chatbot with FastAPI, supporting secure database connections (PostgreSQL, MySQL, MongoDB), natural-language-to-query translation, streaming responses, chat session management, and a similarity-based caching system.

## Features
- **Web UI**: Modern, responsive interface at `/ui` for easy testing and demos
- Database connection management with pooling and timeouts
- Endpoints per spec: connect/validate/disconnect, chat query (streaming), sessions CRUD
- LangChain + LangGraph ReAct agent for NL→SQL/Mongo generation and execution
- Real-time streaming via Server-Sent style JSON lines (newline-delimited JSON)
- Local SQLite persistence for chat sessions, messages, and cache
- OpenAPI/Swagger docs at `/docs`
- Dockerized app and sample PostgreSQL/MongoDB with seed data

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
     cache.py
   (LLM-based only; no rule-based translator)
    cache.py
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

## Run with Docker
1. From the project root (`AI Engineer Role Task`), start docker compose:
   ```bash
   docker compose -f docker/docker-compose.yml up --build
   ```
2. The API will be at `http://localhost:8000` and Web UI at `http://localhost:8000/ui`. Postgres is exposed at `localhost:5432`, MongoDB at `localhost:27017` (from the host). Inside the API container, service hosts are `postgres` and `mongodb`.
3. To enable the LLM agent inside Docker, set environment variables in the `api` service:
   - `OPENAI_API_KEY`: your OpenAI key
   - Optional: `OPENAI_MODEL` (default `gpt-4o-mini`)

### Connect to Postgres (Docker)
When calling the API (which runs in the container), use host `postgres`:

POST `/api/database/connect`
```json
{
  "host": "postgres",
  "port": 5432,
  "database": "sampledb",
  "username": "postgres",
  "password": "postgres",
  "db_type": "postgresql"
}
```

If you run the API locally (not in Docker), use `localhost` as host.

### Connect to MongoDB (Docker)
POST `/api/database/connect`
```
{
  "host": "mongodb",
  "port": 27017,
  "database": "sampledb",
  "username": "appuser",
  "password": "apppassword",
  "db_type": "mongodb",
  "options": { "serverSelectionTimeoutMS": 5000 }
}
```

## Chat: Create a session
POST `/api/chat/sessions`

## Chat: Send a natural language query (streamed response)

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

## Other Endpoints
- GET `/api/chat/sessions`
- GET `/api/chat/sessions/{session_id}/messages`
- DELETE `/api/chat/sessions/{session_id}`
- GET `/api/database/validate/{connection_id}`
- DELETE `/api/database/disconnect/{connection_id}`

## Supported Query Types (examples)
- "Show me all users from last month"
- "How many orders today?" (count)
- "List orders from the past week"
- "Show users"
- "Count users yesterday"

## Notes
- The NL translation uses a ReAct agent powered by LangChain + LangGraph (requires `OPENAI_API_KEY`).
- Caching uses Jaccard similarity on token sets with TTL to speed up repeat/similar queries.
- Sessions, messages, and cache are stored locally in SQLite (`var/app_data.sqlite`).
