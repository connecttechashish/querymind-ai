import os
import sqlite3
import pytest
from unittest.mock import patch
from querymindai_backend.config import get_settings
from querymindai_backend.database import get_admin_db_connection
from querymindai_backend.scripts.init_admin_db import create_admin_schema
from querymindai_backend.scripts.seed_examples import seed_few_shot_examples

@pytest.fixture
def test_admin_db():
    temp_admin_db_path = "test_seed_examples_config.db"
    
    with patch.dict(os.environ, {"ADMIN_DB_PATH": temp_admin_db_path}):
        # Clear settings cache
        get_settings.cache_clear()
        
        if os.path.exists(temp_admin_db_path):
            try:
                os.remove(temp_admin_db_path)
            except PermissionError:
                pass
                
        conn = get_admin_db_connection()
        try:
            create_admin_schema(conn)
        finally:
            conn.close()
            
        yield temp_admin_db_path
        
        if os.path.exists(temp_admin_db_path):
            try:
                os.remove(temp_admin_db_path)
            except PermissionError:
                pass
        get_settings.cache_clear()

def test_seed_few_shot_examples(test_admin_db):
    with patch.dict(os.environ, {"ADMIN_DB_PATH": test_admin_db}):
        get_settings.cache_clear()
        conn = get_admin_db_connection()
        try:
            # Run the seeding logic
            seed_few_shot_examples(conn)
            
            # Verify rows are in the database
            cursor = conn.cursor()
            cursor.execute("SELECT question, sql_query, query_type, is_active FROM few_shot_examples;")
            rows = cursor.fetchall()
            assert len(rows) == 12
            
            # 1. Assert on first SELECT_SIMPLE query
            assert rows[0][0] == "Show all customers"
            assert rows[0][1] == "SELECT * FROM customers;"
            assert rows[0][2] == "SELECT_SIMPLE"
            assert rows[0][3] == 1
            
            # 2. Check category classification distributions
            cursor.execute("SELECT COUNT(*) FROM few_shot_examples WHERE query_type = 'SELECT_SIMPLE';")
            assert cursor.fetchone()[0] == 3
            
            cursor.execute("SELECT COUNT(*) FROM few_shot_examples WHERE query_type = 'SELECT_AGGREGATE';")
            assert cursor.fetchone()[0] == 4
            
            cursor.execute("SELECT COUNT(*) FROM few_shot_examples WHERE query_type = 'SELECT_JOIN';")
            assert cursor.fetchone()[0] == 3
            
            cursor.execute("SELECT COUNT(*) FROM few_shot_examples WHERE query_type = 'SELECT_TEMPORAL';")
            assert cursor.fetchone()[0] == 2
        finally:
            conn.close()
