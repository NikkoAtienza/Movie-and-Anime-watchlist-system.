import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

DATABASE_FILE = Path(__file__).resolve().parent.parent / "watchlist.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS titles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('movie', 'anime')),
    total_episodes INTEGER NOT NULL DEFAULT 1 CHECK (total_episodes >= 1),
    UNIQUE (name, kind)
);

CREATE TABLE IF NOT EXISTS watch_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    title_id INTEGER NOT NULL REFERENCES titles (id) ON DELETE RESTRICT,
    status TEXT NOT NULL DEFAULT 'planned'
        CHECK (status IN ('planned', 'watching', 'completed', 'dropped')),
    episodes_watched INTEGER NOT NULL DEFAULT 0 CHECK (episodes_watched >= 0),
    rating INTEGER NOT NULL DEFAULT 0 CHECK (rating BETWEEN 0 AND 10),
    UNIQUE (user_id, title_id)
);

CREATE TABLE IF NOT EXISTS watch_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id INTEGER NOT NULL REFERENCES watch_entries (id) ON DELETE CASCADE,
    episodes_added INTEGER NOT NULL CHECK (episodes_added >= 0),
    note TEXT NOT NULL DEFAULT '',
    logged_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


class Database:
    def __init__(self, path: Path = DATABASE_FILE):
        self.path = path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.transaction() as connection:
            connection.executescript(SCHEMA)
