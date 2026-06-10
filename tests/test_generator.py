import pytest
from querymindai_backend.pipeline.generator import build_sql_prompt, SQLGenerationResult
from querymindai_backend.pipeline.retriever import RetrievedExample

def test_sql_generation_result_model():
    result = SQLGenerationResult(
        sql="SELECT * FROM customers LIMIT 10;",
        explanation="Fetches 10 customers.",
        provider="mock"
    )
    assert result.sql == "SELECT * FROM customers LIMIT 10;"
    assert result.explanation == "Fetches 10 customers."
    assert result.provider == "mock"

def test_generate_sql_mock():
    from querymindai_backend.pipeline.generator import generate_sql
    
    # 1. Test fallback mock SQL
    result = generate_sql("list customers", "dummy_prompt", provider="mock")
    assert result.provider == "mock"
    assert result.sql == "SELECT * FROM customers LIMIT 10;"
    assert "customers" in result.explanation
    
    # 2. Test "top products by revenue" mock query
    result_revenue = generate_sql("top products by revenue", "dummy_prompt", provider="mock")
    assert result_revenue.provider == "mock"
    
    sql = result_revenue.sql.lower()
    # Verify it joins products, order_items, orders
    assert "select" in sql
    assert "products" in sql
    assert "order_items" in sql
    assert "orders" in sql
    assert "join" in sql
    assert "group by" in sql
    assert "order by" in sql
    
    assert "revenue" in result_revenue.explanation.lower()

def test_generator_prompt_and_mock_requirements():
    from querymindai_backend.pipeline.generator import build_sql_prompt, generate_sql
    
    # Create simple dummy parameters
    question = "top products by revenue"
    schema_context = {"products": ["product_id", "name", "price"]}
    
    # Build prompt
    prompt = build_sql_prompt(
        question=question,
        dialect="sqlite",
        schema_context=schema_context,
        resolved_tables=["products"],
        resolved_columns=["products.name"],
        few_shot_examples=[],
        max_rows_limit=100
    )
    
    # 1. build_sql_prompt includes SELECT-only
    assert "select-only" in prompt.lower()
    
    # 2. build_sql_prompt includes LIMIT rule
    assert "limit" in prompt.lower()
    
    # Generate mock SQL
    result = generate_sql(question, prompt, provider="mock")
    sql_upper = result.sql.upper()
    
    # 3. mock generate_sql returns SELECT
    assert sql_upper.startswith("SELECT")
    
    # 4. mock generate_sql does not return destructive SQL
    blocked_commands = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE"]
    for cmd in blocked_commands:
        assert cmd not in sql_upper

def test_build_sql_prompt_contains_all_rules():
    question = "Who are the top products?"
    dialect = "sqlite"
    schema_context = {
        "products": ["product_id", "name", "price"],
        "orders": ["order_id", "total_amount"]
    }
    resolved_tables = ["products"]
    resolved_columns = ["products.name", "products.price"]
    few_shot_examples = [
        RetrievedExample(
            question="List products",
            sql="SELECT * FROM products;",
            query_type="SELECT_SIMPLE",
            score=0.8
        )
    ]
    max_limit = 50
    
    prompt = build_sql_prompt(
        question=question,
        dialect=dialect,
        schema_context=schema_context,
        resolved_tables=resolved_tables,
        resolved_columns=resolved_columns,
        few_shot_examples=few_shot_examples,
        max_rows_limit=max_limit
    )
    
    # Assertions for required contents:
    # 1. User question
    assert "Who are the top products?" in prompt
    
    # 2. SQL dialect
    assert "sqlite" in prompt
    
    # 3. Schema context
    assert "products" in prompt
    assert "product_id" in prompt
    
    # 4. Resolved tables
    assert "products" in prompt
    
    # 5. Resolved columns
    assert "products.name" in prompt
    assert "products.price" in prompt
    
    # 6. Few-shot examples
    assert "List products" in prompt
    assert "SELECT * FROM products;" in prompt
    assert "SELECT_SIMPLE" in prompt
    
    # 7. SELECT-only rule
    assert "SELECT-only rule" in prompt
    
    # 8. Blocked operations: INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE
    assert "INSERT" in prompt
    assert "UPDATE" in prompt
    assert "DELETE" in prompt
    assert "DROP" in prompt
    assert "ALTER" in prompt
    assert "TRUNCATE" in prompt
    
    # 9. LIMIT rule and limit value
    assert "LIMIT" in prompt
    assert str(max_limit) in prompt
