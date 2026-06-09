import os
import sqlite3
import pytest
from querymindai_backend.pipeline.linker import SchemaLinkResult, read_schema

def test_schema_link_result_pydantic():
    result = SchemaLinkResult()
    assert result.resolved_tables == []
    assert result.resolved_columns == []
    assert result.ambiguities == []
    assert result.needs_clarification is False
    
    custom_result = SchemaLinkResult(
        resolved_tables=["customers"],
        resolved_columns=["customer_id", "email"],
        ambiguities=["multiple amount columns"],
        needs_clarification=True
    )
    assert custom_result.needs_clarification is True
    assert "customers" in custom_result.resolved_tables

def test_read_schema():
    # Setup temporary test database
    temp_db_path = "test_read_schema.db"
    if os.path.exists(temp_db_path):
        try:
            os.remove(temp_db_path)
        except PermissionError:
            pass
        
    conn = sqlite3.connect(temp_db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT);")
        cursor.execute("CREATE TABLE products (product_id INTEGER PRIMARY KEY, price REAL, stock INTEGER);")
        conn.commit()
        
        schema = read_schema(conn)
        assert "users" in schema
        assert "products" in schema
        assert schema["users"] == ["id", "email"]
        assert schema["products"] == ["product_id", "price", "stock"]
    finally:
        conn.close()
        if os.path.exists(temp_db_path):
            try:
                os.remove(temp_db_path)
            except PermissionError:
                pass

def test_link_schema_tables():
    from querymindai_backend.pipeline.linker import link_schema
    
    # 1. "show customers" resolves customers table
    result1 = link_schema("show customers")
    assert "customers" in result1.resolved_tables
    assert result1.needs_clarification is False
    
    # 2. "show products" resolves products table
    result2 = link_schema("show products")
    assert "products" in result2.resolved_tables
    assert result2.needs_clarification is False

def test_link_schema_revenue():
    from querymindai_backend.pipeline.linker import link_schema
    
    # 3. "revenue by product" detects revenue ambiguity
    # 4. needs_clarification is true when ambiguity exists
    result = link_schema("revenue by product")
    assert "products" in result.resolved_tables
    assert "orders" in result.resolved_tables
    assert "payments" in result.resolved_tables
    assert "orders.total_amount" in result.ambiguities
    assert "payments.amount" in result.ambiguities
    assert result.needs_clarification is True

