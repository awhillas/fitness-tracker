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
```
app/
├── security/             # sub-app
│   ├── __init__.py       # export only what needs to be imported in main.py
│   └── v1                # versioning
│       ├── __init__.py
│       ├── templates/    # per-sub-app templates, not shared across sub-apps 
│       |   └── partrials/ # htmx partials for fragments of pages
│       ├── routes.py     # HTTP routes and handlers, no business logic, very thin
│       ├── services.py   # business logic, the meat of the app, DB access, etc
│       ├── schema.py     # DB schema and ORM models
│       └── types.py      # Pydantic types for request/response validation
├── weightings/           # sub-app
│   ├── __init__.py
│   └── v1
│       ├── __init__.py
│       ├── templates/    # per-sub-app templates, not shared across sub-apps 
│       |   └── partrials/ # htmx partials for fragments of pages
│       ├── routes.py
│       ├── services.py
│       ├── aggregates.py # chart aggregation only; no HTTP concerns.
│       ├── schema.py
│       └── types.py
├── health                # sub-app sort of, not versioned, just a single route
│   ├── __init__.py
│   └── routes.py
├── templates/
│   ├── base.html         # base template for all pages
│   ├── error.html        # error page template
│   ├── 404.html          # 404 page template
│   └── partials/         # htmx partials for fragments of pages
├── __init__.py
├── config.py             # app configuration from env vars using pydantic BaseSettings
├── dependencies.py       # common code that cuts across sub-apps (e.g. logging, security, templating)
├── db.py                 # shared connect(), init_db(), get_db() dependency
├── logging_config.py     # logging config, intergrate with logfire etc
└──  main.py              # main entry point, imports sub-apps and routers, sets up logging, etc. Keep minimal.
k8s/                      # Kubernetes manifests for deployment, service, ingress, etc.
docs/                     # documentation for the app, specs, features, todos, changelog, deployment instructions
static/                   # static assets (CSS, JS, images, etc.)
data/                     # SQLite database file and other data files, ignired by git, mounted as a volume in Docker/Kubernetes
tests/                    # unit and integration tests for the app, organized by sub-apps.
```
The general idea is to keep each sub-app self-contained, and organised around the data that they use/relate to with some global stuff at the top level. The `routes.py` files are thin, and delegate to `services.py` for the business logic. The `schema.py` files define the database schema and ORM models, while the `types.py` files define Pydantic types for request/response validation.

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
