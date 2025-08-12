## Technical Approach and Design Decisions

### Overview
The application enables users to connect to relational (PostgreSQL, MySQL) and document (MongoDB) databases and query them using natural language. It exposes the required APIs via FastAPI and streams responses as newline-delimited JSON events for real-time feedback.

### Key Components
- `app/services/connections.py`: Central connection registry handling creation, validation, and disconnection for PostgreSQL/MySQL (SQLAlchemy engines with pooling, pre-ping, timeouts) and MongoDB (pymongo with server selection timeout).
- `app/services/llm_agent.py`: LangChain + LangGraph ReAct agents for SQL and Mongo flows. Agents inspect schema/collections and execute queries via tools, returning columns/rows.
- `app/routers/database.py` and `app/routers/chat.py`: API routers implementing the exact endpoints, request/response schemas, streaming responses, and persistence of sessions/messages.
- `app/models/db_models.py`: Local SQLite for chat sessions, messages, and a cache of previously successful queries.

### Security and Reliability
- Connection pooling with pre-ping and timeouts to avoid stale connections.
- Validation via `SELECT 1` or `ping` before registering connections.
- Parameterized SQL to avoid concatenation of user inputs.
- Errors surfaced with structured responses and non-200 statuses when appropriate.

### Real-time Streaming
- Responses stream as newline-delimited JSON events: `start`, optional `cache_hit`, `generated_sql`/`generated_filter`, `result`, and `end`.
- This keeps clients informed of each stage in the pipeline.

### Caching (Bonus)
- Message normalization and Jaccard similarity to identify similar queries.
- Entries include TTL and hit count; expired entries are ignored.
- Increases responsiveness for repeated or similar questions.

### Extensibility
- Agents can be augmented with additional tools (e.g., DDL introspection, sampler, explain plan).
- Registry supports additional database types with minimal changes.

### Trade-offs
- Pure LLM agent requires `OPENAI_API_KEY` and stable connectivity; in return provides broader NL coverage without hand-written rules.
- SQL dialect differences are handled by the agent with schema context; deeper dialect support can be added via tool hints.

### Testing and Demo
- Docker Compose includes a PostgreSQL instance initialized with sample schema/data for immediate testing.
- API docs available at `/docs` and `/openapi.json`.
