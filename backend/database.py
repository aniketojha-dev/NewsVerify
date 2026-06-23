import sqlite3
import json
from typing import List, Dict, Optional
from backend.config import DATABASE_PATH


class Database:
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                summary TEXT NOT NULL,
                year INTEGER NOT NULL,
                category TEXT NOT NULL,
                sources TEXT NOT NULL DEFAULT '[]',
                keywords TEXT NOT NULL DEFAULT '[]',
                url TEXT,
                published_date TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_events_year ON events(year)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_events_category ON events(category)")
        conn.commit()
        conn.close()

    def add_event(self, title: str, summary: str, year: int, category: str,
                  sources: list, keywords: list, url: str = None, date: str = None) -> int:
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO events (title, summary, year, category, sources, keywords, url, published_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (title, summary, year, category, json.dumps(sources), json.dumps(keywords), url, date)
        )
        conn.commit()
        event_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.close()
        return event_id

    def get_event(self, event_id: int) -> Optional[Dict]:
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
        conn.close()
        if row:
            return dict(row)
        return None

    def search_by_keyword(self, query: str, year: int = None, limit: int = 20) -> List[Dict]:
        conn = self._get_conn()
        sql = "SELECT * FROM events WHERE (title LIKE ? OR summary LIKE ? OR keywords LIKE ?)"
        params = [f'%{query}%', f'%{query}%', f'%{query}%']
        if year:
            sql += " AND year = ?"
            params.append(year)
        sql += " LIMIT ?"
        params.append(limit)
        rows = conn.execute(sql, params).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def search_by_year(self, year: int, category: str = None, limit: int = 50) -> List[Dict]:
        conn = self._get_conn()
        if category:
            rows = conn.execute(
                "SELECT * FROM events WHERE year = ? AND category = ? LIMIT ?",
                (year, category, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM events WHERE year = ? LIMIT ?",
                (year, limit)
            ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_all_events(self) -> List[Dict]:
        conn = self._get_conn()
        rows = conn.execute("SELECT * FROM events").fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def count_events(self) -> int:
        conn = self._get_conn()
        count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        conn.close()
        return count

    def count_by_category(self) -> Dict:
        conn = self._get_conn()
        rows = conn.execute("SELECT category, COUNT(*) as cnt FROM events GROUP BY category").fetchall()
        conn.close()
        return {r["category"]: r["cnt"] for r in rows}

    def delete_all(self):
        conn = self._get_conn()
        conn.execute("DELETE FROM events")
        conn.commit()
        conn.close()

    def clear_all(self):
        self.delete_all()
