import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from querymindai_backend.database import get_admin_db_connection

router = APIRouter(tags=["Admin Config"])

class ModelConfigResponse(BaseModel):
    id: int
    provider: str
    model_name: str
    temperature: float
    sql_dialect: str
    max_tokens: Optional[int] = None
    updated_at: str

class ModelConfigUpdate(BaseModel):
    provider: Optional[str] = None
    model_name: Optional[str] = None
    temperature: Optional[float] = None
    sql_dialect: Optional[str] = None
    max_tokens: Optional[int] = None

@router.get("/admin/config", response_model=ModelConfigResponse)
def get_model_config() -> ModelConfigResponse:
    """
    Retrieves the active model and generator configuration values.
    """
    conn = get_admin_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, provider, model_name, temperature, sql_dialect, max_tokens, updated_at "
            "FROM model_config ORDER BY id DESC LIMIT 1;"
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Model config not found")
        return ModelConfigResponse(
            id=row["id"],
            provider=row["provider"],
            model_name=row["model_name"],
            temperature=row["temperature"],
            sql_dialect=row["sql_dialect"],
            max_tokens=row["max_tokens"],
            updated_at=row["updated_at"]
        )
    finally:
        conn.close()

@router.patch("/admin/config", response_model=ModelConfigResponse)
def update_model_config(update: ModelConfigUpdate) -> ModelConfigResponse:
    """
    Updates the model and generator configuration parameters.
    """
    conn = get_admin_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, provider, model_name, temperature, sql_dialect, max_tokens "
            "FROM model_config ORDER BY id DESC LIMIT 1;"
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Model config not found")
            
        config_id = row["id"]
        
        provider = update.provider if update.provider is not None else row["provider"]
        model_name = update.model_name if update.model_name is not None else row["model_name"]
        temperature = update.temperature if update.temperature is not None else row["temperature"]
        sql_dialect = update.sql_dialect if update.sql_dialect is not None else row["sql_dialect"]
        max_tokens = update.max_tokens if update.max_tokens is not None else row["max_tokens"]
        
        updated_at = datetime.datetime.utcnow().isoformat()
        
        cursor.execute(
            "UPDATE model_config SET provider = ?, model_name = ?, temperature = ?, sql_dialect = ?, max_tokens = ?, updated_at = ? WHERE id = ?;",
            (provider, model_name, temperature, sql_dialect, max_tokens, updated_at, config_id)
        )
        conn.commit()
        
        cursor.execute(
            "SELECT id, provider, model_name, temperature, sql_dialect, max_tokens, updated_at "
            "FROM model_config WHERE id = ?;",
            (config_id,)
        )
        updated_row = cursor.fetchone()
        return ModelConfigResponse(
            id=updated_row["id"],
            provider=updated_row["provider"],
            model_name=updated_row["model_name"],
            temperature=updated_row["temperature"],
            sql_dialect=updated_row["sql_dialect"],
            max_tokens=updated_row["max_tokens"],
            updated_at=updated_row["updated_at"]
        )
    finally:
        conn.close()
