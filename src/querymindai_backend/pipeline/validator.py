import sqlglot
from sqlglot import exp
from pydantic import BaseModel, Field
from typing import List, Optional, Set

class SQLValidationResult(BaseModel):
    valid: bool
    sanitized_sql: Optional[str] = None
    errors: List[str] = Field(default_factory=list)

def get_actual_tables() -> Set[str]:
    """
    Connects to the business database and retrieves the set of actual table names (in lowercase).
    """
    try:
        from querymindai_backend.database import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = set(row[0].lower() for row in cursor.fetchall())
        conn.close()
        return tables
    except Exception:
        # Fallback to empty set if database is not accessible
        return set()

def validate_sql(sql: str) -> SQLValidationResult:
    """
    Parses and validates a generated SQL query using sqlglot.
    Enforces SELECT-only, blocks DDL/DML, checks table existence, and injects limit if missing.
    """
    errors = []
    sql_stripped = sql.strip().rstrip(";")
    if not sql_stripped:
        return SQLValidationResult(
            valid=False,
            sanitized_sql=None,
            errors=["SQL query is empty."]
        )

    try:
        expression = sqlglot.parse_one(sql_stripped)
    except sqlglot.errors.ParseError as e:
        return SQLValidationResult(
            valid=False,
            sanitized_sql=None,
            errors=[f"SQL syntax error: {str(e)}"]
        )

    # 1. Block destructive operations (DDL/DML write classes)
    blocked_classes = [
        exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Alter,
        getattr(exp, "TruncateTable", None), getattr(exp, "Truncate", None),
        getattr(exp, "Create", None), getattr(exp, "Command", None)
    ]
    blocked_classes = [cls for cls in blocked_classes if cls is not None]

    has_write = False
    for node in expression.walk():
        if isinstance(node, tuple(blocked_classes)):
            has_write = True
            break

    # 2. Allow SELECT / Union queries only
    is_select = isinstance(expression, (exp.Select, exp.Union))

    if has_write or not is_select:
        errors.append("Invalid query: Only read-only SELECT queries are allowed. Modifying operations (DELETE, DROP, UPDATE, INSERT, TRUNCATE, ALTER) are blocked.")
        return SQLValidationResult(
            valid=False,
            sanitized_sql=None,
            errors=errors
        )

    # 3. Reject SQL referencing tables that do not exist
    referenced_tables = set(table.name.lower() for table in expression.find_all(exp.Table))
    actual_tables = get_actual_tables()
    
    # Only perform the check if we successfully fetched the schema (to avoid errors in unseeded envs)
    if actual_tables and referenced_tables:
        invalid_tables = referenced_tables - actual_tables
        if invalid_tables:
            errors.append(f"Invalid query: Table(s) {', '.join(invalid_tables)} do not exist in the database.")
            return SQLValidationResult(
                valid=False,
                sanitized_sql=None,
                errors=errors
            )

    # 4. Add LIMIT 100 when missing
    limit = expression.args.get("limit")
    if not limit:
        if hasattr(expression, "limit"):
            try:
                expression = expression.limit(100)
            except Exception:
                pass

    sanitized_sql = expression.sql() + ";"
    return SQLValidationResult(
        valid=True,
        sanitized_sql=sanitized_sql,
        errors=[]
    )
