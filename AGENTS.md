# Repository Guidelines

## Project Structure & Module Organization

- `jobs_manager/`: Django project (settings, URLs, ASGI/WSGI).
- `apps/<domain>/`: Feature apps (e.g., `job`, `quoting`, `timesheet`) with `models/`, `serializers/`, `views/`, `services/`, `tests/`, `schemas/`.
- `scripts/`: Ops/utilities (deployment, data tools, URL docs). NEVER edit `__init__.py`; run `python scripts/update_init.py`.
- `docs/`: Project docs and setup.
- `staticfiles/`, `mediafiles/`: Collected static and uploads.
- `.env`: Already configured locally (see `.env.example` for reference only).

## Build, Test, and Development Commands

- Install (one‑time): `poetry install --with dev` then activate your venv.
- Migrate DB: `python manage.py migrate`
- Run server: `python manage.py runserver`
- Tests: `pytest` (targeted: `pytest apps/job/tests/test_quote_modes.py -q`)
- Format: `black . && isort .`; Lint: `flake8`; Types: `mypy apps/ jobs_manager/`
- JS formatting: `npm run prettier-check` | `npm run prettier-format`

## Coding Style & Conventions

- Keep code short and direct; prefer fewer branches and helpers.
- Fail fast, handle unhappy paths first, no silent fallbacks. Validate inputs up front.
- Avoid try/except solely to customize messages. If you catch, you must persist and re‑raise:
  ```python
  from apps.workflow.services.error_persistence import persist_app_error
  try:
      do_work()
  except Exception as exc:
      persist_app_error(exc); raise
  ```
- Strict typing (MyPy strict), Black 88 + isort(black), Flake8/Ruff.
- Separation of concerns: views thin; business logic in `services/`; DRF I/O via `serializers/`.

## Testing Guidelines

- Pytest + Django; tests under `apps/*/tests/` as `test_*.py` with fixtures in `fixtures/`.
- Chat helpers available: `python run_chat_tests.py [--unit|--integration|--coverage]`.

## Commit & Pull Request Guidelines

- Conventional Commits (e.g., `feat(job): add KPI service`, `fix(quote-chat): guard None job`).
- PRs must use `.github/pull_request_template.md` and include: linked issue, evidence (tests/logs/screenshots), and passing local checks (`black`, `isort`, `flake8`, `mypy`, `pytest`). Note migrations/data impacts.

## Security & Config

- Never commit secrets. `.env` stays local.
- Settings: `jobs_manager/settings/` (local defaults suffice). Ensure DB creds match your local MySQL/MariaDB.
