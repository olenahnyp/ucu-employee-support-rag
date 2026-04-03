import psycopg2
from psycopg2.extras import RealDictCursor
import os
from werkzeug.security import generate_password_hash, check_password_hash

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
        cur.execute("SELECT allowed_category FROM access_control WHERE role = %s", (role,))
        categories = [row[0] for row in cur.fetchall()]
        cur.close()
        conn.close()
        return categories
    except Exception as e:
        print(f"Error fetching categories: {e}")
        return []

def add_new_user(username, password, role):
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        hashed_pw = generate_password_hash(password)
        print(hashed_pw)
        
        cur.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s) ON CONFLICT (username) DO NOTHING",
            (username, hashed_pw, role)
        )
        
        conn.commit()
        print(f"Користувач {username} успішно доданий!")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Помилка: {e}")

def delete_user(username):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE username = %s", (username,))
    conn.commit()
    cur.close()
    conn.close()

def get_all_users():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT username, role FROM users ORDER BY username ASC")
    users = cur.fetchall() 
    cur.close()
    conn.close()
    return users

def add_new_role(role, category):
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute(
            "INSERT INTO access_control (role, allowed_category) VALUES (%s, %s)",
            (role, category)
        )
        
        conn.commit()
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Помилка: {e}")

def delete_role(role, allowed_category):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM access_control WHERE role = %s AND allowed_category = %s", (role, allowed_category))
    conn.commit()
    cur.close()
    conn.close()

def get_all_roles_with_permissions():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT role, allowed_category FROM access_control ORDER BY role;")
    roles = cur.fetchall()
    cur.close()
    conn.close()
    return roles

def get_unique_roles():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT role FROM access_control ORDER BY role ASC")
    roles = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    return roles

def get_categories_for_role(role):
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT allowed_category FROM access_control WHERE role = %s", (role,))
        categories = [row[0] for row in cur.fetchall()]
        
        cur.close()
        conn.close()
        return categories
    except Exception as e:
        print(f"Помилка при отриманні категорій для ролі {role}: {e}")
        return []
