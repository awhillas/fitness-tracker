# Fitness Tracking Web-App

@python-agents.md

## Stack

FastAPI + Jinja2, SQLite storage, htmx partials, pico.css,
d3.js charts, deployed with a Dockerfile and Kubernetes manifests (on k3s).

## Commands

```sh
just install            # uv sync
just run                # uv run uvicorn app.main:app --reload --port 8000
just docker-build       # docker build -t fitness-tracker:latest .
just docker-run         # docker run detached, .env settings, ./data mounted at /data
just docker-stop        # docker stop + rm
just docker-logs        # docker logs -f
just test               # uv run pytest -q
just ruff-check         # uv run ruff check .
just ruff-format-check  # uv run ruff format --check .
just ruff-format        # uv run ruff format .
just type-check         # uv run ty check .
just full-check         # lint + format + type check + tests
```

`just` recipes live in the `justfile`; add new checks there rather than ad-hoc commands.

`pip` is not available on this machine; use `uv`. Do not commit unless asked.

Dependencies live in `pyproject.toml` (production deps plus the `dev` group) and
`uv.lock` is committed. Add packages with `uv add <pkg>` or
`uv add --group dev <pkg>`, and run scripts with `uv run python`.

## Layout

- `app/config.py` — all configuration comes from env vars; add new settings here.
- `app/db.py` — schema, `connect()`, `init_db()`, `get_db()` dependency.
- `app/aggregates.py` — chart aggregation only; no HTTP concerns.
- `app/security.py` — login check, session user, `require_user`, `Unauthenticated`.
- `app/routers/` — one router per area; keep handlers thin.
- `templates/` — full pages; `templates/partials/` — htmx fragments.
- `static/vendor/` — vendored third-party assets, do not fetch assets at runtime.
- `k8s/` — one manifest per object.

## Conventions

- htmx requests (`HX-Request: true`) get partial templates; normal requests get full
  pages. Unauthenticated htmx requests get `401` with `HX-Redirect`; HTML requests
  get `303` to `/login`.
- Validation errors return `400` with an error partial, never a redirect.
- Charts read their data from a `data-series` JSON attribute rendered by Jinja; keep
  the JS free of data fetching.
- `pyproject.toml` pins exact versions; keep `uv.lock` committed and in sync.
- SQLite is single-writer: keep `replicas: 1` and `Recreate` in the deployment.

## Docs

Update `docs/` with every change: `specs.md` for behaviour, `features.md` for
implemented/not-implemented, `todos.md` for open work, `changelog.md` for dated
entries, `deployment.md` for run/deploy instructions. `CLAUDE.md` points here.
