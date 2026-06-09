import pytest
from pydantic import ValidationError
from querymindai_backend.pipeline.classifier import QueryType, ClassifierResult, classify_query

def test_query_type_enum():
    assert QueryType.SELECT_SIMPLE == "SELECT_SIMPLE"
    assert QueryType.SELECT_AGGREGATE == "SELECT_AGGREGATE"
    assert QueryType.SELECT_JOIN == "SELECT_JOIN"
    assert QueryType.SELECT_TEMPORAL == "SELECT_TEMPORAL"
    assert QueryType.UNSUPPORTED == "UNSUPPORTED"
    
    # Check all members
    member_values = [q.value for q in QueryType]
    assert len(member_values) == 5

def test_classifier_result_validation():
    # query_type is required
    with pytest.raises(ValidationError):
        ClassifierResult()
        
    # Valid model with default empty lists
    result = ClassifierResult(query_type=QueryType.SELECT_SIMPLE)
    assert result.query_type == QueryType.SELECT_SIMPLE
    assert result.tables_mentioned == []
    assert result.columns_mentioned == []
    assert result.reason is None

def test_classify_unsupported():
    # Destructive SQL queries
    result = classify_query("Drop the customers table")
    assert result.query_type == QueryType.UNSUPPORTED
    assert "customers" in result.tables_mentioned
    
    result2 = classify_query("delete from products where id = 5")
    assert result2.query_type == QueryType.UNSUPPORTED
    assert "products" in result2.tables_mentioned

def test_classify_aggregate():
    # Aggregate keywords: sum, total, average, avg, count, top, revenue
    result = classify_query("What is the total revenue of all orders?")
    assert result.query_type == QueryType.SELECT_AGGREGATE
    assert "orders" in result.tables_mentioned
    assert "total_amount" in result.columns_mentioned
    
    result2 = classify_query("Count the number of customers")
    assert result2.query_type == QueryType.SELECT_AGGREGATE
    assert "customers" in result2.tables_mentioned

def test_classify_temporal():
    # Temporal keywords: last month, last quarter, today, yesterday, this year, by date
    result = classify_query("Show orders from last month")
    assert result.query_type == QueryType.SELECT_TEMPORAL
    assert "orders" in result.tables_mentioned
    
    result2 = classify_query("List shipments shipped today")
    assert result2.query_type == QueryType.SELECT_TEMPORAL
    assert "shipments" in result2.tables_mentioned

def test_classify_join():
    # Mentions multiple business entities (customer, order, product, payment, shipment, category)
    result = classify_query("Get all customers who placed an order")
    assert result.query_type == QueryType.SELECT_JOIN
    assert "customers" in result.tables_mentioned
    assert "orders" in result.tables_mentioned
    
    result2 = classify_query("List product and their order items")
    assert result2.query_type == QueryType.SELECT_JOIN
    assert "products" in result2.tables_mentioned
    assert "order_items" in result2.tables_mentioned

def test_classify_simple():
    # Default SELECT_SIMPLE
    result = classify_query("Show all products")
    assert result.query_type == QueryType.SELECT_SIMPLE
    assert result.tables_mentioned == ["products"]
    assert result.columns_mentioned == []
