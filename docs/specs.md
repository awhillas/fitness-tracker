# Specs

## Purpose

A small single-user web app for recording body weight over time and viewing it as
daily and weekly charts.

## Data model

```sql
CREATE TABLE IF NOT EXISTS weighings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    weight_kg REAL NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_weighings_date ON weighings (date DESC);
```

- `date` is ISO 8601 (`YYYY-MM-DD`); multiple entries per day are allowed and
  averaged by the charts.
- `weight_kg` must parse as a float and be in the range `0 < w < 500`, stored
  rounded to 2 decimal places.
- SQLite runs in WAL mode with foreign keys enabled.

## Configuration

All configuration is read from environment variables in `app/config.py`.

| Variable | Default | Notes |
| --- | --- | --- |
| `DB_PATH` | `data/fitness.db` | SQLite file; `/data/fitness.db` in the container |
| `USERNAME` | `alex` | single hard-coded user |
| `PASSWORD` | `changeme` | single hard-coded password |
| `SECRET_KEY` | `dev-secret-change-me` | session signing key |
| `PAGE_SIZE` | `30` | weighings per page |
| `DAILY_DAYS` | `7` | daily chart window |
| `WEEKLY_WEEKS` | `8` | weekly chart window |

## Routes

| Method | Path | Behaviour |
| --- | --- | --- |
| `GET` | `/healthz` | JSON health check, no auth |
| `GET` | `/login` | login form |
| `POST` | `/login` | validates credentials, sets session, `303` to `/`; `401` re-renders form on failure |
| `POST` | `/logout` | clears session, redirects to `/login` |
| `GET` | `/` | home page with daily and weekly charts |
| `GET` | `/weighings` | paged list, most recent first; htmx requests get the table partial only |
| `GET` | `/weighings/new` | add form, prefilled with today and the last recorded weight |
| `POST` | `/weighings` | create weighing, `303` to list; `400` with error partial on invalid input |
| `GET` | `/weighings/{id}/edit` | htmx inline edit partial |
| `PUT` | `/weighings/{id}` | update weighing |
| `DELETE` | `/weighings/{id}` | delete weighing, `204` |

Everything except `/login` and `/healthz` requires a session. Unauthenticated HTML
requests redirect to `/login`; htmx requests get `401` with an `HX-Redirect` header.

## Charts

### Daily chart

- Last `DAILY_DAYS` days, oldest on the left.
- One vertical bar per day, height is the mean weight for that day.
- Days with no weighing render a faded placeholder bar and are skipped for the
  error bar.

### Weekly chart

- Last `WEEKLY_WEEKS` ISO weeks, oldest at the top.
- Horizontal bars, y axis is the `YYYY-Www` ISO week label.
- Bar length is the weekly mean; an error bar spans `mean ± sample standard
  deviation` of that week's weighings.
- Weeks with fewer than 2 weighings have no error bar.
- The x axis is truncated to the observed range, so bars start at the left edge of
  the plot area rather than at zero.

## Pagination

`/weighings` shows the most recent `PAGE_SIZE` records per page. Pagination is
server-rendered links; htmx swaps the table partial in place.

## Testing

`tests/test_app.py` covers health, auth, validation, CRUD, pagination and
aggregation. Run with:

```sh
.venv/bin/python -m pytest -q
```
