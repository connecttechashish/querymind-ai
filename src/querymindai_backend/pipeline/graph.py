from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph, START, END

from querymindai_backend.pipeline.classifier import classify_query, QueryType, ClassifierResult
from querymindai_backend.pipeline.linker import link_schema, read_schema, SchemaLinkResult
from querymindai_backend.pipeline.retriever import retrieve_examples, RetrievedExample
from querymindai_backend.pipeline.generator import build_sql_prompt, generate_sql, SQLGenerationResult
from querymindai_backend.pipeline.validator import validate_sql, SQLValidationResult
from querymindai_backend.pipeline.executor import execute_sql, SQLExecutionResult
from querymindai_backend.pipeline.formatter import format_result, FormatResult
from querymindai_backend.database import get_db_connection, get_admin_db_connection

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

# Graph Nodes

def classify_node(state: QueryPipelineState) -> dict:
    """Classifies user intent and sets state status to unsupported if query is invalid."""
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
        return {"status": "failed", "error": f"Classification failed: {str(e)}"}

def link_schema_node(state: QueryPipelineState) -> dict:
    """Resolves schema links and detects ambiguities."""
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
        return {"status": "failed", "error": f"Schema linking failed: {str(e)}"}

def retrieve_examples_node(state: QueryPipelineState) -> dict:
    """Retrieves few-shot examples from the admin configuration database."""
    try:
        examples = retrieve_examples(state["question"])
        return {"examples": examples}
    except Exception:
        return {"examples": []}

def generate_sql_node(state: QueryPipelineState) -> dict:
    """Constructs prompt context and invokes the SQL generator."""
    try:
        # Load business database schema context
        try:
            conn = get_db_connection()
            schema_context = read_schema(conn)
            conn.close()
        except Exception:
            schema_context = {}

        # Default model settings
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

        link_res = state.get("linked_schema")
        prompt = build_sql_prompt(
            question=state["question"],
            dialect=dialect,
            schema_context=schema_context,
            resolved_tables=link_res.resolved_tables if link_res else [],
            resolved_columns=link_res.resolved_columns if link_res else [],
            few_shot_examples=state.get("examples") or [],
            max_rows_limit=max_rows_limit
        )

        gen_res = generate_sql(
            question=state["question"],
            prompt=prompt,
            provider=provider,
            model_name=model_name
        )
        return {"generation": gen_res}
    except Exception as e:
        return {"status": "failed", "error": f"SQL generation failed: {str(e)}"}

def validate_sql_node(state: QueryPipelineState) -> dict:
    """Validates generated SQL logic and tables schema."""
    try:
        gen_res = state.get("generation")
        if not gen_res:
            return {"status": "failed", "error": "No SQL query generated to validate."}
        
        val_res = validate_sql(gen_res.sql)
        if not val_res.valid:
            return {
                "validation": val_res,
                "status": "failed",
                "error": f"SQL validation failed: {', '.join(val_res.errors)}"
            }
        return {"validation": val_res}
    except Exception as e:
        return {"status": "failed", "error": f"SQL validation execution failed: {str(e)}"}

def execute_sql_node(state: QueryPipelineState) -> dict:
    """Executes validated SQL query on business database securely."""
    try:
        gen_res = state.get("generation")
        val_res = state.get("validation")
        if not gen_res:
            return {"status": "failed", "error": "No SQL query generated to execute."}
        
        sql_to_run = val_res.sanitized_sql if (val_res and val_res.sanitized_sql) else gen_res.sql
        exec_res = execute_sql(sql_to_run)
        
        if exec_res.error:
            return {
                "execution": exec_res,
                "status": "failed",
                "error": f"SQL execution error: {exec_res.error}"
            }
        return {"execution": exec_res}
    except Exception as e:
        return {"status": "failed", "error": f"SQL execution failed: {str(e)}"}

def format_result_node(state: QueryPipelineState) -> dict:
    """Formats SQL rows into list of dicts and checks for chart candidates."""
    try:
        exec_res = state.get("execution")
        if not exec_res:
            return {"status": "failed", "error": "No execution result to format."}
        
        fmt_res = format_result(exec_res.columns, exec_res.rows)
        return {
            "formatted_result": fmt_res,
            "status": "success"
        }
    except Exception as e:
        return {"status": "failed", "error": f"Formatting execution result failed: {str(e)}"}

# Conditional Routing Deciders

def check_classify_status(state: QueryPipelineState):
    if state.get("status") == "unsupported":
        return END
    return "link_schema"

def check_link_status(state: QueryPipelineState):
    if state.get("status") == "clarification":
        return END
    return "retrieve_examples"

def check_validation_status(state: QueryPipelineState):
    if state.get("status") == "failed":
        return END
    return "execute_sql"

def check_execution_status(state: QueryPipelineState):
    if state.get("status") == "failed":
        return END
    return "format_result"

# Graph Assembler

def create_query_graph():
    """
    Compiles and returns the LangGraph workflow for the text-to-SQL pipeline.
    """
    builder = StateGraph(QueryPipelineState)
    
    # Register Nodes
    builder.add_node("classify", classify_node)
    builder.add_node("link_schema", link_schema_node)
    builder.add_node("retrieve_examples", retrieve_examples_node)
    builder.add_node("generate_sql", generate_sql_node)
    builder.add_node("validate_sql", validate_sql_node)
    builder.add_node("execute_sql", execute_sql_node)
    builder.add_node("format_result", format_result_node)
    
    # Establish Edges & Routing
    builder.add_edge(START, "classify")
    builder.add_conditional_edges("classify", check_classify_status)
    builder.add_conditional_edges("link_schema", check_link_status)
    builder.add_edge("retrieve_examples", "generate_sql")
    builder.add_edge("generate_sql", "validate_sql")
    builder.add_conditional_edges("validate_sql", check_validation_status)
    builder.add_conditional_edges("execute_sql", check_execution_status)
    builder.add_edge("format_result", END)
    
    return builder.compile()
