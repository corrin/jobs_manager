# Production Data Restore Plan - 20250713

**Backup File:** `prod_backup_20250713_002841.json.gz`
**Schema File:** `prod_backup_20250705_051324_schema.sql` (production schema unchanged)

## EXACT SEQUENCE TO FOLLOW

### Step 5: Reset Database
**Command:**
```bash
sudo mysql --execute="source scripts/reset_database.sql"
```

**Check:**
```bash
MYSQL_PWD=hRjATdbwGhTtsR8e mysql -u django_user -e "SHOW TABLES;" msm_workflow
# Expected: Empty set (0.00 sec)

MYSQL_PWD=hRjATdbwGhTtsR8e mysql -u django_user -e "SHOW DATABASES;" | grep msm_workflow
# Expected: msm_workflow
```

**✅ Success Criteria:** Database reset successfully ❌ NOT STARTED

### Step 6: Apply Production Schema
**Command:**
```bash
MYSQL_PWD=hRjATdbwGhTtsR8e mysql -u django_user msm_workflow --execute="source restore/prod_backup_20250705_051324_schema.sql"
```

**Check:**
```bash
MYSQL_PWD=hRjATdbwGhTtsR8e mysql -u django_user -e "SHOW TABLES;" msm_workflow | wc -l
# Expected: 50+ tables

MYSQL_PWD=hRjATdbwGhTtsR8e mysql -u django_user -e "DESCRIBE workflow_job;" msm_workflow | grep contact_person
# Expected: contact_person	varchar(100)	YES		NULL

MYSQL_PWD=hRjATdbwGhTtsR8e mysql -u django_user -e "SELECT COUNT(*) FROM workflow_job;" msm_workflow
# Expected: 0 (empty table)
```

**✅ Success Criteria:** Production schema applied (50+ tables created) ❌ NOT STARTED

### Step 8: Load Production Data
**Command:**
```bash
MYSQL_PWD=hRjATdbwGhTtsR8e mysql -u django_user msm_workflow --execute="source restore/prod_backup_20250713_002841.sql"
```

**Check:**
```bash
MYSQL_PWD=hRjATdbwGhTtsR8e mysql -u django_user -e "
SELECT 'workflow_job' as table_name, COUNT(*) as count FROM workflow_job
UNION SELECT 'workflow_staff', COUNT(*) FROM workflow_staff
UNION SELECT 'workflow_client', COUNT(*) FROM workflow_client
UNION SELECT 'workflow_timeentry', COUNT(*) FROM workflow_timeentry
UNION SELECT 'workflow_jobpricing', COUNT(*) FROM workflow_jobpricing;
" msm_workflow
# Expected: Hundreds/thousands of records in each table
```

**✅ Success Criteria:** Production data loaded (hundreds/thousands of records) ❌ NOT STARTED

### Step 8a: Apply Django Migrations
**Command:**
```bash
python manage.py migrate
```

**Check:**
```bash
python manage.py showmigrations
# Expected: All migrations should show [X] (applied)
```

**✅ Success Criteria:** Django migrations applied without errors ❌ NOT STARTED

### Step 8b: Load Company Defaults Fixture
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
# Expected: Company defaults loaded: Demo Company
```

**✅ Success Criteria:** Company defaults loaded successfully ❌ NOT STARTED

### Step 9: Verify Specific Data
**Command:**
```bash
MYSQL_PWD=hRjATdbwGhTtsR8e mysql -u django_user -e "
SELECT id, name, job_number, status
FROM workflow_job
WHERE name LIKE '%test%' OR name LIKE '%sample%'
LIMIT 5;
" msm_workflow
# Expected: Real job records with realistic data
```

**✅ Success Criteria:** Sample data verification completed ❌ NOT STARTED

### Step 10: Test Django ORM
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
# Expected: Hundreds/thousands of records, sample job details
```

**✅ Success Criteria:** Django ORM can query all models ❌ NOT STARTED

### Step 11: Create Admin User
**Command:**
```bash
python manage.py shell -c "from apps.accounts.models import Staff; user = Staff.objects.create_user(email='defaultadmin@example.com', password='Default-admin-password', first_name='Default', last_name='Admin'); user.is_staff = True; user.is_superuser = True; user.save(); print(f'Created admin user: {user.email}')"
```

**Check:**
```bash
python manage.py shell -c "from apps.accounts.models import Staff; user = Staff.objects.get(email='defaultadmin@example.com'); print(f'User exists: {user.email}'); print(f'Is active: {user.is_active}'); print(f'Is staff: {user.is_staff}'); print(f'Is superuser: {user.is_superuser}')"
# Expected: All should be True
```

**✅ Success Criteria:** Admin user created and functional ❌ NOT STARTED

### Step 11a: Create Dummy Files for JobFile Instances
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
# Expected: Missing files: 0
```

**✅ Success Criteria:** Dummy files created for all JobFile instances ❌ NOT STARTED

## CRITICAL NOTES

1. **NEVER skip the database reset** - always start fresh
2. **Schema MUST be applied before data** - tables must exist first
3. **Migrations come AFTER data load** - to align current code with production schema
4. **Company defaults fixture comes AFTER migrations** - depends on current schema
5. **NO DEVIATIONS** from this exact sequence

## Files Used

- Reset script: `scripts/reset_database.sql`
- Production schema: `restore/prod_backup_20250705_051324_schema.sql`
- Production data: `restore/prod_backup_20250713_002841.sql` (converted from JSON)
- Company defaults: `apps/workflow/fixtures/company_defaults.json`
