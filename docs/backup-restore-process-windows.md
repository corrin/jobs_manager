# Production Data Backup and Restore Process (Windows 11, PowerShell)

Use this when restoring production data onto a Windows 11 development machine. Commands assume PowerShell 7+, MySQL client tools available on `PATH`, and that you are running in the project root (`jobs_manager`).

## MySQL Connection Pattern (Windows)

All MySQL commands must include `-h "$env:DB_HOST" -P "$env:DB_PORT"`. Set `MYSQL_PWD` before a command and remove it immediately after.

```powershell
$env:MYSQL_PWD = $env:DB_PASSWORD
mysql.exe -h $env:DB_HOST -P $env:DB_PORT -u $env:MYSQL_DB_USER $env:MYSQL_DATABASE -e "SHOW TABLES;"
Remove-Item Env:MYSQL_PWD
```

Always load SQL files with `--execute "source path\to\file.sql"` (avoid `< file.sql` which fails on large files).

## CRITICAL: No Workarounds

The UAT job runs unattended. Do not improvise steps; fix root causes before proceeding.

## Target State (end of process)

Backend on :8000, frontend on :5173, ngrok tunnels for both, database fully reset/restored, migrations applied, connected to dev Xero with tokens refreshed by `run_scheduler`, LLM keys configured, and Playwright tests passing.

## Order Enforcement

Complete steps in order. Testing only after Step 21 (Xero OAuth) is finished.

## Production Steps

### Step 1: Create Backup (Production host)

Run as the production Django user:

```bash
python manage.py backport_data_backup
```

Expect `/tmp/prod_backup_*_complete.zip` (5–25MB).

### Step 2: Transfer Backup to Development

From your Windows dev box (OpenSSH is built in):

```powershell
scp prod-server:/tmp/prod_backup_YYYYMMDD_HHMMSS_complete.zip restore/
```

Verify:

```powershell
Get-ChildItem restore\*.zip
```

### Step 3: Extract Backup Files

```powershell
Expand-Archive -Path restore\prod_backup_YYYYMMDD_HHMMSS_complete.zip -DestinationPath restore -Force
Get-ChildItem restore
# Expect: prod_backup_*.json.gz and prod_backup_*.schema.sql
```

## Development Steps (Windows 11)

### Step 4: Verify Environment Configuration

```powershell
Select-String -Path .env -Pattern '^(MYSQL_DATABASE|MYSQL_DB_USER|DB_PASSWORD|DB_HOST|DB_PORT)='
```

Ensure values look like:

```
MYSQL_DATABASE=msm_workflow
MYSQL_DB_USER=django_user
DB_PASSWORD=your_dev_password
DB_HOST=localhost
DB_PORT=3306
```

If missing, update `.env`. When scripting, pass env vars explicitly.

### Step 5: Reset Database

Run as a user with MySQL admin rights (no sudo on Windows):

```powershell
$env:MYSQL_PWD = '<mysql_root_password_if_needed>'
mysql.exe -u root --execute="source scripts/reset_database.sql"
Remove-Item Env:MYSQL_PWD
```

Check the empty database:

```powershell
$env:MYSQL_PWD = $env:DB_PASSWORD
mysql.exe -h $env:DB_HOST -P $env:DB_PORT -u $env:MYSQL_DB_USER $env:MYSQL_DATABASE -e "SHOW TABLES;"
mysql.exe -h $env:DB_HOST -P $env:DB_PORT -u $env:MYSQL_DB_USER -e "SHOW DATABASES;" | Select-String $env:MYSQL_DATABASE
Remove-Item Env:MYSQL_PWD
```

### Step 6: Apply Production Schema

```powershell
$env:MYSQL_PWD = $env:DB_PASSWORD
mysql.exe -h $env:DB_HOST -P $env:DB_PORT -u $env:MYSQL_DB_USER $env:MYSQL_DATABASE --execute="source restore\\prod_backup_YYYYMMDD_HHMMSS.schema.sql"
Remove-Item Env:MYSQL_PWD
```

Quick checks:

```powershell
$env:MYSQL_PWD = $env:DB_PASSWORD
mysql.exe -h $env:DB_HOST -P $env:DB_PORT -u $env:MYSQL_DB_USER $env:MYSQL_DATABASE -e "SHOW TABLES;" | Measure-Object
mysql.exe -h $env:DB_HOST -P $env:DB_PORT -u $env:MYSQL_DB_USER $env:MYSQL_DATABASE -e "DESCRIBE workflow_job;" | Select-String contact_person
Remove-Item Env:MYSQL_PWD
```

### Step 7: Extract and Convert JSON to SQL

Decompress with Python (works even if gzip/7zip are missing):

```powershell
python - <<'PY'
import gzip, shutil, pathlib
src = pathlib.Path("restore/prod_backup_YYYYMMDD_HHMMSS.json.gz")
dst = src.with_suffix("")  # drop .gz
with gzip.open(src, "rb") as f_in, open(dst, "wb") as f_out:
    shutil.copyfileobj(f_in, f_out)
PY
```

Convert JSON to SQL:

```powershell
python scripts/json_to_mysql.py restore\prod_backup_YYYYMMDD_HHMMSS.json
Get-ChildItem restore\prod_backup_YYYYMMDD_HHMMSS.sql
```

### Step 8: Load Production Data

```powershell
$env:MYSQL_PWD = $env:DB_PASSWORD
mysql.exe -h $env:DB_HOST -P $env:DB_PORT -u $env:MYSQL_DB_USER $env:MYSQL_DATABASE --execute="source restore\\prod_backup_YYYYMMDD_HHMMSS.sql"
Remove-Item Env:MYSQL_PWD
```

Sanity counts:

```powershell
$env:MYSQL_PWD = $env:DB_PASSWORD
mysql.exe -h $env:DB_HOST -P $env:DB_PORT -u $env:MYSQL_DB_USER $env:MYSQL_DATABASE -e @"
SELECT 'workflow_job' as table_name, COUNT(*) as count FROM workflow_job
UNION SELECT 'workflow_staff', COUNT(*) FROM workflow_staff
UNION SELECT 'workflow_client', COUNT(*) FROM workflow_client
UNION SELECT 'job_costset', COUNT(*) FROM job_costset
UNION SELECT 'job_costline', COUNT(*) FROM job_costline;
"@
Remove-Item Env:MYSQL_PWD
```

### Step 9: Apply Django Migrations

```powershell
python manage.py migrate
python manage.py showmigrations
# Expect all marked with [X]
```

### Step 10: Load Company Defaults Fixture

```powershell
python manage.py loaddata apps/workflow/fixtures/company_defaults.json
python scripts/restore_checks/check_company_defaults.py
```

### Step 11: Load AI Providers Fixture (Optional)

Copy `apps/workflow/fixtures/ai_providers.json.example` to `ai_providers.json`, add real API keys, then:

```powershell
python manage.py loaddata apps/workflow/fixtures/ai_providers.json
python scripts/restore_checks/check_ai_providers.py
```

### Step 12: Verify Specific Data

```powershell
$env:MYSQL_PWD = $env:DB_PASSWORD
mysql.exe -h $env:DB_HOST -P $env:DB_PORT -u $env:MYSQL_DB_USER $env:MYSQL_DATABASE -e @"
SELECT id, name, job_number, status
FROM workflow_job
WHERE name LIKE '%test%' OR name LIKE '%sample%'
LIMIT 5;
"@
Remove-Item Env:MYSQL_PWD
```

### Step 13: Test Django ORM

```powershell
python scripts/restore_checks/check_django_orm.py
```

### Step 14: Create Admin User

```powershell
python scripts/restore_checks/create_admin_user.py
python scripts/restore_checks/check_admin_user.py
```

### Step 15: Create Dummy Files for JobFile Instances

```powershell
python scripts/recreate_jobfiles.py
python scripts/restore_checks/check_jobfiles.py
```

### Step 16: Fix Shop Client Name

```powershell
python scripts/restore_checks/fix_shop_client.py
python scripts/restore_checks/check_shop_client.py
```

### Step 17: Ensure Test Client Exists

```powershell
python scripts/restore_checks/check_test_client.py
```

### Step 18: Start ngrok Tunnels (skip for UAT)

Run in separate terminals:

```powershell
ngrok http 8000 --domain=your-backend.ngrok-free.app
ngrok http 5173 --domain=your-frontend.ngrok-free.app
```

Confirm each shows a public Forwarding URL.

### Step 19: Start Development Server (skip for UAT)

```powershell
curl.exe -s -o $null -w "%{http_code}`n" http://localhost:8000
# If not 302, start via VS Code Debug (F5) or runserver.
```

### Step 20: Start Frontend (skip for UAT)

```powershell
curl.exe -s -o $null -w "%{http_code}`n" http://localhost:5173
# If not 200, from ../jobs_manager_front: npm run dev
```

### Step 21: Connect to Xero OAuth (required before tests)

```powershell
pushd ..\jobs_manager_front
npx tsx tests/scripts/xero-login.ts
popd
python scripts/restore_checks/check_xero_token.py
```

### Step 22: Set Xero Tenant ID

```powershell
python manage.py xero --tenant
```

### Step 23: Sync Chart of Accounts from Xero

```powershell
python manage.py start_xero_sync --entity accounts
python scripts/restore_checks/check_xero_accounts.py
```

### Step 24: Sync Pay Items from Xero

```powershell
python manage.py xero --configure-payroll
```

### Step 25: Seed Database to Xero (long-running)

Run in background using `Start-Process`:

```powershell
Start-Process -FilePath python -ArgumentList "manage.py", "seed_xero_from_database" -RedirectStandardOutput logs\seed_xero_output.log -RedirectStandardError logs\seed_xero_output.log
Get-Content logs\seed_xero_output.log -Tail 50 -Wait
```

After completion:

```powershell
python scripts/restore_checks/check_xero_seed.py
```

### Step 26: Sync Xero

```powershell
python manage.py start_xero_sync
```

### Step 27: Start Background Scheduler

Run in a dedicated terminal:

```powershell
python manage.py run_scheduler
```

### Step 28: Test Serializers

```powershell
python scripts/restore_checks/test_serializers.py --verbose
```

### Step 29: Test Kanban HTTP API

```powershell
python scripts/restore_checks/test_kanban_api.py
```

### Step 30: Run Playwright Tests

```powershell
pushd ..\jobs_manager_front
npx playwright test
popd
```

## Troubleshooting (Windows)

- Permission denied on reset: ensure MySQL root credentials are correct and PowerShell is running elevated if needed.
- Missing MySQL client: install MySQL Shell/Workbench or add `mysql.exe` to PATH (typically `C:\Program Files\MySQL\MySQL Server 8.0\bin`).
- `Expand-Archive` errors: unblock the zip (`Unblock-File restore\prod_backup_*.zip`) or re-download.

## File Locations

- Combined backup: `/tmp/prod_backup_YYYYMMDD_HHMMSS_complete.zip` (production)
- Restored artifacts: `restore\prod_backup_*.schema.sql`, `restore\prod_backup_*.json.gz`, generated `restore\prod_backup_*.sql`
- Reset script: `scripts\reset_database.sql`
- Converter: `scripts\json_to_mysql.py`
