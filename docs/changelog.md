# Changelog

## 2026-10-29

- Fixed "today" being computed in the server's UTC clock, which made the add
  weighing form default to yesterday and the home page's daily chart end a day
  early for most of the NZ morning. Added a `TIMEZONE` setting (default
  `Pacific/Auckland`) and a shared `app.dates.today()` used by weighings, charts
  and the eating report; added the `tzdata` dependency.
- Recording a weighing now redirects to the home page (`303`, or `HX-Redirect`
  for htmx submissions) instead of the weighings list.

## 2026-10-12

- Added Babel locale-aware date formatting with Australian English (`en_AU`) and
  `DD-MM-YYYY` defaults, applied to displayed dates and daily chart labels while
  preserving ISO 8601 storage and internal canonical values.
- Replaced free-text date fields with native HTML5 date pickers marked `en-AU`;
  they submit ISO dates, and server-side handlers still accept `DD-MM-YYYY`.

## 2026-10-08

- Reorganized the app into `security/v1`, `weightings/v1` and `health` packages;
  moved feature templates and htmx partials alongside their sub-apps while
  keeping shared page templates under `app/templates/`.
- Split weighing data operations from routes, moved the SQLite schema and chart
  aggregation into the weighing feature, and centralized templates, htmx checks,
  settings and logging setup.
- Switched environment configuration to Pydantic Settings and updated the
  container build to copy the new in-app template layout.
- Reorganized tests by sub-app and corrected the weekly standard-deviation test
  so it checks a week containing exactly two readings.
- Added the `eating` sub-app with user-scoped, effective-dated calorie/protein
  target CRUD, a date-based intake report scaffold, and food catalog/detail pages.
- Added natural-food nutrient entry and idempotent Woolworths product imports
  through Obscura CDP + Playwright; Beautiful Soup parses the allowlisted
  product-details nutrition table and stores normalized per-100-g/ml nutrients.
- Added Beautiful Soup and Playwright dependencies, `OBSCURA_CDP_URL`, eating
  schema initialization, navigation, documentation, and focused eating tests.
- Added an Obscura-captured Woolworths product-page fixture and regression test;
  adjusted nutrient label normalization to match the live table labels.
- Replaced SQLite DDL strings with SQLAlchemy models and introduced Alembic
  migrations that adopt existing tables, preserving existing weighing data.
- Removed configuration constant aliases; application code now reads values
  directly from `config.settings`.
- Added a restartable Obscura Docker Compose service on local CDP port 3000 and
  documented the endpoint for product scraping.
- Exercised the Vitasoy product URL through the Compose CDP server; fixed waiting
  for hidden nutrition tables and inferred ml basis from liquid pack sizes.
- Added a USDA FoodData Central Foundation Foods CSV importer for produce,
  nuts/seeds, eggs, and meat cuts; imported records retain their FDC source links.
- Thinned chart axis strokes and added dashed horizontal gridlines/separators.

## 2026-10-06

- Project scaffold: `app/`, `templates/`, `static/`, `docs/`, `k8s/`, `tests/`.
- Vendored pico.css, htmx and d3 into `static/vendor/`.
- SQLite schema, connection helper with WAL, and `get_db` dependency.
- Daily and weekly aggregation with sample standard deviation.
- Session-based single-user login, `require_user` dependency, and HTML/htmx-aware
  unauthenticated and 404 handlers.
- Routes: health, login/logout, home, add, paged list, inline edit, delete.
- Templates and htmx partials, plus `static/css/app.css` and `static/js/charts.js`.
- Fixed the weekly error-bar caps, which previously drew zero-length lines.
- Dockerfile, Kubernetes manifests with a local-disk PersistentVolume.
- pytest suite (8 tests) covering health, auth, validation, CRUD, pagination and
  aggregation; live smoke test against `uvicorn` verified health, redirects,
  htmx 401, static assets and chart data.
- Switched dependency management to `pyproject.toml` with a `dev` group and
  committed `uv.lock`; `requirements.txt` and `requirements-dev.txt` were removed.
  `.python-version` is pinned to 3.14 to match `requires-python`, the `.venv` was
  recreated on 3.14.7, and the Dockerfile now builds on `python:3.14-slim` with
  `uv sync --frozen`.
- Added `ruff` and `ty` to the `dev` group, and `B008` to the Ruff ignore list so
  FastAPI `Depends()` argument defaults stay idiomatic.
- `pytest` now sets `pythonpath`, so `uv run pytest` works from the repo root.
- `require_user` returns the session user instead of falling through; the
  `parse_fields` validation errors are chained with `raise ... from`; the Jinja
  globals assignment is annotated so `ty` accepts it; `SessionMiddleware` is now
  registered through `Middleware(...)` in the `FastAPI` constructor.
- Added a `justfile` with `ruff-check`, `ruff-format-check`, `ruff-format`,
  `type-check`, `test`, `install`, `run` and an aggregate `full-check` recipe.
- Added `docker-build`, `docker-run`, `docker-stop` and `docker-logs` just recipes
  (aliases `db`, `dr`, `ds`, `dl`), which build `fitness-tracker:latest`, run it
  detached with `.env` settings, mount `./data` at `/data`, force
  `DB_PATH=/data/fitness.db` and run as the host uid so the mounted volume stays
  writable. `docker-run` replaces an existing `fitness-tracker` container and
  `docker-stop` is idempotent. `APP_NAME` in `.env.example` is quoted because `just`'s dotenv parser
  rejects unquoted spaces.
- Linked the favicons in `static/favicons/` from `templates/base.html` (16 px and
  32 px icons, 96 px apple-touch icon), so every page now serves them.
- Added a `docker-push` just recipe (alias `dp`): builds, tags the image as
  `<namespace>/fitness-tracker:latest` and pushes it to Docker Hub. The namespace
  comes from `DOCKERHUB_USERNAME` and the access token from
  `DOCKERHUB_ACCESS_TOKEN`, falling back to the `.env` in the parent directory
  (`DOCKERHUB_TOKEN_FILE` overrides the path); without a token the existing
  `docker login` session is used. The token is piped to
  `docker login --password-stdin` so it never appears in the process list.
