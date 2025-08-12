# Database Chatbot Development Task with FastAPI Integration

This project implements a complete Database Chatbot with FastAPI, supporting secure database connections (PostgreSQL, MySQL, MongoDB), natural-language-to-query translation, streaming responses, chat session management, and a similarity-based caching system.

## Features
- Database connection management with pooling and timeouts
- Endpoints per spec: connect/validate/disconnect, chat query (streaming), sessions CRUD
- LangChain + LangGraph ReAct agent for NL→SQL/Mongo generation and execution
- Real-time streaming via Server-Sent style JSON lines (newline-delimited JSON)
- Local SQLite persistence for chat sessions, messages, and cache
- OpenAPI/Swagger docs at `/docs`
- Dockerized app and sample PostgreSQL with seed data

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

## Run Locally (without Docker)
1. Ensure Python 3.10+ is installed.
2. (Windows CMD) Create and activate a virtualenv:
   ```bat
   python -m venv .venv
   .\.venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install fastapi uvicorn[standard] sqlalchemy psycopg2-binary pymysql pymongo
   # Optional LLM agent support (set OPENAI_API_KEY)
   pip install langchain langgraph langchain-openai
   ```
4. Start the API:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
5. Open Swagger UI: `http://localhost:8000/docs`

## Run with Docker
1. From the project root (`AI Engineer Role Task`), start docker compose:
   ```bash
   docker compose -f docker/docker-compose.yml up --build
   ```
2. The API will be at `http://localhost:8000`. Postgres is exposed at `localhost:5432`, MongoDB at `localhost:27017` (from the host). Inside the API container, service hosts are `postgres` and `mongodb`.
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
POST `/api/chat/query`
```json
{
  "connection_id": "<from connect>",
  "message": "Show me all users from last month",
  "session_id": "<from created session>"
}
```
Response is streamed as newline-delimited JSON events, e.g.:
```json
{"event":"start","session_id":"..."}
{"event":"generated_sql","sql":"SELECT * FROM users WHERE created_at >= :date_from AND created_at <= :date_to LIMIT 100","params":{"date_from":"...","date_to":"..."}}
{"event":"result","data":{"columns":["id","name","email","created_at"],"rows":[...]}}
{"event":"end"}
```

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

## Demo Checklist
- Database connection setup (via `/api/database/connect`)
- Natural language queries (try at least 5 variations)
- Observe streamed events in the response
- Manage chat sessions (create/list/messages/delete)
- Re-run a similar query to see cache hit
