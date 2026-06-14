import os
import sqlite3
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from querymindai_backend.config import get_settings
from querymindai_backend.app import app

client = TestClient(app)

@pytest.fixture(scope="module")
def setup_api_test_databases():
    temp_db_path = "test_api_business.db"
    temp_admin_db_path = "test_api_admin.db"
    
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

def test_post_query_returns_200_for_safe_query(setup_api_test_databases):
    temp_db, temp_admin = setup_api_test_databases
    with patch.dict(os.environ, {
        "DB_PATH": temp_db,
        "ADMIN_DB_PATH": temp_admin
    }):
        get_settings.cache_clear()
        
        payload = {
            "question": "Show all customers",
            "include_sql": True,
            "include_explanation": True
        }
        response = client.post("/query", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["error"] is None
        assert data["row_count"] == 2
        assert len(data["table"]) == 2
        assert data["sql"] is not None
        assert data["explanation"] is not None

def test_delete_request_returns_safe_unsupported_response(setup_api_test_databases):
    temp_db, temp_admin = setup_api_test_databases
    with patch.dict(os.environ, {
        "DB_PATH": temp_db,
        "ADMIN_DB_PATH": temp_admin
    }):
        get_settings.cache_clear()
        
        payload = {
            "question": "Delete all customers",
            "include_sql": True,
            "include_explanation": True
        }
        response = client.post("/query", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unsupported"
        assert "unsupported" in data["error"].lower()
        assert data["sql"] is None
        assert data["explanation"] is None
        assert data["table"] is None

def test_include_sql_false_hides_sql(setup_api_test_databases):
    temp_db, temp_admin = setup_api_test_databases
    with patch.dict(os.environ, {
        "DB_PATH": temp_db,
        "ADMIN_DB_PATH": temp_admin
    }):
        get_settings.cache_clear()
        
        # Test include_sql=False hides SQL
        payload = {
            "question": "Show all customers",
            "include_sql": False,
            "include_explanation": True
        }
        response = client.post("/query", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["sql"] is None
        assert data["explanation"] is not None
        
        # Test include_explanation=False hides explanation
        payload2 = {
            "question": "Show all customers",
            "include_sql": True,
            "include_explanation": False
        }
        response2 = client.post("/query", json=payload2)
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["sql"] is not None
        assert data2["explanation"] is None
