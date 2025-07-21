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

### Scheduler Management
```bash
# Start background scheduler (runs APScheduler jobs)
python manage.py run_scheduler
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

### Frontend
- Django templates with Bootstrap 5, jQuery, ag-Grid
- Separate Vue.js frontend in development (`../jobs_manager_front/`) - **managed by separate Claude Code instance**

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
- **NEVER edit __init__.py files directly** - they are autogenerated. Run `python scripts/update_init.py` to regenerate them after adding/removing Python files

### Defensive Programming Philosophy - CRITICAL TO FOLLOW

**FAIL EARLY, HANDLE UNHAPPY CASES FIRST, NO FALLBACKS**
- Check `if <bad_case>: handle_error()` first, never `if <good_case>:` patterns
- Validate required input data upfront - crash if missing
- No default values or fallbacks that mask configuration/data problems
- Trust the data model - don't work around broken data with exception handling

**MANDATORY ERROR PERSISTENCE**
Every exception handler must call `persist_app_error(exc)` - errors stored permanently in database, never lost to log rotation.

```python
from apps.workflow.services.error_persistence import persist_app_error

try:
    operation()
except Exception as exc:
    persist_app_error(exc)  # MANDATORY
    raise  # Fail fast unless business logic allows continuation
```


## Environment Configuration
See `.env.example` for required environment variables. Key integrations: Xero API, Dropbox, MariaDB.


## Migration Management
- **CRITICAL**: All new migrations must use CostSet/CostLine architecture
- **IMPORTANT**: Legacy model migrations should be for data migration only

## Critical Architecture Guidelines

### For ALL New Development
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
