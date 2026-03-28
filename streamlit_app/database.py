import psycopg2
import os
from werkzeug.security import check_password_hash

def get_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "postgres"),
        database=os.getenv("POSTGRES_DB", "ucu_rag_db"),
        user=os.getenv("POSTGRES_USER", "user"),
        password=os.getenv("POSTGRES_PASSWORD", "password")
    )

def verify_user(username, password):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT password_hash, role FROM users WHERE username = %s", (username,))
        result = cur.fetchone()
        cur.close()
        conn.close()
        if result:
            stored_hash, role = result
            if check_password_hash(stored_hash, password):
                return role
        return None
    except Exception as e:
        print(f"Database error: {e}")
        return None
    
def get_allowed_categories(role):
    try:
        conn = get_connection()
        cur = conn.cursor()
        if role == 'admin':
            return None    
        cur.execute("SELECT allowed_category FROM access_control WHERE role = %s", (role,))
        categories = [row[0] for row in cur.fetchall()]
        cur.close()
        conn.close()
        return categories
    except Exception as e:
        print(f"Error fetching categories: {e}")
        return []
