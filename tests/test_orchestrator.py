import os
import sqlite3
import pytest
from unittest.mock import patch
from querymindai_backend.config import get_settings
from querymindai_backend.pipeline.orchestrator import run_query_pipeline

@pytest.fixture(scope="module")
def setup_test_databases():
    temp_db_path = "test_orchestrator_business.db"
    temp_admin_db_path = "test_orchestrator_admin.db"
    
    with patch.dict(os.environ, {
        "DB_PATH": temp_db_path,
        "ADMIN_DB_PATH": temp_admin_db_path
    }):
        get_settings.cache_clear()
        
        # Clean up existing test database files
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
            cursor.execute("INSERT INTO customers (first_name, email) VALUES ('Bob', 'bob@example.com');")
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
            
            # Insert default configs
            admin_cursor.execute("INSERT INTO guardrails_config (max_row_limit, updated_at) VALUES (100, '2026-06-11T00:00:00');")
            admin_cursor.execute("INSERT INTO model_config (provider, model_name, sql_dialect, updated_at) VALUES ('mock', 'mock-sql-generator', 'sqlite', '2026-06-11T00:00:00');")
            admin_conn.commit()
        finally:
            admin_conn.close()
            
        yield temp_db_path, temp_admin_db_path
        
        # Cleanup after test suite runs
        for p in (temp_db_path, temp_admin_db_path):
            if os.path.exists(p):
                try:
                    os.remove(p)
                except PermissionError:
                    pass
        get_settings.cache_clear()

def test_unsupported_query_stops_safely(setup_test_databases):
    temp_db, temp_admin = setup_test_databases
    with patch.dict(os.environ, {
        "DB_PATH": temp_db,
        "ADMIN_DB_PATH": temp_admin
    }):
        get_settings.cache_clear()
        
        # 1. Unsupported query stops safely
        res = run_query_pipeline("Delete all orders")
        assert res["status"] == "unsupported"
        assert "unsupported" in res["error"].lower()
        # Execution and subsequent fields remain unrun / empty
        assert res["execution"] is None
        assert res["formatted_result"] is None

def test_ambiguous_revenue_query_returns_needs_clarification(setup_test_databases):
    temp_db, temp_admin = setup_test_databases
    with patch.dict(os.environ, {
        "DB_PATH": temp_db,
        "ADMIN_DB_PATH": temp_admin
    }):
        get_settings.cache_clear()
        
        # 2. Ambiguous revenue query returns needs_clarification
        res = run_query_pipeline("Top products by revenue")
        assert res["status"] == "clarification"
        assert res["needs_clarification"] is True
        assert "ambiguous" in res["error"].lower()
        assert res["execution"] is None
        assert res["formatted_result"] is None

def test_simple_safe_query_returns_final_response(setup_test_databases):
    temp_db, temp_admin = setup_test_databases
    with patch.dict(os.environ, {
        "DB_PATH": temp_db,
        "ADMIN_DB_PATH": temp_admin
    }):
        get_settings.cache_clear()
        
        # 3. Simple safe query returns final response structure
        res = run_query_pipeline("Show all customers")
        assert res["status"] == "success"
        assert res["error"] is None
        assert res["classification"] is not None
        assert res["linked_schema"] is not None
        assert res["generation"] is not None
        assert res["validation"] is not None
        assert res["execution"] is not None
        assert res["formatted_result"] is not None
        
        # Validate data in formatted result
        fmt = res["formatted_result"]
        assert len(fmt.data) == 2
        assert fmt.data[0]["first_name"] == "Alice"
        assert fmt.summary == "Returned 2 rows."

def test_pipeline_does_not_crash_on_exceptions(setup_test_databases):
    temp_db, temp_admin = setup_test_databases
    with patch.dict(os.environ, {
        "DB_PATH": temp_db,
        "ADMIN_DB_PATH": temp_admin
    }):
        get_settings.cache_clear()
        
        # 4. Pipeline does not crash and transitions to 'failed' status on invalid SQL generation
        from querymindai_backend.pipeline.generator import SQLGenerationResult
        with patch("querymindai_backend.pipeline.graph.generate_sql") as mock_gen:
            mock_gen.return_value = SQLGenerationResult(
                sql="SELECT * FROM non_existent_table;",
                explanation="Mock invalid SQL query",
                provider="mock"
            )
            res = run_query_pipeline("Show non existent items")
            assert res["status"] == "failed"
            assert "validation failed" in res["error"].lower()
