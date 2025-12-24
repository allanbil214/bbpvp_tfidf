"""
Database connection utilities
"""

import mysql.connector # type: ignore
from mysql.connector import Error # type: ignore
from config import DB_CONFIG

def get_db_connection():
    """Get database connection"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"Database connection error: {e}")
        return None

def test_db_connection():
    """Test database connection"""
    conn = get_db_connection()
    if conn and conn.is_connected():
        info = conn.get_server_info()
        conn.close()
        return True, f"Connected to MySQL Server version {info}"
    return False, "Failed to connect to database"