# ---------------------------------------------------------------------------- #
#                                   SETTINGS                                   #
# ---------------------------------------------------------------------------- #

set shell := ["bash", "-euo", "pipefail", "-c"]
set dotenv-load
set default-list := true

# ---------------------------------------------------------------------------- #
#                                 DEPENDENCIES                                 #
# ---------------------------------------------------------------------------- #

# UV: https://github.com/astral-sh/uv
uv := require("uv")

# Just: https://just.systems
just := require("just")

# Docker: https://docs.docker.com
docker := require("docker")


# ---------------------------------------------------------------------------- #
#                                   CONSTANTS                                  #
# ---------------------------------------------------------------------------- #

IMAGE := "fitness-tracker"
CONTAINER := "fitness-tracker"
PORT := "8000"
ROOT := justfile_dir()
DOCKERHUB_USER := env("DOCKERHUB_USERNAME", "cpill")
TOKEN_FILE := env("DOCKERHUB_TOKEN_FILE", justfile_dir() + "/../.env")
REMOTE_IMAGE := DOCKERHUB_USER + "/" + IMAGE


# ---------------------------------------------------------------------------- #
#                                   COMMANDS                                   #
# ---------------------------------------------------------------------------- #



# Install dependencies
install *args:
    uv sync {{ args }}
alias i := install

# Run the dev server
run *args:
    uv run alembic upgrade head
    uv run uvicorn app.main:app --reload --port 8000 {{ args }}


# ---------------------------------------------------------------------------- #
#                                   CHECKS                                     #
# ---------------------------------------------------------------------------- #

# Lint Python files
[group("checks")]
ruff-check:
    uv run ruff check .
alias rc := ruff-check

# Check Python formatting
[group("checks")]
ruff-format-check:
    uv run ruff format --check .
alias rfc := ruff-format-check

# Format Python files
[group("checks")]
ruff-format:
    uv run ruff format .
alias rw := ruff-format

# Type check Python files
[group("checks")]
type-check:
    uv run ty check .
alias tc := type-check

# Run all checks
[group("checks")]
@full-check:
    just _run-with-status ruff-check
    just _run-with-status ruff-format-check
    just _run-with-status type-check
    just _run-with-status test
    echo ""
    echo -e '{{ GREEN }}All checks passed!{{ NORMAL }}'
alias fc := full-check


# ---------------------------------------------------------------------------- #
#                                    TESTS                                     #
# ---------------------------------------------------------------------------- #

# Run the test suite
[group("tests")]
test *args:
    uv run pytest -q {{ args }}
alias t := test


# ---------------------------------------------------------------------------- #
#                                    DOCKER                                    #
# ---------------------------------------------------------------------------- #

# Build the container image
[group("docker")]
docker-build *args:
    docker build -t {{ IMAGE }}:latest {{ args }} {{ if args == "" { "." } else { "" } }}
alias db := docker-build

# Build, tag with the Docker Hub namespace and push
[group("docker")]
docker-push *args:
    just docker-build
    just _docker-login
    docker tag {{ IMAGE }}:latest {{ REMOTE_IMAGE }}:latest
    docker push {{ REMOTE_IMAGE }}:latest {{ args }}
alias dp := docker-push

# Run the container, reading settings from .env (replaces an existing one)
[group("docker")]
docker-run *args:
    [ -f .env ] || { echo -e '{{ RED }}.env is missing: copy .env.example and set SECRET_KEY, USERNAME and PASSWORD.{{ NORMAL }}'; exit 1; }
    docker rm -f {{ CONTAINER }} >/dev/null 2>&1 || true
    docker run -d --name {{ CONTAINER }} \
        -p {{ PORT }}:8000 \
        -v "{{ ROOT }}/data:/data" \
        --user "$(id -u):$(id -g)" \
        --env-file .env \
        -e DB_PATH=/data/fitness.db \
        {{ args }} \
        {{ IMAGE }}:latest
alias dr := docker-run

# Stop and remove the container
[group("docker")]
docker-stop:
    docker stop {{ CONTAINER }} 2>/dev/null || true
    docker rm {{ CONTAINER }} 2>/dev/null || true
alias ds := docker-stop

# Follow container logs
[group("docker")]
docker-logs *args:
    docker logs -f {{ CONTAINER }} {{ args }}
alias dl := docker-logs


# ---------------------------------------------------------------------------- #
#                             INTERNAL HELPERS                                 #
# ---------------------------------------------------------------------------- #

[group("internal")]
[private]
@_run-with-status recipe *args:
    echo ""
    echo -e '{{ CYAN }}→ Running {{ recipe }}...{{ NORMAL }}'
    just {{ recipe }} {{ args }}
    echo -e '{{ GREEN }}✓ {{ recipe }} completed{{ NORMAL }}'
alias rws := _run-with-status

[group("internal")]
[private]
@_docker-login:
    token="${DOCKERHUB_ACCESS_TOKEN:-$(sed -n 's/^DOCKERHUB_ACCESS_TOKEN=//p' '{{ TOKEN_FILE }}' 2>/dev/null)}"; if [ -z "$token" ]; then echo -e '{{ YELLOW }}No DOCKERHUB_ACCESS_TOKEN: using the existing docker login.{{ NORMAL }}'; else printf '%s' "$token" | docker login -u {{ DOCKERHUB_USER }} --password-stdin; fi
