## Python Development 

Always use the latest version of python possible.

- `uv` for dependency management. Use `pyporject.toml` to track dev and production deps as well as settings for testing and linting.
- `ty` for type checking for everything, use type hints where possible.
- `ruff` for linting
- `Dockerfile` - for deployment
- `pytest` 
- `pydantic` for type models.
- Justfile to keep commands like: lint, type-check, test, build (Docker image) check (run all checks)

## Documentation

There should be a `docs/` dir and it should contain:

- index.md - link all the following docs together.
- `specs.md` - overall specs/goals of the project and how they relate to the features.
- `features.md` - list of product features.
- `todo.md` - todo list for persistent memory of what is needed between sessions.
- `user-guide.md` - simple explanation of how to use each feature.
- `log/` - change log with a file for each change after initial development is done. File names follow: `YYYY-MM-DD-<change slug>.md`

## General coding workflow/practice

This workflow should be applied for every code change to maintain code quality and consistency.

1. Research the planned changes. Web search for trickier problems. Make a checklist and get it approved before making changes.
2. Make changes as per user requests.
3. Red/Green TDD: write the signature with an empty body, write tests for new functionality, and watch them fail before implementing the feature; then implement it and rerun the tests. All test should have a one sentence comment on why the test exists.
4. Lint changes using `ruff` and type checking using `ty`
5. Review changed files according to SOLID/DRY principles and framework best practices. Also look for opportunities to reduce/simplify the amount of code.
6. Refactor according to the outcome of the code review. Try to breakdown longer files, longer than 1000 lines, into smaller files. A bug fix doesn't need surrounding cleanup; a one-shot doesn't need a helper. Don't add cross-cutting helpers before there's a second caller.
7. Run tests after review-driven changes to check functionality is intact and fix problems. Prefer writing tests _without_ mocking.
8. Create or update docs as needed to reflect architecture changes and functional specs. Keep a change log as well.
9. Never `git push` unless specifically instructed to.

There are many ways to structure a project, but the best structure is one that is consistent, straightforward, and free of surprises.

**Correct the spec when the implementation contradicts it.** The spec was written before the code; where building something proved it wrong, fix the spec and say why — a dated note beats a silent overwrite.

## Testing

Tests are using `pytest` and are in `tests/` directory or `packages.
Every test should have single sentence comment on why/what the test is about.

# General rules

- Always run Python scripts with `uv run python` instead of `python` directly.
- **Imports**: Group imports using ruff/isort config in pyproject.toml
- **Naming**: snake_case for variables/functions, PascalCase for classes
- **Types**: Use Python type hints for all functions and return values. Use pydantic for type models
- **Testing**: pytest fixtures for common test setup, use parametrize for edge cases, avoid mocking where possible. Do not mock LLM calls.
