# Technical Context: Jobs Manager

## Technologies Used
- **Backend Framework:** Django (Python)
- **Dependency Management:** Poetry
- **Database:** Likely MariaDB/MySQL (inferred from `mariadb-server` in visible files) or PostgreSQL/SQLite (common Django choices).
- **API Framework:** Django REST Framework (DRF)
- **Linting/Formatting:** `.flake8` and `mypy.ini` indicate the use of Flake8 for linting and MyPy for static type checking.
- **Testing:** `tox.ini` suggests Tox for running tests in multiple environments. `job/tests.py`, `quoting/tests.py`, `workflow/tests.py` indicate standard Django unit/integration tests.
- **Version Control:** `.gitignore` is present, implying Git.
- **Shell Scripting:** Various `.sh` scripts in the `scripts/` directory for deployment, database backups, etc.

## Development Setup
1. **Python Environment:** A Python version compatible with Django (likely 3.8+) is required. Poetry will manage virtual environments.
2. **Database Server:** A running instance of the chosen database (e.g., MariaDB/MySQL or PostgreSQL) is necessary.
3. **Environment Variables:** The `.env.example` file suggests that sensitive configurations (e.g., `SECRET_KEY`, database credentials) are loaded from environment variables. A `.env` file will need to be created based on `.env.example`.
4. **Dependencies:** All Python dependencies are managed by Poetry and listed in `pyproject.toml` and `poetry.lock`.

## Technical Constraints
- **Python Version:** Must adhere to the Python version specified in `pyproject.toml` (if any) or compatible with Django and its dependencies.
- **Database Compatibility:** The application is designed to work with a specific database backend.
- **Django Version:** Compatibility with the installed Django version is crucial.
- **External Services:** Potential reliance on external services like Xero for accounting integration.

## Dependencies
- **Python Packages:** Managed by Poetry.
- **System Dependencies:**
    - Database client libraries (e.g., `mysqlclient` for MySQL/MariaDB, `psycopg2` for PostgreSQL).
    - Potentially `gettext` for internationalization if used.
- **External APIs:** Xero API for accounting integration.
