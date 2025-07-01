# jobs_manager

A Django-based jobs/quotes/work management system customized for **Morris Sheetmetal** needs. Inspired by [django-timepiece](https://github.com/lincolnloop/django-timepiece), with added features such as:

- **CRM** with projects and businesses
- **User dashboards** with budgeted hours based on project contracts
- **Time sheets** (daily, weekly, monthly summaries)
- **Approved and invoiced** time sheet workflows
- **Monthly payroll** reporting (overtime, paid leave, vacation)
- **Project invoicing** with hourly summaries

For detailed documentation including business context, technical details, and setup instructions, see [docs/README.md](docs/README.md).

## Quick Start

### Requirements

- **Python 3.12+**
- **[Poetry](https://python-poetry.org/)** (manages Python dependencies)
- **Node.js + npm** (manages JavaScript dependencies)
- **MariaDB 11.5.2** (locally)

### Installation

See [docs/initial_install.md](docs/initial_install.md) for installation instructions.

### Starting

1. Launch the backend: python manage.py runserver
2. Launch the frontend: npm run dev

Note - both are documented properly in their respective folders (e.g. npm install)

## License

This project is proprietary to **Morris Sheetmetal**. For inquiries or usage permissions, contact the repository maintainer.
