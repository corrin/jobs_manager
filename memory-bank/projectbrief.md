# Project Brief: Jobs Manager

## Overview
This project appears to be a Django-based web application, likely for managing jobs, timesheets, quotes, and accounts. The file structure suggests a modular design with several Django apps (`accounts`, `job`, `quoting`, `timesheet`, `workflow`).

## Core Requirements
The immediate goal is to get the project running in a local development environment. This involves:
1. Setting up the Python environment.
2. Installing project dependencies.
3. Configuring the database.
4. Running database migrations.
5. Starting the Django development server.

## Initial Assumptions
- The project uses Poetry for dependency management, indicated by `pyproject.toml` and `poetry.lock`.
- Database configuration will be handled via Django settings, likely in `jobs_manager/settings/local.py`.
- A `.env` file is used for environment variables, as suggested by `.env.example`.

## Future Goals (Beyond initial run)
- Understand the core functionalities of the application.
- Explore the existing codebase for potential improvements or new features.
- Document key system patterns and technical context as they are discovered.
