# Specs

## Purpose

A small single-user web app for recording body weight, managing daily nutrition
targets, and browsing food nutrient information.

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
- Dates remain ISO 8601 in storage. Forms use native HTML date controls that
  submit `YYYY-MM-DD`; the page locale is Australian English (`en_AU`), and the
  browser determines the date control's visual presentation. Handlers also accept
  `DD-MM-YYYY` values. Other rendered dates use the configured locale and pattern,
  defaulting to `en_AU` and `DD-MM-YYYY`.
- `weight_kg` must parse as a float and be in the range `0 < w < 500`, stored
  rounded to 2 decimal places.
- SQLite runs in WAL mode with foreign keys enabled.

Eating data is stored in `app/eating/v1/schema.py`:

- Daily calorie and protein targets belong to the signed-in username and have an
  effective `start_date`. For any report date, the latest target whose start date
  is on or before that date applies; historical target rows remain available.
- Food records distinguish natural foods from manufactured products. Nutrients
  are stored per 100 g or 100 ml, with energy in kcal and nutrient mass in grams.
  The product source URL is unique, so re-importing a product updates its row.
- Natural-food starter records are imported from USDA FoodData Central Foundation
  Foods (April 2026 CSV release), with FDC source links and nutrients standardized
  to per 100 g. The [USDA FDC downloads](https://fdc.nal.usda.gov/download-datasets/)
  are public domain under [CC0 1.0](https://fdc.nal.usda.gov/api-guide/); attribution
  is retained through source links. The [New Zealand FOODfiles terms of use](https://foodcomposition.co.nz/terms/)
  prohibit modifying their data, so they need permission before unit-normalized
  import.
- Meal entries are not implemented yet; the eating report currently displays
  zero consumed values as a scaffold.

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
| `LOCALE` | `en_AU` | Babel locale used for localized dates |
| `DATE_FORMAT` | `dd-MM-yyyy` | Babel date pattern; displays as `DD-MM-YYYY` |
| `TIMEZONE` | `Pacific/Auckland` | IANA zone that defines "today" for form defaults, chart windows and the eating report |
| `OBSCURA_CDP_URL` | `ws://127.0.0.1:3000/devtools/browser` | Obscura CDP endpoint for product imports |

## Application layout

Feature modules are organized as versioned sub-apps under `app/`: authentication
is in `app/security/v1/`, weighing routes and services are in
`app/weightings/v1/`, and the health endpoint is in `app/health/`. Shared
templates live in `app/templates/`; feature templates and htmx partials live
beside their sub-app. SQLite access remains in `app/db.py`, with the weighing
table and eating models defined with SQLAlchemy in their sub-app `schema.py`
files. Alembic revisions under `migrations/` manage database changes. Eating
targets, foods, and product scraping live in `app/eating/v1/`.
The repeatable USDA seed importer is `app/eating/v1/import_usda.py`.

## Routes

| Method | Path | Behaviour |
| --- | --- | --- |
| `GET` | `/healthz` | JSON health check, no auth |
| `GET` | `/login` | login form |
| `POST` | `/login` | validates credentials, sets session, `303` to `/`; `401` re-renders form on failure |
| `POST` | `/logout` | clears session, redirects to `/login` |
| `GET` | `/` | home page with daily and weekly charts |
| `GET` | `/weighings` | paged list, most recent first; htmx requests get the table partial only |
| `GET` | `/weighings/new` | add form, prefilled with today (in `TIMEZONE`) and the most recent weighing's weight |
| `POST` | `/weighings` | create weighing, `303` to `/` (htmx: `204` with `HX-Redirect: /`); `400` with error partial on invalid input |
| `GET` | `/weighings/{id}/edit` | htmx inline edit partial |
| `PUT` | `/weighings/{id}` | update weighing |
| `DELETE` | `/weighings/{id}` | delete weighing, `204` |
| `GET` | `/eating` | report for today, or `?day=DD-MM-YYYY` (ISO dates are also accepted), with effective targets and consumed totals |
| `GET` | `/eating/targets` | list historical targets and create a target |
| `POST` | `/eating/targets` | create a user-specific target effective from its start date |
| `GET` | `/eating/targets/{id}/edit` | edit a historical target |
| `POST` | `/eating/targets/{id}/edit` | update a target |
| `POST` | `/eating/targets/{id}/delete` | delete a target |
| `GET` | `/eating/foods` | search and browse food/product nutrient records |
| `GET` | `/eating/foods/{id}` | show all stored nutrient details |
| `GET` | `/eating/foods/new` | natural-food entry form |
| `POST` | `/eating/foods` | create a natural-food nutrient record |
| `POST` | `/eating/foods/import` | import an allowlisted Woolworths product URL through Obscura |

Everything except `/login` and `/healthz` requires a session. Unauthenticated HTML
requests redirect to `/login`; htmx requests get `401` with an `HX-Redirect` header.

Woolworths imports only accept HTTPS URLs on `www.woolworths.co.nz` under
`/shop/product-details/`. The app connects to Obscura over its CDP endpoint using
Playwright, then Beautiful Soup removes script/style elements and extracts the
product name and per-100-g/ml nutrition table. Nutrient mass values are normalized
to grams, energy to kcal, and all table nutrients are retained for the detail page.

## Charts

### Daily chart

- Last `DAILY_DAYS` days ending today in `TIMEZONE`, oldest on the left.
- One vertical bar per day, height is the mean weight for that day.
- Days with no weighing render a faded placeholder bar and are skipped for the
  error bar.
- Thin axes and dashed horizontal value gridlines are used for readability.

### Weekly chart

- Last `WEEKLY_WEEKS` ISO weeks, oldest at the top.
- Horizontal bars, y axis is the `YYYY-Www` ISO week label.
- Bar length is the weekly mean; an error bar spans `mean ± sample standard
  deviation` of that week's weighings.
- Weeks with fewer than 2 weighings have no error bar.
- The x axis is truncated to the observed range, so bars start at the left edge of
  the plot area rather than at zero.
- Thin axes and dashed horizontal separators distinguish the weekly bars.

## Pagination

`/weighings` shows the most recent `PAGE_SIZE` records per page. Pagination is
server-rendered links; htmx swaps the table partial in place.

## Testing

The sub-app suites under `tests/` cover health, auth, validation, CRUD,
pagination and aggregation. Run with:

```sh
.venv/bin/python -m pytest -q
```
