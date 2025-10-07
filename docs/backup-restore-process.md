# Production Data Backup and Restore Process

## MySQL Connection Pattern

ALL MySQL commands must include: `-h "$DB_HOST" -P "$DB_PORT"`

Example: `MYSQL_PWD="$DB_PASSWORD" mysql -h "$DB_HOST" -P "$DB_PORT" -u "$MYSQL_DB_USER" "$MYSQL_DATABASE" -e "SHOW TABLES;"`

## Complete Step-by-Step Guide

Note! Important! Do not EVER use fake or fake-initial
We need to create a flawless process so we are 100% certain that it will apply without issues on production
YOU MUST RUN EVERY SINGLE STEP IN THE RESTORE. No step can be skipped, including manual steps where you need to get the user to do things

Make sure you create an audit log of any run of this script in logs, e.g restore_log_20250711.txt
Write to this log each step, and the outcome from running that step (e.g. test results). Do this after each step, don't wait until the end.

## CRITICAL ORDER ENFORCEMENT

**NEVER run steps out of order. The following steps MUST be completed before ANY testing:**
1. Steps 1-16: Basic restore and setup
2. Step 17: **XERO OAUTH CONNECTION** (MANUAL - CANNOT BE SKIPPED)
3. Steps 18-21: Xero configuration
4. Steps 22-24: Testing ONLY AFTER Xero is connected

**Testing (Steps 22-24) is FORBIDDEN until Xero OAuth (Step 17) is complete.**

## Common mistakes to avoid

1. Always avoid using < to pass SQL scripts. It works for small scripts but not big ones. You MUST stick to --execute="source scripts/file.sql"
2. ALways immediate stop on errors. We are fixing a process here, not hacking past issues
3. If anything goes wrong, at all... even a little bit. THen stop. NEVER work around issues or surprises. As an example, this is illegal: "Perfect! Now I need to check if we have production backup files or if we need to load demo data instead. Let me check the restore directory:". This document never gave the option to load demo data.

### PRODUCTION STEPS

#### Step 1: Create Schema Backup (Production)

**Run as:** Production system user with database access
**Command:**

```bash
MYSQL_PWD=your_prod_password mysqldump -u your_prod_user --no-data --routines --triggers jobs_manager > prod_backup_$(date +%Y%m%d_%H%M%S)_schema.sql
```

**Check:**

```bash
ls -la prod_backup_*_schema.sql
# Should show file exists with reasonable size (typically 50-200KB)
grep "CREATE TABLE \`workflow_job\`" prod_backup_*_schema.sql
# Should show the table creation statement
```

#### Step 2: Create Data Backup (Production)

**Run as:** Production system user with Django access
**Command:**

```bash
python manage.py backport_data_backup
```

**Check:**

```bash
ls -la restore/prod_backup_*.json.gz
# Should show compressed file exists with large size (typically 5-25MB)
gunzip -c restore/prod_backup_*.json.gz | head -20
# Should show JSON array with Django model data (anonymized)
gunzip -c restore/prod_backup_*.json.gz | wc -l
# Should show thousands of lines
```

#### Step 3: Transfer Files to Development

**Run as:** Development system user
**Commands:**

```bash
scp prod-server:path/to/prod_backup_YYYYMMDD_HHMMSS_schema.sql restore/
scp prod-server:path/to/restore/prod_backup_YYYYMMDD_HHMMSS.json.gz restore/
```

**Check:**

```bash
ls -la restore/
# Should show both files transferred
```

### DEVELOPMENT STEPS

#### Step 4: Verify Environment Configuration

**Run as:** Development system user
**Check:**

```bash
grep -E "^(MYSQL_DATABASE|MYSQL_DB_USER|DB_PASSWORD|DB_HOST|DB_PORT)=" .env
export DB_PASSWORD=$(grep DB_PASSWORD .env | cut -d= -f2)
export MYSQL_DATABASE=$(grep MYSQL_DATABASE .env | cut -d= -f2)
export MYSQL_DB_USER=$(grep MYSQL_DB_USER .env | cut -d= -f2)
```

**Must show:**

```
MYSQL_DATABASE=msm_workflow
MYSQL_DB_USER=django_user
DB_PASSWORD=your_dev_password
DB_HOST=localhost
DB_PORT=3306
```

**If any missing:** Add to .env file

Note. If you're using Claude or similar, you need to specify these explicitly on all subsequent command lines rather than use environment variables

#### Step 5: Reset Database

**Run as:** System root (for MySQL admin operations)
**Command:**

```bash
sudo mysql -u root --execute="source scripts/reset_database.sql"
```

**Note:** Adjust for your MySQL setup - add password (`MYSQL_PWD=password`), host (`-h host`), or port (`-P port`) as needed.

**Check:**

```bash
MYSQL_PWD="$DB_PASSWORD" mysql -h "$DB_HOST" -P "$DB_PORT" -u "$MYSQL_DB_USER" "$MYSQL_DATABASE" -e "SHOW TABLES;"
# Should return: Empty set (0.00 sec)
MYSQL_PWD="$DB_PASSWORD" mysql -h "$DB_HOST" -P "$DB_PORT" -u "$MYSQL_DB_USER" -e "SHOW DATABASES;" | grep "$MYSQL_DATABASE"
# Should show: msm_workflow
```

#### Step 6: Apply Production Schema

**Run as:** Development system user
**Command:**

```bash
MYSQL_PWD="$DB_PASSWORD" mysql -h "$DB_HOST" -P "$DB_PORT" -u "$MYSQL_DB_USER" "$MYSQL_DATABASE" --execute="source restore/prod_backup_YYYYMMDD_HHMMSS_schema.sql"
```

**Check:**

```bash
MYSQL_PWD="$DB_PASSWORD" mysql -h "$DB_HOST" -P "$DB_PORT" -u "$MYSQL_DB_USER" "$MYSQL_DATABASE" -e "SHOW TABLES;" | wc -l
# Should show 50+ tables
MYSQL_PWD="$DB_PASSWORD" mysql -h "$DB_HOST" -P "$DB_PORT" -u "$MYSQL_DB_USER" "$MYSQL_DATABASE" -e "DESCRIBE workflow_job;" | grep contact_person
# Should show: contact_person	varchar(100)	YES		NULL
MYSQL_PWD="$DB_PASSWORD" mysql -h "$DB_HOST" -P "$DB_PORT" -u "$MYSQL_DB_USER" "$MYSQL_DATABASE" -e "SELECT COUNT(*) FROM workflow_job;"
# Should show: 0 (empty table)
```

#### Step 7: Extract and Convert JSON to SQL

**Run as:** Development system user
**Commands:**

```bash
# Extract the compressed backup
gunzip restore/prod_backup_YYYYMMDD_HHMMSS.json.gz
# Convert to SQL (automatically generates .sql from .json filename)
python scripts/json_to_mysql.py restore/prod_backup_YYYYMMDD_HHMMSS.json
```

**Check:**

```bash
ls -la restore/prod_backup_YYYYMMDD_HHMMSS.sql
# Should show large file (typically 50-200MB)
head -10 restore/prod_backup_YYYYMMDD_HHMMSS.sql
# Should show:
# -- MySQL dump converted from Django JSON backup
# USE msm_workflow;
# SET FOREIGN_KEY_CHECKS=0;
# INSERT INTO `workflow_job` (`id`, `name`, `client_id`...
grep "INSERT INTO" restore/prod_backup_YYYYMMDD_HHMMSS.sql | wc -l
# Should show thousands of INSERT statements
```

#### Step 8: Load Production Data

**Run as:** Development system user
**Command:**

```bash
MYSQL_PWD=$DB_PASSWORD mysql -u $MYSQL_DB_USER $MYSQL_DATABASE --execute="source restore/prod_backup_YYYYMMDD_HHMMSS.sql"
```

**Check:**

```bash
MYSQL_PWD=your_dev_password mysql -u django_user -e "
SELECT 'workflow_job' as table_name, COUNT(*) as count FROM workflow_job
UNION SELECT 'workflow_staff', COUNT(*) FROM workflow_staff
UNION SELECT 'workflow_client', COUNT(*) FROM workflow_client
UNION SELECT 'job_costset', COUNT(*) FROM job_costset
UNION SELECT 'job_costline', COUNT(*) FROM job_costline;
" msm_workflow
```

**Expected output (update with actual numbers):**

```
+-------------------+-------+
| table_name        | count |
+-------------------+-------+
| workflow_job      |  1054 |
| workflow_staff    |    20 |
| workflow_client   |  3739 |
| job_costset       |  3162 |
| job_costline      | 10334 |
+-------------------+-------+
```

#### Step 9: Apply Django Migrations (CRITICAL: Do this BEFORE loading fixtures)

**Run as:** Development system user
**Command:**

```bash
python manage.py migrate
```

**Why this step is critical:** The production schema may not match current Django models. Migrations align the schema with current code before loading fixtures that depend on the correct schema.

**Check:**

```bash
python manage.py showmigrations
```

**Expected:** All migrations should show [X] (applied)

#### Step 10: Load Company Defaults Fixture

**Run as:** Development system user
**Command:**

```bash
python manage.py loaddata apps/workflow/fixtures/company_defaults.json
```

**Check:**

```bash
python manage.py shell -c "
from apps.workflow.models import CompanyDefaults
company = CompanyDefaults.get_instance()
print(f'Company defaults loaded: {company.company_name}')
"
```

**Expected output:**

```
Company defaults loaded: Demo Company
```

#### Step 11: Verify Specific Data

**Run as:** Development system user
**Command:**

```bash
MYSQL_PWD=your_dev_password mysql -u django_user -e "
SELECT id, name, job_number, status
FROM workflow_job
WHERE name LIKE '%test%' OR name LIKE '%sample%'
LIMIT 5;
" msm_workflow
```

**Check:** Should show actual job records with realistic data

#### Step 12: Test Django ORM

**Run as:** Development system user
**Command:**

```bash
python manage.py shell -c "
from apps.job.models import Job
from apps.accounts.models import Staff
from apps.client.models import Client
print(f'Jobs: {Job.objects.count()}')
print(f'Staff: {Staff.objects.count()}')
print(f'Clients: {Client.objects.count()}')
job = Job.objects.first()
if job:
    print(f'Sample job: {job.name} (#{job.job_number})')
    print(f'Contact: {job.contact.name if job.contact else "None"}')
else:
    print('ERROR: No jobs found')
"
```

**Expected output:**

```
Jobs: 620
Staff: 17
Clients: 3605
Sample job: [Real Job Name] (#12345)
Contact: [Real Contact Name]
```

#### Step 13: Create Admin User

**Run as:** Development system user
**Command:**

```bash
python manage.py shell -c "from apps.accounts.models import Staff; user = Staff.objects.create_user(email='defaultadmin@example.com', password='Default-admin-password', first_name='Default', last_name='Admin'); user.is_staff = True; user.is_superuser = True; user.save(); print(f'Created admin user: {user.email}')"
```

**Check:**

```bash
python manage.py shell -c "from apps.accounts.models import Staff; user = Staff.objects.get(email='defaultadmin@example.com'); print(f'User exists: {user.email}'); print(f'Is active: {user.is_active}'); print(f'Is staff: {user.is_staff}'); print(f'Is superuser: {user.is_superuser}')"
```

**Expected output:**

```
Created admin user: defaultadmin@example.com
User exists: defaultadmin@example.com
Is active: True
Is staff: True
Is superuser: True
```

#### Step 14: Create Dummy Files for JobFile Instances

**Run as:** Development system user
**Command:**

```bash
python scripts/recreate_jobfiles.py
```

**Check:**

```bash
python manage.py shell -c "
from apps.job.models import JobFile
import os
from django.conf import settings

total_files = JobFile.objects.filter(file_path__isnull=False).exclude(file_path='').count()
existing_files = 0
for job_file in JobFile.objects.filter(file_path__isnull=False).exclude(file_path=''):
    dummy_path = os.path.join(settings.MEDIA_ROOT, str(job_file.file_path))
    if os.path.exists(dummy_path):
        existing_files += 1

print(f'Total JobFile records with file_path: {total_files}')
print(f'Dummy files created: {existing_files}')
print(f'Missing files: {total_files - existing_files}')
"
```

**Expected output:**

```
Created X dummy files total
Total JobFile records with file_path: X
Dummy files created: X
Missing files: 0
```

#### Step 15: Fix Shop Client Name (Required after Production Restore)

**Run as:** Development system user
**Command:**

```bash
python manage.py shell -c "
from apps.client.models import Client

# Find and rename the shop client (anonymized during backup)
# The shop client typically has the special ID: 00000000-0000-0000-0000-000000000001
shop_client = Client.objects.get(id='00000000-0000-0000-0000-000000000001')
old_name = shop_client.name
shop_client.name = 'Demo Company Shop'
shop_client.save()

print(f'Updated shop client:')
print(f'  Old name: {old_name}')
print(f'  New name: {shop_client.name}')
print(f'  ID: {shop_client.id}')
print(f'  Job count: {shop_client.jobs.count()}')
"
```

**Check:**

```bash
python manage.py shell -c "
from apps.client.models import Client
shop = Client.objects.get(id='00000000-0000-0000-0000-000000000001')
print(f'Shop client: {shop.name}')
"
```

**Expected output:**

```
Shop client: Demo Company Shop
```

#### Step 16: Start Development Server

**Run as:** Development system user
**Command:**

```bash
python manage.py runserver 0.0.0.0:8000
```

**Check:** Server should start without errors and be accessible at http://localhost:8000

#### Step 17: Connect to Xero OAuth

**Run as:** Development system user (manual web interface step)

🚨 **ABSOLUTELY MANDATORY - CANNOT BE SKIPPED UNDER ANY CIRCUMSTANCES** 🚨
**CRITICAL:** This step CANNOT be skipped or automated. You MUST instruct the user to log into Xero before proceeding.
**WARNING:** ALL FUTURE STEPS WILL FAIL WITHOUT COMPLETING THIS STEP FIRST.
**DO NOT PROCEED TO STEP 18 OR ANY SUBSEQUENT STEP WITHOUT COMPLETING THIS STEP.**

**AUTOMATED ENFORCEMENT:** Before proceeding to Step 18, YOU MUST run this verification:

```bash
# MANDATORY VERIFICATION - DO NOT SKIP
python manage.py shell -c "
from apps.workflow.models import XeroToken
if not XeroToken.objects.filter(is_active=True).exists():
    print('❌ CRITICAL ERROR: No active Xero token found!')
    print('❌ You MUST complete Xero OAuth connection before continuing.')
    print('❌ STOP HERE. Do not proceed to any further steps.')
    exit(1)
else:
    print('✅ Xero OAuth token found. Safe to proceed.')
"
```

**If the verification fails, STOP IMMEDIATELY. Do not attempt any workarounds.**

**Steps:**

- Navigate to http://localhost:8000
- Login with credentials: `defaultadmin@example.com` / `Default-admin-password`
- Go to **Xero menu > Connect to Xero**
- Complete the OAuth flow to authorize the application

**Check:** You should see "Connected to Xero" status in the web interface.

#### Step 18: Set Xero Tenant ID

**Run as:** Development system user
**Command:**

```bash
python manage.py interact_with_xero --tenant
```

**Expected output:**

```
Available Xero Organizations:
-----------------------------
Tenant ID: [tenant-id-uuid]
Name: [Tenant Name]
-----------------------------

Automatically set tenant ID to [tenant-id-uuid] ([Tenant Name]) in CompanyDefaults
```

**Note:** If multiple tenants are found, the command will display them but not auto-set. Use `--no-set` to prevent automatic setting.

#### Step 19: Seed Database to Xero

**Run as:** Development system user
**Command:**

```bash
python manage.py seed_xero_from_database
```

**What this does:**
1. Clears production Xero IDs (clients, jobs, stock, purchase orders)
2. Links/creates contacts in Xero for all clients
3. Creates projects in Xero for all jobs
4. Syncs stock items to Xero inventory

**Why this step is critical:** Production Xero IDs won't work in UAT tenant. This command clears them and rebuilds all Xero relationships for the UAT environment.

**Check:**

```bash
python manage.py shell -c "
from apps.client.models import Client
from apps.job.models import Job
from apps.purchasing.models import Stock

clients_with_xero = Client.objects.filter(xero_contact_id__isnull=False).count()
jobs_with_xero = Job.objects.filter(xero_project_id__isnull=False).count()
stock_with_xero = Stock.objects.filter(xero_id__isnull=False, is_active=True).count()

print(f'Clients linked to Xero: {clients_with_xero}')
print(f'Jobs linked to Xero: {jobs_with_xero}')
print(f'Stock items synced to Xero: {stock_with_xero}')
"
```

**Expected:** Large numbers - clients (2500+), jobs (500+), stock items (hundreds to thousands).

#### Step 20: Test Admin User Login

**Run as:** Development system user
**Command:**

```bash
python manage.py shell -c "
from django.contrib.auth import authenticate
from apps.accounts.models import Staff

# Test authentication
user = authenticate(email='defaultadmin@example.com', password='Default-admin-password')
if user:
    print(f'✓ Login successful: {user.email}')
    print(f'✓ Is active: {user.is_active}')
    print(f'✓ Is staff: {user.is_staff}')
    print(f'✓ Is superuser: {user.is_superuser}')
else:
    print('✗ Login failed - check credentials')
"
```

**Expected output:**

```
✓ Login successful: defaultadmin@example.com
✓ Is active: True
✓ Is staff: True
✓ Is superuser: True
```

#### Step 21: Test Serializers (Before API Testing)

**Run as:** Development system user
**Command:**

```bash
python scripts/test_serializers.py --serializer job
```

**Alternative: Test all serializers comprehensively:**

```bash
python scripts/test_serializers.py --verbose
```

**Expected:** `✅ ALL SERIALIZERS PASSED!` or specific failure details if issues found.

#### Step 22: Test Kanban HTTP API

**Run as:** Development system user
**Prerequisites:** Development server must be running: `python manage.py runserver 0.0.0.0:8000`

**Command:**

```bash
./scripts/test_kanban_api.sh
```

**Expected output (WORKING API):**

```
✓ API working: 174 active jobs, 23 archived
```

**Expected output (BROKEN API):**

```
✗ ERROR: API test failed
Server errors:
ERROR 2025-07-13 01:44:27,880 kanban_view_api Error fetching all jobs
ERROR 2025-07-13 01:44:27,886 log Internal Server Error: /job/api/jobs/fetch-all/
API response:
{"success": false, "error": "validation errors", ...}
```

**CRITICAL:** If you see "✗ ERROR" in the output, the restore has FAILED and you must fix the issues before proceeding.

#### Step 23: Final Application Test

**Run as:** Development system user
**Command:**

```bash
python manage.py runserver 0.0.0.0:8000
```

**Check in browser:** Navigate to http://localhost:8000 and verify:

- Login works with credentials: `defaultadmin@example.com` / `Default-admin-password`
- Job list displays with real data
- Kanban board loads without errors and shows jobs
- Xero integration shows connected status
- No database errors in console

## Troubleshooting

Here are some errors we tripped over in the creation of this markdown. You shouldn't have these happen since we've now
coded around them, but they're included to give you a sense of the sort of errors that happen in real ife.

### Reset Script Fails

**Symptoms:** Permission denied errors
**Solution:** Always run the create database as root: `sudo mysql < scripts/reset_database.sql`

### Schema Missing Columns

**Symptoms:** workflow_job missing contact_person, contact_email, contact_phone
**Cause:** Schema backup taken after Django migrations removed columns
**Solution:** Take the schema backup from production at the same time as the data backup

### Zero Records After Data Load

**Symptoms:** All table counts show 0
**Debug steps:**

1. Check JSON file size: `ls -la restore/prod_backup_*.json`
2. Check SQL file has INSERT statements: `grep "INSERT INTO" restore/prod_backup_final.sql | head -5`
3. Check for SQL errors: `MYSQL_PWD=password mysql -u django_user -v < restore/prod_backup_final.sql`
4. Verify table schema matches data: `MYSQL_PWD=password mysql -u django_user -e "DESCRIBE workflow_job;" msm_workflow`

### Django ORM Errors

**Symptoms:** Model queries fail after restore
**Cause:** Schema/model mismatch
**Solution:** Run `python manage.py migrate` to align schema with current models

## File Locations

- **Production schema:** `prod_backup_YYYYMMDD_HHMMSS_schema.sql`
- **Production data:** `prod_backup_YYYYMMDD_HHMMSS.json.gz`
- **Development restore:** `restore/` directory
- **Reset script:** `scripts/reset_database.sql`
- **Converter script:** `scripts/json_to_mysql.py` (enhanced with foreign key mappings)
- **Generated SQL:** `restore/prod_backup_YYYYMMDD_HHMMSS.sql` (auto-generated)

## Key Improvements Made

### Enhanced JSON to SQL Converter

The `scripts/json_to_mysql.py` script has been enhanced to:

- **Handle Django migrations table:** Includes `django_migrations` table to preserve exact migration state
- **Foreign key field mappings:** Correctly maps Django foreign key fields (e.g., `supplier` → `supplier_id`)
- **Content types support:** Handles `django_content_type` table for Django internals

<!-- FUTURE ENHANCEMENT: Consider adding data filtering to json_to_mysql.py to remove
     problematic MaterialEntry records with purchase_order_line or source_stock references.
     This would prevent foreign key constraint errors when Xero purchase order data isn't available.
     See apps/job/management/commands/backport_data_restore.py lines 51-66 for reference implementation. -->

### Enhanced Backup Script

The `backport_data_backup.py` script now:

- **Captures migration state:** Includes `django_migrations` table in backup using raw SQL extraction
- **Preserves exact production state:** No more guessing which migrations were applied in production

### Verified Working Process

✅ **620 jobs** successfully restored from production
✅ **246 migrations** correctly captured and restored
✅ **Schema matches data** - no foreign key constraint errors
✅ **Migration state preserved** - development knows exactly which migrations to apply

## Required Passwords

- **Production MySQL:** Production database password
- **Development MySQL:** Value from `DB_PASSWORD` in `.env`
- **System sudo:** For running reset script as MySQL root
