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
    
def get_allowed_categories(role):
    conn = get_connection()
    cur = conn.cursor() 
    cur.execute("SELECT allowed_category FROM access_control WHERE role = %s", (role,))
    categories = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    return categories

def add_new_user(username, password, role):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM users WHERE username = %s", (username,))
    user_exists = cur.fetchone()
    cur.close()
    conn.close()
    if user_exists:
        raise ValueError(f"Користувач з логіном '{username}' вже існує")
    conn = get_connection()
    cur = conn.cursor()
    hashed_pw = generate_password_hash(password)
    cur.execute(
        "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
        (username, hashed_pw, role)
    )
    conn.commit()
    cur.close()
    conn.close()

def delete_user(username):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE username = %s", (username,))
    deleted_rows = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    if deleted_rows == 0:
        raise ValueError(f"Користувача з логіном '{username}' не знайдено")

def get_all_users():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT username, role FROM users ORDER BY username ASC")
    users = cur.fetchall() 
    cur.close()
    conn.close()
    return users

def add_new_role(role, category):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO access_control (role, allowed_category) VALUES (%s, %s)",
        (role, category)
    )
    conn.commit()
    cur.close()
    conn.close()

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
    conn = get_connection()
    cur = conn.cursor()   
    cur.execute("SELECT allowed_category FROM access_control WHERE role = %s", (role,))
    categories = [row[0] for row in cur.fetchall()]  
    cur.close()
    conn.close()
    return categories
