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

**`job`** - Core job lifecycle management with **modern costing architecture**
- Job model with Kanban-style status tracking (Quoting → In Progress → Completed → Archived)
- **NEW**: CostSet/CostLine for flexible cost tracking (estimate/quote/actual) - **USE FOR ALL NEW DEVELOPMENT**
- **FULLY DEPRECATED**: JobPricing, MaterialEntry, AdjustmentEntry, TimeEntry - **DO NOT USE IN ANY NEW CODE**
- JobFile for document attachments
- JobEvent for comprehensive audit trails
- Service layer for business logic orchestration

**`accounts`** - User management with custom Staff model
- Extends AbstractBaseUser for business-specific requirements
- Password strength validation (minimum 10 characters)
- Role-based permissions and authentication

**`client`** - Customer relationship management
- Client model with bidirectional Xero contact synchronization
- Contact person and communication tracking

**`timesheet`** - Time tracking and billing
- **MIGRATION TO**: CostLine with kind='time' for time tracking - **ALL NEW TIME ENTRIES**
- **DEPRECATED**: TimeEntry model - **DO NOT CREATE NEW TimeEntry RECORDS**
- Billable vs non-billable classification
- Daily/weekly timesheet interfaces
- Wage rate and charge-out rate management

**`purchasing`** - Purchase order and inventory management
- PurchaseOrder with comprehensive Xero integration via XeroPurchaseOrderManager
- Stock management with source tracking and inventory control
- Supplier quote processing and delivery receipts
- **Integration**: Links to CostLine via external references for material costing

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

**Modern Relationships (USE THESE):**
```
Job → CostSet (1:many) → CostLine (1:many)
CostLine → external references via ext_refs JSON field
PurchaseOrder → PurchaseOrderLine → Stock → CostLine (via ext_refs)
Staff → CostLine (time entries via ext_refs)
Client → Job (1:many)
```

**Legacy Relationships (DEPRECATED - DO NOT USE):**
```
Job → JobPricing (1:many) → TimeEntry/MaterialEntry/AdjustmentEntry (1:many)
Staff → TimeEntry (1:many)
PurchaseOrder → PurchaseOrderLine → Stock → MaterialEntry
```

**Design Patterns:**
- UUID primary keys throughout for security
- SimpleHistory for audit trails on critical models
- Soft deletes where appropriate
- **NEW**: JSON ext_refs for flexible external references
- **NEW**: CostSet/CostLine architecture for all cost tracking
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

### Error Handling Patterns
- **Use AppError for persistence**: All exceptions should be logged and persisted to the database using `persist_app_error(exc)`
- **Smart logging levels**:
  - `logger.error()` for critical failures that affect core functionality
  - `logger.warning()` for non-critical errors where processing can continue
  - Always include context like job numbers, user IDs in error messages
- **Graceful degradation**: For non-critical errors, log and persist the error but continue processing with sensible defaults
- **Critical vs Non-Critical**:
  - Critical: Database connection failures, missing core data models
  - Non-Critical: Individual record processing failures, missing optional data

### Error Handling Code Pattern
```python
from apps.workflow.services.error_persistence import persist_app_error

# For critical errors that should stop execution
try:
    critical_operation()
except Exception as exc:
    logger.error(f"Critical error in operation: {str(exc)}")
    persist_app_error(exc)
    raise  # or return empty/default response

# For non-critical errors where processing can continue
try:
    optional_data = get_optional_data(record)
except Exception as exc:
    logger.warning(f"Error getting optional data for {record.id}: {str(exc)}")
    persist_app_error(exc)
    optional_data = default_value  # Continue with sensible default
```

### Testing Approach
Limited test coverage currently - focus on manual testing and data validation commands like `validate_jobs`.

### Integration Architecture
- **Xero API**: Bidirectional sync for contacts, invoices, purchase orders
- **Dropbox**: File storage for job documents
- **Gemini AI**: Price list extraction and processing
- **APScheduler**: Background task scheduling

## Business Context

### Job Lifecycle Workflow (Updated for New Architecture)
1. **Quoting**: Create CostSet with kind='quote' containing CostLine entries for estimates
2. **Job Creation**: Convert accepted quotes to jobs, copy quote CostSet to estimate CostSet
3. **Production**: Kanban board for visual workflow management
4. **Cost Tracking**: Use CostLine with kind='time'/'material'/'adjust' for all cost entries
5. **Material Management**: Track usage via Stock linked to CostLine through ext_refs
6. **Completion**: Generate invoices via Xero integration using actual CostSet data

### Key Business Rules (Updated for New Architecture)
- Jobs progress through defined states with audit trails
- All financial data synchronizes with Xero for accounting
- **ALL cost tracking uses CostSet/CostLine architecture - NO exceptions**
- **Time tracking**: CostLine with kind='time' (replaces TimeEntry)
- **Material costs**: CostLine with kind='material' linked to Stock via ext_refs
- **Adjustments**: CostLine with kind='adjust' for manual cost modifications
- File attachments support workshop job sheets

### Performance Considerations
- ag-Grid for handling large datasets efficiently
- AJAX patterns minimize full page reloads
- Background scheduling for Xero synchronization
- Database indexes on frequently queried UUID fields
- **NEW**: JSON ext_refs for efficient external reference lookups
- **NEW**: CostSet grouping reduces query complexity vs. individual entries

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
- **CRITICAL**: All new migrations must use CostSet/CostLine architecture
- **IMPORTANT**: Legacy model migrations should be for data migration only

## Critical Architecture Guidelines

### For ALL New Development
1. **NEVER create new JobPricing, MaterialEntry, AdjustmentEntry, or TimeEntry records**
2. **ALWAYS use CostSet/CostLine for any cost-related functionality**
3. **Job Creation**: Create initial CostSet with kind='estimate'
4. **Quoting**: Create CostSet with kind='quote' and appropriate CostLine entries
5. **Time Tracking**: Create CostLine with kind='time' and staff reference in ext_refs
6. **Material Usage**: Create CostLine with kind='material' and Stock reference in ext_refs
7. **Adjustments**: Create CostLine with kind='adjust' for manual cost modifications

### Legacy Model Handling
- **Reading**: Legacy models can be read for migration and reporting purposes
- **Writing**: **ABSOLUTELY NO new records in legacy models**
- **Migration**: Gradually migrate existing data to CostSet/CostLine
- **Service Layer**: Abstract legacy/new model differences in service classes

### Service Layer Patterns
- **CostingService**: Handles all CostSet/CostLine operations
- **JobService**: Updated to work with CostSet/CostLine architecture
- **Legacy Support**: Service methods should handle both old and new data during transition

### Complete Migration Strategy

#### Phase 1: Stop Writing to Legacy Models (CURRENT)
- **STATUS**: All new development uses CostSet/CostLine
- **RULE**: No new JobPricing, MaterialEntry, AdjustmentEntry, TimeEntry records
- **IMPLEMENTATION**: Update all forms, APIs, and services

#### Phase 2: Data Migration
- **GOAL**: Migrate all existing legacy data to CostSet/CostLine
- **PROCESS**: Create migration commands for bulk data transfer
- **VALIDATION**: Ensure data integrity and business logic consistency

#### Phase 3: Legacy Model Removal
- **FINAL STEP**: Remove legacy model references and drop tables
- **CLEANUP**: Update all documentation and remove deprecated code
- **VERIFICATION**: Ensure all functionality works with new architecture
