import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from querymindai_backend.database import get_admin_db_connection

router = APIRouter(tags=["Admin Guardrails"])

class GuardrailsResponse(BaseModel):
    id: int
    allow_delete: bool
    allow_drop: bool
    allow_update: bool
    allow_insert: bool
    allow_alter: bool
    max_row_limit: int
    updated_at: str

class GuardrailsUpdate(BaseModel):
    allow_delete: Optional[bool] = None
    allow_drop: Optional[bool] = None
    allow_update: Optional[bool] = None
    allow_insert: Optional[bool] = None
    allow_alter: Optional[bool] = None
    max_row_limit: Optional[int] = None

@router.get("/admin/guardrails", response_model=GuardrailsResponse)
def get_guardrails() -> GuardrailsResponse:
    """
    Retrieves the current active SQL execution guardrails configuration.
    """
    conn = get_admin_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, allow_delete, allow_drop, allow_update, allow_insert, allow_alter, max_row_limit, updated_at "
            "FROM guardrails_config ORDER BY id DESC LIMIT 1;"
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Guardrails config not found")
        return GuardrailsResponse(
            id=row["id"],
            allow_delete=bool(row["allow_delete"]),
            allow_drop=bool(row["allow_drop"]),
            allow_update=bool(row["allow_update"]),
            allow_insert=bool(row["allow_insert"]),
            allow_alter=bool(row["allow_alter"]),
            max_row_limit=row["max_row_limit"],
            updated_at=row["updated_at"]
        )
    finally:
        conn.close()

@router.patch("/admin/guardrails", response_model=GuardrailsResponse)
def update_guardrails(update: GuardrailsUpdate) -> GuardrailsResponse:
    """
    Updates the active SQL execution guardrails configuration parameters.
    """
    conn = get_admin_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, allow_delete, allow_drop, allow_update, allow_insert, allow_alter, max_row_limit "
            "FROM guardrails_config ORDER BY id DESC LIMIT 1;"
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Guardrails config not found")
            
        guardrail_id = row["id"]
        
        allow_delete = int(update.allow_delete) if update.allow_delete is not None else row["allow_delete"]
        allow_drop = int(update.allow_drop) if update.allow_drop is not None else row["allow_drop"]
        allow_update = int(update.allow_update) if update.allow_update is not None else row["allow_update"]
        allow_insert = int(update.allow_insert) if update.allow_insert is not None else row["allow_insert"]
        allow_alter = int(update.allow_alter) if update.allow_alter is not None else row["allow_alter"]
        max_row_limit = update.max_row_limit if update.max_row_limit is not None else row["max_row_limit"]
        
        updated_at = datetime.datetime.utcnow().isoformat()
        
        cursor.execute(
            "UPDATE guardrails_config SET allow_delete = ?, allow_drop = ?, allow_update = ?, allow_insert = ?, allow_alter = ?, max_row_limit = ?, updated_at = ? WHERE id = ?;",
            (allow_delete, allow_drop, allow_update, allow_insert, allow_alter, max_row_limit, updated_at, guardrail_id)
        )
        conn.commit()
        
        cursor.execute(
            "SELECT id, allow_delete, allow_drop, allow_update, allow_insert, allow_alter, max_row_limit, updated_at "
            "FROM guardrails_config WHERE id = ?;",
            (guardrail_id,)
        )
        updated_row = cursor.fetchone()
        return GuardrailsResponse(
            id=updated_row["id"],
            allow_delete=bool(updated_row["allow_delete"]),
            allow_drop=bool(updated_row["allow_drop"]),
            allow_update=bool(updated_row["allow_update"]),
            allow_insert=bool(updated_row["allow_insert"]),
            allow_alter=bool(updated_row["allow_alter"]),
            max_row_limit=updated_row["max_row_limit"],
            updated_at=updated_row["updated_at"]
        )
    finally:
        conn.close()
