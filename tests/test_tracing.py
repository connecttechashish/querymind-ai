import os
import sqlite3
import pytest
from unittest.mock import patch
from querymindai_backend.config import get_settings
from querymindai_backend.utils.tracing import is_tracing_enabled, trace_step
from querymindai_backend.pipeline.orchestrator import run_query_pipeline

@pytest.fixture(scope="module")
def setup_tracing_test_databases():
    temp_db_path = "test_tracing_business.db"
    temp_admin_db_path = "test_tracing_admin.db"
    
    with patch.dict(os.environ, {
        "DB_PATH": temp_db_path,
        "ADMIN_DB_PATH": temp_admin_db_path
    }):
        get_settings.cache_clear()
        
        # Clean up database files from previous test runs
        for p in (temp_db_path, temp_admin_db_path):
            if os.path.exists(p):
                try:
                    os.remove(p)
                except PermissionError:
                    pass
                    
        # Initialize business DB
        conn = sqlite3.connect(temp_db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE customers (customer_id INTEGER PRIMARY KEY, first_name TEXT, email TEXT);")
            cursor.execute("INSERT INTO customers (first_name, email) VALUES ('Alice', 'alice@example.com');")
            conn.commit()
        finally:
            conn.close()
            
        # Initialize admin DB
        admin_conn = sqlite3.connect(temp_admin_db_path)
        try:
            admin_cursor = admin_conn.cursor()
            admin_cursor.execute("""
            CREATE TABLE IF NOT EXISTS model_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT NOT NULL DEFAULT 'mock',
                model_name TEXT NOT NULL DEFAULT 'mock-sql-generator',
                temperature REAL NOT NULL DEFAULT 0.0,
                sql_dialect TEXT NOT NULL DEFAULT 'sqlite',
                max_tokens INTEGER,
                updated_at TEXT NOT NULL
            );
            """)
            admin_cursor.execute("""
            CREATE TABLE IF NOT EXISTS guardrails_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                allow_delete INTEGER NOT NULL DEFAULT 0,
                allow_drop INTEGER NOT NULL DEFAULT 0,
                allow_update INTEGER NOT NULL DEFAULT 0,
                allow_insert INTEGER NOT NULL DEFAULT 0,
                allow_alter INTEGER NOT NULL DEFAULT 0,
                max_row_limit INTEGER NOT NULL DEFAULT 100,
                updated_at TEXT NOT NULL
            );
            """)
            admin_cursor.execute("""
            CREATE TABLE IF NOT EXISTS few_shot_examples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                sql_query TEXT NOT NULL,
                query_type TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );
            """)
            
            # Seed default configurations
            admin_cursor.execute("INSERT INTO guardrails_config (max_row_limit, updated_at) VALUES (100, '2026-06-11T00:00:00');")
            admin_cursor.execute("INSERT INTO model_config (provider, model_name, sql_dialect, updated_at) VALUES ('mock', 'mock-sql-generator', 'sqlite', '2026-06-11T00:00:00');")
            admin_conn.commit()
        finally:
            admin_conn.close()
            
        yield temp_db_path, temp_admin_db_path
        
        # Cleanup
        for p in (temp_db_path, temp_admin_db_path):
            if os.path.exists(p):
                try:
                    os.remove(p)
                except PermissionError:
                    pass
        get_settings.cache_clear()

def test_is_tracing_enabled_returns_false_when_no_api_key():
    # 1. is_tracing_enabled returns false when no API key is present
    with patch.dict(os.environ, {"LANGCHAIN_TRACING_V2": "true", "LANGCHAIN_API_KEY": ""}):
        assert is_tracing_enabled() is False

    with patch.dict(os.environ, {"LANGCHAIN_TRACING_V2": "", "LANGCHAIN_API_KEY": "some-key"}):
        assert is_tracing_enabled() is False

    with patch.dict(os.environ, {"LANGCHAIN_TRACING_V2": "false", "LANGCHAIN_API_KEY": "some-key"}):
        assert is_tracing_enabled() is False

def test_trace_step_does_not_raise_error_when_disabled():
    # 2. trace_step does not raise error when tracing is disabled
    with patch.dict(os.environ, {"LANGCHAIN_TRACING_V2": "false", "LANGCHAIN_API_KEY": ""}):
        try:
            trace_step("test_step", {"input": "test"})
        except Exception as e:
            pytest.fail(f"trace_step raised an exception when disabled: {e}")

def test_orchestrator_works_without_langsmith(setup_tracing_test_databases):
    temp_db, temp_admin = setup_tracing_test_databases
    # Disable tracing environment variables
    with patch.dict(os.environ, {
        "DB_PATH": temp_db,
        "ADMIN_DB_PATH": temp_admin,
        "LANGCHAIN_TRACING_V2": "false",
        "LANGCHAIN_API_KEY": ""
    }):
        get_settings.cache_clear()
        
        # 3. Orchestrator still works without LangSmith (returns results normally)
        res = run_query_pipeline("Show all customers")
        assert res["status"] == "success"
        assert res["error"] is None
        assert res["formatted_result"].summary == "Returned 1 rows."
