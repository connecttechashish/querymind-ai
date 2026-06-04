from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from querymindai_backend.constants import (
    APP_NAME,
    APP_VERSION,
    DEFAULT_ENV,
    DEFAULT_DB_PATH,
    DEFAULT_ADMIN_DB_PATH,
    DEFAULT_MAX_ROW_LIMIT,
)

class Settings(BaseSettings):
    app_name: str = APP_NAME
    app_version: str = APP_VERSION
    app_env: str = DEFAULT_ENV
    db_path: str = DEFAULT_DB_PATH
    admin_db_path: str = DEFAULT_ADMIN_DB_PATH
    max_row_limit: int = DEFAULT_MAX_ROW_LIMIT

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

@lru_cache
def get_settings() -> Settings:
    return Settings()
