# Production Deployment Guide — Local → VM

**Last updated:** 2026-05-07 (verified against prod dump)
**Branch to deploy:** `CTCOAMSHM-1-realtime-collab-handover`
**Prod VM:** `10.82.143.226` (GCP), user `shifthandoversajid`, app at `~/shifthandover_v3/`

---

## What Needs to Change on Prod

This was verified by importing the prod DB dump locally and testing. The exact gaps are:

### DB — Columns to ADD (confirmed missing)

| Table | Column | Why needed |
|---|---|---|
| `incident` | `is_resolved` | Carryforward feature — tracks whether incident was resolved |
| `incident` | `resolved_at` | Carryforward feature — timestamp for 72h closed window |
| `team_member` | `scheduling_role` | Roster scheduler — `lead` or `support` role |
| `team_member` | `lead_shift` | Roster scheduler — preferred shift code |

### DB — Tables (already present on prod, no action needed)

These tables were already in the prod DB (likely created manually earlier):
`handover_session`, `section_lock`, `handover_change`, `draft_incident`, `draft_key_point`, `email_delivery_log`, `team.email_recipients`, `team.priority_alert_recipients`

### Web App — Files (all handled by git pull)

Key files that changed and must be deployed:

| File | What changed |
|---|---|
| `templates/handover_form.html` | Unified incident section (5 cards → 1 Status dropdown) |
| `routes/handover.py` | New incident handling, carryforward logic, 7-day cutoff |
| `routes/collaboration.py` | Real-time collaborative editing routes |
| `routes/collab_sse.py` | SSE push for collab |
| `routes/roster_scheduler.py` | Roster scheduler API |
| `models/collaboration.py` | DB models for collab tables |
| `models/models.py` | `is_resolved`, `resolved_at`, `scheduling_role`, `lead_shift` fields |
| `static/js/yjs.bundle.js` | Self-hosted YJS bundle (91KB) — **must be present** |
| `static/js/collaboration.js` | Collab UI logic |
| `static/js/collaborative_handover_v2.js` | Collab handover form JS |
| `static/js/yjs-sse-provider.js` | YJS SSE provider |
| `app.py` | Blueprint registrations for new routes |
| `start.sh` | Alembic migration runner on startup |

Everything above is on the `CTCOAMSHM-1-realtime-collab-handover` branch — a single `git pull` picks up all of it.

---

## Step 1 — SSH into the VM

```bash
chmod 600 "/Users/sajid_mohammad/Downloads/ssh keys/my-gcp-key"
ssh -i "/Users/sajid_mohammad/Downloads/ssh keys/my-gcp-key" shifthandoversajid@10.82.143.226
```

---

## Step 2 — Backup the Database First

```bash
docker exec shift-db mysqldump -u root -prootpassword --single-transaction shifthandover > ~/backup_before_deploy_$(date +%Y%m%d_%H%M%S).sql
ls -lh ~/backup_before_deploy_*.sql   # confirm non-zero size
```

**Do not proceed if the backup file is 0 bytes.**

---

## Step 3 — Run the 4 DB Migrations (columns only)

These are the ONLY schema changes needed. All new tables already exist on prod.

```bash
docker exec shift-db mysql -u root -prootpassword shifthandover << 'EOF'

-- 1. Incident carryforward columns
ALTER TABLE incident ADD COLUMN is_resolved TINYINT(1) NOT NULL DEFAULT 0;
ALTER TABLE incident ADD COLUMN resolved_at DATETIME NULL;

-- 2. Roster scheduler columns
ALTER TABLE team_member ADD COLUMN scheduling_role VARCHAR(16) NOT NULL DEFAULT 'support';
ALTER TABLE team_member ADD COLUMN lead_shift VARCHAR(8) NULL DEFAULT 'E';

-- 3. Backfill scheduling_role for any NULLs (safety)
UPDATE team_member SET scheduling_role = 'support' WHERE scheduling_role IS NULL OR scheduling_role = '';

-- 4. Register Alembic version so startup doesn't re-run migrations
CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY);
INSERT IGNORE INTO alembic_version VALUES ('fix_scheduling_role_nullable');

EOF
```

**Verify:**
```bash
docker exec shift-db mysql -u root -prootpassword shifthandover \
  -e "DESCRIBE incident;" | grep -E "is_resolved|resolved_at"

docker exec shift-db mysql -u root -prootpassword shifthandover \
  -e "SELECT * FROM alembic_version;"
```

Expected output:
```
is_resolved   tinyint(1)   NO    0
resolved_at   datetime     YES   NULL
version_num: fix_scheduling_role_nullable
```

---

## Step 4 — Update the Code

```bash
cd ~/shifthandover_v3/

# Check current state
git log --oneline -3

# Pull the branch
git fetch origin
git checkout CTCOAMSHM-1-realtime-collab-handover
git pull origin CTCOAMSHM-1-realtime-collab-handover
```

> **If the branch doesn't exist on the remote yet**, push it first from your local machine:
> ```bash
> # On LOCAL machine:
> git push origin CTCOAMSHM-1-realtime-collab-handover
> ```
> Then retry the pull on the VM.

---

## Step 5 — Verify the YJS Bundle

```bash
ls -lh ~/shifthandover_v3/static/js/yjs.bundle.js
# Expected: ~91KB
```

If missing, copy from local machine:
```bash
# On LOCAL machine:
scp -i "/Users/sajid_mohammad/Downloads/ssh keys/my-gcp-key" \
  /Users/sajid_mohammad/Downloads/Documents/shifthandover_v4/shifthandover_v3.5/static/js/yjs.bundle.js \
  shifthandoversajid@10.82.143.226:~/shifthandover_v3/static/js/
```

---

## Step 6 — Rebuild and Restart Containers

```bash
cd ~/shifthandover_v3/

docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d --build

# Watch logs until Flask starts (Ctrl+C to stop)
docker-compose -f docker-compose.prod.yml logs -f web
# Wait for: "Booting worker with pid" or "Listening at: http://0.0.0.0:5000"
```

---

## Step 7 — Verify Deployment

```bash
# App responds
curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/login
# Expected: 200

# New columns present
docker exec shift-db mysql -u root -prootpassword shifthandover \
  -e "DESCRIBE incident;" | grep -E "is_resolved|resolved_at"

# Container is healthy
docker ps | grep shift-web
```

---

## Rollback Plan

**Production deployments are triggered manually** (`when: manual` in GitLab CI) as a deliberate safety gate for this 24x7 NOC platform. This ensures a human reviews the deploy at the time it fires, not just when the MR was merged.

### Step-by-step rollback

```bash
# 1. Identify the last known-good commit
cd ~/shifthandover_v3/
git log --oneline -10

# 2. Take a safety backup before rollback (belt-and-suspenders)
docker exec shift-db mysqldump -u root -prootpassword \
    --single-transaction shifthandover | gzip > ~/backups/db/pre_rollback_$(date +%Y%m%d_%H%M%S).sql.gz

# 3. Roll back the code
docker-compose -f docker-compose.prod.yml down
git checkout <previous-good-commit>        # e.g. git checkout abc1234

# 4. Rebuild and restart
docker-compose -f docker-compose.prod.yml up -d --build

# 5. Verify the app is healthy
curl -s http://localhost:5000/health
docker-compose -f docker-compose.prod.yml logs web --tail=50
```

### DB restore (only if schema change caused the failure)

```bash
# Restore from the pre-deploy backup taken in Step 2 of deployment
BACKUP=~/backups/db/pre_rollback_<timestamp>.sql.gz
zcat $BACKUP | docker exec -i shift-db mysql -u root -prootpassword shifthandover
```

> **Additive columns are safe to leave:** columns like `is_resolved`, `resolved_at`, `scheduling_role`, `lead_shift` are nullable with defaults — rolling back the code while leaving them in the DB is harmless and avoids a DB restore entirely.

### Rollback decision matrix

| Issue | Code rollback | DB restore needed? |
|-------|--------------|-------------------|
| App crashes on startup | Yes | No (unless migration ran) |
| Feature behaves incorrectly | Yes | Rarely |
| Migration added a bad column | Yes | Yes |
| Data corruption detected | Yes | Yes — restore immediately |

---

## Summary Checklist

- [ ] DB backup taken
- [ ] 4 ALTER TABLE columns added
- [ ] `alembic_version` row inserted
- [ ] `git pull` on CTCOAMSHM-1 branch
- [ ] `yjs.bundle.js` present (check size ~91KB)
- [ ] Container rebuilt and started
- [ ] Login verified (HTTP 200)
- [ ] New columns verified in DB
