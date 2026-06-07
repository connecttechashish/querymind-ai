import os
import sqlite3
import pytest
from unittest.mock import patch
from querymindai_backend.config import get_settings
from querymindai_backend.database import get_admin_db_connection

@pytest.fixture(scope="module")
def test_admin_db():
    # Setup temporary database paths for testing
    temp_admin_db_path = "test_admin_config.db"
    temp_business_db_path = "test_business.db"
    
    # Patch environment variables to override settings
    with patch.dict(os.environ, {
        "ADMIN_DB_PATH": temp_admin_db_path,
        "DB_PATH": temp_business_db_path
    }):
        # Clear lru cache to pick up patched settings
        get_settings.cache_clear()
        
        # Reset and recreate the schema and tables
        for path in [temp_admin_db_path, temp_business_db_path]:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except PermissionError:
                    pass
            
        # 1. Initialize a dummy business DB schema to test schema column loading
        from querymindai_backend.database import get_db_connection
        b_conn = get_db_connection()
        try:
            b_cursor = b_conn.cursor()
            b_cursor.execute("CREATE TABLE dummy_table (id INTEGER PRIMARY KEY, name TEXT, age REAL);")
            b_conn.commit()
        finally:
            b_conn.close()

        # 2. Run the admin db setup functions
        from querymindai_backend.scripts.init_admin_db import (
            create_admin_schema,
            populate_default_guardrails,
            populate_default_model_config,
            populate_default_schema_columns,
        )
        
        conn = get_admin_db_connection()
        try:
            create_admin_schema(conn)
            populate_default_guardrails(conn)
            populate_default_model_config(conn)
            populate_default_schema_columns(conn)
        finally:
            conn.close()
        
        yield temp_admin_db_path, temp_business_db_path
        
        # Teardown
        for path in [temp_admin_db_path, temp_business_db_path]:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except PermissionError:
                    pass
        get_settings.cache_clear()

def test_admin_tables_exist(test_admin_db):
    admin_path, _ = test_admin_db
    with patch.dict(os.environ, {"ADMIN_DB_PATH": admin_path}):
        get_settings.cache_clear()
        conn = get_admin_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            
            expected_tables = [
                "schema_columns",
                "few_shot_examples",
                "guardrails_config",
                "query_logs",
                "audit_logs",
                "model_config"
            ]
            for table in expected_tables:
                assert table in tables, f"Table {table} does not exist"
        finally:
            conn.close()

def test_admin_foreign_keys_enabled(test_admin_db):
    admin_path, _ = test_admin_db
    with patch.dict(os.environ, {"ADMIN_DB_PATH": admin_path}):
        get_settings.cache_clear()
        conn = get_admin_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys;")
            fk_enabled = cursor.fetchone()[0]
            assert fk_enabled == 1
        finally:
            conn.close()

def get_table_columns(conn: sqlite3.Connection, table_name: str) -> dict:
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name});")
    return {row[1]: {"type": row[2], "notnull": row[3], "dflt_value": row[4], "pk": row[5]} for row in cursor.fetchall()}

def test_schema_columns_structure(test_admin_db):
    admin_path, _ = test_admin_db
    with patch.dict(os.environ, {"ADMIN_DB_PATH": admin_path}):
        get_settings.cache_clear()
        conn = get_admin_db_connection()
        try:
            cols = get_table_columns(conn, "schema_columns")
            assert "id" in cols
            assert cols["id"]["pk"] == 1
            
            assert "table_name" in cols
            assert cols["table_name"]["type"] == "TEXT"
            assert cols["table_name"]["notnull"] == 1
            
            assert "column_name" in cols
            assert cols["column_name"]["type"] == "TEXT"
            assert cols["column_name"]["notnull"] == 1
            
            assert "data_type" in cols
            assert cols["data_type"]["type"] == "TEXT"
            assert cols["data_type"]["notnull"] == 1
            
            assert "description" in cols
            assert cols["description"]["type"] == "TEXT"
            assert cols["description"]["notnull"] == 0
            
            assert "is_sensitive" in cols
            assert cols["is_sensitive"]["type"] == "INTEGER"
            assert cols["is_sensitive"]["notnull"] == 1
            assert cols["is_sensitive"]["dflt_value"] == "0"
        finally:
            conn.close()

def test_few_shot_examples_structure(test_admin_db):
    admin_path, _ = test_admin_db
    with patch.dict(os.environ, {"ADMIN_DB_PATH": admin_path}):
        get_settings.cache_clear()
        conn = get_admin_db_connection()
        try:
            cols = get_table_columns(conn, "few_shot_examples")
            assert "id" in cols
            assert cols["id"]["pk"] == 1
            
            assert "question" in cols
            assert cols["question"]["type"] == "TEXT"
            assert cols["question"]["notnull"] == 1
            
            assert "sql_query" in cols
            assert cols["sql_query"]["type"] == "TEXT"
            assert cols["sql_query"]["notnull"] == 1
            
            assert "query_type" in cols
            assert cols["query_type"]["type"] == "TEXT"
            assert cols["query_type"]["notnull"] == 1
            
            assert "is_active" in cols
            assert cols["is_active"]["type"] == "INTEGER"
            assert cols["is_active"]["notnull"] == 1
            assert cols["is_active"]["dflt_value"] == "1"
            
            assert "created_at" in cols
            assert cols["created_at"]["type"] == "TEXT"
            assert cols["created_at"]["notnull"] == 1
        finally:
            conn.close()

def test_default_guardrails(test_admin_db):
    admin_path, _ = test_admin_db
    with patch.dict(os.environ, {"ADMIN_DB_PATH": admin_path}):
        get_settings.cache_clear()
        conn = get_admin_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT allow_delete, allow_drop, allow_update, allow_insert, allow_alter, max_row_limit FROM guardrails_config;")
            rows = cursor.fetchall()
            assert len(rows) == 1
            row = rows[0]
            assert row[0] == 0  # allow_delete
            assert row[1] == 0  # allow_drop
            assert row[2] == 0  # allow_update
            assert row[3] == 0  # allow_insert
            assert row[4] == 0  # allow_alter
            assert row[5] == 100  # max_row_limit
        finally:
            conn.close()

def test_default_model_config(test_admin_db):
    admin_path, _ = test_admin_db
    with patch.dict(os.environ, {"ADMIN_DB_PATH": admin_path}):
        get_settings.cache_clear()
        conn = get_admin_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT provider, model_name, temperature, sql_dialect FROM model_config;")
            rows = cursor.fetchall()
            assert len(rows) == 1
            row = rows[0]
            assert row[0] == "mock"
            assert row[1] == "mock-sql-generator"
            assert row[2] == 0.0
            assert row[3] == "sqlite"
        finally:
            conn.close()

def test_default_schema_columns(test_admin_db):
    admin_path, _ = test_admin_db
    with patch.dict(os.environ, {"ADMIN_DB_PATH": admin_path}):
        get_settings.cache_clear()
        conn = get_admin_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT table_name, column_name, data_type, is_sensitive FROM schema_columns;")
            rows = cursor.fetchall()
            # The dummy table has columns: id, name, age
            assert len(rows) == 3
            
            cols = {row[1]: {"table": row[0], "type": row[2], "sensitive": row[3]} for row in rows}
            
            assert "id" in cols
            assert cols["id"]["table"] == "dummy_table"
            assert cols["id"]["type"] == "INTEGER"
            assert cols["id"]["sensitive"] == 0
            
            assert "name" in cols
            assert cols["name"]["table"] == "dummy_table"
            assert cols["name"]["type"] == "TEXT"
            assert cols["name"]["sensitive"] == 0
            
            assert "age" in cols
            assert cols["age"]["table"] == "dummy_table"
            assert cols["age"]["type"] == "REAL"
            assert cols["age"]["sensitive"] == 0
        finally:
            conn.close()

def test_init_admin_db_creates_file():
    # Test that running the main function of init_admin_db creates the database file
    temp_admin_db_path = "test_main_admin_config.db"
    temp_business_db_path = "test_main_business.db"
    
    with patch.dict(os.environ, {
        "ADMIN_DB_PATH": temp_admin_db_path,
        "DB_PATH": temp_business_db_path
    }):
        get_settings.cache_clear()
        
        if os.path.exists(temp_admin_db_path):
            try:
                os.remove(temp_admin_db_path)
            except PermissionError:
                pass
            
        from querymindai_backend.scripts.init_admin_db import main
        
        # Run main script
        main()
        
        # 1. Assert admin_config.db file is created
        assert os.path.exists(temp_admin_db_path), "admin_config.db file should be created"
        
        # 2. Verify all admin tables exist
        conn = sqlite3.connect(temp_admin_db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            
            expected_tables = [
                "schema_columns",
                "few_shot_examples",
                "guardrails_config",
                "query_logs",
                "audit_logs",
                "model_config"
            ]
            for table in expected_tables:
                assert table in tables, f"Table {table} should be created by main()"
                
            # 3. Assert guardrails_config has one default row
            cursor.execute("SELECT COUNT(*) FROM guardrails_config;")
            assert cursor.fetchone()[0] == 1, "guardrails_config should have one default row"
            
            # 5. Assert max_row_limit is 100
            cursor.execute("SELECT max_row_limit FROM guardrails_config;")
            assert cursor.fetchone()[0] == 100, "max_row_limit should be 100"
            
            # 4. Assert model_config has one default row
            cursor.execute("SELECT COUNT(*) FROM model_config;")
            assert cursor.fetchone()[0] == 1, "model_config should have one default row"
            
        finally:
            conn.close()
            
        # Cleanup
        if os.path.exists(temp_admin_db_path):
            try:
                os.remove(temp_admin_db_path)
            except PermissionError:
                pass
        get_settings.cache_clear()

