# Disaster Recovery & Database Backup Runbook

**App:** ShiftHandover NOC Operations Platform  
**Environment:** GCP VM (`10.82.143.226`), Docker Compose, MySQL 8.0  
**Last reviewed:** 2026-05-07

---

## Recovery Objectives

| Metric | Target |
|--------|--------|
| **RTO** (Recovery Time Objective) | ≤ 2 hours for full service restoration |
| **RPO** (Recovery Point Objective) | ≤ 8 hours (3× daily backups) |
| **Backup retention** | 7 days of daily snapshots |
| **Backup location** | `/home/shifthandoversajid/backups/db/` on prod VM |

---

## Backup Strategy

### Automated Database Backups

`scripts/db_backup.sh` runs via cron **3× daily** (recommended schedule below).
It uses `mysqldump --single-transaction` inside the running container so the DB stays live.

```bash
# Recommended crontab (crontab -e on prod VM)
0 2  * * * /home/shifthandoversajid/shifthandover_v3/scripts/db_backup.sh
0 10 * * * /home/shifthandoversajid/shifthandover_v3/scripts/db_backup.sh
0 18 * * * /home/shifthandoversajid/shifthandover_v3/scripts/db_backup.sh
```

Backups are written to `/home/shifthandoversajid/backups/db/db_backup_<timestamp>.sql.gz`.
Files older than 7 days are automatically deleted.

### Verify Backup Health

```bash
# Check recent backups
ls -lh ~/backups/db/db_backup_*.sql.gz | tail -5

# Tail backup log
tail -30 ~/backups/backup.log

# Quick sanity — count tables in latest backup
LATEST=$(ls -t ~/backups/db/db_backup_*.sql.gz | head -1)
zcat $LATEST | grep "^CREATE TABLE" | wc -l   # expect ~30+
```

### Manual On-Demand Backup

```bash
docker exec shift-db mysqldump -u root -prootpassword \
    --single-transaction --routines --triggers \
    --databases shifthandover | gzip > ~/backups/db/manual_$(date +%Y%m%d_%H%M%S).sql.gz
```

---

## Failure Scenarios & Recovery Steps

### Scenario 1 — Application Container Down (most common)

**Symptoms:** `/health` returns 5xx or times out; DB is healthy.

```bash
# SSH into VM
ssh -i "/path/to/gcp-key" shifthandoversajid@10.82.143.226

# Check container status
docker-compose -f docker-compose.prod.yml ps

# Restart only the web container
docker-compose -f docker-compose.prod.yml restart web

# If restart fails — rebuild
docker-compose -f docker-compose.prod.yml up -d --build web

# Verify
curl -s http://localhost:5000/health
```

**Expected RTO:** 5–10 minutes

---

### Scenario 2 — Bad Deployment (rollback needed)

**Symptoms:** App starts but pages error after a recent deploy.

```bash
# 1. Restore DB first if schema changed (run before code rollback)
LATEST_BACKUP=$(ls -t ~/backups/db/db_backup_*.sql.gz | head -1)
zcat $LATEST_BACKUP | docker exec -i shift-db mysql -u root -prootpassword shifthandover

# 2. Roll back code to previous commit
cd ~/shifthandover_v3/
git log --oneline -5                    # identify the last known-good commit
git checkout <previous-good-commit>     # e.g. git checkout abc1234

# 3. Rebuild and restart
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d --build

# 4. Verify
curl -s http://localhost:5000/health
docker-compose -f docker-compose.prod.yml logs web --tail=50
```

**Expected RTO:** 20–30 minutes

---

### Scenario 3 — Database Container Down

**Symptoms:** App shows DB connection errors; `docker ps` shows `shift-db` exited.

```bash
# Restart the DB container
docker-compose -f docker-compose.prod.yml restart db

# Check DB logs for errors
docker-compose -f docker-compose.prod.yml logs db --tail=50

# If DB won't start — check disk space first
df -h

# Restart both in order
docker-compose -f docker-compose.prod.yml stop web celery-worker celery-beat
docker-compose -f docker-compose.prod.yml start db
sleep 15  # wait for MySQL readiness
docker-compose -f docker-compose.prod.yml start web celery-worker celery-beat
```

**Expected RTO:** 10–20 minutes

---

### Scenario 4 — Full VM Recovery (worst case)

**Symptoms:** VM is unreachable or data volume is corrupted.

```bash
# 1. Provision a new GCP VM (same spec)
# 2. Install Docker and Docker Compose
# 3. Clone the repo
git clone https://git.garage.epam.com/shift-handover-automation/shifthandover_v3.git
cd shifthandover_v3/

# 4. Restore secrets (copy from secure vault or backup)
mkdir -p secrets/
# Copy: flask_secret_key, database_url, sso_encryption_key,
#        secrets_master_key, mysql_password, smtp_username, smtp_password

# 5. Start the stack
docker-compose -f docker-compose.prod.yml up -d --build

# 6. Restore DB from latest backup (transfer from backup storage)
scp user@backup-server:~/backups/db/db_backup_latest.sql.gz .
zcat db_backup_latest.sql.gz | docker exec -i shift-db mysql -u root -prootpassword

# 7. Verify
curl -s http://localhost:5000/health
```

**Expected RTO:** 1–2 hours

---

### Scenario 5 — Celery Beat Not Firing Scheduled Tasks

**Symptoms:** Scheduled email digests or ServiceNow polling stopped.

```bash
# Check beat container
docker-compose -f docker-compose.prod.yml ps celery-beat
docker-compose -f docker-compose.prod.yml logs celery-beat --tail=30

# Restart beat (schedule state is persisted in named volume celerybeat_data)
docker-compose -f docker-compose.prod.yml restart celery-beat

# Verify Redis is healthy
docker-compose -f docker-compose.prod.yml exec redis redis-cli ping  # expect PONG
```

---

## Post-Recovery Checklist

After any recovery action:

- [ ] `/health` endpoint returns HTTP 200
- [ ] Can log in with a test account
- [ ] Dashboard loads without errors
- [ ] Check `docker-compose logs web --tail=100` for new errors
- [ ] Verify latest DB backup is non-zero: `ls -lh ~/backups/db/ | tail -3`
- [ ] Notify NOC team lead that recovery is complete
- [ ] Document incident in the shift handover system

---

## Contacts & Escalation

| Role | Action |
|------|--------|
| On-call engineer | First responder — follow scenarios above |
| Team lead | Escalate if RTO > 30 min |
| EPAM infra | GCP VM/disk issues beyond app scope |
