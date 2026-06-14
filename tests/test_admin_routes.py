import os
import sqlite3
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from querymindai_backend.config import get_settings
from querymindai_backend.app import app

client = TestClient(app)

@pytest.fixture(scope="module")
def setup_admin_test_databases():
    temp_db_path = "test_admin_routes_business.db"
    temp_admin_db_path = "test_admin_routes_admin.db"
    
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
                    
        # Setup admin DB schema and configurations
        admin_conn = sqlite3.connect(temp_admin_db_path)
        try:
            admin_cursor = admin_conn.cursor()
            admin_cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_columns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_name TEXT NOT NULL,
                column_name TEXT NOT NULL,
                data_type TEXT NOT NULL,
                description TEXT,
                is_sensitive INTEGER NOT NULL DEFAULT 0,
                UNIQUE(table_name, column_name)
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
            
            # Seed default records
            admin_cursor.execute("INSERT INTO schema_columns (table_name, column_name, data_type, is_sensitive) VALUES ('customers', 'customer_id', 'INTEGER', 0);")
            admin_cursor.execute("INSERT INTO guardrails_config (max_row_limit, updated_at) VALUES (100, '2026-06-11T00:00:00');")
            admin_cursor.execute("INSERT INTO model_config (provider, model_name, sql_dialect, updated_at) VALUES ('mock', 'mock-sql-generator', 'sqlite', '2026-06-11T00:00:00');")
            admin_conn.commit()
        finally:
            admin_conn.close()
            
        yield temp_db_path, temp_admin_db_path
        
        # Cleanup databases
        for p in (temp_db_path, temp_admin_db_path):
            if os.path.exists(p):
                try:
                    os.remove(p)
                except PermissionError:
                    pass
        get_settings.cache_clear()

def test_get_admin_schema(setup_admin_test_databases):
    temp_db, temp_admin = setup_admin_test_databases
    with patch.dict(os.environ, {
        "DB_PATH": temp_db,
        "ADMIN_DB_PATH": temp_admin
    }):
        get_settings.cache_clear()
        
        response = client.get("/admin/schema")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["table_name"] == "customers"
        assert data[0]["column_name"] == "customer_id"

def test_get_admin_examples(setup_admin_test_databases):
    temp_db, temp_admin = setup_admin_test_databases
    with patch.dict(os.environ, {
        "DB_PATH": temp_db,
        "ADMIN_DB_PATH": temp_admin
    }):
        get_settings.cache_clear()
        
        response = client.get("/admin/examples")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

def test_post_admin_examples_creates_example(setup_admin_test_databases):
    temp_db, temp_admin = setup_admin_test_databases
    with patch.dict(os.environ, {
        "DB_PATH": temp_db,
        "ADMIN_DB_PATH": temp_admin
    }):
        get_settings.cache_clear()
        
        payload = {
            "question": "How many customers do we have?",
            "sql_query": "SELECT count(*) FROM customers;",
            "query_type": "SELECT_AGGREGATE",
            "is_active": True
        }
        response = client.post("/admin/examples", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] is not None
        assert data["question"] == payload["question"]
        assert data["sql_query"] == payload["sql_query"]

def test_get_admin_guardrails(setup_admin_test_databases):
    temp_db, temp_admin = setup_admin_test_databases
    with patch.dict(os.environ, {
        "DB_PATH": temp_db,
        "ADMIN_DB_PATH": temp_admin
    }):
        get_settings.cache_clear()
        
        response = client.get("/admin/guardrails")
        assert response.status_code == 200
        data = response.json()
        assert data["max_row_limit"] == 100

def test_patch_admin_guardrails_updates_limit(setup_admin_test_databases):
    temp_db, temp_admin = setup_admin_test_databases
    with patch.dict(os.environ, {
        "DB_PATH": temp_db,
        "ADMIN_DB_PATH": temp_admin
    }):
        get_settings.cache_clear()
        
        payload = {"max_row_limit": 150}
        response = client.patch("/admin/guardrails", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["max_row_limit"] == 150

def test_get_admin_config(setup_admin_test_databases):
    temp_db, temp_admin = setup_admin_test_databases
    with patch.dict(os.environ, {
        "DB_PATH": temp_db,
        "ADMIN_DB_PATH": temp_admin
    }):
        get_settings.cache_clear()
        
        response = client.get("/admin/config")
        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "mock"
