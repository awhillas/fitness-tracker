# Todos

- [ ] Add CSRF tokens to login and write forms.
- [ ] Hash the password instead of comparing against an env value.
- [ ] Rate-limit `POST /login`.
- [ ] Non-JS fallback for inline edit (`PUT`/`DELETE` currently require htmx).
- [ ] Chart tooltips and resize handling.
- [ ] Option to start the weekly chart axis at zero instead of the observed range.
- [ ] CSV export of the weighings table.
- [ ] Backup job for the SQLite file.
- [ ] Add meal and ingredient recording so eating reports can calculate consumed
      kcal and protein from food records.
- [x] Seed natural foods from USDA FoodData Central Foundation Foods.
- [ ] Refresh the USDA Foundation Foods snapshot when a newer release is available.
- [x] Verify product extraction against a live Woolworths product page through
      the Obscura CDP service.
- [ ] Tests for the htmx partial responses and the accept-header behaviour of the
      unauthenticated handler.
- [x] Add a `justfile` with `lint`, `type-check`, `test`, `build` and `check`
      recipes (`ruff` and `ty` are now in the `dev` group).
- [ ] Validate the `k8s/` manifests in CI using the `pyyaml` dev dependency.
- [ ] Add gettext translation catalogs if the interface needs translated text;
      the current localization support covers date display and Australian-form
      date input parsing.
