# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Environment Setup
```bash
# Activate Python environment
poetry shell

# Install dependencies
poetry install
npm install

# Start development server
python manage.py runserver 0.0.0.0:8000

# Start with ngrok tunnel (for Xero integration)
python manage.py runserver_with_ngrok
```

### Code Quality
```bash
# Format code
tox -e format
npm run prettier-format

# Lint code
tox -e lint

# Type checking
tox -e typecheck

# Run all quality checks
tox
```

### Database Operations
```bash
# Apply migrations
python manage.py migrate

# Create database fixtures
python manage.py loaddata apps/workflow/fixtures/company_defaults.json

# then EITHER load demo data

python manage.py loaddata apps/workflow/fixtures/initial_data.json
python manage.py create_shop_jobs
# OR backport from prod
python manage.py backport_data_restore restore/prod_backup_20250614_095927.json.gz
# You MUST do one of these.

# Validate data integrity
python manage.py validate_jobs
```

### Xero Integration
```bash
# Setup Xero for development (finds Demo Company and syncs)
python manage.py setup_dev_xero

# Setup Xero tenant ID only (skip initial sync)
python manage.py setup_dev_xero --skip-sync

# Start Xero synchronization manually
python manage.py start_xero_sync

# Get Xero tenant ID for setup
python manage.py get_xero_tenant_id
```

## Architecture Overview

### Core Application Purpose
Django-based job/project management system for custom metal fabrication business (Morris Sheetmetal). Digitizes a 50+ year paper-based workflow from quote generation to job completion and invoicing.

### Django Apps Architecture

**`workflow`** - Central hub and base functionality
- Base models (CompanyDefaults, XeroAccount, XeroToken, AIProvider)
- Xero accounting integration and synchronization
- Authentication middleware and base templates
- URL routing coordination

**`job`** - Core job lifecycle management
- Job model with Kanban-style status tracking (Quoting → In Progress → Completed → Archived)
- JobPricing for estimates/quotes with revision tracking
- JobFile for document attachments
- JobEvent for comprehensive audit trails
- MaterialEntry/AdjustmentEntry for job costing

**`accounts`** - User management with custom Staff model
- Extends AbstractBaseUser for business-specific requirements
- Password strength validation (minimum 10 characters)
- Role-based permissions and authentication

**`client`** - Customer relationship management
- Client model with bidirectional Xero contact synchronization
- Contact person and communication tracking

**`timesheet`** - Time tracking and billing
- TimeEntry linked to JobPricing for accurate job costing
- Billable vs non-billable classification
- Daily/weekly timesheet interfaces
- Wage rate and charge-out rate management

**`purchasing`** - Purchase order and inventory management
- PurchaseOrder with Xero integration for accounting sync
- Stock management with source tracking
- Supplier quote processing and delivery receipts

**`accounting`** - Financial reporting and KPI tracking
- KPI calendar views and financial analytics
- Invoice generation via Xero integration

**`quoting`** - Quote generation and supplier pricing
- Supplier price list management
- AI-powered price extraction (Gemini integration)
- Web scraping for pricing updates

### Frontend Technology Stack

**Core Libraries:**
- Bootstrap 5.3.3 for responsive UI
- jQuery 3.7.1 for DOM manipulation
- ag-Grid Community 33.0.2 for advanced data tables
- FullCalendar 6.1.17 for scheduling interfaces
- Quill 2.0.3 for rich text editing
- Chart.js 4.4.9 & Highcharts 12.0.2 for data visualization

**JavaScript Architecture:**
- Modular ES6 with feature-specific modules
- AJAX-heavy for real-time updates
- Environment-aware debugging via `env.js`
- Component-based architecture (e.g., `kanban.js`, `timesheet_entry/`)

### Database Design Patterns

**Key Relationships:**
```
Job → JobPricing (1:many) → TimeEntry/MaterialEntry (1:many)
Staff → TimeEntry (1:many)
Client → Job (1:many)
PurchaseOrder → PurchaseOrderLine → Stock → MaterialEntry
```

**Design Patterns:**
- UUID primary keys throughout for security
- SimpleHistory for audit trails on critical models
- Soft deletes where appropriate
- Bidirectional Xero synchronization with conflict resolution

## Development Workflow

### Code Style and Quality
- **Black** (line length 88) and **isort** for Python formatting
- **Prettier** for JavaScript formatting with pre-commit hooks
- **MyPy** with strict configuration for type safety
- **Flake8** and **Pylint** for linting with Django-specific rules

### Defensive Programming Principles
- **TRUST THE DATA MODEL**: Never use `DoesNotExist` exception handling to mask data integrity issues
- **FAIL EARLY**: Let the system fail loudly when data references are broken rather than silently continuing
- **NO SILENT FAILURES**: Defensive programming means stopping bugs early, not letting them continue
- Data integrity violations should cause immediate failure to surface the root problem
- If foreign key references are missing, the backup/restore process or data model has a bug that must be fixed
- FOCUS ON THE UNHAPPY CASE.  If it is appropriate to do error handling then do if <bad_case>: <handle_bad_case>.  NEVER write if <good case> to silently hide bad cases.

### Testing Approach
Limited test coverage currently - focus on manual testing and data validation commands like `validate_jobs`.

### Integration Architecture
- **Xero API**: Bidirectional sync for contacts, invoices, purchase orders
- **Dropbox**: File storage for job documents
- **Gemini AI**: Price list extraction and processing
- **APScheduler**: Background task scheduling

## Business Context

### Job Lifecycle Workflow
1. **Quoting**: Fast quote generation with material/labor estimates
2. **Job Creation**: Convert accepted quotes to jobs with status tracking
3. **Production**: Kanban board for visual workflow management
4. **Time Tracking**: Daily time entry with billable classification
5. **Material Management**: Track usage and costs from purchase orders
6. **Completion**: Generate invoices via Xero integration

### Key Business Rules
- Jobs progress through defined states with audit trails
- All financial data synchronizes with Xero for accounting
- Time entries must be classified as billable/non-billable
- Material costs track back to source purchase orders
- File attachments support workshop job sheets

### Performance Considerations
- ag-Grid for handling large datasets efficiently
- AJAX patterns minimize full page reloads
- Background scheduling for Xero synchronization
- Database indexes on frequently queried UUID fields

## Security and Authentication

### Authentication Model
- Custom Staff model extending AbstractBaseUser
- Password strength validation enforced
- JWT token support available
- Login required middleware with specific exemptions

### Data Protection
- Environment variables for sensitive credentials
- CSRF protection with API exemptions
- File upload restrictions and validation
- Xero token encryption and refresh handling

## Environment Configuration

### Required Environment Variables
- `DATABASE_URL`: MariaDB connection string
- `XERO_CLIENT_ID` / `XERO_CLIENT_SECRET`: Xero API credentials
- `NGROK_DOMAIN`: For development Xero callbacks
- `DJANGO_SECRET_KEY`: Django security key

### Settings Structure
- `settings/base.py`: Shared configuration
- `settings/local.py`: Development with debug tools
- `settings/production_like.py`: Production configuration

## Future Frontend Development

### Vue.js Frontend Project (`../jobs_manager_front/`)
A separate Vue.js frontend application is in development as a modern replacement for the Django templates:

**Technology Stack:**
- **Vue 3** with TypeScript and Composition API
- **Vite** for build tooling and development server
- **Vue Router** for client-side routing
- **Pinia** for state management
- **Tailwind CSS** with shadcn/vue components
- **Axios** for API communication with Django backend

**Architecture:**
- Component-based Vue architecture with composables
- Service layer for API integration (`services/api.ts`, `services/auth.service.ts`)
- Type-safe schemas for data validation (`schemas/kanban.schemas.ts`)
- Separation of concerns with stores, services, and composables

**Current Features:**
- Authentication and login system
- Kanban board for job management
- Dashboard view
- Job card components
- Drag-and-drop functionality

This frontend communicates with the Django backend via API endpoints and represents the future direction for the user interface.

## File Structure Conventions

### Static Files Organization
- `apps/{app}/static/{app}/css/` for app-specific styles
- `apps/{app}/static/{app}/js/` for app-specific JavaScript
- Modular JavaScript with feature-based organization

### Template Organization
- `apps/{app}/templates/{app}/` for app-specific templates
- `workflow/templates/base.html` as base template
- AJAX partial templates for dynamic updates

### Migration Management
- Numbered migrations with descriptive names
- Migration data validation in separate commands
- Careful handling of UUID foreign key relationships
