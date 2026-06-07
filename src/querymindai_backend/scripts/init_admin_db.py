import os
import sys
import sqlite3
from datetime import datetime
from pathlib import Path

# Add the 'src' directory to sys.path to allow running this script directly
src_dir = str(Path(__file__).resolve().parent.parent.parent)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from querymindai_backend.config import get_settings
from querymindai_backend.database import get_admin_db_connection

def reset_admin_db() -> None:
    """
    Resets the admin database by removing the database file or dropping all tables.
    """
    settings = get_settings()
    db_path = settings.admin_db_path
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except PermissionError:
            # Fallback: Drop tables if database file is locked
            conn = get_admin_db_connection()
            try:
                conn.execute("PRAGMA foreign_keys = OFF;")
                tables = ["model_config", "audit_logs", "query_logs", "guardrails_config", "few_shot_examples", "schema_columns"]
                for table in tables:
                    conn.execute(f"DROP TABLE IF EXISTS {table};")
                conn.commit()
            finally:
                conn.close()

def create_admin_schema(conn: sqlite3.Connection) -> None:
    """
    Creates the admin configuration database schema.
    """
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")

    # 1. Schema columns metadata for Schema Manager
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS schema_columns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        table_name TEXT NOT NULL,
        column_name TEXT NOT NULL,
        data_type TEXT NOT NULL,
        description TEXT,
        is_sensitive INTEGER NOT NULL DEFAULT 0,
        UNIQUE(table_name, column_name)
    );
    """)

    # 2. Few-shot examples for Examples Manager
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS few_shot_examples (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question TEXT NOT NULL,
        sql_query TEXT NOT NULL,
        query_type TEXT NOT NULL,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL
    );
    """)

    # 3. Guardrails configuration
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS guardrails_config (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        allow_delete INTEGER NOT NULL DEFAULT 0,
        allow_drop INTEGER NOT NULL DEFAULT 0,
        allow_update INTEGER NOT NULL DEFAULT 0,
        allow_insert INTEGER NOT NULL DEFAULT 0,
        allow_alter INTEGER NOT NULL DEFAULT 0,
        max_row_limit INTEGER NOT NULL DEFAULT 100,
        updated_at TEXT NOT NULL
    );
    """)

    # 4. Query logs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS query_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nl_query TEXT NOT NULL,
        generated_sql TEXT,
        execution_status TEXT NOT NULL,
        latency_ms INTEGER,
        row_count INTEGER,
        error_message TEXT,
        created_at TEXT NOT NULL
    );
    """)

    # 5. Audit logs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        action TEXT NOT NULL,
        details TEXT NOT NULL,
        timestamp TEXT NOT NULL
    );
    """)

    # 6. Model configuration
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS model_config (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        provider TEXT NOT NULL DEFAULT 'mock',
        model_name TEXT NOT NULL DEFAULT 'mock-sql-generator',
        temperature REAL NOT NULL DEFAULT 0.0,
        sql_dialect TEXT NOT NULL DEFAULT 'sqlite',
        max_tokens INTEGER,
        updated_at TEXT NOT NULL
    );
    """)

    conn.commit()

def populate_default_guardrails(admin_conn: sqlite3.Connection) -> None:
    """
    Inserts the default guardrails configuration.
    """
    cursor = admin_conn.cursor()
    now = datetime.utcnow().isoformat()
    cursor.execute(
        """
        INSERT INTO guardrails_config (allow_delete, allow_drop, allow_update, allow_insert, allow_alter, max_row_limit, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """,
        (0, 0, 0, 0, 0, 100, now)
    )
    admin_conn.commit()
    print("Inserted default guardrails_config record.")

def populate_default_model_config(admin_conn: sqlite3.Connection) -> None:
    """
    Inserts the default model configuration.
    """
    cursor = admin_conn.cursor()
    now = datetime.utcnow().isoformat()
    cursor.execute(
        """
        INSERT INTO model_config (provider, model_name, temperature, sql_dialect, max_tokens, updated_at)
        VALUES (?, ?, ?, ?, ?, ?);
        """,
        ("mock", "mock-sql-generator", 0.0, "sqlite", None, now)
    )
    admin_conn.commit()
    print("Inserted default model_config record.")

def populate_default_schema_columns(admin_conn: sqlite3.Connection) -> None:
    """
    Populates schema_columns table with metadata from the business database if it exists.
    """
    settings = get_settings()
    db_path = settings.db_path
    if not os.path.exists(db_path):
        print(f"Business database not found at {db_path}. Skipping schema_columns initialization.")
        return

    try:
        from querymindai_backend.database import get_db_connection
        business_conn = get_db_connection()
    except Exception as e:
        print(f"Failed to connect to business database: {e}. Skipping schema_columns initialization.")
        return

    try:
        business_cursor = business_conn.cursor()
        # Get all user tables, excluding SQLite system tables
        business_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = [row[0] for row in business_cursor.fetchall()]

        columns_data = []
        for table in tables:
            business_cursor.execute(f"PRAGMA table_info({table});")
            for row in business_cursor.fetchall():
                col_name = row[1]
                data_type = row[2]
                columns_data.append((table, col_name, data_type, None, 0))

        if columns_data:
            admin_cursor = admin_conn.cursor()
            admin_cursor.executemany(
                """
                INSERT OR IGNORE INTO schema_columns (table_name, column_name, data_type, description, is_sensitive)
                VALUES (?, ?, ?, ?, ?);
                """,
                columns_data
            )
            admin_conn.commit()
            print(f"Populated schema_columns with {len(columns_data)} columns from the business database.")
    except Exception as e:
        print(f"Error reading business database schema: {e}")
    finally:
        business_conn.close()

def main() -> None:
    print("Resetting admin database...")
    reset_admin_db()

    conn = get_admin_db_connection()
    try:
        print("Creating admin schema...")
        create_admin_schema(conn)
        
        print("Inserting defaults...")
        populate_default_guardrails(conn)
        populate_default_model_config(conn)
        populate_default_schema_columns(conn)
        
        print("Admin database initialized successfully with default records.")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
