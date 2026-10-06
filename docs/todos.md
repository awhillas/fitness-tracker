# Todos

- [ ] Add CSRF tokens to login and write forms.
- [ ] Hash the password instead of comparing against an env value.
- [ ] Rate-limit `POST /login`.
- [ ] Non-JS fallback for inline edit (`PUT`/`DELETE` currently require htmx).
- [ ] Chart tooltips and resize handling.
- [ ] Option to start the weekly chart axis at zero instead of the observed range.
- [ ] CSV export of the weighings table.
- [ ] Backup job for the SQLite file.
- [ ] Tests for the htmx partial responses and the accept-header behaviour of the
      unauthenticated handler.
- [x] Add a `justfile` with `lint`, `type-check`, `test`, `build` and `check`
      recipes (`ruff` and `ty` are now in the `dev` group).
- [ ] Validate the `k8s/` manifests in CI using the `pyyaml` dev dependency.
