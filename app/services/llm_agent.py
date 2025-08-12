from __future__ import annotations

import json
import os
from dataclasses import dataclass
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
        "Always call run_sql to obtain the final answer. Limit results to 100 rows unless a count/aggregate is requested.\n\n"
        f"Schema:\n{schema_ctx}"
    )

    app = create_react_agent(llm, tools, state_modifier=system_preamble)

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

    # Tools
    def list_collections_tool_fn(_: str = "") -> str:
        return ", ".join(db.list_collection_names())

    def sample_collection_tool_fn(collection: str) -> str:
        doc = db[collection].find_one() or {}
        # Provide a compact view to the model
        preview = {k: v for k, v in doc.items() if k != "_id"}
        return json.dumps(preview)

    def mongo_find_tool_fn(payload: str) -> str:
        nonlocal last_filter, result_columns, result_rows
        # payload should be JSON: {"collection": "name", "filter": {...}}
        try:
            data = json.loads(payload)
        except Exception:
            raise ValueError("Input must be a JSON string with keys 'collection' and 'filter'")
        collection = data.get("collection")
        filt = data.get("filter") or {}
        if not isinstance(filt, dict):
            raise ValueError("'filter' must be an object")
        last_filter = filt
        cursor = db[collection].find(filt).limit(100)
        docs = list(cursor)
        if not docs:
            result_columns, result_rows = [], []
            return json.dumps({"columns": [], "rows": []})
        keys = sorted({k for d in docs for k in d.keys() if k != "_id"})
        rows = [[doc.get(k) for k in keys] for doc in docs]
        result_columns, result_rows = keys, rows
        return json.dumps({"columns": keys, "rows": rows})

    tools = [
        Tool(
            name="list_collections",
            description="List MongoDB collections in the current database.",
            func=list_collections_tool_fn,
        ),
        Tool(
            name="sample_collection",
            description=(
                "Return a sample document (without _id) from the given collection to understand its fields."
            ),
            func=sample_collection_tool_fn,
        ),
        Tool(
            name="mongo_find",
            description=(
                "Execute a MongoDB find. Input is a JSON string like {\"collection\":\"users\", \"filter\":{...}}. "
                "Return value is JSON with 'columns' and 'rows'."
            ),
            func=mongo_find_tool_fn,
        ),
    ]

    system_preamble = (
        "You are a helpful data assistant for MongoDB. "
        "Use the tools to list collections, inspect sample documents, and construct a correct MongoDB filter to answer the user's question. "
        "Always call mongo_find to obtain the final answer. Limit results to 100 documents."
    )

    app = create_react_agent(llm, tools, state_modifier=system_preamble)
    final_state = app.invoke({"messages": [("user", question)]})
    final_text: Optional[str] = None
    try:
        msgs = final_state.get("messages") or []
        if msgs:
            final_text = getattr(msgs[-1], "content", None)
    except Exception:
        final_text = None

    return AgentResult(
        generated_sql=None,
        generated_filter=last_filter,
        result_columns=result_columns,
        result_rows=result_rows,
        raw_final=final_text,
    )


