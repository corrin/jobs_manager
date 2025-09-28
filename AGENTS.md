# Repository Guidelines

## Project Structure & Module Organization
- `jobs_manager/` contains Django settings, URLs, ASGI/WSGI entrypoints; adjust environment knobs here.
- Feature apps live in `apps/<domain>/` with `models/`, `serializers/`, `views/`, `services/`, `tests/`, and `schemas/` folders mirrored per domain.
- Ops tools reside in `scripts/`; never edit `__init__.py` manually—run `python scripts/update_init.py` after adding utilities.
- Static assets and uploads are collected under `staticfiles/` and `mediafiles/`; docs sit in `docs/`.

## Build, Test, and Development Commands
- `poetry install --with dev` installs all Python dependencies and tooling.
- `python manage.py migrate` applies schema changes to the local database.
- `python manage.py runserver` starts the Django development server on the default host:port.
- `pytest` runs the full test suite; target with e.g. `pytest apps/job/tests/test_quote_modes.py -q` when iterating.

## Coding Style & Naming Conventions
- Format Python with `black .` (line length 88) followed by `isort .` using the Black profile.
- Enforce linting via `flake8` and strict typing with `mypy apps/ jobs_manager/`.
- Keep modules short, fail fast, and push business logic into `services/`; serializers handle I/O only.
- Follow Django/DRF naming: snake_case for functions, CamelCase for classes, and keep API routes descriptive.

## Testing Guidelines
- Use Pytest with Django fixtures in `apps/*/tests/fixtures/`; name tests `test_*.py`.
- Prefer unit tests near the feature app; add integration coverage through `run_chat_tests.py --integration` if relevant.
- Ensure new logic ships with assertions covering success and edge cases; document regressions with regression tests.

## Commit & Pull Request Guidelines
- Use Conventional Commits, e.g. `feat(job): add KPI service` or `fix(quote-chat): guard None job`.
- PRs must follow `.github/pull_request_template.md`, link issues, and include evidence (logs, screenshots, or test output).
- Confirm `black`, `isort`, `flake8`, `mypy`, and `pytest` pass before raising a PR; note any migrations or data impacts explicitly.

## Security & Configuration Tips
- Do not commit secrets; `.env` is local-only and mirrors `.env.example` for reference.
- Verify database credentials in `jobs_manager/settings/` match your local MariaDB/MySQL.
- Network access is restricted; coordinate any external dependency updates with the maintainers.
