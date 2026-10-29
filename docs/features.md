# Features

## Implemented

- Single-user login with signed session cookies.
- Home page with two charts:
  - daily bars for the last 7 days,
  - horizontal weekly bars for the last 8 ISO weeks, labelled `YYYY-Www`, with
    mean and sample standard deviation error bars.
- Add weighing form, prefilled with today's date (in the configured `TIMEZONE`)
  and the last recorded weight; saving returns to the home page.
- Weighings list, paged at 30 per page, most recent first.
- Inline edit and delete of a single weighing through htmx partials.
- Native HTML5 date pickers marked `en-AU`; controls submit ISO dates, while
  handlers also accept Australian `DD-MM-YYYY` input and store dates as ISO.
- Server-side weight validation (`0 < w < 500`) with error partials.
- Australian date localization using Babel (`en_AU`), displaying dates as
  `DD-MM-YYYY` outside the native date controls.
- htmx-friendly responses: partials for htmx requests, full pages otherwise,
  `HX-Redirect` for unauthenticated htmx requests.
- `/healthz` JSON health check reporting DB status and row count.
- Vendored static assets (pico.css, htmx, d3) so the app runs offline.
- Favicons from `static/favicons/`: 16 px and 32 px icons plus a 96 px
  apple-touch icon, linked from `app/templates/base.html`.
- Dockerfile and Kubernetes manifests with a local-disk PersistentVolume.
- pytest suite covering auth, validation, CRUD, pagination and aggregation.
- Versioned sub-app organization for security and weightings, with shared app
  dependencies and templates separated from feature-owned templates.
- SQLAlchemy models for weighing and eating data, with Alembic-managed schema
  migrations that preserve existing SQLite records.
- Eating report with per-user, effective-dated daily kcal and protein targets,
  target history CRUD, and date-based historical target lookup.
- Food catalog for natural-food entries and imported manufactured products, with
  searchable listings and full nutrient details per 100 g/ml.
- USDA FoodData Central Foundation Foods importer for produce, nuts/seeds, eggs,
  and meat cuts, retaining source links and normalizing nutrient mass units.
- Woolworths NZ product import using Obscura CDP, Playwright, and Beautiful Soup;
  accepted product URLs are restricted to the Woolworths product-details path.
- Woolworths product parsing is covered by a captured product-page fixture.
- Eating reports display target remaining values; consumed values currently show
  zero until meal recording is implemented.

## Not implemented

- CSRF tokens.
- Password hashing (the single user is read from env).
- Registration, multiple users, or multi-account login.
- Recording meals and calculating actual daily intake from meal ingredients.
- htmx-free fallback for inline edit (the `PUT`/`DELETE` actions need htmx).
- Chart tooltips, resize handling, and an option to start the axis at zero.
- Translation catalogs for localizing interface text; date localization is
  currently handled with Babel.
- CSV export / import, backups, and unit tests for the chart JS.
