# Xero Projects Sync Plan

## Overview
This document outlines the plan to synchronize job data between Morris Sheetmetal's job management system and Xero Projects API.

**Business Purpose:** Complete project-based financial tracking. All projects need to exist in Xero so that all revenue (invoices) and costs (bills, expenses) can be allocated to projects for accurate profitability reporting. Our ERP handles operations; Xero handles accounting - both need the same project structure.

## Current State Analysis

### Our Job Model
- **Job** with Kanban status tracking (Quoting → In Progress → Completed → Archived)
- **CostSet/CostLine** architecture for flexible cost tracking
- **Client** relationships with bidirectional Xero contact sync
- Time tracking via CostLine entries
- Material costs via Stock/CostLine references

### Xero Projects Model
- **Project** with status (INPROGRESS, CLOSED)
- Contact association (contactId)
- Time tracking (minutesLogged, minutesToBeInvoiced)
- Financial tracking (totalTaskAmount, totalExpenseAmount, estimates)
- Currency support
- Deposit and invoice tracking

## Mapping Strategy

### Job → Project Mapping
| Our Model | Xero Projects | Notes |
|-----------|---------------|-------|
| Job.id | projectId | Add `xero_project_id` CharField to Job model (following Client.xero_contact_id pattern) |
| Job.name | name | Direct mapping |
| Job.client | contactId | Use existing client sync |
| Job.status | status | Most statuses → INPROGRESS (work active, costs accumulating), only "archived" → CLOSED |
| Job.delivery_date | deadlineUTC | Map existing delivery_date field |
| Job.latest_estimate | estimate.value | Map latest_estimate total (Xero quotes sync separately from projects) |

### Financial Data Sync
| Our Data | Xero Projects | Sync Direction |
|----------|---------------|----------------|
| CostLine time entries | minutesLogged | One-way push (our system → Xero) for project profitability |
| CostLine material costs | totalExpenseAmount | One-way push (our system → Xero) for project profitability |
| Invoice data | totalInvoiced | Xero is source of truth (invoicing happens there) |

## Technical Implementation

### Authentication & Authorization
- Use existing XeroToken infrastructure
- Required scope: `projects` (View and manage your projects - Projects, Tasks, Time)
- Rate limits: 60 calls/minute, 5000 calls/day

### Sync Patterns

#### Initial Sync
1. Sync ALL existing jobs to Xero (complete historical project data for financial reporting)
2. Use existing sync infrastructure with batching to respect API rate limits
3. <How do we handle jobs that already exist in both systems?>
4. <What's our strategy for handling sync failures during initial load?>

#### Ongoing Sync
- **Push Sync Triggers:**
  - Every time the edit job button is clicked (covers creation, and major edits)
  - Job status change to "archived" (immediate - close project in Xero)
  - Hourly batch sync (existing scheduled sync)
  - Manual "Sync Now" UI button
  - Conservative approach to respect Xero's daily API limits

- **Pull Sync**: <Do we need to pull changes from Xero Projects?>
  - Time entries added directly in Xero
  - Status changes made in Xero
  - <How often do we poll for changes?>

#### Conflict Resolution
- <What happens when same project is modified in both systems?>
- <Which system is the source of truth for different data types?>
- <How do we handle deleted projects in either system?>

### Data Storage

#### New Models Needed
```python
# Proposed model structure
class XeroProject(models.Model):
    job = models.OneToOneField(Job, related_name='xero_project')
    xero_project_id = models.CharField(max_length=50, unique=True)
    last_sync_at = models.DateTimeField()
    sync_status = models.CharField(choices=[...])  # <What statuses do we need?>
    # <What other fields for sync metadata?>
```

#### Job Model Extensions (Required)
**Following Client model sync pattern, Job needs these fields:**
```python
# Add to apps/job/models/job.py
xero_project_id = models.CharField(
    max_length=255, unique=True, null=True, blank=True
)
xero_last_synced = models.DateTimeField(
    null=True, blank=True, default=timezone.now
)
xero_last_modified = models.DateTimeField(
    null=False, blank=False, default=timezone.now
)
```

#### Staff Model Extensions (Required)
**For time entry mapping to Xero users:**
```python
# Add to apps/accounts/models.py Staff model
xero_user_id = models.CharField(
    max_length=255, unique=True, null=True, blank=True
)
```

#### Invoice Model Changes (Required)
**Current limitation:** Invoice has OneToOneField with Job, but Xero Projects can have multiple invoices.
```python
# CHANGE in apps/accounting/models/invoice.py
# FROM:
job = models.OneToOneField("job.Job", related_name="invoice", ...)

# TO:
job = models.ForeignKey("job.Job", related_name="invoices", ...)
```
**Impact:** This changes `job.invoice` to `job.invoices.all()` - requires code updates throughout system.

**Job model changes needed:**
```python
# REMOVE existing invoiced property completely:
# @property
# def invoiced(self) -> bool:
#     ...

# ADD new BooleanField:
fully_invoiced = models.BooleanField(default=False)
```

**Breaking Changes:** All code using `job.invoiced` (property) must be updated to use `job.fully_invoiced` (field). This field is manually managed by Xero sync, not calculated.

#### CostLine Sync Tracking (Required for Bidirectional Sync)
**Our system is master, Xero can only create new entries**
```python
# Add to CostLine model
xero_time_id = models.CharField(max_length=255, null=True, blank=True)      # For time entries
xero_expense_id = models.CharField(max_length=255, null=True, blank=True)   # For material expenses
xero_last_synced = models.DateTimeField(null=True, blank=True)
xero_last_modified = models.DateTimeField(null=True, blank=True)
```

**Sync Rules:**
- **Updates**: Our system → Xero only (we are master)
- **Creates**: Bidirectional (Xero time/expense entries → our CostLines)
- **Conflicts**: Fail fast with error persistence, no fallbacks
- **Deletes**: Our system → Xero only (we are master)

**API Efficiency:**
- **One API call per job sync** - bulk all time/expense entries together
- CostLine tracking used to determine what to sync, not for individual API calls
- Minimize API costs by batching everything for each project

**CostLine → Xero Mapping:**
- `kind='time'` → Xero time entries
- All other kinds (`material`, `adjust`, etc.) → Xero expense entries
- **Never skip any CostLines** - totals must match between systems

### Service Layer Architecture

#### Xero Projects Sync Infrastructure
**CORRECT APPROACH:** Follow Client sync pattern, NOT XeroDocumentManager (which is for financial documents)

**Key files to create/modify:**
1. Add sync fields to `apps/job/models/job.py`
2. Add transform function to `apps/workflow/api/xero/sync.py`
3. Add Projects API calls to `apps/workflow/api/xero/xero.py`
4. Update ENTITY_CONFIGS in sync.py

**Client sync follows this pattern:**
```python
# In sync.py - transform function
def transform_project(xero_project, xero_id):
    # Convert Xero project to Job fields
    # Similar to transform_invoice, transform_bill, etc.

# In sync.py - ENTITY_CONFIGS
"projects": (
    "projects",        # xero_entity_type
    "projects",        # our_entity_type
    Job,               # model
    "get_projects",    # api_method
    lambda items: sync_entities(items, Job, "project_id", transform_project),
    None,              # additional_params
    "single",          # pagination_mode
),

# Push to Xero (like sync_client_to_xero)
def sync_job_to_xero(job):
    # Push job changes to Xero Projects API
```

## Migration Strategy

### Phase 1: Read-Only Integration
- One-way sync (our system → Xero) - our system is the one that creates projects
- Include all active jobs (complete financial tracking)
- Bidirectional sync of CostLines (can create time entries in either, can create stock usage in either)
- Note in phase 1 we will only be syncing to Xero, but we must be writing on the assumption of bidirectional sync coming VERY soon.

### Phase 2: Bidirectional Sync
- <When do we enable pulling data from Xero back to our system?>
- <What's our rollback strategy if sync causes issues?>

### Phase 3: Advanced Features
- <Do we need to sync project tasks/subtasks?>
- <How do we handle Xero's time tracking vs our CostLine approach?>

## Questions for Business Requirements

### Functional Requirements
1. Sync ALL jobs (including shop jobs and "special" status) for complete financial tracking
2. Time entries editable in our system only, pushed to Xero for reporting
3. All jobs must have valid clients (shop jobs use shop client)
4. Archived jobs stay synced (marked CLOSED in Xero) for historical reporting

### Business Rules
1. <Which system should be the source of truth for project estimates?>
2. <How do we handle currency differences if client uses different currency?>
3. <Should completed jobs in our system automatically close Xero projects?>
4. <Do we sync deposits and invoice tracking or keep that Xero-only?>

### User Experience
1. <Should users see Xero sync status in our job interface?>
2. <How do we handle sync errors - alert users or background retry?>
3. <Should there be manual sync triggers or only automatic?>

## Risk Assessment

### Technical Risks
- <API rate limit constraints with large job volumes>
- <Data consistency issues during network failures>
- <Schema changes in either system breaking sync>

### Business Risks
- <Duplicate work entries if sync fails>
- <Financial discrepancies between systems>
- <User confusion about which system to use>

### Mitigation Strategies
- <Error persistence using existing persist_app_error infrastructure>
- <Transaction rollback strategies for failed syncs>
- <Monitoring and alerting for sync health>

## Testing Strategy

### Unit Tests
- <Test mapping logic between Job and Project models>
- <Test conflict resolution scenarios>
- <Test error handling and recovery>

### Integration Tests
- <Test with Xero sandbox environment>
- <Test rate limiting behavior>
- <Test authentication token refresh>

### User Acceptance Testing
- <Test scenarios with actual business workflows>
- <Performance testing with realistic data volumes>

## Monitoring & Maintenance

### Sync Health Monitoring
- <What metrics do we track for sync performance?>
- <How do we detect and alert on sync failures?>
- <Dashboard for monitoring sync status across jobs?>

### Data Integrity Checks
- <Regular validation that synced data matches?>
- <Process for identifying and fixing sync discrepancies?>

## Implementation Timeline

### Milestone 1: Foundation (Week 1-2)
- XeroProject model creation
- Basic XeroProjectsManager service
- Authentication setup

### Milestone 2: One-way Sync (Week 3-4)
- Job → Project creation sync
- Status mapping implementation
- <Other priorities?>

### Milestone 3: Financial Data Sync (Week 5-6)
- CostLine → Xero time/expense sync
- Estimate synchronization
- <Other financial data priorities?>

### Milestone 4: Production Rollout (Week 7-8)
- <Rollout strategy and timeline?>
- <Training and documentation priorities?>

---

## Open Questions Summary
- UUID handling and ID mapping strategy
- Status mapping between 4-status and 2-status systems
- Bidirectional vs one-way sync approach
- Conflict resolution and source of truth decisions
- Initial sync strategy for existing data
- Required Xero API scopes and permissions
- Error handling and recovery mechanisms
- Performance considerations for large job volumes
