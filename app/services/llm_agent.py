from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Callable

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

# LangChain / LangGraph imports
try:  # Soft dependency; validated at runtime
    from langchain_openai import ChatOpenAI 
    from langchain_core.tools import Tool 
    from langgraph.prebuilt import create_react_agent 
except Exception as exc:  # pragma: no cover
    ChatOpenAI = None 
    Tool = None 
    create_react_agent = None 


@dataclass
class AgentResult:
    generated_sql: Optional[str]
    generated_filter: Optional[Dict[str, Any]]
    result_columns: List[str]
    result_rows: List[List[Any]]
    raw_final: Optional[str] = None

class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime objects by converting them to ISO format strings."""
    
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj) 

def _ensure_langchain_available() -> None:
    if ChatOpenAI is None or Tool is None or create_react_agent is None:
        raise RuntimeError(
            "LangChain/LangGraph not installed. Please install 'langchain', 'langgraph', and 'langchain-openai'."
        )


def _build_schema_context(engine: Engine) -> str:
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    lines: List[str] = []
    for table in tables:
        try:
            cols = inspector.get_columns(table)
            col_parts = [f"{c['name']} {c.get('type')}" for c in cols]
            lines.append(f"Table {table} (" + ", ".join(col_parts) + ")")
        except Exception:
            lines.append(f"Table {table}")
    return "\n".join(lines)


def _default_llm(temperature: float) -> "ChatOpenAI":
    _ensure_langchain_available()
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set in environment")
    return ChatOpenAI(model=model, temperature=temperature, streaming=True)


def run_sql_react_agent(
    engine: Engine,
    question: str,
    temperature: float = 0.4,
) -> AgentResult:
    _ensure_langchain_available()

    schema_ctx = _build_schema_context(engine)
    dialect_name = getattr(engine.dialect, "name", "sql")
    llm = _default_llm(temperature)

    # Accumulators to capture tool effects
    result_columns: List[str] = []
    result_rows: List[List[Any]] = []
    last_sql: Optional[str] = None

    # Tools
    def list_tables_tool_fn(_: str = "") -> str:
        inspector = inspect(engine)
        return ", ".join(inspector.get_table_names())

    def describe_table_tool_fn(table: str) -> str:
        inspector = inspect(engine)
        cols = inspector.get_columns(table)
        return "; ".join([f"{c['name']} {c.get('type')}" for c in cols])

    def run_sql_tool_fn(sql: str) -> str:
        nonlocal last_sql, result_columns, result_rows
        last_sql = sql
        with engine.connect() as conn:
            res = conn.execute(text(sql))
            if res.returns_rows:
                result_columns = list(res.keys())
                result_rows = [list(r) for r in res.fetchall()]
                return json.dumps({"columns": result_columns, "rows": result_rows})
            else:
                result_columns = ["rowcount"]
                result_rows = [[res.rowcount]]
                return json.dumps({"columns": result_columns, "rows": result_rows})

    tools = [
        Tool(
            name="list_tables",
            description=(
                "List all available SQL tables. Use this first to see what data is available."
            ),
            func=list_tables_tool_fn,
        ),
        Tool(
            name="describe_table",
            description=(
                "Describe the columns and types for a given table. Input MUST be a single table name."
            ),
            func=describe_table_tool_fn,
        ),
        Tool(
            name="run_sql",
            description=(
                "Execute a SQL query and return results as JSON with 'columns' and 'rows'. "
                "Only use valid SQL for this database dialect."
            ),
            func=run_sql_tool_fn,
        ),
    ]

    system_preamble = (
        "You are a helpful data assistant. You can browse database schema and write SQL. "
        "Use the tools to first inspect tables and columns, then construct a correct SQL query to answer the user's question. "
        f"Target SQL dialect: {dialect_name}. Use database-specific syntax accordingly. "
        "Give response to user in simple string not tables.\n"
        "Always call run_sql to obtain the final answer. Limit results to 100 rows unless a count/aggregate is requested.\n\n"
        f"Schema:\n{schema_ctx}"
    )

    app = create_react_agent(llm, tools, prompt=system_preamble)

    # Run the agent synchronously. We rely on the tool result as source of truth.
    final_state = app.invoke({"messages": [("user", question)]})
    final_text: Optional[str] = None
    try:
        msgs = final_state.get("messages") or []
        if msgs:
            final_text = getattr(msgs[-1], "content", None)
    except Exception:
        final_text = None

    return AgentResult(
        generated_sql=last_sql,
        generated_filter=None,
        result_columns=result_columns,
        result_rows=result_rows,
        raw_final=final_text,
    )


def run_mongo_react_agent(
    client: Any,
    database: str,
    question: str,
    temperature: float = 0.4,
) -> AgentResult:
    _ensure_langchain_available()
    llm = _default_llm(temperature)

    db = client[database]

    # Accumulators
    last_filter: Optional[Dict[str, Any]] = None
    result_columns: List[str] = []
    result_rows: List[List[Any]] = []
    last_collection: Optional[str] = None

    # Enhanced Tools
    def list_collections_tool_fn(_: str = "") -> str:
        """List all collections in the database."""
        try:
            collections = db.list_collection_names()
            print(collections)  
            if not collections:
                return "No collections found in database"
            return f"Available collections: {', '.join(collections)}"
        except Exception as e:
            return f"Error listing collections: {str(e)}"

    def collection_info_tool_fn(collection_names: str) -> str:
        """Get schema and sample documents for specified collections."""
        try:
            print(collection_names)
            collections = [name.strip() for name in collection_names.split(",")]
            info_parts = []
            
            for collection_name in collections:
                if collection_name not in db.list_collection_names():
                    info_parts.append(f"❌ Collection '{collection_name}' does not exist")
                    continue
                
                # Get sample documents to understand schema
                sample_docs = list(db[collection_name].find().limit(3))
                if not sample_docs:
                    info_parts.append(f"📭 Collection '{collection_name}' is empty")
                    continue
                
                # Extract field information
                all_fields = set()
                field_types = {}
                for doc in sample_docs:
                    for key, value in doc.items():
                        if key != "_id":
                            all_fields.add(key)
                            field_types[key] = type(value).__name__
                
                # Get document count
                doc_count = db[collection_name].count_documents({})
                
                sample_display = {k: v for k, v in sample_docs[0].items() if k != '_id'}
                
                info_parts.append(
                    f"📋 Collection '{collection_name}' ({doc_count} documents):\n"
                    f"   Fields: {', '.join(sorted(all_fields))}\n"
                    f"   Sample: {json.dumps(sample_display, default=str, indent=2)}"
                )
            
            return "\n\n".join(info_parts)
        except Exception as e:
            return f"❌ Error getting collection info: {str(e)}"

    def mongo_query_tool_fn(query_json: str) -> str:
        """Execute a MongoDB query and return results."""
        nonlocal last_filter, result_columns, result_rows, last_collection
        print(query_json)
        try:
            # Parse the query JSON
            query_data = json.loads(query_json)
            collection_name = query_data.get("collection")
            filter_query = query_data.get("filter", {})
            limit = min(query_data.get("limit", 50), 100)  # Cap at 100
            
            if not collection_name:
                return "❌ Error: 'collection' field is required in query JSON"
            
            available_collections = db.list_collection_names()
            if collection_name not in available_collections:
                return f"❌ Error: Collection '{collection_name}' does not exist. Available: {', '.join(available_collections)}"
            
            # Store for result tracking
            last_collection = collection_name
            last_filter = filter_query
            print(f"last_filter: {last_filter}")
            # Execute query
            cursor = db[collection_name].find(filter_query).limit(limit)
            docs = list(cursor)
            
            if not docs:
                result_columns, result_rows = [], []
                return json.dumps({
                    "status": "success",
                    "message": f"No documents found in '{collection_name}' matching filter",
                    "collection": collection_name,
                    "filter": filter_query,
                    "count": 0,
                    "columns": [],
                    "rows": []
                })
            
            # Extract fields from documents
            all_keys = set()
            for doc in docs:
                all_keys.update(doc.keys())
            all_keys.discard("_id")  # Remove _id for cleaner display
            
            columns = sorted(list(all_keys))
            rows = []
            
            for doc in docs:
                row = []
                for col in columns:
                    value = doc.get(col)
                    # Convert complex types to strings for display
                    if isinstance(value, (dict, list)):
                        value = json.dumps(value, default=str)
                    elif value is None:
                        value = None
                    else:
                        value = str(value)
                    row.append(value)
                rows.append(row)
            
            result_columns, result_rows = columns, rows
            
            return json.dumps({
                "status": "success",
                "message": f"✅ Found {len(docs)} documents in '{collection_name}'",
                "collection": collection_name,
                "filter": filter_query,
                "count": len(docs),
                "columns": columns,
                "rows": rows
            })
            
        except json.JSONDecodeError:
            return "❌ Error: Invalid JSON format. Expected: {\"collection\": \"collection_name\", \"filter\": {...}}"
        except Exception as e:
            return f"❌ Error executing MongoDB query: {str(e)}"

    def count_documents_tool_fn(query_json: str) -> str:
        """Count documents matching a filter."""
        print(query_json)
        try:
            query_data = json.loads(query_json)
            collection_name = query_data.get("collection")
            filter_query = query_data.get("filter", {})
            if not collection_name:
                return "❌ Error: 'collection' field is required"
                
            if collection_name not in db.list_collection_names():
                available = ', '.join(db.list_collection_names())
                return f"❌ Error: Collection '{collection_name}' does not exist. Available: {available}"
            
            count = db[collection_name].count_documents(filter_query)

            # Store for result tracking
            nonlocal last_filter, last_collection, result_columns, result_rows
            last_collection = collection_name
            last_filter = filter_query

            print(f"last_filter: {last_filter}")

            result_columns = ["count"]
            result_rows = [[count]]
            
            return json.dumps({
                "status": "success",
                "collection": collection_name,
                "filter": filter_query,
                "count": count,
                "message": f"✅ Found {count} documents matching the filter"
            })
            
        except json.JSONDecodeError:
            return "❌ Error: Invalid JSON. Expected: {\"collection\": \"name\", \"filter\": {...}}"
        except Exception as e:
            return f"❌ Error counting documents: {str(e)}"

    tools = [
        Tool(
            name="list_collections",
            description="📋 List all collections in the MongoDB database. Input: empty string. Returns: comma-separated collection names.",
            func=list_collections_tool_fn,
        ),
        Tool(
            name="collection_info",
            description=(
                "🔍 Get detailed schema and sample documents for MongoDB collections. "
                "Input: comma-separated collection names (e.g., 'users, orders'). "
                "Output: field names, document count, and sample documents for each collection. "
                "Use this to understand collection structure before querying."
            ),
            func=collection_info_tool_fn,
        ),
        Tool(
            name="mongo_query",
            description=(
                "🔎 Execute a MongoDB find query and return documents. "
                "Input: JSON string with 'collection' (required) and 'filter' (optional). "
                "Example: {\"collection\": \"users\", \"filter\": {\"active\": true}} "
                "Use this to retrieve actual data. Always use this tool to get the final answer."
            ),
            func=mongo_query_tool_fn,
        ),
        Tool(
            name="count_documents",
            description=(
                "🔢 Count documents matching a filter in a MongoDB collection. "
                "Input: JSON string with 'collection' and 'filter'. "
                "Example: {\"collection\": \"users\", \"filter\": {\"department\": \"Engineering\"}} "
                "Use this for count/aggregate queries."
            ),
            func=count_documents_tool_fn,
        ),
    ]

    # Improved system prompt with clear workflow
    system_preamble = (
        f"You are an expert MongoDB assistant for database '{database}'. Follow this exact workflow:\n\n"
        "STEP 1: Always start by calling 'list_collections' to see what collections exist\n"
        "STEP 2: Call 'collection_info' for relevant collections to understand their structure\n"
        "STEP 3: Use the appropriate tool:\n"
        "   - For COUNT queries → use 'count_documents'\n"
        "   - For DATA queries → use 'mongo_query'\n\n"
        "MONGODB FILTER EXAMPLES:\n"
        "- Find all: {{}}\n"
        "- Find by field: {{\"name\": \"John\"}}\n"
        "- Find with comparison: {{\"age\": {\"$gt\": 25}}}\n"
        "- Find with regex: {{\"name\": {\"$regex\": \"John\", \"$options\": \"i\"}}}\n"
        "- Find multiple conditions: {{\"active\": true, \"department\": \"Engineering\"}}\n\n"
        "CRITICAL RULES:\n"
        "1. ALWAYS use exact collection names from list_collections\n"
        "2. Use collection_info to understand field names before querying\n"
        "3. Provide JSON in exact format: {{\"collection\": \"name\", \"filter\": {...}}}\n"
        "4. For count questions, use count_documents, not mongo_query\n"
        "5. Keep filters simple and based on actual field names\n\n"
        "6. Give response to user in simple string not tables.\n"
        "Answer the user's question step by step using these tools."
    )

    try:
        app = create_react_agent(llm, tools, prompt=system_preamble)
        
        # Configure with limits to prevent recursion
        config = {
            "recursion_limit": 10,  # Reduced from default 25
            "timeout": 25,  # 25 second timeout
        }
        
        final_state = app.invoke(
            {"messages": [("user", question)]},
            config=config
        )
        
        final_text: Optional[str] = None
        print("--------------------------------")
        print("last_filter")
        print(last_filter)
        print("--------------------------------")
        print("result_columns")
        print(result_columns)
        print("--------------------------------")
        print("result_rows")
        print(result_rows)
        print("--------------------------------")
        try:
            msgs = final_state.get("messages") or []
            if msgs:
                final_text = getattr(msgs[-1], "content", None)
                print("--------------------------------")
                print(final_text)
                print("--------------------------------")
        except Exception:
            final_text = None

        return AgentResult(
            generated_sql=None,
            generated_filter=last_filter,
            result_columns=result_columns,
            result_rows=result_rows,
            raw_final=final_text,
        )
        
    except Exception as e:
        error_msg = str(e)
        
        # Implement simple fallback for common queries if agent fails
        if "recursion" in error_msg.lower() or "timeout" in error_msg.lower():
            try:
                # Simple fallback logic for basic queries
                collections = db.list_collection_names()
                
                # Handle basic "show users" type queries
                if any(word in question.lower() for word in ["show", "list", "get"]) and "user" in question.lower():
                    if "users" in collections:
                        docs = list(db["users"].find({}).limit(10))
                        if docs:
                            all_keys = set()
                            for doc in docs:
                                all_keys.update(doc.keys())
                            all_keys.discard("_id")
                            keys = sorted(list(all_keys))
                            rows = [[str(doc.get(k)) for k in keys] for doc in docs]
                            
                            return AgentResult(
                                generated_sql=None,
                                generated_filter={},
                                result_columns=keys,
                                result_rows=rows,
                                raw_final=f"Fallback: Showing 10 users (agent hit limits)"
                            )
                
                # Handle count queries
                if any(word in question.lower() for word in ["count", "how many"]) and "user" in question.lower():
                    if "users" in collections:
                        count = db["users"].count_documents({})
                        return AgentResult(
                            generated_sql=None,
                            generated_filter={},
                            result_columns=["count"],
                            result_rows=[[count]],
                            raw_final=f"Fallback: User count is {count} (agent hit limits)"
                        )
                        
            except Exception:
                pass
        
        return AgentResult(
            generated_sql=None,
            generated_filter=None,
            result_columns=["error"],
            result_rows=[[f"MongoDB Agent Error: {error_msg}"]],
            raw_final=f"Error: {error_msg}"
        )
