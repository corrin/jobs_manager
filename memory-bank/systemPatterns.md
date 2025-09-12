# System Patterns: Jobs Manager

## Architecture Overview
The project is a Django monolithic application, structured into several distinct Django apps. This indicates a clear separation of concerns, with each app handling a specific domain (e.g., `accounts`, `job`, `quoting`, `timesheet`, `workflow`).

## Key Technical Decisions
- **Django Framework:** The core of the application is built on Django, leveraging its ORM, MVT (Model-View-Template) architecture, and built-in features for rapid development.
- **Django REST Framework (DRF):** The presence of `serializers.py` files in various apps (`accounts`, `job`, `timesheet`, `workflow`) suggests the use of DRF for building RESTful APIs, likely for frontend interactions or integrations.
- **Database:** While not explicitly stated, Django projects typically use PostgreSQL, MySQL, or SQLite. The `mariadb-server` in the visible files might indicate a preference for MariaDB/MySQL.
- **Dependency Management:** Poetry is used for managing Python dependencies, ensuring reproducible environments.
- **Historical Data (Django Simple History):** The `HistoricalJob` and `HistoricalStaff` models in `job/migrations` and `accounts/migrations` respectively, suggest the use of a package like `django-simple-history` for tracking changes to model instances.
- **Static Files & Templates:** Standard Django practices for serving static assets and rendering HTML templates are in place.

## Design Patterns in Use
- **MVC/MVT:** Django's inherent architecture follows the Model-View-Template pattern.
    - **Models:** Define the data structure and business logic (`job/models/`, `accounts/models.py`, etc.).
    - **Views:** Handle request processing and interact with models (`job/views/`, `accounts/views/`, etc.).
    - **Templates:** Render the user interface (`job/templates/`, `accounts/templates/`, etc.).
- **Service Layer:** The `job/services/` directory indicates a service layer pattern, abstracting complex business logic from views and models, promoting reusability and testability.
- **Enums:** The `job/enums.py` and `workflow/enums.py` files suggest the use of Python Enums for defining fixed sets of choices, improving code readability and maintainability.
- **Management Commands:** Custom Django management commands (`accounts/management/commands/`, `job/management/commands/`, `quoting/management/commands/`) are used for administrative tasks, data imports, or background processes.

## Component Relationships
- **`accounts`:** Manages user authentication, staff, and client accounts. Likely provides authentication for other apps.
- **`job`:** Core application for managing jobs, material entries, job parts, and related files. Depends on `accounts` for staff assignments.
- **`quoting`:** Handles the creation and management of quotes. Likely interacts with `job` for linking quotes to jobs.
- **`timesheet`:** Manages time entries for staff. Depends on `accounts` for staff information and potentially `job` for linking time to specific jobs.
- **`workflow`:** Appears to provide common utilities, middleware, context processors, and potentially defines overall application flow or shared components.
- **`jobs_manager` (Project Root):** Contains global settings, URL routing, and WSGI/ASGI configurations.
