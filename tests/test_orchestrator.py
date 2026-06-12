import os
import sqlite3
import pytest
from unittest.mock import patch
from querymindai_backend.config import get_settings
from querymindai_backend.database import get_db_connection, get_admin_db_connection
from querymindai_backend.scripts.init_admin_db import (
    create_admin_schema,
    populate_default_guardrails,
    populate_default_model_config,
    populate_default_schema_columns
)
from querymindai_backend.scripts.seed_examples import seed_few_shot_examples
from querymindai_backend.pipeline.orchestrator import run_query_pipeline

@pytest.fixture(scope="module")
def setup_test_databases():
    temp_db_path = "test_orchestrator_business.db"
    temp_admin_db_path = "test_orchestrator_config.db"
    
    # Remove files if they exist from previous runs
    for path in (temp_db_path, temp_admin_db_path):
        if os.path.exists(path):
            try:
                os.remove(path)
            except PermissionError:
                pass

    # 1. Setup business database with standard tables
    conn = sqlite3.connect(temp_db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE customers (customer_id INTEGER PRIMARY KEY, first_name TEXT, email TEXT);")
        cursor.execute("CREATE TABLE products (product_id INTEGER PRIMARY KEY, name TEXT);")
        cursor.execute("CREATE TABLE orders (order_id INTEGER PRIMARY KEY, customer_id INTEGER, total_amount REAL);")
        cursor.execute("CREATE TABLE order_items (order_item_id INTEGER PRIMARY KEY, order_id INTEGER, product_id INTEGER, quantity INTEGER, unit_price REAL);")
        
        cursor.execute("INSERT INTO customers (first_name, email) VALUES ('Alice', 'alice@example.com');")
        cursor.execute("INSERT INTO customers (first_name, email) VALUES ('Bob', 'bob@example.com');")
        cursor.execute("INSERT INTO products (name) VALUES ('Laptop');")
        cursor.execute("INSERT INTO products (name) VALUES ('Book');")
        cursor.execute("INSERT INTO orders (customer_id, total_amount) VALUES (1, 1500.0);")
        cursor.execute("INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (1, 1, 1, 1500.0);")
        conn.commit()
    finally:
        conn.close()

    # Apply patches to environment variables
    with patch.dict(os.environ, {"DB_PATH": temp_db_path, "ADMIN_DB_PATH": temp_admin_db_path}):
        get_settings.cache_clear()
        
        # 2. Setup admin database
        admin_conn = sqlite3.connect(temp_admin_db_path)
        try:
            create_admin_schema(admin_conn)
            populate_default_guardrails(admin_conn)
            populate_default_model_config(admin_conn)
            # Read metadata from temp business database to populate schema columns
            populate_default_schema_columns(admin_conn)
            seed_few_shot_examples(admin_conn)
        finally:
            admin_conn.close()
            
        yield temp_db_path, temp_admin_db_path

    # Cleanup database files
    for path in (temp_db_path, temp_admin_db_path):
        if os.path.exists(path):
            try:
                os.remove(path)
            except PermissionError:
                pass
    get_settings.cache_clear()


def test_unsupported_query_stops_safely(setup_test_databases):
    # Requirement 1: Unsupported query stops safely
    temp_db_path, temp_admin_db_path = setup_test_databases
    with patch.dict(os.environ, {"DB_PATH": temp_db_path, "ADMIN_DB_PATH": temp_admin_db_path}):
        get_settings.cache_clear()
        
        res = run_query_pipeline("Delete all orders")
        assert res["status"] == "unsupported"
        assert res["error"] is not None
        assert "Unsupported query type" in res["error"]
        assert res["classification"] is not None
        assert res["classification"].query_type == "UNSUPPORTED"
        assert res["formatted_result"] is None


def test_ambiguous_revenue_query_returns_needs_clarification(setup_test_databases):
    # Requirement 2: Ambiguous revenue query returns needs_clarification
    temp_db_path, temp_admin_db_path = setup_test_databases
    with patch.dict(os.environ, {"DB_PATH": temp_db_path, "ADMIN_DB_PATH": temp_admin_db_path}):
        get_settings.cache_clear()
        
        res = run_query_pipeline("Show category revenue details.")
        assert res["status"] == "clarification"
        assert res["needs_clarification"] is True
        assert res["linked_schema"] is not None
        assert "orders.total_amount" in res["linked_schema"].ambiguities
        assert res["formatted_result"] is None


def test_simple_safe_query_returns_final_response_structure(setup_test_databases):
    # Requirement 3: Simple safe query returns final response structure
    temp_db_path, temp_admin_db_path = setup_test_databases
    with patch.dict(os.environ, {"DB_PATH": temp_db_path, "ADMIN_DB_PATH": temp_admin_db_path}):
        get_settings.cache_clear()
        
        res = run_query_pipeline("Show me all customers.")
        assert res["status"] == "success"
        assert res["error"] is None
        assert res["classification"] is not None
        assert res["classification"].query_type == "SELECT_SIMPLE"
        assert res["linked_schema"] is not None
        assert "customers" in res["linked_schema"].resolved_tables
        assert res["generation"] is not None
        assert res["validation"] is not None
        assert res["validation"].valid is True
        assert res["execution"] is not None
        assert res["execution"].row_count == 2
        assert res["formatted_result"] is not None
        assert len(res["formatted_result"].data) == 2
        assert res["formatted_result"].summary == "Returned 2 rows."


def test_pipeline_does_not_crash(setup_test_databases):
    # Requirement 4: Pipeline does not crash
    temp_db_path, temp_admin_db_path = setup_test_databases
    with patch.dict(os.environ, {"DB_PATH": temp_db_path, "ADMIN_DB_PATH": temp_admin_db_path}):
        get_settings.cache_clear()
        
        # Multiple queries to verify robustness
        for query in ["Show products list", "get orders count", "invalid syntax query"]:
            res = run_query_pipeline(query)
            # The queries should execute or fail gracefully without raising an unhandled exception
            assert isinstance(res, dict)
            assert "status" in res
            assert "error" in res
