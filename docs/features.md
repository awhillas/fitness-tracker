# Features

## Implemented

- Single-user login with signed session cookies.
- Home page with two charts:
  - daily bars for the last 7 days,
  - horizontal weekly bars for the last 8 ISO weeks, labelled `YYYY-Www`, with
    mean and sample standard deviation error bars.
- Add weighing form, prefilled with today's date and the last recorded weight.
- Weighings list, paged at 30 per page, most recent first.
- Inline edit and delete of a single weighing through htmx partials.
- Server-side validation (ISO date, weight `0 < w < 500`) with error partials.
- htmx-friendly responses: partials for htmx requests, full pages otherwise,
  `HX-Redirect` for unauthenticated htmx requests.
- `/healthz` JSON health check reporting DB status and row count.
- Vendored static assets (pico.css, htmx, d3) so the app runs offline.
- Favicons from `static/favicons/`: 16 px and 32 px icons plus a 96 px
  apple-touch icon, linked from `templates/base.html`.
- Dockerfile and Kubernetes manifests with a local-disk PersistentVolume.
- pytest suite covering auth, validation, CRUD, pagination and aggregation.

## Not implemented

- CSRF tokens.
- Password hashing (the single user is read from env).
- Registration, multiple users, or per-user data.
- htmx-free fallback for inline edit (the `PUT`/`DELETE` actions need htmx).
- Chart tooltips, resize handling, and an option to start the axis at zero.
- CSV export / import, backups, and unit tests for the chart JS.
