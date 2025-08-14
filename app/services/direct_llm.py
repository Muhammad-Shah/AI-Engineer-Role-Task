from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict, List, Optional, AsyncGenerator

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

# LangChain imports
try:
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage, SystemMessage
except Exception:
    ChatOpenAI = None
    HumanMessage = None
    SystemMessage = None


def _serialize_value(value: Any) -> Any:
    """Convert database values to JSON-serializable format."""
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    elif isinstance(value, (dict, list)):
        return json.dumps(value, default=str)
    elif value is None:
        return None
    else:
        return str(value)


@dataclass
class DirectLLMResult:
    is_database_query: bool
    generated_sql: Optional[str]
    generated_filter: Optional[Dict[str, Any]]
    result_columns: List[str]
    result_rows: List[List[Any]]
    conversational_response: Optional[str]
    error: Optional[str] = None


def _ensure_langchain_available() -> None:
    if ChatOpenAI is None or HumanMessage is None or SystemMessage is None:
        raise RuntimeError(
            "LangChain not installed. Please install 'langchain' and 'langchain-openai'."
        )


def _get_llm(temperature: float = 0.3) -> "ChatOpenAI":
    _ensure_langchain_available()
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set in environment")
    return ChatOpenAI(model=model, temperature=temperature, streaming=True)


def _build_sql_schema_context(engine: Engine) -> str:
    """Build detailed schema context for SQL databases."""
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    dialect_name = getattr(engine.dialect, "name", "sql")
    
    schema_parts = [f"Database Dialect: {dialect_name}\n"]
    
    for table in tables:
        try:
            cols = inspector.get_columns(table)
            col_details = []
            for c in cols:
                col_type = str(c.get('type', 'unknown'))
                nullable = "" if c.get('nullable', True) else " NOT NULL"
                col_details.append(f"  {c['name']} {col_type}{nullable}")
            
            # Get foreign keys if available
            try:
                fks = inspector.get_foreign_keys(table)
                fk_info = []
                for fk in fks:
                    fk_info.append(f"  FK: {fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']}")
            except:
                fk_info = []
            
            table_info = f"Table: {table}\n" + "\n".join(col_details)
            if fk_info:
                table_info += "\n" + "\n".join(fk_info)
            
            schema_parts.append(table_info)
        except Exception:
            schema_parts.append(f"Table: {table} (schema unavailable)")
    
    return "\n\n".join(schema_parts)


def _build_mongo_schema_context(client: Any, database: str) -> str:
    """Build schema context for MongoDB."""
    db = client[database]
    collections = db.list_collection_names()
    
    schema_parts = [f"MongoDB Database: {database}\n"]
    
    for collection_name in collections:
        try:
            # Get sample documents to understand schema
            sample_docs = list(db[collection_name].find().limit(3))
            doc_count = db[collection_name].count_documents({})
            
            if sample_docs:
                # Extract field information
                all_fields = set()
                field_examples = {}
                for doc in sample_docs:
                    for key, value in doc.items():
                        if key != "_id":
                            all_fields.add(key)
                            if key not in field_examples:
                                field_examples[key] = f"{type(value).__name__}: {repr(value)}"
                
                field_info = [f"  {field} ({field_examples.get(field, 'unknown')})" for field in sorted(all_fields)]
                collection_info = f"Collection: {collection_name} ({doc_count} documents)\n" + "\n".join(field_info)
            else:
                collection_info = f"Collection: {collection_name} (empty)"
            
            schema_parts.append(collection_info)
        except Exception:
            schema_parts.append(f"Collection: {collection_name} (schema unavailable)")
    
    return "\n\n".join(schema_parts)


async def run_direct_sql_llm(
    engine: Engine,
    question: str,
    temperature: float = 0.3,
) -> AsyncGenerator[Dict[str, Any], None]:
    """Direct LLM approach for SQL generation and execution with streaming."""
    _ensure_langchain_available()
    
    try:
        llm = _get_llm(temperature)
        schema_context = _build_sql_schema_context(engine)
        dialect_name = getattr(engine.dialect, "name", "sql")
        
        yield {"event": "start", "message": "Analyzing your question..."}
        
        # System prompt for direct SQL generation
        system_prompt = f"""You are an expert SQL assistant. Analyze the user's question and respond appropriately.

DATABASE SCHEMA:
{schema_context}

DIALECT: {dialect_name}

INSTRUCTIONS:
1. If the question is about database data/queries, generate SQL and respond with JSON format:
   {{"type": "database_query", "sql": "SELECT ...", "explanation": "This query will..."}}

2. If the question is conversational/general, respond with JSON format:
   {{"type": "conversation", "response": "Your conversational response here"}}

3. For database queries:
   - Write valid {dialect_name} SQL syntax
   - Use proper table/column names from schema
   - Limit results to 100 rows unless aggregation
   - Handle date/time queries appropriately
   - Use parameterized queries when possible

4. Always respond with valid JSON in one of the two formats above.

Examples:
- "Show me all users" → {{"type": "database_query", "sql": "SELECT * FROM users LIMIT 100", "explanation": "Retrieving all user records"}}
- "Hello" → {{"type": "conversation", "response": "Hello! I'm here to help you query your database. What would you like to know about your data?"}}
- "How are you?" → {{"type": "conversation", "response": "I'm doing well! I'm ready to help you explore your database. What data would you like to examine?"}}
"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=question)
        ]
        
        yield {"event": "llm_processing", "message": "Generating response..."}
        
        # Get LLM response
        response = await llm.ainvoke(messages)
        llm_content = response.content
        
        yield {"event": "llm_response", "content": llm_content}
        
        # Parse LLM response
        try:
            # Extract JSON from response (handle cases where LLM adds extra text)
            json_match = re.search(r'\{.*\}', llm_content, re.DOTALL)
            if json_match:
                response_data = json.loads(json_match.group())
            else:
                response_data = json.loads(llm_content)
            
            response_type = response_data.get("type")
            
            if response_type == "database_query":
                sql = response_data.get("sql")
                explanation = response_data.get("explanation", "")
                
                if sql:
                    yield {"event": "generated_sql", "sql": sql, "explanation": explanation}
                    
                    # Execute SQL
                    yield {"event": "executing_sql", "message": "Executing query..."}
                    
                    with engine.connect() as conn:
                        result = conn.execute(text(sql))
                        
                        if result.returns_rows:
                            columns = list(result.keys())
                            rows = [[_serialize_value(value) for value in row] for row in result.fetchall()]
                            
                            yield {
                                "event": "result",
                                "data": {
                                    "columns": columns,
                                    "rows": rows,
                                    "sql": sql,
                                    "explanation": explanation
                                }
                            }
                        else:
                            yield {
                                "event": "result", 
                                "data": {
                                    "columns": ["affected_rows"],
                                    "rows": [[result.rowcount]],
                                    "sql": sql,
                                    "explanation": explanation
                                }
                            }
                else:
                    yield {"event": "error", "message": "No SQL generated from question"}
                    
            elif response_type == "conversation":
                conversational_response = response_data.get("response", "I'm here to help with your database!")
                yield {
                    "event": "conversation",
                    "message": conversational_response
                }
            else:
                yield {"event": "error", "message": f"Unknown response type: {response_type}"}
                
        except json.JSONDecodeError:
            # If JSON parsing fails, treat as conversational
            yield {
                "event": "conversation", 
                "message": llm_content
            }
        except Exception as e:
            yield {"event": "sql_error", "message": f"SQL execution error: {str(e)}"}
    
    except Exception as e:
        yield {"event": "error", "message": f"System error: {str(e)}"}
    
    finally:
        yield {"event": "end"}


async def run_direct_mongo_llm(
    client: Any,
    database: str,
    question: str,
    temperature: float = 0.3,
) -> AsyncGenerator[Dict[str, Any], None]:
    """Direct LLM approach for MongoDB query generation and execution with streaming."""
    _ensure_langchain_available()
    
    try:
        llm = _get_llm(temperature)
        schema_context = _build_mongo_schema_context(client, database)
        
        yield {"event": "start", "message": "Analyzing your question..."}
        
        # System prompt for direct MongoDB generation
        system_prompt = f"""You are an expert MongoDB assistant. Analyze the user's question and respond appropriately.

DATABASE SCHEMA:
{schema_context}

INSTRUCTIONS:
1. If the question is about database data/queries, generate MongoDB query and respond with JSON format:
   {{"type": "database_query", "collection": "collection_name", "operation": "find|count", "filter": {{}}, "explanation": "This query will..."}}

2. If the question is conversational/general, respond with JSON format:
   {{"type": "conversation", "response": "Your conversational response here"}}

3. For database queries:
   - Use exact collection names from schema
   - Write valid MongoDB filter syntax
   - Use "find" for data retrieval, "count" for counting
   - Limit results to 100 documents
   - Handle text search with $regex operator

4. Always respond with valid JSON in one of the two formats above.

MongoDB Filter Examples:
- Find all: {{}}
- Find by field: {{"name": "John"}}
- Find with comparison: {{"age": {{"$gt": 25}}}}
- Find with regex: {{"name": {{"$regex": "John", "$options": "i"}}}}
- Find multiple: {{"active": true, "department": "Engineering"}}

Examples:
- "Show me all users" → {{"type": "database_query", "collection": "users", "operation": "find", "filter": {{}}, "explanation": "Retrieving all user documents"}}
- "How many users?" → {{"type": "database_query", "collection": "users", "operation": "count", "filter": {{}}, "explanation": "Counting total users"}}
- "Hello" → {{"type": "conversation", "response": "Hello! I can help you query your MongoDB database. What would you like to know?"}}
"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=question)
        ]
        
        yield {"event": "llm_processing", "message": "Generating response..."}
        
        # Get LLM response
        response = await llm.ainvoke(messages)
        llm_content = response.content
        
        yield {"event": "llm_response", "content": llm_content}
        
        # Parse LLM response
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', llm_content, re.DOTALL)
            if json_match:
                response_data = json.loads(json_match.group())
            else:
                response_data = json.loads(llm_content)
            
            response_type = response_data.get("type")
            
            if response_type == "database_query":
                collection = response_data.get("collection")
                operation = response_data.get("operation", "find")
                filter_query = response_data.get("filter", {})
                explanation = response_data.get("explanation", "")
                
                if collection:
                    db = client[database]
                    
                    # Validate collection exists
                    if collection not in db.list_collection_names():
                        available = ', '.join(db.list_collection_names())
                        yield {"event": "error", "message": f"Collection '{collection}' not found. Available: {available}"}
                        return
                    
                    yield {
                        "event": "generated_filter", 
                        "collection": collection,
                        "operation": operation,
                        "filter": filter_query, 
                        "explanation": explanation
                    }
                    
                    # Execute MongoDB query
                    yield {"event": "executing_query", "message": f"Executing {operation} on {collection}..."}
                    
                    if operation == "count":
                        count = db[collection].count_documents(filter_query)
                        yield {
                            "event": "result",
                            "data": {
                                "columns": ["count"],
                                "rows": [[count]],
                                "collection": collection,
                                "operation": operation,
                                "filter": filter_query,
                                "explanation": explanation
                            }
                        }
                    else:  # find operation
                        cursor = db[collection].find(filter_query).limit(100)
                        docs = list(cursor)
                        
                        if not docs:
                            yield {
                                "event": "result",
                                "data": {
                                    "columns": [],
                                    "rows": [],
                                    "collection": collection,
                                    "operation": operation,
                                    "filter": filter_query,
                                    "explanation": explanation,
                                    "message": "No documents found matching the criteria"
                                }
                            }
                        else:
                            # Extract columns and rows
                            all_keys = set()
                            for doc in docs:
                                all_keys.update(doc.keys())
                            all_keys.discard("_id")
                            
                            columns = sorted(list(all_keys))
                            rows = []
                            
                            for doc in docs:
                                row = []
                                for col in columns:
                                    value = doc.get(col)
                                    if value is None:
                                        row.append(None)
                                    else:
                                        row.append(_serialize_value(value))
                                rows.append(row)
                            
                            yield {
                                "event": "result",
                                "data": {
                                    "columns": columns,
                                    "rows": rows,
                                    "collection": collection,
                                    "operation": operation,
                                    "filter": filter_query,
                                    "explanation": explanation
                                }
                            }
                else:
                    yield {"event": "error", "message": "No collection specified in query"}
                    
            elif response_type == "conversation":
                conversational_response = response_data.get("response", "I'm here to help with your database!")
                yield {
                    "event": "conversation",
                    "message": conversational_response
                }
            else:
                yield {"event": "error", "message": f"Unknown response type: {response_type}"}
                
        except json.JSONDecodeError:
            # If JSON parsing fails, treat as conversational
            yield {
                "event": "conversation", 
                "message": llm_content
            }
        except Exception as e:
            yield {"event": "query_error", "message": f"Query execution error: {str(e)}"}
    
    except Exception as e:
        yield {"event": "error", "message": f"System error: {str(e)}"}
    
    finally:
        yield {"event": "end"}



