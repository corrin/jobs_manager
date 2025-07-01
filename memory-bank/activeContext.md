# Active Context: Jobs Manager

## Current Work Focus
The primary focus is to get the "Jobs Manager" Django project running in a local development environment. This involves setting up the Python environment, installing dependencies, configuring the database, running migrations, and starting the development server.

## Recent Changes
- Initial Memory Bank files (`projectbrief.md`, `productContext.md`, `systemPatterns.md`, `techContext.md`) have been created to establish foundational project understanding.

## Next Steps
1. **Environment Setup:**
    - Verify Python version compatibility.
    - Install Poetry if not already present.
    - Install project dependencies using Poetry.
2. **Database Configuration:**
    - Create a `.env` file based on `.env.example` and configure database settings (e.g., for MariaDB/MySQL or SQLite).
    - Ensure the database server is running (if using an external DB like MariaDB/MySQL).
3. **Database Migrations:**
    - Run Django database migrations to set up the schema.
4. **Run Development Server:**
    - Start the Django development server.
5. **Initial Exploration:**
    - Access the application in a web browser.
    - Attempt to create a superuser for administrative access.

## Active Decisions and Considerations
- **Database Choice:** The presence of `mariadb-server` suggests MariaDB/MySQL, but SQLite is often simpler for initial local setup. I will prioritize setting up with SQLite first for simplicity, and if issues arise or a specific database is required, I will switch to MariaDB/MySQL.
- **Python Version:** Need to check `pyproject.toml` for the exact Python version requirement.
- **Dependency Installation:** Poetry will handle this, but potential issues with system dependencies (e.g., database client libraries) might arise.
