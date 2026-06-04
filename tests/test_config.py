import os
from unittest.mock import patch
from querymindai_backend.config import Settings, get_settings

def test_settings_default_values():
    settings = Settings()
    assert settings.app_name == "QueryMind AI"
    assert settings.app_version == "0.1.0"
    assert settings.app_env == "development"
    assert settings.db_path == "querymind.db"
    assert settings.admin_db_path == "admin_config.db"
    assert settings.max_row_limit == 100

def test_get_settings_cache():
    # clear get_settings lru cache to make sure we get a fresh read
    get_settings.cache_clear()
    settings1 = get_settings()
    settings2 = get_settings()
    assert settings1 is settings2

def test_settings_env_override():
    # Use patch to temporarily set environment variables
    with patch.dict(os.environ, {"APP_NAME": "Override Name", "MAX_ROW_LIMIT": "50"}):
        # We need to instantiate a new Settings class to read from env
        settings = Settings()
        assert settings.app_name == "Override Name"
        assert settings.max_row_limit == 50
