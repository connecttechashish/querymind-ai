from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from querymindai_backend.database import get_admin_db_connection

router = APIRouter(tags=["Admin Schema"])

class SchemaColumnResponse(BaseModel):
    id: int
    table_name: str
    column_name: str
    data_type: str
    description: Optional[str] = None
    is_sensitive: bool

@router.get("/admin/schema", response_model=List[SchemaColumnResponse])
def get_admin_schema() -> List[SchemaColumnResponse]:
    """
    Retrieves all schema columns from the admin configuration database.
    """
    conn = get_admin_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, table_name, column_name, data_type, description, is_sensitive "
            "FROM schema_columns ORDER BY table_name, column_name;"
        )
        rows = cursor.fetchall()
        return [
            SchemaColumnResponse(
                id=row["id"],
                table_name=row["table_name"],
                column_name=row["column_name"],
                data_type=row["data_type"],
                description=row["description"],
                is_sensitive=bool(row["is_sensitive"])
            )
            for row in rows
        ]
    finally:
        conn.close()
