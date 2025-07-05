# Production Data Backup and Restore Process

## Complete Step-by-Step Guide

Note! Important! Do not EVER use fake or fake-initial
We need to create a flawless process so we are 100% certain that it will apply without issues on production

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
grep -E "^(MYSQL_DATABASE|MSM_DB_USER|DB_PASSWORD|DB_HOST|DB_PORT)=" .env
export DB_PASSWORD=$(grep DB_PASSWORD .env | cut -d= -f2)
export MYSQL_DATABASE=$(grep MYSQL_DATABASE .env | cut -d= -f2)
export MSM_DB_USER=$(grep MSM_DB_USER .env | cut -d= -f2)
```
**Must show:**
```
MYSQL_DATABASE=msm_workflow
MSM_DB_USER=django_user
DB_PASSWORD=your_dev_password
DB_HOST=localhost
DB_PORT=3306
```
**If any missing:** Add to .env file

Note.  If you're using Claude or similar, you need to specify these explicitly on all subsequent command lines rather than use environment variables

#### Step 5: Reset Database
**Run as:** System root (for MySQL admin operations)
**Command:**
```bash
sudo mysql --execute="source scripts/reset_database.sql"
```
**Check:**
```bash
MYSQL_PWD=your_dev_password mysql -u django_user -e "SHOW TABLES;" msm_workflow
# Should return: Empty set (0.00 sec)
MYSQL_PWD=your_dev_password mysql -u django_user -e "SHOW DATABASES;" | grep msm_workflow
# Should show: msm_workflow
```

#### Step 6: Apply Production Schema
**Run as:** Development system user
**Command:**
```bash
MYSQL_PWD=$DB_PASSWORD mysql -u $MSM_DB_USER $MYSQL_DATABASE --execute="source restore/prod_backup_YYYYMMDD_HHMMSS_schema.sql"
```
**Check:**
```bash
MYSQL_PWD=your_dev_password mysql -u django_user -e "SHOW TABLES;" msm_workflow | wc -l
# Should show 50+ tables
MYSQL_PWD=your_dev_password mysql -u django_user -e "DESCRIBE workflow_job;" msm_workflow | grep contact_person
# Should show: contact_person	varchar(100)	YES		NULL
MYSQL_PWD=your_dev_password mysql -u django_user -e "SELECT COUNT(*) FROM workflow_job;" msm_workflow
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
MYSQL_PWD=$DB_PASSWORD mysql -u $MSM_DB_USER $MYSQL_DATABASE --execute="source restore/prod_backup_YYYYMMDD_HHMMSS.sql"
```
**Check:**
```bash
MYSQL_PWD=your_dev_password mysql -u django_user -e "
SELECT 'workflow_job' as table_name, COUNT(*) as count FROM workflow_job
UNION SELECT 'workflow_staff', COUNT(*) FROM workflow_staff  
UNION SELECT 'workflow_client', COUNT(*) FROM workflow_client
UNION SELECT 'workflow_timeentry', COUNT(*) FROM workflow_timeentry
UNION SELECT 'workflow_jobpricing', COUNT(*) FROM workflow_jobpricing;
" msm_workflow
```
**Expected output (update with actual numbers):**
```
+-------------------+-------+
| table_name        | count |
+-------------------+-------+
| workflow_job      |   620 |
| workflow_staff    |    17 |
| workflow_client   |  3605 |
| workflow_timeentry|  4104 |
| workflow_jobpricing|  1896 |
+-------------------+-------+
```

#### Step 8a: Apply Django Migrations (CRITICAL: Do this BEFORE loading fixtures)
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

#### Step 8b: Load Company Defaults Fixture
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

#### Step 9: Verify Specific Data
**Run as:** Development system user
**Command:**
```bash
MYSQL_PWD=your_dev_password mysql -u django_user -e "
SELECT id, name, job_number, status, contact_person
FROM workflow_job 
WHERE name LIKE '%test%' OR name LIKE '%sample%'
LIMIT 5;
" msm_workflow
```
**Check:** Should show actual job records with realistic data

#### Step 10: Test Django ORM
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
    print(f'Contact: {job.contact_person}')
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

#### Step 11: Create Admin User
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

#### Step 11a: Create Dummy Files for JobFile Instances
**Run as:** Development system user
**Command:**
```bash
python manage.py shell -c "
import os
from django.conf import settings
from apps.job.models import JobFile

print('Creating dummy files for JobFile instances...')
count = 0
for job_file in JobFile.objects.filter(file_path__isnull=False).exclude(file_path=''):
    dummy_path = os.path.join(settings.MEDIA_ROOT, str(job_file.file_path))
    os.makedirs(os.path.dirname(dummy_path), exist_ok=True)
    with open(dummy_path, 'w') as f:
        f.write(f'Dummy file for JobFile {job_file.pk}\\n')
        f.write(f'Original path: {job_file.file_path}\\n')
        f.write(f'Original filename: {job_file.filename}\\n')
        f.write(f'Job: {job_file.job.name if job_file.job else \"None\"}\\n')
    count += 1
    if count % 10 == 0:
        print(f'Created {count} dummy files...')
print(f'Created {count} dummy files total')
"
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

#### Step 12: Setup Xero Integration
**Run as:** Development system user (after server is running)
**Steps:**
1. **Start the development server:**
   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```

2. **Connect to Xero via web interface:**
   - Navigate to http://localhost:8000
   - Login with credentials: `defaultadmin@example.com` / `Default-admin-password`
   - Go to **Xero menu > Connect to Xero**
   - Complete the OAuth flow to authorize the application

3. **Get Xero tenant ID:**
   ```bash
   python manage.py get_xero_tenant_id
   ```
   **Expected output:**
   ```
   Available Xero tenants:
   - [Tenant Name]: [tenant-id-uuid]
   ```

4. **Update company defaults with tenant ID:**
   ```bash
   python manage.py shell -c "
   from apps.workflow.models import CompanyDefaults
   company = CompanyDefaults.get_instance()
   company.xero_tenant_id = 'YOUR_TENANT_ID_FROM_PREVIOUS_STEP'
   company.save()
   print(f'Updated company defaults with Xero tenant ID: {company.xero_tenant_id}')
   "
   ```

5. **Run initial Xero sync:**
   ```bash
   python manage.py start_xero_sync
   ```
   **Check:** Should show sync progress and completion without errors

**Verification:**
```bash
python manage.py shell -c "
from apps.workflow.models import CompanyDefaults
from apps.client.models import Client
company = CompanyDefaults.get_instance()
print(f'Xero tenant ID: {company.xero_tenant_id}')
print(f'Last sync: {company.last_xero_sync}')
print(f'Clients count: {Client.objects.count()}')
"
```

#### Step 13: Final Application Test
**Run as:** Development system user
**Command:**
```bash
python manage.py runserver 0.0.0.0:8000
```
**Check in browser:** Navigate to http://localhost:8000 and verify:
- Login works with credentials: `defaultadmin@example.com` / `Default-admin-password`
- Job list displays with real data
- Xero integration shows connected status
- No database errors in console

## Troubleshooting

Here are some errors we tripped over in the creation of this markdown.  You shouldn't have these happen since we've now 
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