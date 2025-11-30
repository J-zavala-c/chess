"""
Módulo: database.db_manager
CRUD básico para guardar y buscar partidas (SQLite).
"""
import sqlite3
import datetime
from typing import List, Tuple, Optional

DB_FILENAME = 'chess_games.db'

class DBManager:
    def __init__(self, filename: str = DB_FILENAME):
        self.conn = sqlite3.connect(filename)
        self._create()

    def _create(self):
        c = self.conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                white TEXT,
                black TEXT,
                result TEXT,
                pgn TEXT
            )
        ''')
        self.conn.commit()

    def save_game(self, pgn_text: str, white: str = 'White', black: str = 'Black', result: str = '*') -> int:
        c = self.conn.cursor()
        date = datetime.datetime.utcnow().isoformat()
        c.execute('INSERT INTO games (date, white, black, result, pgn) VALUES (?, ?, ?, ?, ?)',
                (date, white, black, result, pgn_text))
        self.conn.commit()
        return c.lastrowid

    def search_games(self, query: Optional[str] = None, limit: int = 100) -> List[Tuple[int, str, str, str, str]]:
        c = self.conn.cursor()
        sql = 'SELECT id, date, white, black, result FROM games'
        params = []
        if query:
            sql += ' WHERE pgn LIKE ?'
            params.append(f'%{query}%')
        sql += ' ORDER BY date DESC LIMIT ?'
        params.append(limit)
        c.execute(sql, params)
        return c.fetchall()

    def load_pgn_by_id(self, game_id: int) -> Optional[str]:
        c = self.conn.cursor()
        c.execute('SELECT pgn FROM games WHERE id = ?', (game_id,))
        row = c.fetchone()
        return row[0] if row else None

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass
