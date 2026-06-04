import os
import sqlite3
import pytest
from unittest.mock import patch
from querymindai_backend.config import get_settings
from querymindai_backend.database import get_db_connection
from querymindai_backend.scripts.seed_db import (
    create_schema,
    seed_categories,
    seed_customers,
    seed_products,
    prepare_orders_data,
    seed_orders,
    seed_order_items,
    seed_payments,
    seed_shipments,
)

@pytest.fixture(scope="module")
def test_db():
    # Setup temporary database path for testing
    temp_db_path = "test_querymind.db"
    
    # Patch environment variable to override settings
    with patch.dict(os.environ, {"DB_PATH": temp_db_path}):
        # Clear lru cache to pick up patched settings
        get_settings.cache_clear()
        
        # Reset and seed the test db
        if os.path.exists(temp_db_path):
            try:
                os.remove(temp_db_path)
            except PermissionError:
                pass
            
        conn = get_db_connection()
        try:
            create_schema(conn)
            
            # Run seeding
            cat_ids = seed_categories(conn)
            cust_ids = seed_customers(conn)
            prods = seed_products(conn, cat_ids)
            orders_info = prepare_orders_data(cust_ids, prods, count=300)
            
            seed_orders(conn, orders_info)
            seed_order_items(conn, orders_info)
            seed_payments(conn, orders_info)
            seed_shipments(conn, orders_info)
        finally:
            conn.close()
        
        yield temp_db_path
        
        # Teardown
        if os.path.exists(temp_db_path):
            try:
                os.remove(temp_db_path)
            except PermissionError:
                pass
        get_settings.cache_clear()

def test_tables_exist(test_db):
    with patch.dict(os.environ, {"DB_PATH": test_db}):
        get_settings.cache_clear()
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            
            expected_tables = ["customers", "categories", "products", "orders", "order_items", "payments", "shipments"]
            for table in expected_tables:
                assert table in tables
        finally:
            conn.close()

def test_tables_have_rows(test_db):
    with patch.dict(os.environ, {"DB_PATH": test_db}):
        get_settings.cache_clear()
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            tables = ["customers", "categories", "products", "orders", "order_items", "payments", "shipments"]
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table};")
                count = cursor.fetchone()[0]
                assert count > 0, f"Table {table} should have seeded rows"
                
                # Check specific counts
                if table == "customers":
                    assert count == 100
                elif table == "products":
                    assert count == 30
                elif table == "orders":
                    assert count == 300
        finally:
            conn.close()

def test_foreign_keys_enabled(test_db):
    with patch.dict(os.environ, {"DB_PATH": test_db}):
        get_settings.cache_clear()
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys;")
            fk_enabled = cursor.fetchone()[0]
            assert fk_enabled == 1
            
            # Test foreign key violation raises IntegrityError
            with pytest.raises(sqlite3.IntegrityError):
                cursor.execute(
                    "INSERT INTO products (name, description, price, stock_quantity, category_id) VALUES (?, ?, ?, ?, ?);",
                    ("Bad Product", "No Category", 9.99, 10, 99999)
                )
                conn.commit()
        finally:
            conn.close()

def test_ambiguity_fields_exist(test_db):
    with patch.dict(os.environ, {"DB_PATH": test_db}):
        get_settings.cache_clear()
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            
            # Verify orders.total_amount exists and has data
            cursor.execute("SELECT total_amount FROM orders LIMIT 1;")
            row = cursor.fetchone()
            assert row is not None
            assert isinstance(row[0], (int, float))
            
            # Verify payments.amount exists and has data
            cursor.execute("SELECT amount FROM payments LIMIT 1;")
            row = cursor.fetchone()
            assert row is not None
            assert isinstance(row[0], (int, float))
        finally:
            conn.close()
