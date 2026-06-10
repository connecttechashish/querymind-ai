import json
from pydantic import BaseModel
from typing import List, Dict, Any
from querymindai_backend.pipeline.retriever import RetrievedExample

class SQLGenerationResult(BaseModel):
    sql: str
    explanation: str
    provider: str

def build_sql_prompt(
    question: str,
    dialect: str,
    schema_context: Dict[str, List[str]],
    resolved_tables: List[str],
    resolved_columns: List[str],
    few_shot_examples: List[RetrievedExample],
    max_rows_limit: int = 100
) -> str:
    """
    Builds the LLM prompt for SQL generation based on the PRD SQL Generator specifications.
    Includes dialect, schema context, resolved elements, few-shot examples, and security guardrails.
    """
    # 1. Base instructions and safety rules
    instructions = f"""You are an expert SQL query generator for the {dialect} database dialect.
Your task is to translate the user's natural language question into a clean, optimized SQL query.

Adhere strictly to the following critical security and logic rules:
1. **SELECT-only rule**: You are only allowed to generate read-only SELECT queries.
2. **Blocked operations**: Do NOT generate any SQL commands that alter data or structure. Commands containing INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, or other modifying actions are strictly forbidden and blocked.
3. **LIMIT rule**: You must append a LIMIT constraint of at most {max_rows_limit} rows to the query to protect database performance (unless the user question explicitly requests a different limit).
"""

    # 2. Schema structure & resolved items
    schema_formatted = ""
    for table, columns in schema_context.items():
        schema_formatted += f"- Table '{table}' columns: {', '.join(columns)}\n"

    database_context = f"""
Database Schema Context:
{schema_formatted}
Resolved tables matching user query: {', '.join(resolved_tables) if resolved_tables else "None"}
Resolved columns matching user query: {', '.join(resolved_columns) if resolved_columns else "None"}
"""

    # 3. Few-shot example contexts
    examples_formatted = ""
    if few_shot_examples:
        examples_formatted = "\nUse these similar question-to-SQL pairs as context references:\n"
        for i, ex in enumerate(few_shot_examples, 1):
            examples_formatted += f"Example {i}:\n"
            examples_formatted += f"  Question: {ex.question}\n"
            examples_formatted += f"  SQL: {ex.sql}\n"
            examples_formatted += f"  Query Type: {ex.query_type}\n\n"

    # 4. User question and response template formatting
    user_query = f"""
User Question: "{question}"

Generate the SQL query to fetch the requested information. 
Output format:
Provide the generated SQL statement inside an <sql>...</sql> block, and a short 1-2 sentence explanation inside an <explanation>...</explanation> block.
"""

    return instructions + database_context + examples_formatted + user_query

def generate_sql(
    question: str,
    prompt: str,
    provider: str = "mock",
    model_name: str = "mock-sql-generator"
) -> SQLGenerationResult:
    """
    Generates SQL based on the prompt. If provider is 'mock', returns deterministic mock SQL.
    Does not require API keys for the mock provider.
    """
    if provider == "mock":
        q_lower = question.lower()
        if "top products by revenue" in q_lower or ("products" in q_lower and "revenue" in q_lower):
            sql = (
                "SELECT p.name, SUM(oi.quantity * oi.unit_price) AS revenue\n"
                "FROM products p\n"
                "JOIN order_items oi ON p.product_id = oi.product_id\n"
                "JOIN orders o ON oi.order_id = o.order_id\n"
                "GROUP BY p.product_id, p.name\n"
                "ORDER BY revenue DESC\n"
                "LIMIT 10;"
            )
            explanation = "Joins products with order_items and orders, aggregates product revenue using quantity and unit price, sorts in descending order, and limits to top 10 products."
        else:
            # Fallback mock SQL
            sql = "SELECT * FROM customers LIMIT 10;"
            explanation = "Simple SELECT query retrieving all columns from customers table with a limit of 10 rows."

        return SQLGenerationResult(
            sql=sql,
            explanation=explanation,
            provider=provider
        )

    # Real LLM provider implementation placeholder
    raise NotImplementedError(f"LLM Provider '{provider}' not implemented yet.")
