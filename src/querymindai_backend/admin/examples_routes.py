import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from querymindai_backend.database import get_admin_db_connection

router = APIRouter(tags=["Admin Examples"])

class ExampleResponse(BaseModel):
    id: int
    question: str
    sql_query: str
    query_type: str
    is_active: bool
    created_at: str

class ExampleCreate(BaseModel):
    question: str
    sql_query: str
    query_type: str
    is_active: bool = True

class ExampleUpdate(BaseModel):
    question: Optional[str] = None
    sql_query: Optional[str] = None
    query_type: Optional[str] = None
    is_active: Optional[bool] = None

@router.get("/admin/examples", response_model=List[ExampleResponse])
def get_examples() -> List[ExampleResponse]:
    """
    Retrieves all few-shot examples from the admin configuration database.
    """
    conn = get_admin_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, question, sql_query, query_type, is_active, created_at FROM few_shot_examples ORDER BY id DESC;")
        rows = cursor.fetchall()
        return [
            ExampleResponse(
                id=row["id"],
                question=row["question"],
                sql_query=row["sql_query"],
                query_type=row["query_type"],
                is_active=bool(row["is_active"]),
                created_at=row["created_at"]
            )
            for row in rows
        ]
    finally:
        conn.close()

@router.post("/admin/examples", response_model=ExampleResponse)
def create_example(example: ExampleCreate) -> ExampleResponse:
    """
    Creates a new few-shot example in the database.
    """
    created_at = datetime.datetime.utcnow().isoformat()
    conn = get_admin_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO few_shot_examples (question, sql_query, query_type, is_active, created_at) VALUES (?, ?, ?, ?, ?);",
            (example.question, example.sql_query, example.query_type, int(example.is_active), created_at)
        )
        conn.commit()
        example_id = cursor.lastrowid
        
        cursor.execute("SELECT id, question, sql_query, query_type, is_active, created_at FROM few_shot_examples WHERE id = ?;", (example_id,))
        row = cursor.fetchone()
        return ExampleResponse(
            id=row["id"],
            question=row["question"],
            sql_query=row["sql_query"],
            query_type=row["query_type"],
            is_active=bool(row["is_active"]),
            created_at=row["created_at"]
        )
    finally:
        conn.close()

@router.put("/admin/examples/{example_id}", response_model=ExampleResponse)
def update_example(example_id: int, example: ExampleUpdate) -> ExampleResponse:
    """
    Updates an existing few-shot example.
    """
    conn = get_admin_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, question, sql_query, query_type, is_active FROM few_shot_examples WHERE id = ?;", (example_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Example not found")
            
        question = example.question if example.question is not None else row["question"]
        sql_query = example.sql_query if example.sql_query is not None else row["sql_query"]
        query_type = example.query_type if example.query_type is not None else row["query_type"]
        is_active = int(example.is_active) if example.is_active is not None else row["is_active"]
        
        cursor.execute(
            "UPDATE few_shot_examples SET question = ?, sql_query = ?, query_type = ?, is_active = ? WHERE id = ?;",
            (question, sql_query, query_type, is_active, example_id)
        )
        conn.commit()
        
        cursor.execute("SELECT id, question, sql_query, query_type, is_active, created_at FROM few_shot_examples WHERE id = ?;", (example_id,))
        updated_row = cursor.fetchone()
        return ExampleResponse(
            id=updated_row["id"],
            question=updated_row["question"],
            sql_query=updated_row["sql_query"],
            query_type=updated_row["query_type"],
            is_active=bool(updated_row["is_active"]),
            created_at=updated_row["created_at"]
        )
    finally:
        conn.close()

@router.delete("/admin/examples/{example_id}")
def delete_example(example_id: int):
    """
    Deletes a few-shot example.
    """
    conn = get_admin_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM few_shot_examples WHERE id = ?;", (example_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Example not found")
            
        cursor.execute("DELETE FROM few_shot_examples WHERE id = ?;", (example_id,))
        conn.commit()
        return {"message": "Example deleted successfully", "id": example_id}
    finally:
        conn.close()
