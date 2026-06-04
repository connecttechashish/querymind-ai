from querymindai_backend.constants import (
    APP_NAME,
    APP_VERSION,
    DEFAULT_ENV,
    DEFAULT_DB_PATH,
    DEFAULT_ADMIN_DB_PATH,
    DEFAULT_MAX_ROW_LIMIT,
)

def test_constants_values():
    assert APP_NAME == "QueryMind AI"
    assert APP_VERSION == "0.1.0"
    assert DEFAULT_ENV == "development"
    assert DEFAULT_DB_PATH == "querymind.db"
    assert DEFAULT_ADMIN_DB_PATH == "admin_config.db"
    assert DEFAULT_MAX_ROW_LIMIT == 100
