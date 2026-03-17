# Delivery Intelligence Platform — Disaster Recovery Runbook

Last updated: 2026-03-16  
Owner: Platform Team  
Classification: Internal — Ops

---

## 1. RTO / RPO Targets

| Tier | Scenario | RTO | RPO |
|------|----------|-----|-----|
| P1 | Full platform outage (DB + API) | < 1 h | < 15 min |
| P2 | API-only outage (DB healthy) | < 15 min | 0 (no data loss) |
| P3 | Single replica crash-loop | < 5 min | 0 (auto-healed by HPA) |

---

## 2. Backup Schedule

### PostgreSQL + PostGIS
| Backup type | Tool | Frequency | Retention | Destination |
|-------------|------|-----------|-----------|-------------|
| Continuous WAL shipping | pgBackRest / Barman | Every 5 min | 7 days | S3 bucket `s3://delivery-platform-backups/wal/` |
| Daily base backup | pg_dump (plaintext SQL + custom format) | 02:00 UTC | 30 days | S3 `s3://delivery-platform-backups/daily/` |
| Weekly full dump | pg_dumpall | Sunday 03:00 UTC | 90 days | S3 `s3://delivery-platform-backups/weekly/` |

**Verify backup integrity (run weekly):**
```bash
# Restore latest daily backup to a test instance and run smoke queries
pg_restore --list s3://delivery-platform-backups/daily/$(date +%Y-%m-%d).dump | head -20
```

### Redis
Redis is used for rate-limiting, pub/sub fan-out, and ephemeral session state — **not primary data store**.  
RDB snapshots (`SAVE` every 60 s if ≥ 1000 keys changed) are enabled. Redis data loss is acceptable up to the RPO window; the application degrades gracefully if Redis is empty.

---

## 3. Failure Scenarios & Recovery Steps

### 3.1 — API Pod Crash Loop (P3)

**Symptoms:** Kubernetes `CrashLoopBackOff`; Alertmanager fires `FrequentPodRestarts`.

```bash
# 1. Inspect pod logs
kubectl logs -n delivery-platform -l app.kubernetes.io/name=delivery-platform --previous

# 2. Describe for OOMKill or config errors
kubectl describe pod -n delivery-platform -l app.kubernetes.io/name=delivery-platform

# 3. If OOMKill, scale up memory limit
helm upgrade delivery-platform deploy/helm/delivery-platform/ \
  -f deploy/helm/delivery-platform/values-prod.yaml \
  --set resources.limits.memory=2Gi --reuse-values

# 4. If bad config / secret, fix the secret then trigger rolling restart
kubectl rollout restart deployment/delivery-platform -n delivery-platform
```

---

### 3.2 — Database Unavailable (P1/P2)

**Symptoms:** `PostgresDown` alert; API returns 500 on all data endpoints; `/health` still returns 200.

#### Option A — Failover to read replica (if streaming replication is configured)
```bash
# Promote the replica
pg_ctl promote -D /var/lib/postgresql/data

# Update the DATABASE_URL secret to point to the replica's endpoint
kubectl create secret generic app-secrets -n delivery-platform \
  --from-literal=DATABASE_URL="postgresql+asyncpg://user:pass@replica-host:5432/deliverydb" \
  --dry-run=client -o yaml | kubectl apply -f -

# Rolling restart to pick up new secret
kubectl rollout restart deployment/delivery-platform -n delivery-platform
```

#### Option B — Restore from S3 backup (RDS / bare-metal)
```bash
# 1. Create a fresh PostgreSQL 15 instance with PostGIS
psql -c "CREATE EXTENSION IF NOT EXISTS postgis;"

# 2. Restore from latest daily dump
aws s3 cp s3://delivery-platform-backups/daily/$(date +%Y-%m-%d).dump /tmp/restore.dump
pg_restore --no-owner --role=deliveryapp -d deliverydb /tmp/restore.dump

# 3. Apply WAL segments from the snapshot forward (if using pgBackRest)
pgbackrest --stanza=main restore --type=time "--target=$(date -u +'%Y-%m-%d %H:%M:%S')"

# 4. Run Alembic to validate schema is at head
DATABASE_URL="postgresql+asyncpg://..." alembic upgrade head

# 5. Update DATABASE_URL secret and rolling restart (see Option A above)
```

---

### 3.3 — Redis Unavailable (P2 degraded)

**Symptoms:** `RedisDown` alert; rate-limiter falls back to in-memory (per-instance); WebSocket pub/sub fan-out stops working (single-node delivery still works).

```bash
# 1. Check Redis pod / service
kubectl get pods -n delivery-platform -l app=redis
kubectl logs -n delivery-platform -l app=redis --previous

# 2. If data lost but instance recovered, no action needed — Redis repopulates
# 3. If instance unrecoverable, spin a new one
helm upgrade redis bitnami/redis -n delivery-platform --reuse-values

# 4. Verify connectivity from API pod
kubectl exec -n delivery-platform deploy/delivery-platform -- \
  python -c "import redis.asyncio as r; import asyncio; asyncio.run(r.from_url('$REDIS_URL').ping())"
```

---

### 3.4 — Full Cluster Loss (P1)

```bash
# 1. Provision new K8s cluster (EKS/GKE/AKS)
# 2. Install cert-manager, nginx-ingress, external-secrets-operator
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/latest/download/cert-manager.yaml

# 3. Restore secrets from Vault / AWS Secrets Manager into K8s
# (assumes External Secrets Operator is bootstrapped)
kubectl apply -f deploy/k8s/external-secrets.yaml

# 4. Restore database (Section 3.2 Option B above)

# 5. Deploy the platform
helm upgrade --install delivery-platform deploy/helm/delivery-platform/ \
  -f deploy/helm/delivery-platform/values-prod.yaml \
  --set secret.SECRET_KEY="..." \
  --set secret.DATABASE_URL="..." \
  --set secret.REDIS_URL="..."

# 6. Verify
kubectl rollout status deployment/delivery-platform -n delivery-platform
curl -f https://api.deliveryplatform.com/health
```

---

## 4. Backup Verification (Monthly)

Run this checklist on the first Monday of each month:

- [ ] `aws s3 ls s3://delivery-platform-backups/daily/ | tail -5` — confirm recent backups exist
- [ ] Restore latest daily dump to staging DB and run: `SELECT count(*) FROM packages; SELECT count(*) FROM users;`
- [ ] Verify Alembic head matches production: `alembic heads` on staging == production
- [ ] Test alert routing: `amtool alert add alertname=TestAlert severity=critical` → confirm Slack message received
- [ ] Rotate `SECRET_KEY` on staging and verify JWT re-issue flow works

---

## 5. Contact Escalation

| Level | Who | When |
|-------|-----|------|
| L1 | On-call engineer (PagerDuty rotation) | Any P1/P2 alert |
| L2 | Platform Team Lead | RTO < 30 min remaining |
| L3 | CTO | Full data loss risk or RTO breach |