# Production Data Backup and Restore Process

## MySQL Connection Pattern

ALL MySQL commands must include: `-h "$DB_HOST" -P "$DB_PORT"`

**Linux/WSL (bash):**
```bash
MYSQL_PWD="$DB_PASSWORD" mysql -h "$DB_HOST" -P "$DB_PORT" -u "$MYSQL_DB_USER" "$MYSQL_DATABASE" -e "SHOW TABLES;"
```

**Windows (PowerShell):**
```powershell
$env:MYSQL_PWD = $env:DB_PASSWORD
mysql.exe -h $env:DB_HOST -P $env:DB_PORT -u $env:MYSQL_DB_USER $env:MYSQL_DATABASE -e "SHOW TABLES;"
Remove-Item Env:MYSQL_PWD
```

Note: On Windows, always use `--execute "source path\to\file.sql"` for loading SQL files, and remove MYSQL_PWD after each command.

## Complete Step-by-Step Guide

Note! Important! Do not EVER use fake or fake-initial
We need to create a flawless process so we are 100% certain that it will apply without issues on production
YOU MUST RUN EVERY SINGLE STEP IN THE RESTORE. No step can be skipped, including manual steps where you need to get the user to do things

Make sure you create an audit log of any run of this script in logs, e.g restore_log_20250711.txt
Write to this log each step, and the outcome from running that step (e.g. test results). Do this after each step, don't wait until the end.

## Overview/Target State

You should end up with:
1. The backend running on port 8000
2. ngrok mapping a public domain to the backend
3. ngrok mapping a public domain to the frontend
4. The frontend (in its own repo) running on port 5173
5. The database fully deleted, then restored from prod
6. All migrations applied
7. Linked to the dev Xero
8. Key data from prod's restore synced to the dev xero
9. The Xero token is locked in via python manage.py run_scheduler
10. LLM keys set up and configured
11. Playwright tests pass


## CRITICAL ORDER ENFORCEMENT

**NEVER run steps out of order. The following steps MUST be completed before ANY testing:**
1. Steps 1-20: Basic restore and setup
2. Step 21: **XERO OAUTH CONNECTION** (CANNOT BE SKIPPED)
3. Steps 22-27: Xero configuration
4. Steps 28-30: Testing ONLY AFTER Xero is connected

## Common mistakes to avoid

1. Always avoid using < to pass SQL scripts. It works for small scripts but not big ones. You MUST stick to --execute="source scripts/file.sql"
2. Always immediate stop on errors. We are fixing a process here, not hacking past issues
3. If anything goes wrong, at all... even a little bit. Then stop. NEVER work around issues or surprises. As an example, this is illegal: "Perfect! Now I need to check if we have production backup files or if we need to load demo data instead. Let me check the restore directory:". This document never gave the option to load demo data.

### PRODUCTION STEPS

#### Step 1: Create Backup (Production)

**Run as:** Production system user with Django access
**Command:**

```bash
python manage.py backport_data_backup
```

This creates a zip file in `/tmp` containing both the schema and anonymized data backup.

**Check:**

```bash
ls -la /tmp/prod_backup_*_complete.zip
# Should show zip file (typically 5-25MB)
```

#### Step 2: Transfer Backup to Development

**Command:**

```bash
scp prod-server:/tmp/prod_backup_YYYYMMDD_HHMMSS_complete.zip restore/
```

**Check:**

```bash
ls -la restore/*.zip
# Should show the zip file transferred
```

#### Step 3: Extract Backup Files

**Command:**

```bash
cd restore && unzip prod_backup_YYYYMMDD_HHMMSS_complete.zip
```

**Check:**

```bash
ls -la restore/
# Should show both .json.gz and .schema.sql files
```

### DEVELOPMENT STEPS

#### Step 4: Verify Environment Configuration

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
export MYSQL_PWD="$DB_PASSWORD" && mysql -h "$DB_HOST" -P "$DB_PORT" -u "$MYSQL_DB_USER" "$MYSQL_DATABASE" -e "SHOW TABLES;"
# Should return: Empty set (0.00 sec)
export MYSQL_PWD="$DB_PASSWORD" && mysql -h "$DB_HOST" -P "$DB_PORT" -u "$MYSQL_DB_USER" -e "SHOW DATABASES;" | grep "$MYSQL_DATABASE"
# Should show: msm_workflow
```

#### Step 6: Apply Production Schema

**Command:**

```bash
export MYSQL_PWD="$DB_PASSWORD" && mysql -h "$DB_HOST" -P "$DB_PORT" -u "$MYSQL_DB_USER" "$MYSQL_DATABASE" --execute="source restore/prod_backup_YYYYMMDD_HHMMSS.schema.sql"
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

**Command:**

```bash
MYSQL_PWD="$DB_PASSWORD" mysql -h "$DB_HOST" -P "$DB_PORT" -u "$MYSQL_DB_USER" "$MYSQL_DATABASE" --execute="source restore/prod_backup_YYYYMMDD_HHMMSS.sql"
```

**Check:**

```bash
MYSQL_PWD="$DB_PASSWORD" mysql -h "$DB_HOST" -P "$DB_PORT" -u "$MYSQL_DB_USER" "$MYSQL_DATABASE" -e "
SELECT 'workflow_job' as table_name, COUNT(*) as count FROM workflow_job
UNION SELECT 'workflow_staff', COUNT(*) FROM workflow_staff
UNION SELECT 'workflow_client', COUNT(*) FROM workflow_client
UNION SELECT 'job_costset', COUNT(*) FROM job_costset
UNION SELECT 'job_costline', COUNT(*) FROM job_costline;
"
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

#### Step 11: Load AI Providers Fixture (Optional)


**Prerequisite:** Copy `apps/workflow/fixtures/ai_providers.json.example` to `ai_providers.json` and add your real API keys.

**Command:**

```bash
python manage.py loaddata apps/workflow/fixtures/ai_providers.json
```

**Check (validates API keys actually work):**

```bash
python manage.py shell -c "
from apps.workflow.models import AIProvider
from apps.workflow.services.llm_service import LLMService
from apps.workflow.enums import AIProviderTypes
from mistralai import Mistral

results = []

# Test Claude and Gemini via LLMService (chat)
for ptype in [AIProviderTypes.ANTHROPIC, AIProviderTypes.GOOGLE]:
    provider = AIProvider.objects.filter(provider_type=ptype).first()
    if not provider or not provider.api_key:
        print(f'{ptype}: ✗ Not configured')
        continue
    try:
        svc = LLMService(provider_type=ptype)
        resp = svc.get_text_response([{'role': 'user', 'content': 'Say hi in 2 words'}])
        print(f'{provider.name}: ✓ {resp.strip()[:30]}')
    except Exception as e:
        print(f'{provider.name}: ✗ {str(e)[:50]}')

# Test Mistral via SDK (OCR model - just validate key works)
provider = AIProvider.objects.filter(provider_type=AIProviderTypes.MISTRAL).first()
if provider and provider.api_key:
    try:
        client = Mistral(api_key=provider.api_key)
        models = client.models.list()
        print(f'Mistral: ✓ API key valid ({len(models.data)} models available)')
    except Exception as e:
        print(f'Mistral: ✗ {str(e)[:50]}')
else:
    print('Mistral: ✗ Not configured')
"
```

**Expected output:**

```
Claude: ✓ Hello there!
Gemini: ✓ Hi there!
Mistral: ✓ API key valid (X models available)
```

#### Step 12: Verify Specific Data

**Command:**

```bash
MYSQL_PWD="$DB_PASSWORD" mysql -h "$DB_HOST" -P "$DB_PORT" -u "$MYSQL_DB_USER" "$MYSQL_DATABASE" -e "
SELECT id, name, job_number, status
FROM workflow_job
WHERE name LIKE '%test%' OR name LIKE '%sample%'
LIMIT 5;
"
```

**Check:** Should show actual job records with realistic data

#### Step 13: Test Django ORM

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

#### Step 14: Create Admin User

**Command:**

```bash
python manage.py shell -c "from apps.accounts.models import Staff; user = Staff.objects.create_user(email='defaultadmin@example.com', password='Default-admin-password', first_name='Default', last_name='Admin'); user.is_office_staff = True; user.is_superuser = True; user.save(); print(f'Created admin user: {user.email}')"
```

**Check:**

```bash
python manage.py shell -c "from apps.accounts.models import Staff; user = Staff.objects.get(email='defaultadmin@example.com'); print(f'User exists: {user.email}'); print(f'Is active: {user.is_active}'); print(f'Is office staff: {user.is_office_staff}'); print(f'Is superuser: {user.is_superuser}')"
```

**Expected output:**

```
Created admin user: defaultadmin@example.com
User exists: defaultadmin@example.com
Is active: True
Is staff: True
Is superuser: True
```

#### Step 15: Create Dummy Files for JobFile Instances

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
    dummy_path = os.path.join(settings.DROPBOX_WORKFLOW_FOLDER, str(job_file.file_path))
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

#### Step 16: Fix Shop Client Name (Required after Production Restore)

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
#### Step 17: Verify Test Client Exists or Create if Needed


The test client is used by the test suite. Create it if missing:

```bash
python manage.py shell -c "
from apps.workflow.models import CompanyDefaults
from apps.client.models import Client
from django.utils import timezone

cd = CompanyDefaults.get_instance()
client = Client.objects.filter(name=cd.test_client_name).first()

if client:
    print(f'Test client already exists: {client.name} (ID: {client.id})')
else:
    client = Client(
        name=cd.test_client_name,
        is_account_customer=False,
        xero_last_modified=timezone.now(),
        xero_last_synced=timezone.now(),
    )
    client.save()
    print(f'Created test client: {client.name} (ID: {client.id})')
"
```

**Expected output:**
```
Created test client: ABC Carpet Cleaning TEST IGNORE (ID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)
```

#### Step 18: Start ngrok Tunnels (skip for UAT)

**Commands (run in separate terminals):**

Note, these are often already running.  Check first.

```bash
# Terminal 1: ngrok for backend (replace with your domain)
ngrok http 8000 --domain=your-backend.ngrok-free.app

# Terminal 2: ngrok for frontend (replace with your domain)
ngrok http 5173 --domain=your-frontend.ngrok-free.app
```

**Check:** Both ngrok tunnels should show "Forwarding" status with public URLs.

#### Step 19: Start Development Server (skip for UAT)


**Check if server is already running:**

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000
```

If you get 302, **SKIP this step** - server is already running.

**If curl fails, ask the user to start the server:**

In VS Code: Run menu > Start Debugging (F5)

**Check:** Re-run the curl command above - should return 302.

#### Step 20: Start Frontend (skip for UAT)


**Check if frontend is already running:**

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:5173
```

If you get 200, **SKIP this step** - frontend is already running.

**If curl fails, start the frontend (in separate terminal):**

```bash
cd ../jobs_manager_front && npm run dev
```

**Check:** Re-run the curl command above - should return 200.

#### Step 21: Connect to Xero OAuth


🚨 **MANDATORY - all future steps will fail without this.** 🚨

**Command:**

```bash
pushd ../jobs_manager_front && npx tsx tests/scripts/xero-login.ts && popd
```

**What this does:**
This script automates the Xero OAuth login flow using Playwright. It navigates to the frontend, logs in with the default admin credentials, and completes the Xero OAuth authorization.

**Check:**

```bash
python manage.py shell -c "
from apps.workflow.models import XeroToken
from django.utils import timezone

token = XeroToken.objects.first()
if not token:
    print('❌ No Xero token found. Login script may have failed.')
    exit(1)
if token.expires_at and token.expires_at < timezone.now():
    print('❌ Xero token is expired.')
    exit(1)

print('✅ Xero OAuth token found.')
"
```

#### Step 22: Set Xero Tenant ID

**Command:**

```bash
python manage.py xero --tenant
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

#### Step 23: Sync Chart of Accounts from Xero

**Command:**

```bash
python manage.py start_xero_sync --entity accounts
```

**What this does:**
Fetches the chart of accounts from Xero and populates the XeroAccount table with account codes, names, and types. This is required for stock sync to work correctly (needs account codes 200 for Sales and 300 for Purchases).

**Check:**

```bash
python manage.py shell -c "
from apps.workflow.models import XeroAccount
print(f'Total accounts synced: {XeroAccount.objects.count()}')
sales = XeroAccount.objects.filter(account_code='200').first()
purchases = XeroAccount.objects.filter(account_code='300').first()
print(f'Sales account (200): {sales.account_name if sales else \"NOT FOUND\"}')
print(f'Purchases account (300): {purchases.account_name if purchases else \"NOT FOUND\"}')
"
```

**Expected output:**

```
Total accounts synced: 50+ accounts
Sales account (200): Sales
Purchases account (300): Purchases
```

#### Step 24: Sync Pay Items from Xero

**Command:**

```bash
python manage.py xero --configure-payroll
```

**Expected output:** `✓ XeroPayItem sync completed!`

#### Step 25: Seed Database to Xero


**WARNING:** This step takes 10+ minutes. Run in background.

**Command:**

```bash
nohup python manage.py seed_xero_from_database > logs/seed_xero_output.log 2>&1 &
echo "Background process started, PID: $!"
```

**What this does:**
1. Clears production Xero IDs (clients, jobs, stock, purchase orders, staff)
2. Links/creates contacts in Xero for all clients
3. Creates projects in Xero for all jobs
4. Syncs stock items to Xero inventory (using account codes from Step 23)
5. Links/creates payroll employees for all active staff (uses Staff UUID in job_title for reliable re-linking)

**Monitor progress:**

```bash
tail -f logs/seed_xero_output.log
# Press Ctrl+C to stop watching
```

**Check completion:**

```bash
python manage.py shell -c "
from apps.client.models import Client
from apps.job.models import Job
from apps.purchasing.models import Stock
from apps.accounts.models import Staff

clients_with_xero = Client.objects.filter(xero_contact_id__isnull=False).count()
jobs_with_xero = Job.objects.filter(xero_project_id__isnull=False).count()
stock_with_xero = Stock.objects.filter(xero_id__isnull=False, is_active=True).count()
staff_with_xero = Staff.objects.filter(xero_user_id__isnull=False, date_left__isnull=True).count()

print(f'Clients linked to Xero: {clients_with_xero}')
print(f'Jobs linked to Xero: {jobs_with_xero}')
print(f'Stock items synced to Xero: {stock_with_xero}')
print(f'Staff linked to Xero Payroll: {staff_with_xero}')
"
```

**Expected:** Large numbers - clients (2500+), jobs (500+), stock items (hundreds to thousands), staff (all active staff).

#### Step 26: Sync Xero

**Command:**

```bash
python manage.py start_xero_sync
```

**Expected output:**

Error and warning free sync between local and xero data.

#### Step 27: Start Background Scheduler

**Command (in separate terminal):**

```bash
python manage.py run_scheduler
```

This keeps the Xero token refreshed automatically.

#### Step 28: Test Serializers

**Command:**

```bash
python scripts/test_serializers.py --verbose
```

**Expected:** `✅ ALL SERIALIZERS PASSED!` or specific failure details if issues found.

#### Step 29: Test Kanban HTTP API

**Command:**

```bash
python scripts/test_kanban_api.py
```

**Expected output:**

```
✓ API working: 174 active jobs, 23 archived
```

#### Step 30: Run Playwright Tests

**Command:**

```bash
cd ../jobs_manager_front && npx playwright test
```

**Expected:** All tests pass.

## Troubleshooting

Here are some errors we tripped over in the creation of this markdown. You shouldn't have these happen since we've now
coded around them, but they're included to give you a sense of the sort of errors that happen in real life.

### Reset Script Fails

**Symptoms:** Permission denied errors
**Solution:** run the create database as root: `sudo mysql --execute="source scripts/reset_database.sql"`

### Schema Missing Columns

**Symptoms:** workflow_job missing contact_person, contact_email, contact_phone
**Cause:** Schema backup taken after Django migrations removed columns
**Solution:** Take the schema backup from production at the same time as the data backup

### Zero Records After Data Load

**Symptoms:** All table counts show 0
**Debug steps:**

1. Check JSON file size: `ls -la restore/prod_backup_*.json`
2. Check SQL file has INSERT statements: `grep "INSERT INTO" restore/prod_backup_*.sql | head -5`
3. Check for SQL errors: `MYSQL_PWD="$DB_PASSWORD" mysql -h "$DB_HOST" -P "$DB_PORT" -u "$MYSQL_DB_USER" "$MYSQL_DATABASE" -v --execute="source restore/prod_backup_*.sql"`
4. Verify table schema matches data: `MYSQL_PWD="$DB_PASSWORD" mysql -h "$DB_HOST" -P "$DB_PORT" -u "$MYSQL_DB_USER" "$MYSQL_DATABASE" -e "DESCRIBE workflow_job;"`

### Django ORM Errors

**Symptoms:** Model queries fail after restore
**Cause:** Schema/model mismatch
**Solution:** Run `python manage.py migrate` to align schema with current models

## File Locations

- **Combined backup:** `/tmp/prod_backup_YYYYMMDD_HHMMSS_complete.zip` (created by backup command)
- **Production schema:** `prod_backup_YYYYMMDD_HHMMSS.schema.sql` (inside zip)
- **Production data:** `prod_backup_YYYYMMDD_HHMMSS.json.gz` (inside zip)
- **Development restore:** `restore/` directory
- **Reset script:** `scripts/reset_database.sql`
- **Converter script:** `scripts/json_to_mysql.py`
- **Generated SQL:** `restore/prod_backup_YYYYMMDD_HHMMSS.sql` (auto-generated from JSON)

## Key Improvements Made

### Enhanced JSON to SQL Converter

The `scripts/json_to_mysql.py` script has been enhanced to:

- **Handle Django migrations table:** Includes `django_migrations` table to preserve exact migration state
- **Foreign key field mappings:** Correctly maps Django foreign key fields (e.g., `supplier` → `supplier_id`)
- **Content types support:** Handles `django_content_type` table for Django internals

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
