# Deployment

## Local development

```sh
uv sync
cp .env.example .env
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

Python 3.14 is pinned in `.python-version` and `requires-python`. Dependencies come
from `pyproject.toml` and are locked in `uv.lock`.

The SQLite file defaults to `data/fitness.db`; override with `DB_PATH`.
Date presentation defaults to Australian English (`LOCALE=en_AU`) and
`DATE_FORMAT=dd-MM-yyyy` (`DD-MM-YYYY`); override these in `.env` if needed.
Date forms use native HTML5 pickers marked `en-AU` and submit ISO `YYYY-MM-DD`
values. Their visual format is determined by the browser; server-side handlers
also accept `DD-MM-YYYY` values.
Database schema changes are managed with Alembic. `just run` applies pending
migrations automatically. Create revisions with:

```sh
uv run alembic revision --autogenerate -m "describe schema change"
uv run alembic upgrade head
```

The USDA Foundation Foods importer downloads and caches the official April 2026
CSV archive under `data/imports/`, then upserts the selected natural-food records
by FDC source URL. Preview the input before writing it with:

```sh
uv run python -m app.eating.v1.import_usda --dry-run
uv run python -m app.eating.v1.import_usda
```

Woolworths product imports use the Obscura CDP server in `docker-compose.yaml`.
Start it with `docker compose up -d`; its CDP endpoint is
`ws://127.0.0.1:3000/devtools/browser` and is the default `OBSCURA_CDP_URL`. The
compose service uses host networking because the requested `serve` command binds
to loopback. Set `OBSCURA_CDP_URL` to a reachable endpoint if the app runs outside
the host process (for example, in a separate Docker or Kubernetes container).

## Docker

With `just` (`just docker-build`, `just docker-push`, `just docker-run`,
`just docker-stop`, `just docker-logs`), which reads settings from `.env` and
mounts `./data` at `/data`:

```sh
just docker-build
just docker-run
```

Raw equivalent:

```sh
docker build -t fitness-tracker:latest .
docker run -d --name fitness-tracker \
  -p 8000:8000 \
  -v ./data:/data \
  --user "$(id -u):$(id -g)" \
  --env-file .env \
  fitness-tracker:latest
```

### Pushing to Docker Hub

```sh
just docker-push    # alias: just dp
```

`just docker-push` builds, tags the image as `<namespace>/fitness-tracker:latest`
and pushes it. The namespace comes from `DOCKERHUB_USERNAME` (default `cpill`), and
the access token from `DOCKERHUB_ACCESS_TOKEN`, falling back to the `.env` in the
parent directory (`DOCKERHUB_TOKEN_FILE` overrides the path). If no token is found
the existing `docker login` session is used. The token is piped to
`docker login --password-stdin`, never passed as a command-line argument, and the
token file is not committed.

`just docker-run` replaces any existing `fitness-tracker` container, so re-running
it after a code change is safe; `just docker-stop` is idempotent.

`--user` is needed locally because the mounted `./data` directory is owned by the
host user, while the image runs as uid `10001`; in Kubernetes the equivalent is
`fsGroup: 10001`.

The image is built on `python:3.14-slim`, installs the locked production
dependencies with `uv sync --frozen --no-install-project --no-dev`, runs as uid
`10001`, applies Alembic migrations before starting, expects the database at
`/data/fitness.db`, and uses `/healthz` as its
healthcheck. `just docker-run` forces `DB_PATH=/data/fitness.db` so the `.env`
value used for local development does not point inside the container at a
relative path.

## Kubernetes

Manifests live in `k8s/`: `namespace.yaml`, `secret.yaml`, `pv.yaml`, `pvc.yaml`,
`deployment.yaml`, `service.yaml`.

1. Build and load the image into the cluster, e.g.:

   ```sh
   docker build -t fitness-tracker:latest .
   kind load docker-image fitness-tracker:latest
   ```

2. Edit `k8s/secret.yaml` (or create the secret out-of-band) and `k8s/pv.yaml`
   to point at the real host path and node hostname. If the cluster has a
   local-path StorageClass, delete `pv.yaml` and set `storageClassName` in
   `pvc.yaml` instead.

3. Apply:

   ```sh
   kubectl apply -f k8s/namespace.yaml
   kubectl apply -f k8s/secret.yaml
   kubectl apply -f k8s/pv.yaml
   kubectl apply -f k8s/pvc.yaml
   kubectl apply -f k8s/deployment.yaml
   kubectl apply -f k8s/service.yaml
   ```

4. Reach the app:

   ```sh
   kubectl -n fitness port-forward svc/fitness-tracker 8000:80
   ```

## Notes

- `replicas: 1` and `strategy: Recreate` are deliberate: SQLite is single-writer,
  so two pods sharing the same volume would corrupt data.
- The PVC must be `ReadWriteOnce` and bound to a single node; the `local` PV with
  `nodeAffinity` keeps the pod on the node that owns the disk.
- The container has a read-only root filesystem, so the only writable path is the
  mounted data volume (plus an `emptyDir` at `/tmp`).
- `fsGroup: 10001` makes the mounted directory writable by the container user.
- Back up by copying `fitness.db` or with `sqlite3 /data/fitness.db ".backup /backup/fitness.db"`.
