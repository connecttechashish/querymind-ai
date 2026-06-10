import os
import sqlite3
import pytest
from unittest.mock import patch
from querymindai_backend.config import get_settings
from querymindai_backend.pipeline.validator import validate_sql, SQLValidationResult

@pytest.fixture(scope="module")
def test_business_db():
    temp_db_path = "test_validator_business.db"
    
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
            cursor.execute("CREATE TABLE customers (id INTEGER, name TEXT);")
            cursor.execute("CREATE TABLE products (id INTEGER, title TEXT);")
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

def test_sql_validation_result_pydantic():
    res = SQLValidationResult(valid=True, sanitized_sql="SELECT * FROM customers LIMIT 100;", errors=[])
    assert res.valid is True
    assert res.sanitized_sql == "SELECT * FROM customers LIMIT 100;"
    assert res.errors == []

def test_validate_sql_valid_select_appends_limit(test_business_db):
    with patch.dict(os.environ, {"DB_PATH": test_business_db}):
        get_settings.cache_clear()
        res = validate_sql("SELECT * FROM customers")
        assert res.valid is True
        assert "LIMIT 100" in res.sanitized_sql
        assert res.sanitized_sql.endswith(";")
        assert len(res.errors) == 0

def test_validate_sql_valid_select_retains_limit(test_business_db):
    with patch.dict(os.environ, {"DB_PATH": test_business_db}):
        get_settings.cache_clear()
        res = validate_sql("SELECT * FROM customers LIMIT 15;")
        assert res.valid is True
        assert "LIMIT 15" in res.sanitized_sql
        assert "LIMIT 100" not in res.sanitized_sql
        assert res.sanitized_sql.endswith(";")

def test_validate_sql_invalid_syntax():
    res = validate_sql("SELECT * FROM;")
    assert res.valid is False
    assert len(res.errors) > 0
    assert "syntax error" in res.errors[0].lower()

def test_validate_sql_blocks_modifying_operations():
    # 1. DELETE
    assert validate_sql("DELETE FROM customers;").valid is False
    # 2. DROP
    assert validate_sql("DROP TABLE customers;").valid is False
    # 3. UPDATE
    assert validate_sql("UPDATE customers SET first_name = 'Bob';").valid is False
    # 4. INSERT
    assert validate_sql("INSERT INTO customers (first_name) VALUES ('Bob');").valid is False
    # 5. ALTER
    assert validate_sql("ALTER TABLE customers ADD COLUMN temp TEXT;").valid is False
    # 6. TRUNCATE
    assert validate_sql("TRUNCATE TABLE customers;").valid is False

def test_validate_sql_tables_exist(test_business_db):
    with patch.dict(os.environ, {"DB_PATH": test_business_db}):
        get_settings.cache_clear()
        
        # Valid table in the schema
        res_valid = validate_sql("SELECT * FROM customers;")
        assert res_valid.valid is True
        assert len(res_valid.errors) == 0
        
        # Table not in the schema should be rejected
        res_invalid = validate_sql("SELECT * FROM non_existent_table;")
        assert res_invalid.valid is False
        assert len(res_invalid.errors) > 0
        assert "do not exist" in res_invalid.errors[0]

def test_validator_prd_requirements(test_business_db):
    with patch.dict(os.environ, {"DB_PATH": test_business_db}):
        get_settings.cache_clear()
        
        # 1. SELECT is valid.
        res = validate_sql("SELECT * FROM customers;")
        assert res.valid is True
        
        # 2. DELETE is blocked.
        assert validate_sql("DELETE FROM customers;").valid is False
        
        # 3. DROP is blocked.
        assert validate_sql("DROP TABLE customers;").valid is False
        
        # 4. UPDATE is blocked.
        assert validate_sql("UPDATE customers SET name = 'Alice';").valid is False
        
        # 5. Missing LIMIT is added.
        res_no_limit = validate_sql("SELECT * FROM customers;")
        assert "LIMIT 100" in res_no_limit.sanitized_sql
        
        # 6. Invalid table is blocked.
        assert validate_sql("SELECT * FROM non_existent_table;").valid is False

