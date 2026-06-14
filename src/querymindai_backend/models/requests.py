from pydantic import BaseModel
from typing import Optional

class QueryRequest(BaseModel):
    """
    Request model for the text-to-SQL query pipeline API.
    """
    question: str
    user_id: Optional[str] = None
    include_sql: bool = True
    include_explanation: bool = True
