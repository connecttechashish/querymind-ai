import os
import random
import sqlite3
from datetime import datetime, timedelta
from faker import Faker
from querymindai_backend.config import get_settings
from querymindai_backend.database import get_db_connection

# Initialize Faker
fake = Faker()
# Set seed for reproducibility
Faker.seed(42)
random.seed(42)

def reset_database() -> None:
    """
    Resets the database by removing the database file or dropping all tables.
    """
    settings = get_settings()
    db_path = settings.db_path
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except PermissionError:
            # Fallback: Drop tables if database file is locked
            conn = get_db_connection()
            try:
                conn.execute("PRAGMA foreign_keys = OFF;")
                tables = ["shipments", "payments", "order_items", "orders", "products", "categories", "customers"]
                for table in tables:
                    conn.execute(f"DROP TABLE IF EXISTS {table};")
                conn.commit()
            finally:
                conn.close()

def create_schema(conn: sqlite3.Connection) -> None:
    """
    Creates the business database schema.
    """
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    # 1. Customers
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        phone TEXT,
        created_at TEXT NOT NULL
    );
    """)
    
    # 2. Categories
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        category_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        description TEXT
    );
    """)
    
    # 3. Products
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        product_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        price REAL NOT NULL,
        stock_quantity INTEGER NOT NULL,
        category_id INTEGER,
        FOREIGN KEY (category_id) REFERENCES categories (category_id)
    );
    """)
    
    # 4. Orders
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        order_id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        order_date TEXT NOT NULL,
        status TEXT NOT NULL,
        total_amount REAL NOT NULL,
        FOREIGN KEY (customer_id) REFERENCES customers (customer_id)
    );
    """)
    
    # 5. Order Items
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS order_items (
        order_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER,
        product_id INTEGER,
        quantity INTEGER NOT NULL,
        unit_price REAL NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders (order_id) ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES products (product_id)
    );
    """)
    
    # 6. Payments
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER,
        payment_date TEXT NOT NULL,
        payment_method TEXT NOT NULL,
        amount REAL NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders (order_id)
    );
    """)
    
    # 7. Shipments
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS shipments (
        shipment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER,
        shipment_date TEXT NOT NULL,
        tracking_number TEXT NOT NULL UNIQUE,
        carrier TEXT NOT NULL,
        status TEXT NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders (order_id)
    );
    """)
    
    conn.commit()

def seed_categories(conn: sqlite3.Connection) -> list:
    """
    Seeds categories and returns a list of category IDs.
    """
    cursor = conn.cursor()
    categories_data = [
        ("Electronics", "Gadgets, devices, and accessories"),
        ("Clothing", "Apparel, footwear, and accessories"),
        ("Home & Kitchen", "Kitchenware, furniture, and home decor"),
        ("Books", "Fiction, non-fiction, and textbooks"),
        ("Sports & Outdoors", "Sporting goods and outdoor gear"),
        ("Beauty", "Cosmetics, skincare, and personal care"),
    ]
    cursor.executemany(
        "INSERT INTO categories (name, description) VALUES (?, ?);",
        categories_data
    )
    conn.commit()
    cursor.execute("SELECT category_id FROM categories;")
    return [row[0] for row in cursor.fetchall()]

def seed_customers(conn: sqlite3.Connection) -> list:
    """
    Seeds 100 customer records and returns a list of customer IDs.
    """
    cursor = conn.cursor()
    customers_data = []
    emails = set()
    while len(customers_data) < 100:
        first_name = fake.first_name()
        last_name = fake.last_name()
        email = f"{first_name.lower()}.{last_name.lower()}{random.randint(100, 999)}@example.com"
        if email not in emails:
            emails.add(email)
            phone = fake.phone_number()
            created_at = fake.date_time_between(start_date="-1y", end_date="now").isoformat()
            customers_data.append((first_name, last_name, email, phone, created_at))
            
    cursor.executemany(
        "INSERT INTO customers (first_name, last_name, email, phone, created_at) VALUES (?, ?, ?, ?, ?);",
        customers_data
    )
    conn.commit()
    cursor.execute("SELECT customer_id FROM customers;")
    return [row[0] for row in cursor.fetchall()]

def seed_products(conn: sqlite3.Connection, category_ids: list) -> list:
    """
    Seeds 30 product records and returns a list of product info dictionaries.
    """
    cursor = conn.cursor()
    products_data = []
    product_names = [
        ("Smartphone", "Latest model with high-res camera"),
        ("Laptop", "Lightweight, powerful developer laptop"),
        ("Wireless Headphones", "Active noise cancelling bluetooth headphones"),
        ("Smart Watch", "Fitness tracker with heart rate monitor"),
        ("Running Shoes", "Comfortable and durable athletic shoes"),
        ("Leather Jacket", "Classic black stylish leather jacket"),
        ("Coffee Maker", "Drip coffee machine with programmable timer"),
        ("Air Fryer", "Digital controls for oil-free cooking"),
        ("Blender", "High speed countertop blender for smoothies"),
        ("T-Shirt", "100% cotton crewneck basic tee"),
        ("Jeans", "Slim fit stretch denim blue jeans"),
        ("Backpack", "Water-resistant travel backpack with laptop sleeve"),
        ("Desk Lamp", "LED reading light with adjustable brightness"),
        ("Office Chair", "Ergonomic mesh back task chair"),
        ("Keyboard", "Mechanical gaming keyboard with RGB backlights"),
        ("Mouse", "Ergonomic wireless optical mouse"),
        ("Monitor", "27-inch 4K UHD widescreen monitor"),
        ("Vacuum Cleaner", "Cordless stick vacuum for pet hair"),
        ("Water Bottle", "Insulated stainless steel sports flask"),
        ("Yoga Mat", "Non-slip exercise mat with carrying strap"),
        ("Dumbbell Set", "Adjustable hand weights for home workouts"),
        ("Skincare Serum", "Hydrating hyaluronic acid face serum"),
        ("Shampoo", "Sulfate-free nourishing hair cleanser"),
        ("Novel", "Best-selling mystery paperback book"),
        ("Cookbook", "Easy family recipes for healthy meals"),
        ("Board Game", "Strategy tabletop game for family game nights"),
        ("Sleeping Bag", "Warm lightweight camping sleeping bag"),
        ("Tent", "Waterproof 4-person family dome tent"),
        ("Power Bank", "Portable charger high capacity battery pack"),
        ("Bluetooth Speaker", "Waterproof outdoor wireless speaker"),
    ]
    for i in range(30):
        if i < len(product_names):
            name, desc = product_names[i]
        else:
            name = f"{fake.word().capitalize()} {fake.word().capitalize()}"
            desc = fake.sentence()
        price = round(random.uniform(5.0, 1200.0), 2)
        stock = random.randint(10, 500)
        cat_id = random.choice(category_ids)
        products_data.append((name, desc, price, stock, cat_id))
        
    cursor.executemany(
        "INSERT INTO products (name, description, price, stock_quantity, category_id) VALUES (?, ?, ?, ?, ?);",
        products_data
    )
    conn.commit()
    cursor.execute("SELECT product_id, price FROM products;")
    return [dict(row) for row in cursor.fetchall()]

def prepare_orders_data(customer_ids: list, products: list, count: int = 300) -> list:
    """
    Prepares order and line item data in memory to guarantee relational integrity.
    """
    orders_info = []
    for order_id in range(1, count + 1):
        cust_id = random.choice(customer_ids)
        order_date_dt = fake.date_time_between(start_date="-6m", end_date="now")
        order_date = order_date_dt.isoformat()
        status = random.choice(["Completed", "Shipped", "Pending", "Cancelled"])
        
        # Items selection
        num_items = random.randint(1, 4)
        items_selected = random.sample(products, num_items)
        
        items = []
        total_amount = 0.0
        for prod in items_selected:
            qty = random.randint(1, 3)
            unit_price = prod["price"]
            total_amount += qty * unit_price
            items.append({
                "product_id": prod["product_id"],
                "quantity": qty,
                "unit_price": unit_price
            })
            
        total_amount = round(total_amount, 2)
        orders_info.append({
            "order_id": order_id,
            "customer_id": cust_id,
            "order_date": order_date,
            "order_date_dt": order_date_dt,
            "status": status,
            "total_amount": total_amount,
            "items": items
        })
    return orders_info

def seed_orders(conn: sqlite3.Connection, orders_info: list) -> None:
    """
    Seeds orders data.
    """
    cursor = conn.cursor()
    orders_data = [(o["order_id"], o["customer_id"], o["order_date"], o["status"], o["total_amount"]) for o in orders_info]
    cursor.executemany(
        "INSERT INTO orders (order_id, customer_id, order_date, status, total_amount) VALUES (?, ?, ?, ?, ?);",
        orders_data
    )
    conn.commit()

def seed_order_items(conn: sqlite3.Connection, orders_info: list) -> None:
    """
    Seeds order items data.
    """
    cursor = conn.cursor()
    items_data = []
    for o in orders_info:
        order_id = o["order_id"]
        for item in o["items"]:
            items_data.append((order_id, item["product_id"], item["quantity"], item["unit_price"]))
    cursor.executemany(
        "INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (?, ?, ?, ?);",
        items_data
    )
    conn.commit()

def seed_payments(conn: sqlite3.Connection, orders_info: list) -> None:
    """
    Seeds payments data.
    """
    cursor = conn.cursor()
    payments_data = []
    for o in orders_info:
        status = o["status"]
        if status != "Cancelled" and (status != "Pending" or random.random() > 0.3):
            order_id = o["order_id"]
            order_date_dt = o["order_date_dt"]
            total_amount = o["total_amount"]
            pay_date = (order_date_dt + timedelta(minutes=random.randint(2, 60))).isoformat()
            pay_method = random.choice(["Credit Card", "PayPal", "Bank Transfer", "Apple Pay"])
            payments_data.append((order_id, pay_date, pay_method, total_amount))
    cursor.executemany(
        "INSERT INTO payments (order_id, payment_date, payment_method, amount) VALUES (?, ?, ?, ?);",
        payments_data
    )
    conn.commit()

def seed_shipments(conn: sqlite3.Connection, orders_info: list) -> None:
    """
    Seeds shipments data.
    """
    cursor = conn.cursor()
    shipments_data = []
    for o in orders_info:
        status = o["status"]
        if status in ["Shipped", "Completed"]:
            order_id = o["order_id"]
            order_date_dt = o["order_date_dt"]
            ship_date = (order_date_dt + timedelta(days=random.randint(1, 3))).isoformat()
            tracking = f"1Z{random.randint(100000, 999999)}A{random.randint(10, 99)}"
            carrier = random.choice(["FedEx", "UPS", "DHL", "USPS"])
            ship_status = "Delivered" if status == "Completed" else "In Transit"
            shipments_data.append((order_id, ship_date, tracking, carrier, ship_status))
    cursor.executemany(
        "INSERT INTO shipments (order_id, shipment_date, tracking_number, carrier, status) VALUES (?, ?, ?, ?, ?);",
        shipments_data
    )
    conn.commit()

def main() -> None:
    print("Resetting database...")
    reset_database()
    
    conn = get_db_connection()
    try:
        print("Creating schema...")
        create_schema(conn)
        
        print("Seeding categories...")
        category_ids = seed_categories(conn)
        
        print("Seeding customers...")
        customer_ids = seed_customers(conn)
        
        print("Seeding products...")
        products = seed_products(conn, category_ids)
        
        print("Preparing orders data...")
        orders_info = prepare_orders_data(customer_ids, products, count=300)
        
        print("Seeding orders...")
        seed_orders(conn, orders_info)
        
        print("Seeding order items...")
        seed_order_items(conn, orders_info)
        
        print("Seeding payments...")
        seed_payments(conn, orders_info)
        
        print("Seeding shipments...")
        seed_shipments(conn, orders_info)
        
        print("Database seeded successfully with all tables populated.")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
