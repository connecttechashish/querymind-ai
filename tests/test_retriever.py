import os
import sqlite3
import pytest
from unittest.mock import patch
from querymindai_backend.config import get_settings
from querymindai_backend.database import get_admin_db_connection
from querymindai_backend.scripts.init_admin_db import create_admin_schema
from querymindai_backend.scripts.seed_examples import seed_few_shot_examples
from querymindai_backend.pipeline.retriever import retrieve_examples, tokenize

@pytest.fixture(scope="module")
def test_admin_db():
    temp_admin_db_path = "test_retriever_config.db"
    
    with patch.dict(os.environ, {"ADMIN_DB_PATH": temp_admin_db_path}):
        get_settings.cache_clear()
        
        if os.path.exists(temp_admin_db_path):
            try:
                os.remove(temp_admin_db_path)
            except PermissionError:
                pass
                
        conn = get_admin_db_connection()
        try:
            create_admin_schema(conn)
            seed_few_shot_examples(conn)
        finally:
            conn.close()
            
        yield temp_admin_db_path
        
        if os.path.exists(temp_admin_db_path):
            try:
                os.remove(temp_admin_db_path)
            except PermissionError:
                pass
        get_settings.cache_clear()

def test_tokenize():
    tokens = tokenize("Show all, customers!")
    assert tokens == {"show", "all", "customers"}

def test_retrieve_examples_top_k(test_admin_db):
    with patch.dict(os.environ, {"ADMIN_DB_PATH": test_admin_db}):
        get_settings.cache_clear()
        
        # Test retrieve default top_k=3
        results = retrieve_examples("Show me all the customers")
        assert len(results) == 3
        
        # Check fields structure
        first = results[0]
        assert first.question == "Show all customers"
        assert first.sql == "SELECT * FROM customers;"
        assert first.query_type == "SELECT_SIMPLE"
        assert first.score > 0.0

def test_retrieve_examples_custom_top_k(test_admin_db):
    with patch.dict(os.environ, {"ADMIN_DB_PATH": test_admin_db}):
        get_settings.cache_clear()
        
        results = retrieve_examples("Show me all the customers", top_k=5)
        assert len(results) == 5

def test_retrieve_examples_no_overlap(test_admin_db):
    with patch.dict(os.environ, {"ADMIN_DB_PATH": test_admin_db}):
        get_settings.cache_clear()
        
        # If words exist but don't overlap, scores should be 0.0
        results = retrieve_examples("xyzabc qwerty")
        assert len(results) == 3
        assert all(r.score == 0.0 for r in results)

def test_retrieve_examples_specific_revenue(test_admin_db):
    with patch.dict(os.environ, {"ADMIN_DB_PATH": test_admin_db}):
        get_settings.cache_clear()
        
        # Search "top products by revenue"
        results = retrieve_examples("top products by revenue")
        
        # Verify at least one example is returned
        assert len(results) >= 1
        
        # Verify returned example has question and sql
        first_match = results[0]
        assert first_match.question is not None
        assert len(first_match.question) > 0
        assert first_match.sql is not None
        assert len(first_match.sql) > 0
        
        # Assert that keyword similarity picked up related examples containing 'top' or 'products' or 'revenue'
        assert any(kw in first_match.question.lower() for kw in ["top", "products", "revenue"])

