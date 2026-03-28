import psycopg2
from werkzeug.security import generate_password_hash

def add_new_user(username, password, role='user'):
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="ucu_rag_db",
            user="user",
            password="password",
            port="5432"
        )
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
    conn = psycopg2.connect(
        host="localhost",
        database="ucu_rag_db",
        user="user",
        password="password",
        port="5432"
    )
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE username = %s", (username,))
    conn.commit()
    cur.close()
    conn.close()

if __name__ == "__main__":
    add_new_user("admin", "admin")