# Movie and Anime Watchlist System (FastAPI + SQLite)

**Click me**: https://github.com/NikkoAtienza/Movie-and-Anime-watchlist-system

## Problem and solution

Students who watch both movies and anime often lose track of what they have watched, which episode they stopped at, and what they thought of each title. Notes in phone apps or chats get scattered and are never updated.

This system keeps one organized record per viewer. A viewer adds titles to a personal watchlist, logs the episodes watched after each session, and finishes a title with a rating. Every progress update is saved together with a history log, so the viewer can always see when and how far they watched.

Intended users: students or small groups of friends who want a shared tracker with a separate watchlist for each person.

## Features

- Users: register, list, rename, delete
- Title catalog: add movies and anime with their episode count, search by name, filter by kind
- Watchlist entries: add a title to a user's list, list and search entries by user, status or name, update status and rating, remove
- Log progress (transaction): add episodes watched, update the status automatically, and write a history row
- Finish a title (transaction): complete a title, set the rating, and write a history row
- Watch history per entry
- Input validation and clear 404, 409 and 422 errors

## Database design

Four tables with primary keys and foreign keys:

| Table | Key columns | Purpose |
| --- | --- | --- |
| users | id (PK), username (unique) | Who owns a watchlist |
| titles | id (PK), name, kind, total_episodes, unique (name, kind) | Catalog of movies and anime |
| watch_entries | id (PK), user_id (FK to users), title_id (FK to titles), status, episodes_watched, rating, unique (user_id, title_id) | One user's record of one title |
| watch_history | id (PK), entry_id (FK to watch_entries), episodes_added, note, logged_at | Log of each progress update |

Relationships:

```
users 1 --- * watch_entries * --- 1 titles
                   |
                   1
                   |
                   * watch_history
```

Integrity rules:

- Foreign keys are switched on for every connection (PRAGMA foreign_keys = ON).
- Deleting a user also deletes their entries and history (ON DELETE CASCADE).
- Deleting an entry also deletes its history (ON DELETE CASCADE).
- A title that is on any watchlist cannot be deleted (ON DELETE RESTRICT, returns 409).
- A viewer cannot add the same title twice (unique user_id and title_id).
- A title's episode total cannot be lowered below what someone has already watched.
- CHECK constraints limit kind, status and rating to valid values.

## Transactional workflow

Logging progress changes two tables, so both changes must succeed together or not at all.

1. Read the entry and reject it if it is already completed (409).
2. Add the episodes, capped at the title's total.
3. Set the status to completed if the total is reached, otherwise watching.
4. Update watch_entries and insert a row in watch_history.

Each request uses one database connection. The connection commits when the request succeeds and rolls back if anything raises an error, so a failure after step 4's first write never leaves half-saved data. Finishing a title works the same way.

## OOP design

| Class | File | Responsibility |
| --- | --- | --- |
| Database | app/database.py | Opens connections, turns on foreign keys, runs transactions, creates the tables |
| BaseRepository | app/repositories.py | Shared helpers for running SQL and turning database errors into ConflictError |
| UserRepository, TitleRepository, EntryRepository, HistoryRepository | app/repositories.py | Inherit from BaseRepository. Each one owns the SQL of one table |
| WatchlistService | app/services.py | Business workflow (log progress, finish). Combines repositories |
| NotFoundError, ConflictError | app/errors.py | Custom errors that main.py converts to 404 and 409 |
| Pydantic models (UserInput, User, TitleInput, Title, Entry, and others) | app/models.py | Validate input and shape responses |

OOP ideas used: encapsulation (SQL hidden inside repositories), inheritance (repositories extend BaseRepository), composition (the service holds repositories), and separation of responsibilities (routes, workflow, data access and models are in separate files).

## Project structure

```
main.py             routes and error handlers
requirements.txt
app/
    database.py     Database class and table definitions
    models.py       Pydantic data classes
    repositories.py repository classes (SQL)
    services.py     WatchlistService (transactions)
    errors.py       custom errors
```

watchlist.db is created automatically the first time the app starts.

## Run it on Windows (VS Code)

1. Open the project folder in VS Code (File > Open Folder).
2. Open a terminal (Terminal > New Terminal).
3. Create the virtual environment:

```
py -m venv .venv
```

4. Activate it:

```
.\.venv\Scripts\Activate.ps1
```

If scripts are blocked, run this once and activate again:

```
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

5. Install the packages:

```
python -m pip install -r requirements.txt
```

6. Start the server:

```
python -m uvicorn main:app --reload
```

7. Open http://127.0.0.1:8000/docs in your browser.

Press Ctrl+C to stop the server. If you used an older version of this project, delete the old watchlist.db first.

## Endpoints

| Endpoint | Parameters | Purpose |
| --- | --- | --- |
| GET / | None | Displays a welcome message |
| GET /users | None | Lists all users |
| GET /users/{user_id} | user_id: int | Gets one user |
| POST /user | user: UserInput | Creates a user |
| PUT /user/{user_id} | user_id: int, user: UserInput | Renames a user |
| DELETE /user/{user_id} | user_id: int | Deletes a user and their entries |
| GET /titles | search: text, kind: movie or anime (both optional) | Lists or searches the catalog |
| GET /titles/{title_id} | title_id: int | Gets one title |
| POST /title | title: TitleInput | Adds a title |
| PUT /title/{title_id} | title_id: int, title: TitleInput | Updates a title |
| DELETE /title/{title_id} | title_id: int | Deletes a title that is not in use |
| GET /entries | user_id, status, search (all optional) | Lists or searches watchlist entries |
| GET /entries/{entry_id} | entry_id: int | Gets one entry with user and title details |
| POST /entry | entry: EntryInput | Adds a title to a user's watchlist |
| PUT /entry/{entry_id} | entry_id: int, entry: EntryUpdate | Changes status (planned, watching, dropped) and rating |
| DELETE /entry/{entry_id} | entry_id: int | Removes an entry and its history |
| POST /entry/{entry_id}/progress | entry_id: int, progress: ProgressInput | Transaction: log episodes watched |
| POST /entry/{entry_id}/finish | entry_id: int, finish: FinishInput | Transaction: complete a title with a rating |
| GET /entries/{entry_id}/history | entry_id: int | Shows the watch history of an entry |

Errors:

- 404: the record does not exist
- 409: the change breaks a rule (duplicate, title in use, entry already completed)
- 422: the data is invalid (empty name, rating above 10, wrong kind or status)

## Test it from the docs page

Click an endpoint, click "Try it out", fill in the fields, then click "Execute". Suggested order:

1. POST /user with `{"username": "nikko"}`
2. POST /title with `{"name": "Steins;Gate", "kind": "anime", "total_episodes": 24}`
3. POST /title with `{"name": "Inception", "kind": "movie"}`
4. POST /entry with `{"user_id": 1, "title_id": 1}`
5. POST /entry/1/progress with `{"episodes": 10, "note": "Watched after class"}`
6. GET /entries/1 (status is watching, 10 episodes watched)
7. POST /entry/1/progress with `{"episodes": 20}` (capped at 24, status becomes completed)
8. GET /entries/1/history (two rows: 10 and 14 episodes)
9. POST /entry/1/finish (409, already completed)
10. GET /titles?search=stein (search)
11. DELETE /title/1 (409, the title is on a watchlist)

## How the safe SQL works

Queries never join user input into the SQL text. They use ? placeholders and pass the values separately:

```python
self._one(
    "SELECT id, username, created_at FROM users WHERE id = ?", (user_id,)
)
```

Even search text such as `'; DROP TABLE titles;--` is treated as plain text.

## Common problems

- "python is not recognized": reinstall Python and tick "Add to PATH", or use py instead of python.
- "No module named fastapi": the virtual environment is not active, or step 5 was skipped.
- Port already in use: add --port 8001 to the uvicorn command.
- Want a fresh database: stop the server and delete watchlist.db.
