import pytest
from querymindai_backend.pipeline.classifier import QueryType, classify_query

def test_select_simple():
    result = classify_query("Show all customers")
    assert result.query_type == QueryType.SELECT_SIMPLE
    assert "customers" in result.tables_mentioned

def test_select_aggregate():
    result = classify_query("Top 10 products by revenue")
    assert result.query_type == QueryType.SELECT_AGGREGATE
    assert "products" in result.tables_mentioned
    assert "total_amount" in result.columns_mentioned

def test_select_temporal():
    result = classify_query("Orders from last quarter")
    assert result.query_type == QueryType.SELECT_TEMPORAL
    assert "orders" in result.tables_mentioned

def test_select_join():
    result = classify_query("Customers and their orders")
    assert result.query_type == QueryType.SELECT_JOIN
    assert "customers" in result.tables_mentioned
    assert "orders" in result.tables_mentioned

def test_unsupported():
    result = classify_query("Delete all orders")
    assert result.query_type == QueryType.UNSUPPORTED
    assert "orders" in result.tables_mentioned
