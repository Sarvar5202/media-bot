import sqlite3
import os

DB_PATH = "users.db"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
        try:
            conn.execute("ALTER TABLE users ADD COLUMN username TEXT")
        except sqlite3.OperationalError:
            pass
        conn.commit()

def add_user(user_id: int, username: str = None):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO users (user_id, username) 
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET username=excluded.username
        """, (user_id, username))
        conn.commit()

def get_users_count() -> int:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("SELECT COUNT(*) FROM users")
        return cursor.fetchone()[0]

def get_all_users(limit: int = 50) -> list:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("SELECT user_id, username FROM users ORDER BY rowid DESC LIMIT ?", (limit,))
        return cursor.fetchall()
