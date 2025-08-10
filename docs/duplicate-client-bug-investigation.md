# Duplicate Client Bug Investigation Plan

## Problem Statement

After running the backup-restore process, we discovered duplicate client records in the database. Investigation needed to determine the source and fix the root cause.

## Current Situation - 2025-08-10

After completing the restore process with our fixed `sync_clients()` logic, we still have duplicate client records:

```
Hamilton Group: 2 records
Preston, Alexander and Garcia: 2 records  
Molina Inc: 2 records
Roman Ltd: 2 records
Martinez PLC: 2 records
... (27 total duplicate names)
```

## Investigation Plan

### 1. Determine Source of Duplicates

We need to systematically check each step to identify where duplicates are introduced:

#### Step 8A: Check Production Data After Load
**Purpose:** Verify if duplicates exist in the restored production data itself.

**Command:**
```bash
MYSQL_PWD=hRjATdbwGhTtsR8e mysql -u django_user msm_workflow -e "
SELECT name, COUNT(*) as count, GROUP_CONCAT(id) as client_ids
FROM workflow_client
GROUP BY name
HAVING COUNT(*) > 1
ORDER BY count DESC
LIMIT 10;
"
```

#### Step 9A: Check After Django Migrations  
**Purpose:** Verify if Django migrations create duplicate records.

**Command:** (Same as Step 8A - run after migrations)

#### Step 10A: Check After Company Defaults Fixture
**Purpose:** Verify if fixtures create duplicate records.

**Command:** (Same as Step 8A - run after fixture loading)

#### Step 20A: Check After Xero Sync
**Purpose:** Verify if Xero sync creates duplicate records.

**Command:** (Same as Step 8A - run after sync)

### 2. Source Data Investigation

#### Check JSON Backup for Duplicates
**Purpose:** Verify if the production backup itself contains duplicate client names.

**Command:**
```bash
python -c "
import json
import gzip
from collections import Counter

with gzip.open('restore/prod_backup_YYYYMMDD_HHMMSS.json.gz', 'rt') as f:
    data = json.load(f)

clients = [item for item in data if item['model'] == 'client.client']
names = [client['fields']['name'] for client in clients]
duplicates = {name: count for name, count in Counter(names).items() if count > 1}

print(f'Total clients in JSON: {len(clients)}')
print(f'Duplicate names in JSON: {len(duplicates)}')
for name, count in sorted(duplicates.items(), key=lambda x: x[1], reverse=True)[:10]:
    print(f'  {name}: {count} records')
"
```

### 3. Possible Scenarios

#### Scenario A: Production Database Has Duplicates
- **Evidence:** Duplicates found in Step 8A check
- **Cause:** Production database actually contains duplicate client names
- **Solution:** This is expected production data - no bug in our process

#### Scenario B: JSON Backup Creates Duplicates  
- **Evidence:** No duplicates in production, but duplicates in JSON
- **Cause:** Bug in `backport_data_backup.py` command
- **Solution:** Fix the backup script

#### Scenario C: SQL Conversion Creates Duplicates
- **Evidence:** Clean JSON, duplicates after Step 8
- **Cause:** Bug in `json_to_mysql.py` script  
- **Solution:** Fix the conversion script

#### Scenario D: Django Migrations Create Duplicates
- **Evidence:** Clean after Step 8, duplicates after Step 9
- **Cause:** Django migration creates duplicate records
- **Solution:** Fix the problematic migration

#### Scenario E: Fixtures Create Duplicates
- **Evidence:** Clean after Step 9, duplicates after Step 10
- **Cause:** Company defaults or other fixtures add duplicates
- **Solution:** Fix the fixture data

#### Scenario F: Xero Sync Creates Duplicates
- **Evidence:** Clean until Step 20, duplicates after sync
- **Cause:** Bug in sync logic (despite our fixes)
- **Solution:** Further fix the sync logic

### 4. Resolution Strategy

1. **Identify the exact step** where duplicates first appear
2. **Investigate the root cause** in that step's process
3. **Fix the underlying issue** (not just work around it)
4. **Add validation** to prevent future occurrences
5. **Re-test the entire process** from scratch

### 5. Prevention Measures

Add duplicate detection checks to backup-restore-process.md after each major step:

- **After Step 8:** Check for duplicates after data load
- **After Step 9:** Check for duplicates after migrations  
- **After Step 10:** Check for duplicates after fixtures
- **After Step 20:** Check for duplicates after sync

If duplicates are found at any step, **FAIL EARLY** and investigate before proceeding.

## Success Criteria

- [ ] Identify exact step where duplicates are introduced
- [ ] Understand root cause (production data vs process bug)
- [ ] Fix or document the issue appropriately  
- [ ] Complete restore process without unexpected duplicates
- [ ] Add permanent validation to catch regressions

## Investigation Results

### Status: IN PROGRESS

**Next Steps:**
1. Reset database and restart restore process
2. Run duplicate check after each major step
3. Identify where duplicates first appear
4. Fix the root cause