from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class RootResponse(BaseModel):
    message: str
    app_name: str
    version: str

class HealthResponse(BaseModel):
    status: str
    app_name: str
    version: str
    environment: str

class QueryResponse(BaseModel):
    """
    Response model returning the pipeline run execution details and formatted results.
    """
    status: str
    question: str
    sql: Optional[str] = None
    explanation: Optional[str] = None
    table: Optional[List[Dict[str, Any]]] = None
    nl_summary: Optional[str] = None
    row_count: int = 0
    latency_ms: float = 0.0
    error: Optional[str] = None
    needs_clarification: Optional[bool] = None
