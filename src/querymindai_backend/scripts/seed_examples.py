import os
import sys
import sqlite3
from datetime import datetime
from pathlib import Path

# Add the 'src' directory to sys.path to allow running this script directly
src_dir = str(Path(__file__).resolve().parent.parent.parent)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from querymindai_backend.database import get_admin_db_connection

def seed_few_shot_examples(conn: sqlite3.Connection) -> None:
    """
    Clears the existing few-shot examples and seeds a default set of 12 examples
    covering SELECT_SIMPLE, SELECT_AGGREGATE, SELECT_JOIN, and SELECT_TEMPORAL.
    """
    cursor = conn.cursor()
    cursor.execute("DELETE FROM few_shot_examples;")
    
    now = datetime.utcnow().isoformat()
    examples = [
        # SELECT_SIMPLE
        (
            "Show all customers",
            "SELECT * FROM customers;",
            "SELECT_SIMPLE",
            1,
            now
        ),
        (
            "List all products with stock quantity less than 10",
            "SELECT name, stock_quantity FROM products WHERE stock_quantity < 10;",
            "SELECT_SIMPLE",
            1,
            now
        ),
        (
            "Get the email and phone number of customer John Doe",
            "SELECT email, phone FROM customers WHERE first_name = 'John' AND last_name = 'Doe';",
            "SELECT_SIMPLE",
            1,
            now
        ),
        # SELECT_AGGREGATE
        (
            "What is the total revenue from all orders?",
            "SELECT SUM(total_amount) AS total_revenue FROM orders;",
            "SELECT_AGGREGATE",
            1,
            now
        ),
        (
            "What is the average price of a product?",
            "SELECT AVG(price) AS average_price FROM products;",
            "SELECT_AGGREGATE",
            1,
            now
        ),
        (
            "Count the total number of orders",
            "SELECT COUNT(*) AS total_orders FROM orders;",
            "SELECT_AGGREGATE",
            1,
            now
        ),
        (
            "Get the top 5 most expensive products",
            "SELECT name, price FROM products ORDER BY price DESC LIMIT 5;",
            "SELECT_AGGREGATE",
            1,
            now
        ),
        # SELECT_JOIN
        (
            "Show orders and their customer details",
            "SELECT o.order_id, o.order_date, c.first_name, c.last_name, c.email FROM orders o JOIN customers c ON o.customer_id = c.customer_id;",
            "SELECT_JOIN",
            1,
            now
        ),
        (
            "List all products and their categories",
            "SELECT p.name AS product_name, c.name AS category_name FROM products p JOIN categories c ON p.category_id = c.category_id;",
            "SELECT_JOIN",
            1,
            now
        ),
        (
            "Find payments for order ID 10",
            "SELECT p.payment_id, p.payment_date, p.payment_method, p.amount FROM payments p JOIN orders o ON p.order_id = o.order_id WHERE o.order_id = 10;",
            "SELECT_JOIN",
            1,
            now
        ),
        # SELECT_TEMPORAL
        (
            "Show all orders placed in May 2026",
            "SELECT * FROM orders WHERE order_date >= '2026-05-01' AND order_date < '2026-06-01';",
            "SELECT_TEMPORAL",
            1,
            now
        ),
        (
            "List orders shipped in the last 30 days",
            "SELECT o.order_id, s.shipment_date FROM orders o JOIN shipments s ON o.order_id = s.order_id WHERE s.shipment_date >= date('now', '-30 days');",
            "SELECT_TEMPORAL",
            1,
            now
        )
    ]
    
    cursor.executemany(
        """
        INSERT INTO few_shot_examples (question, sql_query, query_type, is_active, created_at)
        VALUES (?, ?, ?, ?, ?);
        """,
        examples
    )
    conn.commit()
    print(f"Successfully seeded {len(examples)} few-shot examples.")

def main() -> None:
    conn = get_admin_db_connection()
    try:
        print("Seeding few-shot examples into admin database...")
        seed_few_shot_examples(conn)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
