import os
import sqlite3
import pytest
from unittest.mock import patch
from querymindai_backend.config import get_settings
from querymindai_backend.pipeline.executor import execute_sql, SQLExecutionResult

@pytest.fixture(scope="module")
def test_db():
    temp_db_path = "test_executor_business.db"
    
    with patch.dict(os.environ, {"DB_PATH": temp_db_path}):
        get_settings.cache_clear()
        
        if os.path.exists(temp_db_path):
            try:
                os.remove(temp_db_path)
            except PermissionError:
                pass
                
        conn = sqlite3.connect(temp_db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE customers (customer_id INTEGER PRIMARY KEY, first_name TEXT, email TEXT);")
            cursor.execute("INSERT INTO customers (first_name, email) VALUES ('Alice', 'alice@example.com');")
            cursor.execute("INSERT INTO customers (first_name, email) VALUES ('Bob', 'bob@example.com');")
            conn.commit()
        finally:
            conn.close()
            
        yield temp_db_path
        
        if os.path.exists(temp_db_path):
            try:
                os.remove(temp_db_path)
            except PermissionError:
                pass
        get_settings.cache_clear()

def test_sql_execution_result_pydantic():
    res = SQLExecutionResult(
        columns=["customer_id", "first_name"],
        rows=[[1, "Alice"], [2, "Bob"]],
        row_count=2,
        latency_ms=1.5,
        error=None
    )
    assert res.columns == ["customer_id", "first_name"]
    assert res.row_count == 2
    assert res.error is None

def test_execute_select_from_customers(test_db):
    # Requirement 1: Execute SELECT from customers
    with patch.dict(os.environ, {"DB_PATH": test_db}):
        get_settings.cache_clear()
        
        res = execute_sql("SELECT first_name, email FROM customers ORDER BY first_name ASC;")
        assert res.error is None
        
        # Requirement 2: Returns columns and rows
        assert res.columns == ["first_name", "email"]
        assert res.rows == [["Alice", "alice@example.com"], ["Bob", "bob@example.com"]]
        
        # Requirement 3: row_count is correct
        assert res.row_count == 2
        assert res.latency_ms >= 0.0

def test_write_sql_rejected_or_fails_safely(test_db):
    # Requirement 4: Write SQL is rejected or fails safely
    with patch.dict(os.environ, {"DB_PATH": test_db}):
        get_settings.cache_clear()
        
        # Test write operation INSERT is rejected/fails safely
        res_insert = execute_sql("INSERT INTO customers (first_name, email) VALUES ('Charlie', 'charlie@example.com');")
        assert res_insert.error is not None
        assert res_insert.row_count == 0
        
        # Test write operation UPDATE is rejected/fails safely
        res_update = execute_sql("UPDATE customers SET email = 'hacked@example.com' WHERE first_name = 'Alice';")
        assert res_update.error is not None
        assert res_update.row_count == 0
        
        # Test raw SQL error is caught and fails safely
        res_err = execute_sql("SELECT * FROM non_existent_table;")
        assert res_err.error is not None
        assert res_err.row_count == 0
