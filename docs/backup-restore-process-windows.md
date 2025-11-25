# Production Data Backup and Restore Process (Windows + PowerShell)

This document mirrors `docs/backup-restore-process.md` but rewrites every step for Windows 11 with native PowerShell commands. Follow it exactly and keep an audit log (e.g., `logs/restore_log_YYYYMMDD_HHMMSS.txt`) that records every step and verification result.

## MySQL Connection Pattern (PowerShell)

All MySQL commands must pass in host and port explicitly:

```powershell
$env:MYSQL_PWD = $env:DB_PASSWORD
mysql.exe -h $env:DB_HOST -P $env:DB_PORT -u $env:MYSQL_DB_USER $env:MYSQL_DATABASE -e "SHOW TABLES;"
Remove-Item Env:MYSQL_PWD
```

- Always wrap multi-line SQL in `--execute "source path\to\file.sql"`.
- Remove the `MYSQL_PWD` environment variable immediately after each command.

## Complete Step-by-Step Guide (Windows)

**Process safety rules remain the same:** never skip a step, never continue after an error, and always capture results in the audit log.

### Step 1: Create Schema Backup (Production)

Run on the production host. Example PowerShell command:

```powershell
$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$backupName = "prod_backup_${timestamp}_schema.sql"
$env:MYSQL_PWD = $env:PROD_DB_PASSWORD
mysqldump.exe -u $env:PROD_DB_USER --no-data --routines --triggers $env:MYSQL_DATABASE > $backupName
Remove-Item Env:MYSQL_PWD
Get-ChildItem $backupName
Select-String -Path $backupName -Pattern 'CREATE TABLE `workflow_job`'
```

### Step 2: Create Data Backup (Production)

```powershell
poetry run python manage.py backport_data_backup
Get-ChildItem restore\prod_backup_*_schema.sql, restore\prod_backup_*.json.gz
Get-Content -Path restore\prod_backup_*.json.gz -TotalCount 20 | Write-Host
python - <<'PY'
import gzip, sys
import itertools
path = r"restore/prod_backup_latest.json.gz"
with gzip.open(path, 'rt', encoding='utf-8') as fh:
    for line in itertools.islice(fh, 20):
        print(line.rstrip())
PY
```

### Step 3: Transfer Files to Development

Use `scp` (from Git for Windows) or your deployment tooling to copy both files into the local `restore/` directory.

```powershell
scp prod-server:/path/to/prod_backup_YYYYMMDD_HHMMSS_schema.sql restore/
scp prod-server:/path/to/prod_backup_YYYYMMDD_HHMMSS.json.gz restore/
Get-ChildItem restore/
```

### Step 4: Verify Environment Configuration

```powershell
Select-String -Path .env -Pattern '^(MYSQL_DATABASE|MYSQL_DB_USER|DB_PASSWORD|DB_HOST|DB_PORT)='
$env:MYSQL_DATABASE = (Select-String -Path .env -Pattern '^MYSQL_DATABASE=').Line.Split('=')[1]
$env:MYSQL_DB_USER = (Select-String -Path .env -Pattern '^MYSQL_DB_USER=').Line.Split('=')[1]
$env:DB_PASSWORD = (Select-String -Path .env -Pattern '^DB_PASSWORD=').Line.Split('=')[1]
$env:DB_HOST = (Select-String -Path .env -Pattern '^DB_HOST=').Line.Split('=')[1]
$env:DB_PORT = (Select-String -Path .env -Pattern '^DB_PORT=').Line.Split('=')[1]
```

Expected values:

```
MYSQL_DATABASE=msm_workflow
MYSQL_DB_USER=root
DB_PASSWORD=********
DB_HOST=127.0.0.1
DB_PORT=3306
```

### Step 5: Reset Database

Run as MySQL admin (root):

```powershell
$env:MYSQL_PWD = $env:DB_PASSWORD
mysql.exe -h 127.0.0.1 -P 3306 -u root --execute "source scripts/reset_database.sql"
Remove-Item Env:MYSQL_PWD
```

Verification:

```powershell
$env:MYSQL_PWD = $env:DB_PASSWORD
mysql.exe -h 127.0.0.1 -P 3306 -u root msm_workflow -e "SHOW TABLES;"
mysql.exe -h 127.0.0.1 -P 3306 -u root -e "SHOW DATABASES;" | Select-String msm_workflow
Remove-Item Env:MYSQL_PWD
```

### Step 6: Apply Production Schema

```powershell
$schema = "restore/prod_backup_YYYYMMDD_HHMMSS_schema.sql"
$env:MYSQL_PWD = $env:DB_PASSWORD
mysql.exe -h 127.0.0.1 -P 3306 -u root msm_workflow --execute "source $schema"
Remove-Item Env:MYSQL_PWD
```

Checks:

```powershell
$env:MYSQL_PWD = $env:DB_PASSWORD
mysql.exe -NB -h 127.0.0.1 -P 3306 -u root msm_workflow -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='msm_workflow';"
mysql.exe -h 127.0.0.1 -P 3306 -u root msm_workflow -e "DESCRIBE workflow_job;"
Remove-Item Env:MYSQL_PWD
```

### Step 7: Extract and Convert JSON to SQL

```powershell
$backupJson = "restore/prod_backup_YYYYMMDD_HHMMSS.json.gz"
python - <<'PY'
import gzip, shutil, pathlib
src = pathlib.Path(r"restore/prod_backup_YYYYMMDD_HHMMSS.json.gz")
dst = src.with_suffix('')
with gzip.open(src, 'rb') as src_fh, open(dst, 'wb') as dst_fh:
    shutil.copyfileobj(src_fh, dst_fh)
print(f"Extracted {dst} ({dst.stat().st_size} bytes)")
PY
$env:PYTHONUTF8 = 1
poetry run python scripts/json_to_mysql.py $backupJson.Replace('.gz','')
Remove-Item Env:PYTHONUTF8
```

Checks:

```powershell
Get-ChildItem restore\prod_backup_YYYYMMDD_HHMMSS.sql
Get-Content -Path restore\prod_backup_YYYYMMDD_HHMMSS.sql -TotalCount 10
Select-String -Path restore\prod_backup_YYYYMMDD_HHMMSS.sql -Pattern 'INSERT INTO' | Measure-Object
```

### Step 8: Load Production Data

```powershell
$dataSql = "restore/prod_backup_YYYYMMDD_HHMMSS.sql"
$env:MYSQL_PWD = $env:DB_PASSWORD
mysql.exe -h 127.0.0.1 -P 3306 -u root msm_workflow --execute "source $dataSql"
Remove-Item Env:MYSQL_PWD
```

Verify counts:

```powershell
$env:MYSQL_PWD = $env:DB_PASSWORD
mysql.exe -h 127.0.0.1 -P 3306 -u root -p msm_workflow -e @"
SELECT 'workflow_job' AS table_name, COUNT(*) AS count FROM workflow_job
UNION SELECT 'workflow_staff', COUNT(*) FROM workflow_staff
UNION SELECT 'workflow_client', COUNT(*) FROM workflow_client
UNION SELECT 'job_costset', COUNT(*) FROM job_costset
UNION SELECT 'job_costline', COUNT(*) FROM job_costline;
"@
Remove-Item Env:MYSQL_PWD
```

### Step 9: Apply Django Migrations

```powershell
poetry run python manage.py migrate
poetry run python manage.py showmigrations
```

### Step 10: Load Company Defaults Fixture

```powershell
poetry run python manage.py loaddata apps/workflow/fixtures/company_defaults.json
poetry run python manage.py shell -c "from apps.workflow.models import CompanyDefaults; company = CompanyDefaults.get_instance(); print(company.company_name)"
```

### Step 11: Verify Specific Data

```powershell
$env:MYSQL_PWD = $env:DB_PASSWORD
mysql.exe -h 127.0.0.1 -P 3306 -u root -p msm_workflow -e "SELECT id,name,job_number,status FROM workflow_job ORDER BY updated_at DESC LIMIT 5;"
Remove-Item Env:MYSQL_PWD
```

### Step 12: Test Django ORM

```powershell
poetry run python - <<'PY'
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','jobs_manager.settings')
import django
django.setup()
from apps.job.models import Job
from apps.accounts.models import Staff
from apps.client.models import Client
print(f"Jobs: {Job.objects.count()}")
print(f"Staff: {Staff.objects.count()}")
print(f"Clients: {Client.objects.count()}")
job = Job.objects.order_by('-updated_at').first()
if job:
    print(f"Sample job: {job.name} (#{job.job_number}) status={job.status}")
    contact = job.contact.name if job.contact else 'None'
    print(f"Contact: {contact}")
else:
    print('ERROR: No jobs found')
PY
```

### Step 13: Create Admin User

```powershell
poetry run python - <<'PY'
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','jobs_manager.settings')
import django
django.setup()
from apps.accounts.models import Staff
user, _ = Staff.objects.get_or_create(email='defaultadmin@example.com', defaults={'first_name':'Default','last_name':'Admin'})
user.first_name = 'Default'
user.last_name = 'Admin'
user.is_staff = True
user.is_superuser = True
user.is_active = True
user.set_password('Default-admin-password')
user.save()
print('Admin ensured:', user.email)
PY
```

### Step 14: Create Dummy Files for JobFile Instances

If `pandoc`/`wkhtmltopdf`/ImageMagick are installed, run the original script:

```powershell
poetry run python scripts/recreate_jobfiles.py
```

If those tools are unavailable, generate simple text placeholders:

```powershell
poetry run python - <<'PY'
import os, pathlib
os.environ.setdefault('DJANGO_SETTINGS_MODULE','jobs_manager.settings')
import django
django.setup()
from django.conf import settings
from apps.job.models import JobFile
base = pathlib.Path(settings.DROPBOX_WORKFLOW_FOLDER)
created = skipped = 0
records = JobFile.objects.filter(file_path__isnull=False).exclude(file_path='')
for jf in records:
    dest = base / str(jf.file_path)
    if dest.exists():
        skipped += 1
        continue
    dest.parent.mkdir(parents=True, exist_ok=True)
    job_name = jf.job.name if jf.job else 'Unknown job'
    job_number = jf.job.job_number if jf.job else 'N/A'
    dest.write_text(f"Job: {job_name}\nNumber: {job_number}\nFile: {jf.filename}\n", encoding='utf-8')
    created += 1
print(f"Created placeholders: {created}, skipped existing: {skipped}, total: {records.count()}")
PY
```

### Step 15: Fix Shop Client Name

```powershell
poetry run python - <<'PY'
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','jobs_manager.settings')
import django
django.setup()
from apps.client.models import Client
shop_id = '00000000-0000-0000-0000-000000000001'
client = Client.objects.get(id=shop_id)
old_name = client.name
client.name = 'Demo Company Shop'
client.save()
print('Old name:', old_name)
print('New name:', client.name)
print('Job count:', client.jobs.count())
PY
```

### Step 16: Start Development Server

```powershell
$httpCode = curl.exe -s -o NUL -w "%{http_code}" http://localhost:8000
if ($httpCode -eq '000') {
    poetry run python manage.py runserver 0.0.0.0:8000
}
```

### Step 17: Connect to Xero OAuth (Manual)

1. Browse to http://localhost:8000 and log in with `defaultadmin@example.com` / `Default-admin-password`.
2. Go to **Xero > Connect to Xero** and complete OAuth.
3. Verify token:

```powershell
poetry run python - <<'PY'
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','jobs_manager.settings')
import django
django.setup()
from apps.workflow.models import XeroToken
from django.utils import timezone
count = XeroToken.objects.count()
if count == 0:
    raise SystemExit('CRITICAL: No Xero token found. STOP.')
token = XeroToken.objects.first()
if token.expires_at and token.expires_at < timezone.now():
    raise SystemExit('CRITICAL: Xero token expired. Reconnect before continuing.')
print('Xero OAuth token valid. Expires at:', token.expires_at)
PY
```

### Step 18: Set Xero Tenant ID

```powershell
poetry run python manage.py interact_with_xero --tenant
```

### Step 18.5: Sync Chart of Accounts

```powershell
poetry run python manage.py start_xero_sync --entity accounts
poetry run python - <<'PY'
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','jobs_manager.settings')
import django
django.setup()
from apps.workflow.models import XeroAccount
print('Total accounts synced:', XeroAccount.objects.count())
for code in ('200','300'):
    acct = XeroAccount.objects.filter(account_code=code).first()
    print(f'Account {code}:', acct.account_name if acct else 'NOT FOUND')
PY
```

### Step 19: Seed Database to Xero

Use `Start-Process` to run the long job in the background:

```powershell
$log = "logs/seed_xero_output.log"
Start-Process -FilePath "poetry" -ArgumentList "run","python","manage.py","seed_xero_from_database" -RedirectStandardOutput $log -RedirectStandardError $log -WindowStyle Hidden
Get-Content -Path $log -Wait
```

Verify completion:

```powershell
poetry run python - <<'PY'
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','jobs_manager.settings')
import django
django.setup()
from apps.client.models import Client
from apps.job.models import Job
from apps.purchasing.models import Stock
print('Clients linked to Xero:', Client.objects.filter(xero_contact_id__isnull=False).count())
print('Jobs linked to Xero:', Job.objects.filter(xero_project_id__isnull=False).count())
print('Stock items synced to Xero:', Stock.objects.filter(xero_id__isnull=False, is_active=True).count())
PY
```

### Step 20: Test Admin User Login

```powershell
poetry run python - <<'PY'
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','jobs_manager.settings')
import django
django.setup()
from django.contrib.auth import authenticate
user = authenticate(email='defaultadmin@example.com', password='Default-admin-password')
if user:
    print('Login successful:', user.email)
    print('Is staff:', user.is_staff)
else:
    raise SystemExit('Login failed - check credentials')
PY
```

### Step 21: Test Serializers

```powershell
poetry run python scripts/test_serializers.py --serializer job
# or to run all
poetry run python scripts/test_serializers.py --verbose
```

### Step 22: Test Kanban HTTP API

Ensure `manage.py runserver` is running. From PowerShell, call the script via Git Bash:

```powershell
bash ./scripts/test_kanban_api.sh
```

Interpret output exactly as documented in the Linux guide.

### Step 23: Final Application Test

```powershell
poetry run python manage.py runserver 0.0.0.0:8000
```

Open http://localhost:8000 and validate login, job list, Kanban board, and Xero status.

### Step 24: Troubleshooting Notes

Common fixes are identical to the Linux document. Use these Windows-friendly commands:

- **Reset script fails:** ensure PowerShell session is elevated and rerun Step 5.
- **Schema missing columns:** confirm you copied both `.schema.sql` and `.json.gz` from the same production snapshot.
- **Zero records after data load:**
  ```powershell
  Get-ChildItem restore\*.json
  Select-String -Path restore\*.sql -Pattern 'INSERT INTO' -Context 0,2 | Select-Object -First 5
  $env:MYSQL_PWD = $env:DB_PASSWORD
  mysql.exe -h 127.0.0.1 -P 3306 -u root msm_workflow -e "DESCRIBE workflow_job;"
  Remove-Item Env:MYSQL_PWD
  ```

## File Locations

Same as Linux version: schema/data backups live in `restore/`, reset script in `scripts/reset_database.sql`, converter in `scripts/json_to_mysql.py`, and generated SQL in `restore/prod_backup_YYYYMMDD_HHMMSS.sql`.

## Key Improvements and Reminders

- JSON-to-SQL converter handles migrations/content types.
- Backups capture `django_migrations` to preserve migration state.
- Always use Decimal, wrap risky steps in `transaction.atomic()`, and persist exceptions with `persist_app_error(...)`.
- Keep following the audit and manual validation checklist at the end of every restore.
