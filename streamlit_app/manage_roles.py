import psycopg2

def add_new_role(role, category):
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="ucu_rag_db",
            user="user",
            password="password",
            port="5432"
        )
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
    conn = psycopg2.connect(
        host="localhost",
        database="ucu_rag_db",
        user="user",
        password="password",
        port="5432"
    )
    cur = conn.cursor()
    cur.execute("DELETE FROM access_control WHERE role = %s AND allowed_category = %s", (role, allowed_category))
    conn.commit()
    cur.close()
    conn.close()

if __name__ == "__main__":
    add_new_role("admin", "Public")