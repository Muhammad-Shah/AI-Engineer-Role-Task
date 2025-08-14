# Database Chatbot Web UI

A modern, responsive web interface for the Database Chatbot API that provides an intuitive way to interact with databases using natural language.

## Features

### 🔌 **Database Connection Management**
- Support for PostgreSQL, MySQL, and MongoDB
- Real-time connection status indicators
- Connection validation and health checks
- Secure credential handling

### 💬 **Interactive Chat Interface**
- Real-time streaming responses
- Session management (create, switch, delete)
- Message history persistence
- Export chat sessions

### 🤖 **Smart Query Processing**
- Natural language to SQL/MongoDB conversion
- Live feedback during query processing
- Cache hit indicators for improved performance
- SQL/Query visualization

### 🎨 **Modern UI/UX**
- Clean, professional design
- Responsive layout (desktop/mobile)
- Dark/light theme support
- Interactive data tables
- Toast notifications

## Getting Started

### 1. Start the API Server
```bash
docker-compose -f docker/docker-compose.yml up --build
```

### 2. Access the Web UI
Open your browser and navigate to: **http://localhost:8000/ui**

### 3. Connect to a Database
1. Fill in your database connection details in the left sidebar
2. Click "Connect" to establish the connection
3. Watch for the green "Connected" status indicator

### 4. Start Chatting
1. Click "New Session" to create a chat session
2. Type your questions in natural language
3. Watch as your queries are processed in real-time
4. Explore the interactive data results

## Example Usage Flow

### PostgreSQL Connection (Docker)
```json
{
  "host": "postgres",     // Use "postgres" if API runs in Docker
  "port": 5432,
  "database": "sampledb",
  "username": "postgres",
  "password": "postgres",
  "db_type": "postgresql"
}
```

### MongoDB Connection (Docker)
```json
{
  "host": "mongodb",     // Use "mongodb" if API runs in Docker
  "port": 27017,
  "database": "sampledb",
  "username": "appuser",
  "password": "apppassword",
  "db_type": "mongodb"
}
```

### Example Natural Language Queries
- **"Show me all users"** → `SELECT * FROM users LIMIT 100`
- **"How many active users do we have?"** → `SELECT COUNT(*) FROM users WHERE active = true`
- **"List users in Engineering department"** → `SELECT * FROM users WHERE department = 'Engineering'`
- **"Show orders from last month"** → `SELECT * FROM orders WHERE order_date >= ...`
- **"What products are in stock?"** → `SELECT * FROM products WHERE stock_quantity > 0`

## UI Components

### Connection Panel
- **Database Type Selector**: Choose between PostgreSQL, MySQL, MongoDB
- **Connection Form**: Host, port, database, credentials
- **Status Indicator**: Real-time connection status
- **Connection Info**: Display connected database details

### Chat Interface
- **Session List**: View and manage chat sessions
- **Message Area**: Streaming conversation with formatted results
- **Input Field**: Natural language query input
- **Example Queries**: Quick-start query buttons

### Data Display
- **Interactive Tables**: Sortable, scrollable data results
- **Query Insights**: View generated SQL/MongoDB queries
- **Cache Indicators**: See when results come from cache
- **Export Options**: Download chat sessions as JSON

## Streaming Events

The UI handles various real-time events:

| Event | Description | Visual Indicator |
|-------|-------------|------------------|
| `start` | Query processing begins | 🤖 Processing... |
| `cache_hit` | Similar query found in cache | ⚡ Cache Hit! |
| `agent_started` | LLM agent begins analysis | 🔄 Agent Started |
| `generated_sql` | SQL query generated | 💡 Generated SQL |
| `generated_filter` | MongoDB filter generated | 💡 Generated Filter |
| `result` | Query results available | 📊 Results |
| `error` | Processing error occurred | ❌ Error |
| `end` | Query processing complete | ✅ Completed |

## Advanced Features

### Smart Caching System
- Automatically detects similar queries
- Shows cache hit probability
- Reduces response time for repeated questions
- Configurable similarity threshold

### Session Management
- Multiple concurrent chat sessions
- Persistent conversation history
- Session export/import capabilities
- Easy session switching

### Error Handling
- Graceful connection failure recovery
- Detailed error messages
- Retry mechanisms
- User-friendly notifications

## Technical Details

### Frontend Stack
- **Pure JavaScript**: No framework dependencies
- **Modern CSS**: CSS Grid, Flexbox, Custom Properties
- **Font Awesome**: Icons and visual elements
- **Fetch API**: HTTP requests with streaming support

### Key Features
- **Responsive Design**: Mobile-first approach
- **Real-time Updates**: Server-sent events via fetch streaming
- **Local Storage**: Session state persistence
- **Progressive Enhancement**: Works without JavaScript for basic features

### Performance Optimizations
- **Lazy Loading**: Messages loaded on demand
- **Virtual Scrolling**: Handle large result sets
- **Debounced Inputs**: Reduced API calls
- **Connection Pooling**: Efficient resource usage

## Troubleshooting

### Common Issues

**🔴 "API is not running" Error**
- Ensure the FastAPI server is started on port 8000
- Check firewall settings
- Verify CORS configuration

**🔴 "Connection failed" Error**
- Verify database credentials
- Check if database server is accessible
- Ensure network connectivity

**🔴 "Query failed" Error**
- Set `OPENAI_API_KEY` environment variable
- Check OpenAI API quota/limits
- Verify LLM dependencies are installed

**🔴 "No results" Message**
- Query might be too specific
- Database might be empty
- Check table/collection names

### Debug Mode
Add `?debug=1` to the URL to enable debug logging:
```
http://localhost:8000/ui?debug=1
```


### Impressive Queries to Demo:
```sql
"Show me all users"                    -- Basic table display
"How many orders were placed today?"   -- Aggregation query
"List Engineering department users"    -- Filtering
"What's our user count by department?" -- Grouping
"Show recent orders with details"      -- Complex joins
```