import sqlite3
from collections.abc import Iterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse

from app.database import Database
from app.errors import ConflictError, NotFoundError
from app.models import (
    Entry,
    EntryInput,
    EntryUpdate,
    FinishInput,
    HistoryRecord,
    Kind,
    ProgressInput,
    Status,
    Title,
    TitleInput,
    User,
    UserInput,
)
from app.repositories import (
    EntryRepository,
    HistoryRepository,
    TitleRepository,
    UserRepository,
)
from app.services import WatchlistService

database = Database()


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.initialize()
    yield


app = FastAPI(title="Movie and Anime Watchlist System", lifespan=lifespan)


@app.exception_handler(NotFoundError)
def handle_not_found(request: Request, error: NotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(error)})


@app.exception_handler(ConflictError)
def handle_conflict(request: Request, error: ConflictError):
    return JSONResponse(status_code=409, content={"detail": str(error)})


def get_connection() -> Iterator[sqlite3.Connection]:
    with database.transaction() as connection:
        yield connection


Connection = Annotated[sqlite3.Connection, Depends(get_connection)]


def get_users(connection: Connection) -> UserRepository:
    return UserRepository(connection)


def get_titles(connection: Connection) -> TitleRepository:
    return TitleRepository(connection)


def get_entries(connection: Connection) -> EntryRepository:
    return EntryRepository(connection)


def get_history(connection: Connection) -> HistoryRepository:
    return HistoryRepository(connection)


def get_service(
    entries: Annotated[EntryRepository, Depends(get_entries)],
    history: Annotated[HistoryRepository, Depends(get_history)],
) -> WatchlistService:
    return WatchlistService(entries, history)


Users = Annotated[UserRepository, Depends(get_users)]
Titles = Annotated[TitleRepository, Depends(get_titles)]
Entries = Annotated[EntryRepository, Depends(get_entries)]
History = Annotated[HistoryRepository, Depends(get_history)]
Service = Annotated[WatchlistService, Depends(get_service)]


@app.get("/")
def home():
    return {"message": "Welcome! Visit /docs to try the API."}


@app.get("/users", response_model=list[User])
def get_users_list(users: Users):
    return users.list_all()


@app.get("/users/{user_id}", response_model=User)
def get_user(user_id: int, users: Users):
    return users.get(user_id)


@app.post("/user", response_model=User, status_code=201)
def create_user(user: UserInput, users: Users):
    return users.create(user)


@app.put("/user/{user_id}", response_model=User)
def update_user(user_id: int, user: UserInput, users: Users):
    return users.update(user_id, user)


@app.delete("/user/{user_id}")
def delete_user(user_id: int, users: Users):
    users.delete(user_id)
    return {"message": "User deleted successfully"}


@app.get("/titles", response_model=list[Title])
def get_titles_list(titles: Titles, search: str | None = None, kind: Kind | None = None):
    return titles.list_all(search, kind)


@app.get("/titles/{title_id}", response_model=Title)
def get_title(title_id: int, titles: Titles):
    return titles.get(title_id)


@app.post("/title", response_model=Title, status_code=201)
def create_title(title: TitleInput, titles: Titles):
    return titles.create(title)


@app.put("/title/{title_id}", response_model=Title)
def update_title(title_id: int, title: TitleInput, titles: Titles):
    return titles.update(title_id, title)


@app.delete("/title/{title_id}")
def delete_title(title_id: int, titles: Titles):
    titles.delete(title_id)
    return {"message": "Title deleted successfully"}


@app.get("/entries", response_model=list[Entry])
def get_entries_list(
    entries: Entries,
    user_id: int | None = None,
    status: Status | None = None,
    search: str | None = None,
):
    return entries.list_all(user_id, status, search)


@app.get("/entries/{entry_id}", response_model=Entry)
def get_entry(entry_id: int, entries: Entries):
    return entries.get(entry_id)


@app.post("/entry", response_model=Entry, status_code=201)
def create_entry(entry: EntryInput, entries: Entries):
    return entries.create(entry)


@app.put("/entry/{entry_id}", response_model=Entry)
def update_entry(entry_id: int, entry: EntryUpdate, entries: Entries):
    return entries.update(entry_id, entry)


@app.delete("/entry/{entry_id}")
def delete_entry(entry_id: int, entries: Entries):
    entries.delete(entry_id)
    return {"message": "Entry deleted successfully"}


@app.post("/entry/{entry_id}/progress", response_model=Entry)
def log_progress(entry_id: int, progress: ProgressInput, service: Service):
    return service.log_progress(entry_id, progress)


@app.post("/entry/{entry_id}/finish", response_model=Entry)
def finish_entry(entry_id: int, finish: FinishInput, service: Service):
    return service.finish(entry_id, finish)


@app.get("/entries/{entry_id}/history", response_model=list[HistoryRecord])
def get_entry_history(entry_id: int, entries: Entries, history: History):
    entries.get(entry_id)
    return history.list_for_entry(entry_id)
