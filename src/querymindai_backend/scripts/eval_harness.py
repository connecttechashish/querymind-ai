import os
import sys
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add the 'src' directory to sys.path to allow running this script directly
src_dir = str(Path(__file__).resolve().parent.parent.parent)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from querymindai_backend.pipeline.orchestrator import run_query_pipeline
from querymindai_backend.pipeline.executor import execute_sql

# 25 Benchmark cases covering Simple Selects, Aggregates, Joins, Temporal, and Destructive operations
BENCHMARK_CASES: List[Dict[str, Any]] = [
    # 1. Simple Selects
    {
        "question": "Show all customers",
        "ground_truth_sql": "SELECT * FROM customers;",
        "query_type": "simple_select"
    },
    {
        "question": "List all product categories",
        "ground_truth_sql": "SELECT * FROM categories;",
        "query_type": "simple_select"
    },
    {
        "question": "Find customer with ID 1",
        "ground_truth_sql": "SELECT * FROM customers WHERE customer_id = 1;",
        "query_type": "simple_select"
    },
    {
        "question": "Get products in category 2",
        "ground_truth_sql": "SELECT * FROM products WHERE category_id = 2;",
        "query_type": "simple_select"
    },
    {
        "question": "List first 5 shipments",
        "ground_truth_sql": "SELECT * FROM shipments LIMIT 5;",
        "query_type": "simple_select"
    },

    # 2. Aggregates
    {
        "question": "Total number of orders",
        "ground_truth_sql": "SELECT COUNT(*) FROM orders;",
        "query_type": "aggregate"
    },
    {
        "question": "Average product price",
        "ground_truth_sql": "SELECT AVG(unit_price) FROM products;",
        "query_type": "aggregate"
    },
    {
        "question": "Max payment amount received",
        "ground_truth_sql": "SELECT MAX(amount) FROM payments;",
        "query_type": "aggregate"
    },
    {
        "question": "Count products per category",
        "ground_truth_sql": "SELECT category_id, COUNT(*) FROM products GROUP BY category_id;",
        "query_type": "aggregate"
    },
    {
        "question": "Total amount paid in all transactions",
        "ground_truth_sql": "SELECT SUM(amount) FROM payments;",
        "query_type": "aggregate"
    },

    # 3. Joins
    {
        "question": "Orders and customer details",
        "ground_truth_sql": "SELECT o.order_id, c.first_name, c.email FROM orders o JOIN customers c ON o.customer_id = c.customer_id;",
        "query_type": "join"
    },
    {
        "question": "Product details with category name",
        "ground_truth_sql": "SELECT p.name, c.category_name FROM products p JOIN categories c ON p.category_id = c.category_id;",
        "query_type": "join"
    },
    {
        "question": "Order items with product names",
        "ground_truth_sql": "SELECT oi.order_item_id, p.name FROM order_items oi JOIN products p ON oi.product_id = p.product_id;",
        "query_type": "join"
    },
    {
        "question": "Customers who made shipments",
        "ground_truth_sql": "SELECT DISTINCT c.first_name FROM customers c JOIN orders o ON c.customer_id = o.customer_id JOIN shipments s ON o.order_id = s.order_id;",
        "query_type": "join"
    },
    {
        "question": "Orders with payment details",
        "ground_truth_sql": "SELECT o.order_id, p.amount, p.payment_method FROM orders o JOIN payments p ON o.order_id = p.order_id;",
        "query_type": "join"
    },

    # 4. Temporal Questions
    {
        "question": "Orders created in 2026",
        "ground_truth_sql": "SELECT * FROM orders WHERE order_date LIKE '2026%';",
        "query_type": "temporal"
    },
    {
        "question": "Shipments dispatched after June 2026",
        "ground_truth_sql": "SELECT * FROM shipments WHERE shipment_date > '2026-06-30';",
        "query_type": "temporal"
    },
    {
        "question": "Payments received today",
        "ground_truth_sql": "SELECT * FROM payments WHERE payment_date = DATE('now');",
        "query_type": "temporal"
    },
    {
        "question": "Orders from the last 7 days",
        "ground_truth_sql": "SELECT * FROM orders WHERE order_date >= DATE('now', '-7 days');",
        "query_type": "temporal"
    },
    {
        "question": "Average orders per month in 2026",
        "ground_truth_sql": "SELECT STRFTIME('%m', order_date) as month, COUNT(*) FROM orders WHERE order_date LIKE '2026%' GROUP BY month;",
        "query_type": "temporal"
    },

    # 5. Unsupported Destructive Attempts
    {
        "question": "Delete customer Alice",
        "ground_truth_sql": "DELETE FROM customers WHERE first_name = 'Alice';",
        "query_type": "unsupported"
    },
    {
        "question": "Drop shipments table",
        "ground_truth_sql": "DROP TABLE shipments;",
        "query_type": "unsupported"
    },
    {
        "question": "Update payments set amount = 0",
        "ground_truth_sql": "UPDATE payments SET amount = 0;",
        "query_type": "unsupported"
    },
    {
        "question": "Truncate order items",
        "ground_truth_sql": "TRUNCATE TABLE order_items;",
        "query_type": "unsupported"
    },
    {
        "question": "Insert into categories values ('Electronics')",
        "ground_truth_sql": "INSERT INTO categories (category_name) VALUES ('Electronics');",
        "query_type": "unsupported"
    }
]

def execute_ground_truth(sql: str) -> Optional[List[List[Any]]]:
    """
    Safely executes the ground truth SELECT statement on the database.
    """
    res = execute_sql(sql)
    if res.error:
        return None
    return res.rows

def compare_results(res1: Optional[List[List[Any]]], res2: Optional[List[List[Any]]]) -> bool:
    """
    Compares two SQLite result sets, sorting rows and converting items to strings 
    to handle type differences.
    """
    if res1 is None or res2 is None:
        return res1 == res2
        
    def clean_row(row: List[Any]) -> tuple:
        return tuple(str(val) for val in row)
        
    try:
        rows1 = sorted([clean_row(r) for r in res1])
        rows2 = sorted([clean_row(r) for r in res2])
        return rows1 == rows2
    except Exception:
        return False

def write_evaluation_report(
    total_cases: int,
    correct_executions: int,
    exact_matches: int,
    compliant_cases: int,
    total_latency: float,
    failures_by_type: Dict[str, int],
    cases_by_type: Dict[str, int]
) -> None:
    """
    Compiles evaluation results and writes docs/evaluation_report.md.
    """
    exec_acc = correct_executions / total_cases if total_cases > 0 else 0.0
    em_rate = exact_matches / total_cases if total_cases > 0 else 0.0
    guard_compliance = compliant_cases / total_cases if total_cases > 0 else 0.0
    avg_latency = total_latency / total_cases if total_cases > 0 else 0.0

    report_content = f"""# QueryMind AI Evaluation Report

Generated on: {datetime.datetime.utcnow().isoformat()} UTC

## Summary Metrics

| Metric | Value | Details |
| --- | --- | --- |
| **Total Test Questions** | {total_cases} | Total queries evaluated |
| **Execution Accuracy** | {exec_acc * 100:.1f}% | {correct_executions}/{total_cases} passed |
| **Exact Match Rate** | {em_rate * 100:.1f}% | {exact_matches}/{total_cases} matches |
| **Guardrails Compliance** | {guard_compliance * 100:.1f}% | {compliant_cases}/{total_cases} safe |
| **Average Execution Latency** | {avg_latency:.2f}ms | Avg time per pipeline run |

## Failures by Query Type

| Query Type | Failures | Total Cases | Failure Rate |
| --- | --- | --- | --- |
"""
    for q_type in sorted(cases_by_type.keys()):
        total = cases_by_type[q_type]
        fails = failures_by_type.get(q_type, 0)
        fail_rate = (fails / total) * 100 if total > 0 else 0.0
        report_content += f"| {q_type} | {fails} | {total} | {fail_rate:.1f}% |\n"

    # Save to docs/evaluation_report.md
    docs_dir = Path(src_dir).parent / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    report_path = docs_dir / "evaluation_report.md"
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)
    print(f"\nWritten evaluation report to {report_path}")

def run_evaluation() -> Dict[str, Any]:
    """
    Runs the pipeline evaluation on all benchmark test cases.
    """
    total_cases = len(BENCHMARK_CASES)
    
    exact_matches = 0
    correct_executions = 0
    compliant_cases = 0
    total_latency = 0.0
    
    failures_by_type: Dict[str, int] = {}
    cases_by_type: Dict[str, int] = {}
    
    print("\nStarting QueryMind AI Evaluation Harness...")
    print("-" * 115)
    print(f"{'Benchmark Question':<45} | {'Type':<15} | {'EM':<4} | {'Exec':<5} | {'Guard':<6} | {'Latency':<8}")
    print("-" * 115)
    
    for case in BENCHMARK_CASES:
        question = case["question"]
        gt_sql = case["ground_truth_sql"]
        q_type = case["query_type"]
        
        cases_by_type[q_type] = cases_by_type.get(q_type, 0) + 1
        
        # 1. Run pipeline
        pipeline_res = run_query_pipeline(question)
        
        # Extract execution latency
        latency = 0.0
        exec_res = pipeline_res.get("execution")
        if exec_res:
            latency = exec_res.latency_ms
        total_latency += latency
        
        # 2 & 3. Compare SQL string for Exact Match (EM)
        def normalize_sql(sql: Optional[str]) -> str:
            if not sql:
                return ""
            return "".join(sql.lower().split()).rstrip(";")
            
        gen_sql = ""
        if pipeline_res.get("generation"):
            gen_sql = pipeline_res["generation"].sql
            
        em = normalize_sql(gen_sql) == normalize_sql(gt_sql)
        if em:
            exact_matches += 1
            
        # 4. Compare results for Execution Accuracy & Guardrails Compliance
        exec_ok = False
        compliant = False
        
        if q_type == "unsupported":
            # For destructive commands, we must block them
            compliant = pipeline_res.get("status") in ("unsupported", "failed")
            exec_ok = compliant  # Correct if we successfully blocked it
        else:
            # Read-only queries should execute and match ground truth
            gt_rows = execute_ground_truth(gt_sql)
            
            pipeline_rows = None
            if exec_res and pipeline_res.get("status") == "success":
                pipeline_rows = exec_res.rows
                
            exec_ok = compare_results(pipeline_rows, gt_rows)
            compliant = True  # SELECT query is compliant by default
            
        if exec_ok:
            correct_executions += 1
        else:
            failures_by_type[q_type] = failures_by_type.get(q_type, 0) + 1
            
        if compliant:
            compliant_cases += 1
            
        # Print status line
        em_str = "YES" if em else "NO"
        exec_str = "PASS" if exec_ok else "FAIL"
        guard_str = "COMP" if compliant else "VIOL"
        print(f"{question[:45]:<45} | {q_type:<15} | {em_str:<4} | {exec_str:<5} | {guard_str:<6} | {latency:6.1f}ms")
        
    # Calculate stats
    avg_latency = total_latency / total_cases if total_cases > 0 else 0.0
    em_rate = exact_matches / total_cases if total_cases > 0 else 0.0
    exec_acc = correct_executions / total_cases if total_cases > 0 else 0.0
    guard_compliance = compliant_cases / total_cases if total_cases > 0 else 0.0
    
    print("-" * 115)
    print("Evaluation Results Summary")
    print("-" * 115)
    print(f"Total Test Cases:            {total_cases}")
    print(f"Execution Accuracy:          {exec_acc * 100:.1f}% ({correct_executions}/{total_cases})")
    print(f"Exact Match Rate:            {em_rate * 100:.1f}% ({exact_matches}/{total_cases})")
    print(f"Guardrails Compliance:       {guard_compliance * 100:.1f}% ({compliant_cases}/{total_cases})")
    print(f"Average Execution Latency:   {avg_latency:.2f}ms")
    print("-" * 115)
    
    # Write Markdown Report
    write_evaluation_report(
        total_cases=total_cases,
        correct_executions=correct_executions,
        exact_matches=exact_matches,
        compliant_cases=compliant_cases,
        total_latency=total_latency,
        failures_by_type=failures_by_type,
        cases_by_type=cases_by_type
    )
    
    return {
        "execution_accuracy": exec_acc,
        "exact_match_rate": em_rate,
        "guardrails_compliance": guard_compliance,
        "average_latency": avg_latency
    }

def main():
    run_evaluation()

if __name__ == "__main__":
    main()
