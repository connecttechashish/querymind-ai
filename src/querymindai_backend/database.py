import sqlite3
from querymindai_backend.config import get_settings

def get_db_connection() -> sqlite3.Connection:
    """
    Returns an open SQLite database connection to the business database.
    Ensures foreign key constraints are enabled.
    """
    settings = get_settings()
    conn = sqlite3.connect(settings.db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn

def get_admin_db_connection() -> sqlite3.Connection:
    """
    Returns an open SQLite database connection to the admin database.
    Ensures foreign key constraints are enabled.
    """
    settings = get_settings()
    conn = sqlite3.connect(settings.admin_db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn
