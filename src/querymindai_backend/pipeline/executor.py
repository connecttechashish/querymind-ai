import os
import time
import sqlite3
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Any, Optional
from querymindai_backend.config import get_settings

class SQLExecutionResult(BaseModel):
    columns: List[str] = Field(default_factory=list)
    rows: List[List[Any]] = Field(default_factory=list)
    row_count: int = 0
    latency_ms: float = 0.0
    error: Optional[str] = None

def get_readonly_connection() -> sqlite3.Connection:
    """
    Returns a read-only SQLite database connection using URI parameters.
    """
    settings = get_settings()
    db_path = settings.db_path
    
    # Resolve absolute path and convert to file URI for read-only mode
    db_uri = Path(db_path).resolve().as_uri() + "?mode=ro"
    
    # sqlite3 requires uri=True to process query parameters in filename
    conn = sqlite3.connect(db_uri, uri=True)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn

def execute_sql(sanitized_sql: str) -> SQLExecutionResult:
    """
    Executes a SELECT SQL statement on a read-only database connection.
    Captures columns, rows, row count, execution latency, and errors safely.
    """
    sql_stripped = sanitized_sql.strip()
    
    # Pre-execution check: block non-SELECT statements
    if not sql_stripped.upper().startswith("SELECT"):
        return SQLExecutionResult(
            columns=[],
            rows=[],
            row_count=0,
            latency_ms=0.0,
            error="Database execution error: Only SELECT queries are permitted."
        )

    try:
        conn = get_readonly_connection()
        cursor = conn.cursor()
        
        start_time = time.perf_counter()
        cursor.execute(sql_stripped)
        rows_raw = cursor.fetchall()
        end_time = time.perf_counter()
        
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = [list(row) for row in rows_raw]
        row_count = len(rows)
        latency_ms = (end_time - start_time) * 1000
        
        conn.close()
        return SQLExecutionResult(
            columns=columns,
            rows=rows,
            row_count=row_count,
            latency_ms=round(latency_ms, 2),
            error=None
        )
    except Exception as e:
        return SQLExecutionResult(
            columns=[],
            rows=[],
            row_count=0,
            latency_ms=0.0,
            error=f"Database execution error: {str(e)}"
        )
