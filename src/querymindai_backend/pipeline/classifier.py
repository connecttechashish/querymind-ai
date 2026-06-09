from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Optional

class QueryType(str, Enum):
    SELECT_SIMPLE = "SELECT_SIMPLE"
    SELECT_AGGREGATE = "SELECT_AGGREGATE"
    SELECT_JOIN = "SELECT_JOIN"
    SELECT_TEMPORAL = "SELECT_TEMPORAL"
    UNSUPPORTED = "UNSUPPORTED"

class ClassifierResult(BaseModel):
    query_type: QueryType
    tables_mentioned: List[str] = Field(default_factory=list)
    columns_mentioned: List[str] = Field(default_factory=list)
    reason: Optional[str] = None

def classify_query(question: str) -> ClassifierResult:
    """
    Classifies a natural language question using a rule-based approach.
    Extracts tables and columns mentioned and assigns a QueryType.
    """
    q_lower = question.lower()
    
    # Extract tables mentioned based on common term synonyms
    table_map = {
        "customer": "customers",
        "customers": "customers",
        "category": "categories",
        "categories": "categories",
        "product": "products",
        "products": "products",
        "order": "orders",
        "orders": "orders",
        "payment": "payments",
        "payments": "payments",
        "shipment": "shipments",
        "shipments": "shipments",
        "item": "order_items",
        "items": "order_items",
    }
    tables_mentioned = list(sorted(list(set(
        table_name for term, table_name in table_map.items() if term in q_lower
    ))))
    
    # Extract columns mentioned based on keywords
    column_map = {
        "email": "email",
        "phone": "phone",
        "price": "price",
        "stock": "stock_quantity",
        "status": "status",
        "amount": "amount",
        "revenue": "total_amount",
        "first name": "first_name",
        "last name": "last_name",
        "date": "date",
    }
    columns_mentioned = list(sorted(list(set(
        col_name for term, col_name in column_map.items() if term in q_lower
    ))))

    # Rule 1: Unsupported operations (destructives/DDL)
    unsupported_keywords = ["delete", "drop", "update", "insert", "alter", "truncate"]
    if any(keyword in q_lower for keyword in unsupported_keywords):
        return ClassifierResult(
            query_type=QueryType.UNSUPPORTED,
            tables_mentioned=tables_mentioned,
            columns_mentioned=columns_mentioned,
            reason="Query contains unsupported destructive SQL operations."
        )

    # Rule 2: Aggregations (sum, total, average, avg, count, top, revenue)
    aggregate_keywords = ["sum", "total", "average", "avg", "count", "top", "revenue"]
    if any(keyword in q_lower for keyword in aggregate_keywords):
        return ClassifierResult(
            query_type=QueryType.SELECT_AGGREGATE,
            tables_mentioned=tables_mentioned,
            columns_mentioned=columns_mentioned,
            reason="Query asks for aggregation, count, or top limit."
        )

    # Rule 3: Temporal conditions (last month, last quarter, today, yesterday, this year, by date)
    temporal_keywords = ["last month", "last quarter", "today", "yesterday", "this year", "by date"]
    if any(keyword in q_lower for keyword in temporal_keywords):
        return ClassifierResult(
            query_type=QueryType.SELECT_TEMPORAL,
            tables_mentioned=tables_mentioned,
            columns_mentioned=columns_mentioned,
            reason="Query asks for temporal analysis or date/time conditions."
        )

    # Rule 4: Joins (mentions multiple business entities like customer and order, product and order)
    entity_roots = ["customer", "order", "product", "payment", "shipment", "category"]
    entities_found = [root for root in entity_roots if root in q_lower]
    if len(entities_found) >= 2:
        return ClassifierResult(
            query_type=QueryType.SELECT_JOIN,
            tables_mentioned=tables_mentioned,
            columns_mentioned=columns_mentioned,
            reason=f"Query mentions multiple entities: {', '.join(entities_found)}."
        )

    # Rule 5: Simple SELECT
    return ClassifierResult(
        query_type=QueryType.SELECT_SIMPLE,
        tables_mentioned=tables_mentioned,
        columns_mentioned=columns_mentioned,
        reason="Query is a simple retrieval."
    )
