from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from querymindai_backend.database import get_admin_db_connection

router = APIRouter(tags=["Admin Logs"])

class QueryLogResponse(BaseModel):
    id: int
    nl_query: str
    generated_sql: Optional[str] = None
    execution_status: str
    latency_ms: Optional[float] = None
    row_count: Optional[int] = None
    error_message: Optional[str] = None
    created_at: str

@router.get("/admin/logs", response_model=List[QueryLogResponse])
def get_query_logs() -> List[QueryLogResponse]:
    """
    Retrieves all text-to-SQL query log entries from the admin database,
    ordered by the most recent first.
    """
    conn = get_admin_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, nl_query, generated_sql, execution_status, latency_ms, row_count, error_message, created_at "
            "FROM query_logs ORDER BY id DESC;"
        )
        rows = cursor.fetchall()
        return [
            QueryLogResponse(
                id=row["id"],
                nl_query=row["nl_query"],
                generated_sql=row["generated_sql"],
                execution_status=row["execution_status"],
                latency_ms=row["latency_ms"],
                row_count=row["row_count"],
                error_message=row["error_message"],
                created_at=row["created_at"]
            )
            for row in rows
        ]
    finally:
        conn.close()
