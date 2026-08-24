import sqlite3
import asyncio

class SQLiteConnection:
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

    async def execute(self, query, *args):
        for i in range(10, 0, -1):
            query = query.replace(f"${i}", "?")
        query = query.replace("TIMESTAMP WITH TIME ZONE", "TIMESTAMP")
        query = query.replace("BIGINT PRIMARY KEY", "INTEGER PRIMARY KEY")
        query = query.replace("BOOLEAN DEFAULT TRUE", "INTEGER DEFAULT 1")
        query = query.replace("BOOLEAN", "INTEGER")
        query = query.replace("TRUE", "1").replace("FALSE", "0")
        query = query.replace("NOW() - INTERVAL '24 HOURS'", "datetime('now', '-1 day')")
        
        # PostgreSQL ON CONFLICT (user_id) DO UPDATE SET ...
        # SQLite uses ON CONFLICT(user_id) DO UPDATE SET ...
        
        try:
            return await asyncio.to_thread(self._execute, query, args)
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                pass
            else:
                raise e

    def _execute(self, query, args):
        cursor = self.conn.cursor()
        cursor.execute(query, args)
        self.conn.commit()
        return cursor.rowcount

    async def fetchval(self, query, *args):
        for i in range(10, 0, -1):
            query = query.replace(f"${i}", "?")
        query = query.replace("TRUE", "1").replace("FALSE", "0")
        query = query.replace("NOW() - INTERVAL '24 HOURS'", "datetime('now', '-1 day')")
        return await asyncio.to_thread(self._fetchval, query, args)

    def _fetchval(self, query, args):
        cursor = self.conn.cursor()
        cursor.execute(query, args)
        row = cursor.fetchone()
        return row[0] if row else None

    async def fetchrow(self, query, *args):
        for i in range(10, 0, -1):
            query = query.replace(f"${i}", "?")
        query = query.replace("TRUE", "1").replace("FALSE", "0")
        query = query.replace("NOW() - INTERVAL '24 HOURS'", "datetime('now', '-1 day')")
        return await asyncio.to_thread(self._fetchrow, query, args)

    def _fetchrow(self, query, args):
        cursor = self.conn.cursor()
        cursor.execute(query, args)
        row = cursor.fetchone()
        return dict(row) if row else None

    async def fetch(self, query, *args):
        for i in range(10, 0, -1):
            query = query.replace(f"${i}", "?")
        query = query.replace("TRUE", "1").replace("FALSE", "0")
        query = query.replace("NOW() - INTERVAL '24 HOURS'", "datetime('now', '-1 day')")
        return await asyncio.to_thread(self._fetch, query, args)

    def _fetch(self, query, args):
        cursor = self.conn.cursor()
        cursor.execute(query, args)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

class SQLitePool:
    def __init__(self, db_path="local_bot_db.sqlite3"):
        self.conn = SQLiteConnection(db_path)
        
    class AcquireContext:
        def __init__(self, conn):
            self.conn = conn
        async def __aenter__(self):
            return self.conn
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    def acquire(self):
        return self.AcquireContext(self.conn)
