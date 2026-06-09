import sqlite3
from pydantic import BaseModel, Field
from typing import Dict, List

class SchemaLinkResult(BaseModel):
    resolved_tables: List[str] = Field(default_factory=list)
    resolved_columns: List[str] = Field(default_factory=list)
    ambiguities: List[str] = Field(default_factory=list)
    needs_clarification: bool = False

def read_schema(conn: sqlite3.Connection) -> Dict[str, List[str]]:
    """
    Reads the schema of the provided SQLite connection using PRAGMA table_info.
    Returns a dictionary mapping table name to its list of column names.
    """
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tables = [row[0] for row in cursor.fetchall()]
    
    schema = {}
    for table in tables:
        cursor.execute(f"PRAGMA table_info({table});")
        # row[1] is column name from table_info results
        schema[table] = [row[1] for row in cursor.fetchall()]
        
    return schema

def link_schema(question: str) -> SchemaLinkResult:
    """
    Links synonyms in the natural language question to tables and columns in the schema.
    Identifies ambiguities (e.g. 'revenue') and flags if clarification is needed.
    """
    q_lower = question.lower()
    resolved_tables = set()
    resolved_columns = set()
    ambiguities = []
    needs_clarification = False

    # Synonym mappings
    table_synonyms = {
        "customer": "customers",
        "product": "products",
        "order": "orders",
        "payment": "payments",
        "shipment": "shipments",
        "category": "categories"
    }

    for term, table in table_synonyms.items():
        # Check both singular and plural forms
        if term in q_lower or table in q_lower:
            resolved_tables.add(table)

    # Column synonyms mapping to multiple fields (ambiguity)
    if "revenue" in q_lower:
        ambiguities.extend(["orders.total_amount", "payments.amount"])
        needs_clarification = True
        # Since revenue references fields in orders and payments, resolve their tables
        resolved_tables.add("orders")
        resolved_tables.add("payments")

    return SchemaLinkResult(
        resolved_tables=list(sorted(list(resolved_tables))),
        resolved_columns=list(sorted(list(resolved_columns))),
        ambiguities=list(sorted(ambiguities)),
        needs_clarification=needs_clarification
    )

