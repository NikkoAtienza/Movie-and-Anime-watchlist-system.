from app.errors import ConflictError
from app.models import Entry, FinishInput, ProgressInput
from app.repositories import EntryRepository, HistoryRepository


class WatchlistService:
    def __init__(self, entries: EntryRepository, history: HistoryRepository):
        self.entries = entries
        self.history = history

    def log_progress(self, entry_id: int, data: ProgressInput) -> Entry:
        entry = self.entries.get(entry_id)
        if entry.status == "completed":
            raise ConflictError("This title is already completed")

        remaining = entry.total_episodes - entry.episodes_watched
        added = min(data.episodes, remaining)
        watched = entry.episodes_watched + added
        status = "completed" if watched >= entry.total_episodes else "watching"

        self.entries.save_progress(entry_id, watched, status, entry.rating)
        self.history.add(entry_id, added, data.note)
        return self.entries.get(entry_id)

    def finish(self, entry_id: int, data: FinishInput) -> Entry:
        entry = self.entries.get(entry_id)
        if entry.status == "completed":
            raise ConflictError("This title is already completed")

        remaining = entry.total_episodes - entry.episodes_watched
        self.entries.save_progress(entry_id, entry.total_episodes, "completed", data.rating)
        self.history.add(entry_id, remaining, "Marked as finished")
        return self.entries.get(entry_id)
