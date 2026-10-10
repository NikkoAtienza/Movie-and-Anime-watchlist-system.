import sqlite3

from app.errors import ConflictError, NotFoundError
from app.models import (
    Entry,
    EntryInput,
    EntryUpdate,
    HistoryRecord,
    Title,
    TitleInput,
    User,
    UserInput,
)


class BaseRepository:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def _one(self, sql, params=()):
        return self.connection.execute(sql, params).fetchone()

    def _all(self, sql, params=()):
        return self.connection.execute(sql, params).fetchall()

    def _write(self, sql, params=(), conflict_message="This change breaks a database rule"):
        try:
            return self.connection.execute(sql, params)
        except sqlite3.IntegrityError as error:
            raise ConflictError(conflict_message) from error


class UserRepository(BaseRepository):
    def list_all(self) -> list[User]:
        rows = self._all("SELECT id, username, created_at FROM users ORDER BY id")
        return [User(**dict(row)) for row in rows]

    def get(self, user_id: int) -> User:
        row = self._one(
            "SELECT id, username, created_at FROM users WHERE id = ?", (user_id,)
        )
        if row is None:
            raise NotFoundError("User not found")
        return User(**dict(row))

    def create(self, data: UserInput) -> User:
        cursor = self._write(
            "INSERT INTO users (username) VALUES (?)",
            (data.username,),
            "That username is already taken",
        )
        return self.get(cursor.lastrowid)

    def update(self, user_id: int, data: UserInput) -> User:
        cursor = self._write(
            "UPDATE users SET username = ? WHERE id = ?",
            (data.username, user_id),
            "That username is already taken",
        )
        if cursor.rowcount == 0:
            raise NotFoundError("User not found")
        return self.get(user_id)

    def delete(self, user_id: int) -> None:
        cursor = self._write("DELETE FROM users WHERE id = ?", (user_id,))
        if cursor.rowcount == 0:
            raise NotFoundError("User not found")


class TitleRepository(BaseRepository):
    def list_all(self, search: str | None = None, kind: str | None = None) -> list[Title]:
        rows = self._all(
            "SELECT id, name, kind, total_episodes FROM titles "
            "WHERE (? IS NULL OR name LIKE '%' || ? || '%') "
            "AND (? IS NULL OR kind = ?) "
            "ORDER BY name",
            (search, search, kind, kind),
        )
        return [Title(**dict(row)) for row in rows]

    def get(self, title_id: int) -> Title:
        row = self._one(
            "SELECT id, name, kind, total_episodes FROM titles WHERE id = ?",
            (title_id,),
        )
        if row is None:
            raise NotFoundError("Title not found")
        return Title(**dict(row))

    def create(self, data: TitleInput) -> Title:
        cursor = self._write(
            "INSERT INTO titles (name, kind, total_episodes) VALUES (?, ?, ?)",
            (data.name, data.kind, data.total_episodes),
            "That title already exists",
        )
        return self.get(cursor.lastrowid)

    def update(self, title_id: int, data: TitleInput) -> Title:
        self.get(title_id)
        ahead = self._one(
            "SELECT 1 FROM watch_entries WHERE title_id = ? AND episodes_watched > ?",
            (title_id, data.total_episodes),
        )
        if ahead is not None:
            raise ConflictError(
                "Someone has already watched more episodes than the new total"
            )
        self._write(
            "UPDATE titles SET name = ?, kind = ?, total_episodes = ? WHERE id = ?",
            (data.name, data.kind, data.total_episodes, title_id),
            "That title already exists",
        )
        return self.get(title_id)

    def delete(self, title_id: int) -> None:
        cursor = self._write(
            "DELETE FROM titles WHERE id = ?",
            (title_id,),
            "This title is on a watchlist, remove those entries first",
        )
        if cursor.rowcount == 0:
            raise NotFoundError("Title not found")


class EntryRepository(BaseRepository):
    SELECT_ENTRY = (
        "SELECT e.id, e.user_id, u.username, e.title_id, t.name AS title_name, "
        "t.kind, t.total_episodes, e.status, e.episodes_watched, e.rating "
        "FROM watch_entries e "
        "JOIN users u ON u.id = e.user_id "
        "JOIN titles t ON t.id = e.title_id "
    )

    def list_all(
        self,
        user_id: int | None = None,
        status: str | None = None,
        search: str | None = None,
    ) -> list[Entry]:
        rows = self._all(
            self.SELECT_ENTRY
            + "WHERE (? IS NULL OR e.user_id = ?) "
            "AND (? IS NULL OR e.status = ?) "
            "AND (? IS NULL OR t.name LIKE '%' || ? || '%') "
            "ORDER BY e.id",
            (user_id, user_id, status, status, search, search),
        )
        return [Entry(**dict(row)) for row in rows]

    def get(self, entry_id: int) -> Entry:
        row = self._one(self.SELECT_ENTRY + "WHERE e.id = ?", (entry_id,))
        if row is None:
            raise NotFoundError("Entry not found")
        return Entry(**dict(row))

    def create(self, data: EntryInput) -> Entry:
        if self._one("SELECT 1 FROM users WHERE id = ?", (data.user_id,)) is None:
            raise NotFoundError("User not found")
        if self._one("SELECT 1 FROM titles WHERE id = ?", (data.title_id,)) is None:
            raise NotFoundError("Title not found")
        cursor = self._write(
            "INSERT INTO watch_entries (user_id, title_id) VALUES (?, ?)",
            (data.user_id, data.title_id),
            "That title is already on this user's watchlist",
        )
        return self.get(cursor.lastrowid)

    def update(self, entry_id: int, data: EntryUpdate) -> Entry:
        cursor = self._write(
            "UPDATE watch_entries SET status = ?, rating = ? WHERE id = ?",
            (data.status, data.rating, entry_id),
        )
        if cursor.rowcount == 0:
            raise NotFoundError("Entry not found")
        return self.get(entry_id)

    def save_progress(
        self, entry_id: int, episodes_watched: int, status: str, rating: int
    ) -> None:
        self._write(
            "UPDATE watch_entries "
            "SET episodes_watched = ?, status = ?, rating = ? WHERE id = ?",
            (episodes_watched, status, rating, entry_id),
        )

    def delete(self, entry_id: int) -> None:
        cursor = self._write("DELETE FROM watch_entries WHERE id = ?", (entry_id,))
        if cursor.rowcount == 0:
            raise NotFoundError("Entry not found")


class HistoryRepository(BaseRepository):
    def add(self, entry_id: int, episodes_added: int, note: str) -> None:
        self._write(
            "INSERT INTO watch_history (entry_id, episodes_added, note) "
            "VALUES (?, ?, ?)",
            (entry_id, episodes_added, note),
        )

    def list_for_entry(self, entry_id: int) -> list[HistoryRecord]:
        rows = self._all(
            "SELECT id, entry_id, episodes_added, note, logged_at "
            "FROM watch_history WHERE entry_id = ? ORDER BY id",
            (entry_id,),
        )
        return [HistoryRecord(**dict(row)) for row in rows]
