# Production Data Restore Plan

## Prerequisites
```bash
# Set database password from environment
export DB_PASSWORD=$(grep DB_PASSWORD .env | cut -d= -f2)
```

## Target End State
**Local database with:**
- All anonymized production data (20,965+ records) successfully inserted
- Database schema at latest migration version (0029+)
- All Django models working correctly with the restored data

## Step-by-Step Plan to Achieve This

### Step 1: Restore Production Schema
```bash
# Reset database (run as root)
sudo mysql < scripts/reset_database.sql
# Apply production schema
mysql -u django_user -p$DB_PASSWORD msm_workflow < restore/schema_only_backup.sql
```

**Test Step 1 Success - Show Full Table Structure:**
```bash
# Show complete job_job table structure
mysql -u django_user -p$DB_PASSWORD -e "DESCRIBE job_job;" msm_workflow
```

**To update expected columns for future versions:**
```bash
# Extract column list from converted SQL (run this to update the plan)
grep "INSERT INTO.*job_job" restore/prod_backup_final.sql | head -1 | sed 's/.*(`\([^)]*\)`).*/\1/' | tr ',' '\n'
```

**Expected**: Must include these columns (from prod_backup_final.sql):
`id`, `name`, `client_id`, `order_number`, `contact_person`, `contact_email`, `contact_phone`, `contact_id`, `job_number`, `material_gauge_quantity`, `description`, `quote_acceptance_date`, `delivery_date`, `status`, `job_is_valid`, `collected`, `paid`, `charge_out_rate`, `pricing_methodology`, `latest_estimate_pricing_id`, `latest_quote_pricing_id`, `latest_reality_pricing_id`, `created_at`, `updated_at`, `complex_job`, `notes`, `created_by_id`, `priority`

**If missing contact_person, contact_email, contact_phone, material_gauge_quantity**: Schema restore failed


### Step 2: Debug JSON-to-SQL Converter Failure
**Extract small test sample:**
```bash
# First decompress the backup if needed
if [ -f restore/prod_backup_YYYYMMDD_HHMMSS.json.gz ]; then
    gunzip restore/prod_backup_YYYYMMDD_HHMMSS.json.gz
fi
# Extract sample
head -20 restore/prod_backup_YYYYMMDD_HHMMSS.json > restore/debug_sample.json
python scripts/json_to_mysql.py restore/debug_sample.json restore/debug_sample.sql
```

**Analyze generated SQL for common failures:**
- String escaping issues (newlines, quotes in descriptions)
- Boolean conversion (`true/false` → `1/0`)
- Field mapping errors (`client` → `client_id`)
- INSERT syntax errors

**Test Step 2 Success - Verify Exact Sample Data:**
```bash
# Load sample and validate specific data from JSON made it to database
mysql -u django_user -p$DB_PASSWORD msm_workflow < restore/debug_sample.sql

# Check specific job from JSON exists with correct data
mysql -u django_user -p$DB_PASSWORD -e "
SELECT id, name, job_number, status, contact_person 
FROM workflow_job 
WHERE id = 'd178765f-9062-4dc7-af4f-001e8eb1fbb0';
" msm_workflow
```
**Expected**: Must show exact row with:
- id: d178765f-9062-4dc7-af4f-001e8eb1fbb0  
- name: Cat litter tray
- job_number: 95456
- status: rejected  
- contact_person: Stephen Lopez

**If no row or wrong data**: Converter failed, debug field mappings and SQL syntax

### Step 3: Fix Converter and Test Until Working
**Fix identified issues in `scripts/json_to_mysql.py`**
**Re-test sample until it inserts data correctly**
**Verify Django can see the test data:**
```bash
python manage.py shell -c "from apps.job.models import Job; print(Job.objects.count())"
```

### Step 4: Full Data Conversion and Restore
```bash
# Reset to clean state
sudo mysql < scripts/reset_database.sql
mysql -u django_user -p$DB_PASSWORD msm_workflow < restore/schema_only_backup.sql

# Convert and load full dataset
python scripts/json_to_mysql.py restore/prod_backup_20250704_231657.json restore/prod_backup_final.sql
mysql -u django_user -p$DB_PASSWORD msm_workflow < restore/prod_backup_final.sql
```

**Test Step 4 Success - Verify Exact Expected Counts:**

**To update expected counts for future versions:**
```bash
# Get actual counts from JSON backup (run this to update the plan)
grep '"model":' restore/prod_backup_20250704_231657.json | sort | uniq -c
```

```bash
# Check database has exactly the expected record counts from JSON
mysql -u django_user -p$DB_PASSWORD -e "
SELECT 'workflow_job' as table_name, COUNT(*) as actual, 620 as expected FROM workflow_job
UNION SELECT 'workflow_staff', COUNT(*), 17 FROM workflow_staff  
UNION SELECT 'workflow_client', COUNT(*), 3605 FROM workflow_client
UNION SELECT 'timesheet_timeentry', COUNT(*), 4104 FROM timesheet_timeentry
UNION SELECT 'workflow_jobpricing', COUNT(*), 1896 FROM workflow_jobpricing;
" msm_workflow

# Verify specific job data is correct
mysql -u django_user -p$DB_PASSWORD -e "
SELECT id, name, job_number, status, contact_person
FROM workflow_job 
WHERE id = 'd178765f-9062-4dc7-af4f-001e8eb1fbb0';
" msm_workflow
```
**Expected**: Actual counts must exactly match expected (620 jobs, 17 staff, 3605 clients, 4104 timeentries, 1896 jobpricings)
**If any mismatch**: Data loss, duplication, or conversion failure

### Step 5: Apply Django Migrations to Latest
```bash
python manage.py showmigrations  # Should show 0028 applied, 0029+ pending
python manage.py migrate  # Apply all pending migrations
```

**Verify migration success:**
```bash
python manage.py showmigrations  # All migrations should show [X]
mysql -u django_user -p$DB_PASSWORD -e "DESCRIBE workflow_job;" msm_workflow
```
**Expected**: Schema should reflect current Django model state after migrations are applied

### Step 6: Final Verification of End State
**Verify Django ORM works with migrated data:**
```bash
python manage.py shell -c "
from apps.job.models import Job
from apps.accounts.models import Staff  
from apps.client.models import Client
print(f'Jobs: {Job.objects.count()}')
print(f'Staff: {Staff.objects.count()}')
print(f'Clients: {Client.objects.count()}')
print(f'Sample job: {Job.objects.first().name if Job.objects.exists() else \"None\"}')
"
```

## Success Criteria Checklist
- [ ] Database contains exactly 20,965 records (620 jobs + 17 staff + 3605 clients + 4104 timeentries + 1896 jobpricings + others)
- [ ] All Django migrations applied successfully (0029+ all marked [X])
- [ ] Django ORM can query all models without errors
- [ ] Specific test data validates correctly (Cat litter tray job with correct fields)
- [ ] No fake migrations used
- [ ] Data integrity maintained throughout process

## Critical Failure Points to Watch
1. **Silent SQL failures**: Converter generates malformed SQL that doesn't throw errors but inserts nothing
2. **Migration failures**: Schema changes break with production data
3. **Django ORM incompatibility**: Models can't read migrated production data

If any step fails, STOP and debug before proceeding.