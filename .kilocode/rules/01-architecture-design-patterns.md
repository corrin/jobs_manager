# Architecture and Design Patterns

## 🚨 DEFENSIVE PROGRAMMING PHILOSOPHY - CRITICAL TO FOLLOW 🚨

### FAIL EARLY, HANDLE UNHAPPY PATHS FIRST, NO FALLBACKS

**Mandatory Patterns:**

- Always check `if <bad_case>: handle_error()` first, never `if <good_case>:`
- Validate required input data up front – fail if missing
- No default values or fallbacks that mask config/data issues
- Trust the data model – do not work around broken data with exception handling

**Implementation Example:**

```python
def create_job(data: Dict[str, Any], user: Staff) -> Job:
    """Creates a new Job with essential data."""
    # Guard clauses – early return for validations
    if not data.get("name"):
        raise ValueError("Job name is required")
    if not data.get("client_id"):
        raise ValueError("Client is required")
    try:
        client = Client.objects.get(id=data["client_id"])
    except Client.DoesNotExist:
        raise ValueError("Client not found")
    # Continue only with valid data...
```

### MANDATORY ERROR PERSISTENCE

**Every exception handler MUST call `persist_app_error(exc)` – errors are permanently stored in the database, never lost to log rotation.**

```python
from apps.workflow.services.error_persistence import persist_app_error

try:
    operation()
except Exception as exc:
    persist_app_error(exc)  # MANDATORY
    raise  # Fail fast unless business logic allows continuation
```

## Absolute Separation of Frontend-Backend Responsibilities

### 🚨 NEVER PUT FRONTEND LOGIC IN THE BACKEND. NEVER PUT BACKEND LOGIC IN THE FRONTEND. 🚨

**Backend-ONLY Responsibilities:**

- Data persistence and retrieval
- Business logic and calculations
- Data validation and integrity
- API contracts and real data serialization
- Authentication and authorization
- Integrations with external systems

**Cross-Contamination Forbidden:**

- ❌ Backend serializers for static UI constants (dropdown options, labels, etc.)
- ❌ Backend views returning HTML or UI-specific data structures
- ❌ Frontend making business logic decisions or calculations
- ❌ Frontend bypassing backend validation
- ❌ Frontend defining data structures for backend data
- ❌ Shared code between frontend and backend (except API contracts)

**Rule:** If it doesn't involve database, business rules, or external systems, it belongs to the frontend. If it involves data integrity, calculations, or persistence, it belongs to the backend.

## Django App Architecture

### Focused App Structure

**`workflow`** – Central Hub

- Base functionality and integration coordination
- Base models (CompanyDefaults, XeroAccount, XeroToken, AIProvider)
- Xero accounting integration and sync
- Authentication middleware and base templates

**`job`** – Job Lifecycle Management

- CostSet/CostLine architecture for flexible cost tracking
- Kanban-style status tracking
- Comprehensive audit trails

**`accounts`** – User Management

- Extends AbstractBaseUser for business-specific requirements
- Password strength validation (minimum 10 characters)
- Role-based permissions

**`client`** – Client Relationship Management

- Bidirectional Xero contact sync
- Contact person and communication tracking

**`timesheet`** – Time Tracking

- CostLine with kind='time' for time tracking
- Staff references stored in meta JSON field

**`purchasing`** – Purchase Order Management

- Comprehensive Xero integration via XeroPurchaseOrderManager
- **Integration**: Links to CostLine via external references for material costing

**`accounting`** – Financial Reporting

- KPI calendar views and financial analytics
- Invoice generation via Xero integration

**`quoting`** – Quotation Generation

- Supplier price list management
- Price extraction with AI (Gemini integration)

## Data Model Patterns

### Core Data Relationships

```python
Job → CostSet (1:many) → CostLine (1:many)
CostLine → external references via ext_refs JSON field
PurchaseOrder → PurchaseOrderLine → Stock → CostLine (via ext_refs)
Staff → CostLine (time entries via meta.staff_id)
Client → Job (1:many)
```

### Mandatory Design Patterns

- **UUID primary keys** everywhere for security
- **SimpleHistory** for audit trails in critical models
- **Soft deletes** where appropriate
- JSON ext_refs for flexible external references
- JSON meta for entry-specific data (dates, staff, billability)
- CostSet/CostLine architecture for all cost tracking
- accounting_date field on CostLine for KPI reporting
- Bidirectional Xero sync with conflict resolution

## Service Layer Patterns

### Mandatory Service Structure

```python
class JobRestService:
    """
    Service layer for Job REST operations.
    Implements all business rules related to Job manipulation via REST API.
    """
    @staticmethod
    def create_job(data: Dict[str, Any], user: Staff) -> Job:
        """
        Creates a new Job with essential data.
        Applies early return for validations.
        """
        # Guard clauses – early return for validations
        if not data.get("name"):
            raise ValueError("Job name is required")
        # Implementation...
    @staticmethod
    def _validate_can_disable_complex_mode(job: Job) -> Dict[str, Any]:
        """Private methods for complex validation logic."""
        # Implementation...
```

### Service Patterns

- **CostingService**: Handles all CostSet/CostLine operations
- **JobService**: Updated to work with CostSet/CostLine architecture
- **XeroSyncService**: Manages bidirectional sync with Xero
- **ErrorPersistenceService**: Handles mandatory error persistence

## Development Patterns

### Job Costing Workflow

1. Create initial CostSet with kind='estimate'
2. **Quotation**: Create CostSet with kind='quote' and appropriate CostLine entries
3. **Time Tracking**: Create CostLine with kind='time', staff reference in meta.staff_id, date in meta.date and accounting_date
4. **Material Usage**: Create CostLine with kind='material', Stock reference in ext_refs, accounting_date set
5. **Adjustments**: Create CostLine with kind='adjust', accounting_date set to when adjustment was made

## Dependency Injection and IoC

### Injection Patterns

```python
# Use dependency injection for testability
class JobService:
    def __init__(self, cost_service: CostingService = None):
        self.cost_service = cost_service or CostingService()
    def create_job_with_estimate(self, job_data: dict, estimate_data: dict):
        job = self.create_job(job_data)
        self.cost_service.create_estimate_cost_set(job, estimate_data)
        return job
```

## Event-Driven Architecture

### Event Patterns

**Event-driven development is used exclusively for the `Job` model via the `JobEvent` model.**

- All business events (status changes, updates, etc.) for jobs are persisted as `JobEvent` records.
- Do **not** use Django signals or custom event buses for job-related events.
- All event creation must occur through explicit model/service logic (see `Job.save()` and `_create_change_events()` in the codebase).
- Other models (e.g., CostLine, Xero sync) do **not** use event-driven patterns—use direct service calls and database updates.

**Example:**

```python
# Correct: Creating a JobEvent for a status change
JobEvent.objects.create(
    job=job,
    event_type="status_changed",
    description=f"Status changed from '{old_status}' to '{new_status}'",
    staff=user,
)
```

## Related References

- See: [02-code-organization-structure.md](./02-code-organization-structure.md)
- See: [06-error-management-logging.md](./06-error-management-logging.md)
- See: [04-data-handling-persistence.md](./04-data-handling-persistence.md)
