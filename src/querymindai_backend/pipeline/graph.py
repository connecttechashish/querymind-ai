from typing import TypedDict, List, Optional, Dict, Any
from langgraph.graph import StateGraph, START, END

from querymindai_backend.database import get_db_connection, get_admin_db_connection
from querymindai_backend.pipeline.classifier import classify_query, QueryType, ClassifierResult
from querymindai_backend.pipeline.linker import link_schema, read_schema, SchemaLinkResult
from querymindai_backend.pipeline.retriever import retrieve_examples, RetrievedExample
from querymindai_backend.pipeline.generator import build_sql_prompt, generate_sql, SQLGenerationResult
from querymindai_backend.pipeline.validator import validate_sql, SQLValidationResult
from querymindai_backend.pipeline.executor import execute_sql, SQLExecutionResult
from querymindai_backend.pipeline.formatter import format_result, FormatResult

class QueryPipelineState(TypedDict, total=False):
    """
    State definition for the LangGraph query execution pipeline.
    Allows partial updates at each stage of the pipeline graph.
    """
    question: str
    classification: Optional[ClassifierResult]
    linked_schema: Optional[SchemaLinkResult]
    examples: Optional[List[RetrievedExample]]
    generation: Optional[SQLGenerationResult]
    validation: Optional[SQLValidationResult]
    execution: Optional[SQLExecutionResult]
    formatted_result: Optional[FormatResult]
    status: str
    error: Optional[str]
    needs_clarification: bool

# --- Node Functions ---

def node_classify(state: QueryPipelineState) -> Dict[str, Any]:
    """Classifies the query type (e.g. simple, join, unsupported)."""
    if state.get("status") in ("failed", "unsupported", "clarification"):
        return {}
    try:
        class_res = classify_query(state["question"])
        if class_res.query_type == QueryType.UNSUPPORTED:
            return {
                "classification": class_res,
                "status": "unsupported",
                "error": "Unsupported query type: " + (class_res.reason or "unknown reason")
            }
        return {"classification": class_res}
    except Exception as e:
        return {
            "status": "failed",
            "error": f"Classification failed: {str(e)}"
        }

def node_link_schema(state: QueryPipelineState) -> Dict[str, Any]:
    """Links synonyms in the question to database tables/columns."""
    if state.get("status") in ("failed", "unsupported", "clarification"):
        return {}
    try:
        link_res = link_schema(state["question"])
        if link_res.needs_clarification:
            return {
                "linked_schema": link_res,
                "status": "clarification",
                "needs_clarification": True,
                "error": f"Ambiguous terms detected. Ambiguities: {', '.join(link_res.ambiguities)}"
            }
        return {"linked_schema": link_res}
    except Exception as e:
        return {
            "status": "failed",
            "error": f"Schema linking failed: {str(e)}"
        }

def node_retrieve_examples(state: QueryPipelineState) -> Dict[str, Any]:
    """Retrieves related few-shot query-to-SQL training examples."""
    if state.get("status") in ("failed", "unsupported", "clarification"):
        return {}
    try:
        examples = retrieve_examples(state["question"])
        return {"examples": examples}
    except Exception:
        return {"examples": []}

def node_generate_sql(state: QueryPipelineState) -> Dict[str, Any]:
    """Generates the prompt and calls the text-to-SQL generation model."""
    if state.get("status") in ("failed", "unsupported", "clarification"):
        return {}
    try:
        # Load business database schema context
        try:
            conn = get_db_connection()
            schema_context = read_schema(conn)
            conn.close()
        except Exception:
            schema_context = {}

        # Default model settings (with fallback)
        provider = "mock"
        model_name = "mock-sql-generator"
        dialect = "sqlite"
        max_rows_limit = 100

        # Load database settings if available
        try:
            admin_conn = get_admin_db_connection()
            cursor = admin_conn.cursor()
            cursor.execute("SELECT provider, model_name, sql_dialect FROM model_config ORDER BY id DESC LIMIT 1;")
            row = cursor.fetchone()
            if row:
                provider = row["provider"]
                model_name = row["model_name"]
                dialect = row["sql_dialect"]
                
            cursor.execute("SELECT max_row_limit FROM guardrails_config ORDER BY id DESC LIMIT 1;")
            row_limit = cursor.fetchone()
            if row_limit:
                max_rows_limit = row_limit["max_row_limit"]
            admin_conn.close()
        except Exception:
            pass

        # Build Prompt
        prompt = build_sql_prompt(
            question=state["question"],
            dialect=dialect,
            schema_context=schema_context,
            resolved_tables=state["linked_schema"].resolved_tables if state.get("linked_schema") else [],
            resolved_columns=state["linked_schema"].resolved_columns if state.get("linked_schema") else [],
            few_shot_examples=state.get("examples") or [],
            max_rows_limit=max_rows_limit
        )

        # Call generation
        gen_res = generate_sql(
            question=state["question"],
            prompt=prompt,
            provider=provider,
            model_name=model_name
        )
        return {"generation": gen_res}
    except Exception as e:
        return {
            "status": "failed",
            "error": f"SQL generation failed: {str(e)}"
        }

def node_validate_sql(state: QueryPipelineState) -> Dict[str, Any]:
    """Validates the generated SQL structure and table names."""
    if state.get("status") in ("failed", "unsupported", "clarification"):
        return {}
    try:
        sql = state["generation"].sql if state.get("generation") else ""
        val_res = validate_sql(sql)
        if not val_res.valid:
            return {
                "validation": val_res,
                "status": "failed",
                "error": f"SQL validation failed: {', '.join(val_res.errors)}"
            }
        return {"validation": val_res}
    except Exception as e:
        return {
            "status": "failed",
            "error": f"SQL validation execution failed: {str(e)}"
        }

def node_execute_sql(state: QueryPipelineState) -> Dict[str, Any]:
    """Executes the safe sanitized SQL query on read-only database."""
    if state.get("status") in ("failed", "unsupported", "clarification"):
        return {}
    try:
        sql = state["validation"].sanitized_sql if (state.get("validation") and state["validation"].sanitized_sql) else (state["generation"].sql if state.get("generation") else "")
        exec_res = execute_sql(sql)
        if exec_res.error:
            return {
                "execution": exec_res,
                "status": "failed",
                "error": f"SQL execution error: {exec_res.error}"
            }
        return {"execution": exec_res}
    except Exception as e:
        return {
            "status": "failed",
            "error": f"SQL execution failed: {str(e)}"
        }

def node_format_result(state: QueryPipelineState) -> Dict[str, Any]:
    """Formats the data rows and column names into readable response representation."""
    if state.get("status") in ("failed", "unsupported", "clarification"):
        return {}
    try:
        columns = state["execution"].columns if state.get("execution") else []
        rows = state["execution"].rows if state.get("execution") else []
        fmt_res = format_result(columns, rows)
        return {
            "formatted_result": fmt_res,
            "status": "success"
        }
    except Exception as e:
        return {
            "status": "failed",
            "error": f"Formatting execution result failed: {str(e)}"
        }

# --- Routing Functions ---

def route_after_classify(state: QueryPipelineState) -> str:
    if state.get("status") == "unsupported":
        return END
    return "link_schema"

def route_after_link_schema(state: QueryPipelineState) -> str:
    if state.get("status") == "clarification":
        return END
    return "retrieve_examples"

def route_after_generate_sql(state: QueryPipelineState) -> str:
    if state.get("status") == "failed":
        return END
    return "validate_sql"

def route_after_validate_sql(state: QueryPipelineState) -> str:
    if state.get("status") == "failed":
        return END
    return "execute_sql"

def route_after_execute_sql(state: QueryPipelineState) -> str:
    if state.get("status") == "failed":
        return END
    return "format_result"

# --- Compiled Graph Builder ---

def create_query_graph():
    """
    Constructs and compiles the StateGraph workflow using LangGraph.
    """
    builder = StateGraph(QueryPipelineState)

    # 1. Add nodes
    builder.add_node("classify", node_classify)
    builder.add_node("link_schema", node_link_schema)
    builder.add_node("retrieve_examples", node_retrieve_examples)
    builder.add_node("generate_sql", node_generate_sql)
    builder.add_node("validate_sql", node_validate_sql)
    builder.add_node("execute_sql", node_execute_sql)
    builder.add_node("format_result", node_format_result)

    # 2. Add entry point using START
    builder.add_edge(START, "classify")

    # 3. Add conditional & static edges
    builder.add_conditional_edges(
        "classify",
        route_after_classify,
        {
            END: END,
            "link_schema": "link_schema"
        }
    )
    builder.add_conditional_edges(
        "link_schema",
        route_after_link_schema,
        {
            END: END,
            "retrieve_examples": "retrieve_examples"
        }
    )
    builder.add_edge("retrieve_examples", "generate_sql")
    builder.add_conditional_edges(
        "generate_sql",
        route_after_generate_sql,
        {
            END: END,
            "validate_sql": "validate_sql"
        }
    )
    builder.add_conditional_edges(
        "validate_sql",
        route_after_validate_sql,
        {
            END: END,
            "execute_sql": "execute_sql"
        }
    )
    builder.add_conditional_edges(
        "execute_sql",
        route_after_execute_sql,
        {
            END: END,
            "format_result": "format_result"
        }
    )
    builder.add_edge("format_result", END)

    return builder.compile()
