from querymindai_backend.pipeline.formatter import format_result, FormatResult

def test_converts_rows_to_table_dictionaries():
    columns = ["customer_id", "first_name", "email"]
    rows = [
        [1, "Alice", "alice@example.com"],
        [2, "Bob", "bob@example.com"]
    ]
    res = format_result(columns, rows)
    assert isinstance(res, FormatResult)
    assert res.data == [
        {"customer_id": 1, "first_name": "Alice", "email": "alice@example.com"},
        {"customer_id": 2, "first_name": "Bob", "email": "bob@example.com"}
    ]
    assert res.summary == "Returned 2 rows."
    assert res.suggested_chart is None

def test_summary_includes_row_count():
    columns = ["customer_id"]
    rows = []
    res = format_result(columns, rows)
    assert res.summary == "Returned 0 rows."
    assert res.data == []
    assert res.suggested_chart is None

def test_chart_suggestion_appears_for_category_plus_numeric_result():
    # Exactly one text (category_name) and one numeric (revenue)
    columns = ["category_name", "revenue"]
    rows = [
        ["Electronics", 1500.50],
        ["Books", 320.00]
    ]
    res = format_result(columns, rows)
    assert res.suggested_chart == {
        "type": "bar",
        "x": "category_name",
        "y": "revenue"
    }

def test_no_chart_suggestion_when_criteria_not_met():
    # Multiple text columns
    columns = ["category_name", "subcategory_name", "revenue"]
    rows = [
        ["Electronics", "Phones", 1500.50],
        ["Books", "Fiction", 320.00]
    ]
    res = format_result(columns, rows)
    assert res.suggested_chart is None
    
    # Multiple numeric columns
    columns = ["category_name", "units_sold", "revenue"]
    rows = [
        ["Electronics", 10, 1500.50],
        ["Books", 5, 320.00]
    ]
    res = format_result(columns, rows)
    assert res.suggested_chart is None
    
    # No text columns (only numeric)
    columns = ["id", "revenue"]
    rows = [
        [1, 1500.50],
        [2, 320.00]
    ]
    res = format_result(columns, rows)
    assert res.suggested_chart is None
