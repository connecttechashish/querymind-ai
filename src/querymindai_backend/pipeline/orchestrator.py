from typing import Dict, Any
from querymindai_backend.database import get_db_connection, get_admin_db_connection
from querymindai_backend.pipeline.graph import QueryPipelineState
from querymindai_backend.pipeline.classifier import classify_query, QueryType
from querymindai_backend.pipeline.linker import link_schema, read_schema
from querymindai_backend.pipeline.retriever import retrieve_examples
from querymindai_backend.pipeline.generator import build_sql_prompt, generate_sql
from querymindai_backend.pipeline.validator import validate_sql
from querymindai_backend.pipeline.executor import execute_sql
from querymindai_backend.pipeline.formatter import format_result

def run_query_pipeline(question: str) -> QueryPipelineState:
    """
    Runs the full text-to-SQL analytics pipeline end-to-end sequentially.
    
    1. Classify query intent
    2. If unsupported, stop
    3. Link schema tables/columns and resolve synonyms
    4. If ambiguity detected, stop and request clarification
    5. Retrieve matching few-shot examples
    6. Generate SQL using the builder & generator
    7. Validate generated SQL structure and table names
    8. If invalid, stop
    9. Execute SQL securely on read-only connection
    10. Format columns and rows into a structured summary & chart recommendation
    """
    # Initialize pipeline state
    state: QueryPipelineState = {
        "question": question,
        "classification": None,
        "linked_schema": None,
        "examples": None,
        "generation": None,
        "validation": None,
        "execution": None,
        "formatted_result": None,
        "status": "pending",
        "error": None,
        "needs_clarification": False
    }

    # 1. Classify Query
    try:
        class_res = classify_query(question)
        state["classification"] = class_res
        
        # 2. Check for unsupported intent
        if class_res.query_type == QueryType.UNSUPPORTED:
            state["status"] = "unsupported"
            state["error"] = "Unsupported query type: " + (class_res.reason or "unknown reason")
            return state
    except Exception as e:
        state["status"] = "failed"
        state["error"] = f"Classification failed: {str(e)}"
        return state

    # 3. Link Schema & Synonyms
    try:
        link_res = link_schema(question)
        state["linked_schema"] = link_res
        
        # 4. Check for ambiguity / needs clarification
        if link_res.needs_clarification:
            state["status"] = "clarification"
            state["needs_clarification"] = True
            state["error"] = f"Ambiguous terms detected. Ambiguities: {', '.join(link_res.ambiguities)}"
            return state
    except Exception as e:
        state["status"] = "failed"
        state["error"] = f"Schema linking failed: {str(e)}"
        return state

    # 5. Retrieve few-shot examples
    try:
        examples = retrieve_examples(question)
        state["examples"] = examples
    except Exception:
        state["examples"] = []

    # 6. Generate SQL Query
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
            question=question,
            dialect=dialect,
            schema_context=schema_context,
            resolved_tables=link_res.resolved_tables,
            resolved_columns=link_res.resolved_columns,
            few_shot_examples=state["examples"],
            max_rows_limit=max_rows_limit
        )

        # Call generation
        gen_res = generate_sql(
            question=question,
            prompt=prompt,
            provider=provider,
            model_name=model_name
        )
        state["generation"] = gen_res
    except Exception as e:
        state["status"] = "failed"
        state["error"] = f"SQL generation failed: {str(e)}"
        return state

    # 7. Validate SQL query
    try:
        val_res = validate_sql(gen_res.sql)
        state["validation"] = val_res

        # 8. Check if validation failed
        if not val_res.valid:
            state["status"] = "failed"
            state["error"] = f"SQL validation failed: {', '.join(val_res.errors)}"
            return state
    except Exception as e:
        state["status"] = "failed"
        state["error"] = f"SQL validation execution failed: {str(e)}"
        return state

    # 9. Execute SQL securely
    try:
        sql_to_run = val_res.sanitized_sql if val_res.sanitized_sql else gen_res.sql
        exec_res = execute_sql(sql_to_run)
        state["execution"] = exec_res

        if exec_res.error:
            state["status"] = "failed"
            state["error"] = f"SQL execution error: {exec_res.error}"
            return state
    except Exception as e:
        state["status"] = "failed"
        state["error"] = f"SQL execution failed: {str(e)}"
        return state

    # 10. Format execution output
    try:
        fmt_res = format_result(exec_res.columns, exec_res.rows)
        state["formatted_result"] = fmt_res
        state["status"] = "success"
    except Exception as e:
        state["status"] = "failed"
        state["error"] = f"Formatting execution result failed: {str(e)}"

    return state
