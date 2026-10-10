# Production Readiness Plan — Delivery Intelligence Platform

**Created:** 2026-10-07
**Branch at assessment:** `rehab-investigation-20261001` (35 commits ahead of `main`)
**Baseline readiness:** **42%**
**Target:** 100% = safe to run real deliveries for real customers

---

## How progress is measured

Readiness is scored across 10 areas, weighted by how much each matters to a safe launch. Each phase below closes out one area. Each area starts with partial credit for work that already exists (Helm charts, CI pipeline, 173 passing tests, production config checks, and so on).

| # | Area | Weight | Baseline credit | Readiness after phase |
|---|------|-------:|----------------:|----------------------:|
| 0 | Secrets & credential exposure | 10 | 3 | **49%** |
| 1 | Repository hygiene | 10 | 2 | **57%** |
| 2 | API contract & in-flight rehab work | 10 | 5 | **62%** |
| 3 | Test suite reliability | 15 | 8 | **69%** |
| 4 | Application security hardening | 15 | 6 | **78%** |
| 5 | Data, migrations & backups | 8 | 5 | **81%** |
| 6 | Build & deployment pipeline | 12 | 6 | **87%** |
| 7 | Observability & operations | 10 | 4 | **93%** |
| 8 | Client apps (web + mobile) | 5 | 2 | **96%** |
| 9 | Documentation & release | 5 | 1 | **100%** |
|   | **Total** | **100** | **42** | |

**Scoring a phase partway through:** each task in a phase is worth an equal share of the points that phase still has to earn. Example: Phase 0 has 7 points left across 7 tasks, so each finished task adds 1%.

After each phase, fill in its **Changes made** log and its **Checkpoint** line. A phase counts as done only when every item under its *Verify* heading passes.

---

## Phase 0 — Secrets & credential exposure  (49% when done)

**Why first:** credentials are exposed now. Every day they stay valid adds risk, and nothing later in the plan reduces it.

### Planned changes
Phase 0 now has 9 tasks (2 were added after the history scan), each worth 7/9 ≈ 0.8%.

- [ ] **Rotate the Expo account password** *(owner action)*. It was committed in plain text in `RUNBOOK.md` and has been in git history since at least commit `f68d80f1`. ✅ Removed from the file. 2026-10-09: two-factor authentication turned on and access tokens revoked. *Still to do:* change the password itself.
- [ ] **Revoke the leaked TomTom API key** *(owner action, added after scan)*. A real key was committed to `.env.example` in `70fab920` and `bc97e9e5`. It is no longer in `.env` but is still in `.env.bak-20260803` and in git history.
- [x] **Remove the hardcoded device key default.** `DIAD_API_KEY` now comes from `settings` with no default. If no key is set, every device request is rejected, and production refuses to start with no key or with the old `dev-secret-key-123`.
- [x] **Use a constant-time comparison** for the device token (`hmac.compare_digest`).
- [x] **Delete `generate_temp_token`** from `services/auth.py`.
- [x] **Keep `.env` out of the Docker image.** Added env files, virtualenvs, caches, uploads, backups and dumps to `.dockerignore`. *(`*.txt` was not added, because it would exclude `requirements.txt`.)*
- [x] **Scan the full git history with gitleaks.** Also **fixed `.gitleaks.toml`**: it defined no rules and didn't extend the defaults, so every scan reported "no leaks found". It also allowlisted `.env.example`, which is where the TomTom key leaked.
- [ ] **Consider rotating `SECRET_KEY`** *(owner action, added after scan)*. Five admin/manager JWTs were committed (in `src/mobile/App.js`, `test_ws.py`, and a file named `$token = eyJ….md`). All of them expired between 2026-02-06 and 2026-09-22, so none can be replayed. If any was signed with the real production key, rotating it is a cheap precaution.
- [ ] **Decide on rewriting history** *(owner decision)*. Removing secrets and large binaries from history (`git filter-repo`) means everyone must re-clone. Record the decision here.

### Verify
- [x] gitleaks (default rules) finds nothing in the working tree: `src/`, `tests/`, `tools/`, `deploy/`, `.github/`, `docs/` and the root docs.
- [ ] `docker run --rm delivery_backend:latest ls -a /app | grep .env` prints nothing. *Not run yet: Docker Desktop was stopped.*
- [x] The backend refuses to start with `ENVIRONMENT=production` and no `DIAD_API_KEY`, or with the old default (`tests/unit/test_device_auth.py`).

### Changes made (2026-10-08, committed in `4f9df4c9`)
| File | Change |
|---|---|
| `src/backend/core/config.py` | Added `DIAD_API_KEY` setting (no default) and a production startup check that rejects an empty key or the old default |
| `src/backend/services/auth.py` | Reads the key from `settings`; rejects all requests when no key is set; `hmac.compare_digest`; removed `generate_temp_token`; `AuthService(api_key=...)` for tests |
| `tests/unit/test_device_auth.py` | **New**: 11 tests covering accept, reject, no key configured, and production startup with and without a key |
| `tests/conftest.py` | Sets `DIAD_API_KEY=test-device-key` before the app loads |
| `tests/unit/test_api_basics.py`, `test_api_health.py`, `test_routing_api.py` | Use the test key, not the old hardcoded one |
| `tests/unit/test_final_coverage.py` | Removed the test for the deleted `generate_temp_token` |
| `tools/simulators/fleet_sim.py` | No hardcoded key; uses `DEVICE_API_KEY` or `DIAD_API_KEY` |
| `test_ws.py` | Reads the token from `DISPATCH_TOKEN`; the committed JWT is removed |
| `RUNBOOK.md` | Password removed; placeholder until Phase 7 |
| `.gitleaks.toml` | Extends the default rules; path allowlist removed |
| `.dockerignore` | Excludes `.env*`, virtualenvs, caches, uploads, backups, dumps |
| `deploy/helm/.../secret.yaml`, `values*.yaml` | Added a `DIAD_API_KEY` secret entry |
| `.github/workflows/ci.yml` | Staging deploy passes `secrets.STAGING_DIAD_API_KEY` |

**Test result:** 183 passed, 35 failed. Before: 173 passed, 35 failed. All 35 failures existed before this phase; see Phase 3. The 11 new tests all pass.

**Checkpoint:** ☐ Phase 0 in progress: 5 of 9 tasks done → readiness **46%** (49% when the owner actions are done)

---

## Phase 1 — Repository hygiene  (57% when done)

**Why:** the repo has 61,024 tracked files (60,589 of them proof photos) and a 94 MB `.git`. The root has about 90 items, including 9 different start/stop scripts. This slows every clone, search, review and Docker build.

### Planned changes
Phase 1 has 8 tasks, each worth 8/8 = 1%.

- [x] **Stop tracking generated data and binaries** (`git rm -r --cached`; the files stay on disk): `src/uploads/`, `data/uploads/`, `storage/proofs/`, `src/data/uploads/`, `src/mobile/node.exe`, `src/mobile/node-runtime/`, `auth_inventory.txt`, `.coverage`, `token_response.json`, `refresh_response.json`. Added to `.gitignore`.
  - *Kept:* `src/analytics/ml_models/eta_model.joblib`. `eta_predictor.py` loads it at runtime, so untracking it would break ETA predictions in built images. Revisit in Phase 6 (artifact storage).
  - *Correction:* `token_response.json` and `verify_deployment.ps1` are ordinary files, not directories.
- [x] **Clean the project root (tracked files).** Removed with `git rm`, so all of them are recoverable from history:
  - the three files whose names start with `# ` (day-1 scaffolding)
  - `DELIVERYINTELLIGENCEPLATORM.txt` (an outdated folder tree)
  - `launch.json` (misplaced VS Code config)
  - `test_sig.txt`, and `dispatch_full.txt` (a stale copy of `dispatch.py`)
  - five orphaned mobile files saved under nested paths like `src/mobile/src/api/src/mobile/...`, which nothing imports

  *Kept:* `dummy_image.jpg`, which `tools/generate_traffic.ps1` uses.
- [x] **Clean the project root (untracked files).** Deleted on 2026-10-08 with the owner's approval: `nul`, `frontend.log`, `frontend_v2.log`, `simulation.log` (3.4 MB), and the empty directories `prometheus.yml/`, `prometheus-alerts.yml/`, `alertmanager.yml/` and `backend/`. *Still to do:* `rehab-session-2026-10-01.diff`, once the rehab work is committed in Phase 2.
- [x] **Merge the startup scripts** into [scripts/dev/start.ps1](../scripts/dev/start.ps1) and [scripts/dev/stop.ps1](../scripts/dev/stop.ps1). See the table under *Changes made*.
- [x] **Monitoring mounts: no change needed.** The `./deploy/monitoring/...` paths are correct when the file is combined with the root compose file, as its header says. The root `*.yml` directories are leftovers from an older root compose file, and are listed under the untracked cleanup above.
- [x] **Use one Python environment.** `venv/` deleted (184 MB, unused). On 2026-10-08 `.venv` was rebuilt on Python 3.12.10 from `requirements.txt` (223 packages, `pip check` clean). The unit suite gives the same result as on 3.14 (183 passed, the 33 known failures), and warnings fell from about 17,400 to 1,513. Original task: recreate `.venv` on Python 3.12 (`py -3.12 -m venv .venv`) to match Docker and CI; it is currently 3.14. Added `.python-version` (3.12).
- [x] **Move the manuals and reports** into `docs/manuals/` and `docs/reports/` with `git mv`.
- [ ] **Clean up branches** *(owner decision)*. Merge or delete `stabilization/2026-09` and `feature/advanced-geofencing`, and work through the open Dependabot PRs.

### Verify
- [x] `git ls-files | wc -l` is under 1,500.
- [ ] The root has 25 or fewer entries *(after the owner's untracked cleanup)*.
- [ ] A fresh clone, then `scripts/dev/start.ps1`, then `/health` returning 200 all work. *Not run: Docker Desktop is stopped.*

### Changes made (2026-10-08)
**Startup scripts**: 13 root scripts replaced by 4 in `scripts/dev/`:

| Old script | What happened |
|---|---|
| `daily_startup.ps1` | Basis for `start.ps1` (preflight checks, data kept between runs) |
| `start_all.ps1`, `clean_start.ps1`, `tools/simulators/start_all.ps1` | Removed. They ran `docker compose down --volumes` on every start, which **wiped the database**. `clean_start` also stopped **every container on the machine** and killed all `python`/`node` processes. A wipe is now opt-in: `start.ps1 -Reset`, which asks for confirmation. Their database wait loop always timed out, because compose had no healthcheck; `delivery_db` now has one. |
| `start_platform.ps1` | Removed. It was stale (port 8002, a Grafana service no longer in compose) and **hardcoded and printed a Grafana admin password**, which has been in git history since March. Monitoring is now `start.ps1 -Monitoring`. |
| `start-dev.ps1` / `stop-dev.ps1` | Emulator, `adb reverse` and Expo steps moved into `start.ps1 -Mobile` and `stop.ps1`. The backend now runs in Docker, not a local uvicorn window. |
| `run_simulation.ps1`, `run_fleet_simulator.ps1` | Replaced by `start.ps1 -Simulate -Drivers N`. `run_simulation` hardcoded a driver password; `run_fleet_simulator` set a variable the simulator never read. |
| `initialize_backend.ps1` + `src/backend/init_db.py` | Removed. `init_db.py` imported modules that don't exist; Alembic migrations create the schema. |
| `load_env.ps1` | Folded into `start.ps1` |
| `verify_deployment.ps1` | Health check folded into `start.ps1`. Its `/api/dispatches` check called a route that doesn't exist. |
| `setup_secrets.ps1`, `configure-mobile-env.ps1` | Moved to `scripts/dev/`. Paths fixed, the mobile port changed from 8002 to 8000, and an optional dispatcher password prompt added. |

**Seeding:** new `tools/seed_dev_data.py`, replacing `tools/seed_db.py` and the inline seeds that set `admin` to a hardcoded password on every start. It reads passwords from `.env.backend`, creates only missing accounts, adds driver profiles D001–Dnnn, and refuses to run with `ENVIRONMENT=production`.

**Simulator:** restored `main()`, `--drivers` and `BACKEND_URL` in `tools/simulators/fleet_sim.py`. All three were accidentally removed in `e1130f76` (2026-09-27), so the simulator had been doing nothing when run.

**Checkpoint:** ☐ Phase 1 in progress: 7 of 8 tasks done → readiness **53%** (54% when the branches are cleaned up). Root entries: 61, down from about 90.

---

## Phase 2 — API contract & in-flight rehab work  (62% when done)

**Why:** the uncommitted rehab session changes public URLs. The web and mobile clients must agree with the backend before anything else is built on top.

### Planned changes
- [x] **Fix the router prefixes.** The working-copy change to `src/backend/api/main.py` removes the prefixes passed in `main.py` so each router's own prefix applies. That fixes double paths like `/dispatch/dispatch/*`, but some routes move:
  - `geofence.py` has no prefix of its own, so `POST /geofence/verify` becomes `POST /verify`. Add `prefix="/geofence"` to the router. ✅
  - Command center moves from `/command-center/api/*` to `/api/*`. Pick one path and update the clients. ✅ No client in the repo calls it; kept `/api/*`.
  - Advanced routing moves from `/advanced-routing/advanced-route/*` to `/advanced-route/*`. Confirm the clients use the new path. ✅ No client in the repo calls it.
- [x] **Restore the delivery endpoints the mobile app calls** *(added 2026-10-10)*. The app calls `POST /delivery/confirm`, `POST /delivery/scan` and `GET /delivery/recent-proofs`. None of them exist in the committed `delivery.py` or in the uncommitted rewrite, so proof of delivery cannot be submitted from the phone. The 6 failing tests in `tests/integration/test_delivery_flow.py` cover these endpoints.
- [x] **Add a route snapshot test.** It should list every `METHOD /path` the app exposes and fail on any unplanned change. *(HTTP routes only; WebSocket routes are not in the OpenAPI schema.)*
- [x] **Make startup fail when a router doesn't load.** `safe_include` (`main.py:114-124`) logs a warning and carries on for every router except websocket, so a broken import silently removes whole APIs. In production, raise on any failure. *(Raises in every environment unless `ALLOW_DEGRADED_STARTUP=1`.)*
- [x] **Remove the direct SQLite connection** from `main.py` (lines 4 and 50-52). Every request should go through the SQLAlchemy/Postgres session.
- [ ] **Keep one delivery router.** Delete `delivery_backup.py` and `delivery.py.corrupt.backup`; the old versions remain in git history. *(`.corrupt.backup` removed. `delivery_backup.py` is untracked, so deleting it is permanent; it is fully superseded by `dfa6fdce` and can go once the owner agrees.)*
- [ ] **Make the mobile app build and log in** *(added 2026-10-10; blocks Verify)*. `App.js` imports `./screens/*`, but the screens live in `./src/screens/`. `src/api/client.js` has no default export, yet `authStore`, `HomeScreen`, `offlineQueueService` and `notificationService` import one, so login crashes. `package.json` is missing packages the code imports (`axios`, `expo-location`, `@react-navigation/*`, `expo-secure-store`, `expo-notifications`, AsyncStorage, `expo-sqlite`). No request sends the login token, and every `/delivery/*` endpoint now requires one. `offlineQueueService` marks any 4xx as FAILED, so a 401 would strand a proof; it must retry after login instead. Other calls with no backend route: `GET /routing/sample-route/{id}`, `POST /notifications/register-token` and `POST /debug/reset-db` (mobile), and `POST /dispatch/assign` (web; the API has `PUT /dispatch/jobs/{id}/assign`).
- [ ] **Commit the rehab work in small, reviewable commits**, then merge `rehab-investigation-20261001` into `main` through a PR so CI runs.

### Verify
- The route snapshot test passes and the snapshot has been reviewed.
- The web dashboard and mobile app can log in, list jobs, complete a delivery and check a geofence against the local stack.
- `main` contains all the rehab work, and CI is green on the merge.

### Changes made
**2026-10-10:** reviewed the uncommitted rehab changes and committed the safe parts. With Docker running, the full suite went from 31 failed and 11 errors to 15 failed, 237 passed and 12 skipped, with no new failures.

| Commit | Change |
|---|---|
| `9aa98ede` | Phase 0 status note (Expo 2FA, tokens revoked) |
| `1adcd127` | Routers own their prefixes; `/route` → `/routing`; geofence keeps `/geofence/verify` |
| `8b13b728` | Dispatch test: unknown driver on assign returns 404, not 400. The rehab copy also deleted 5 dispatch tests; they pass with the prefix fix, so they were kept |
| `92a087b6` | Restored the truncated `tests/e2e/conftest.py`; the 11 e2e tests now load and skip unless `E2E_DATABASE_URL` is set |
| `b5f327d8` | Removed the empty `delivery.py.corrupt.backup` |

**2026-10-10 (continued):** delivery endpoints and the rest of the backend Phase 2 items. Suite: 9 failed, 259 passed, 12 skipped. Each commit was tested on its own in a clean checkout.

| Commit | Change |
|---|---|
| `2ae267fb` | Restored proof storage (`core/storage.py` from `a5163284`): Cloudflare R2 when configured, local disk otherwise. The cut-down copy could save photos but not list or show them |
| `dfa6fdce` | Delivery router rebuilt from `a5163284`, the uncommitted rewrite and `delivery_backup.py`: `confirm` saves the photo first, 404s on unknown packages instead of inventing them, and closes the dispatch job; new `scan` loads a package by ID or tracking code; all endpoints require login. 15 new tests |
| `573bc740` | SQLite proof database removed from `main.py`; a router that fails to import now stops startup |
| `1d6b597d` | Route snapshot test (`tests/unit/route_snapshot.txt`, 58 routes) |

**Not committed:**

- `src/backend/api/routes/delivery_backup.py` (untracked; superseded, delete when agreed).
- `src/analytics/ml_models/eta_model.joblib`. Running the test suite rewrites this tracked file, so the change is a test side effect, not work to commit. The tests should write to a temporary path instead (Phase 3).

**Still failing (Phase 3):** 8 tests in `tests/unit/test_api_basics.py` and `tests/unit/test_api_health.py` expect `/health` to return `{"status": "online"}`, a `/secure-ping` endpoint and a `/` → docs redirect, none of which the API provides; decide which side is right. `tests/test_heartbeat.py` counts 49 where it expects at least 50.

**Not yet verified live:** the running `delivery_backend` container still has the old code. Rebuild it (`docker compose up --build -d backend`) before testing against the local stack.

**Checkpoint:** ☐ Phase 2 complete → readiness **62%**

---

## Phase 3 — Test suite reliability  (69% when done)

**Why:** 35 of 208 unit and smoke tests fail locally. Most need a live Redis, so a red run doesn't separate real bugs from environment noise.

### Planned changes
- [ ] **Swap live Redis for `fakeredis`** in a shared fixture in `tests/conftest.py`. This fixes the 23 `redis.exceptions.ConnectionError` failures.
- [ ] **Look into the 8 status-code failures** (403 or 404 returned where 200 or 400 was expected) in `test_api_health.py`, `test_auth_routes.py` and `test_routing_api.py`. Fix the code or the test, and record which one was wrong.
- [ ] **Fix the stale API tests.** `test_api_basics.py` and `test_api_health.py` call `/secure-ping`, which the backend no longer has (404). They also expect `/health` to return `{"status": "online"}`, but it now returns `"ok"` plus a timestamp. Either restore the endpoints or update the tests, and record which was correct.
- [ ] **Separate the smoke tests.** Mark `tests/smoke/` with `@pytest.mark.smoke` and leave them out of the default run; they need a running server. Run them only after a deploy.
- [ ] **Replace the coverage-padding files.** Fold `test_coverage_boost.py` and `test_final_coverage.py` into tests named after the behaviour they check.
- [ ] **Bring the warning count down.** It is about 17,000; start with the `httpx`/`starlette` TestClient deprecation and any `datetime.utcnow` use.
- [ ] **Run integration tests against real services.** In CI, add `postgis/postgis` and `redis` service containers and run `tests/integration` and `tests/e2e` against them, not SQLite in memory.
- [ ] **Raise the coverage gate in steps.** It is 35% today (`.github/workflows/ci.yml`); move to 50%, then 70%.

### Verify
- `pytest` reports 0 failures locally with Docker stopped (unit) and with it running (integration and e2e).
- CI is green on 3 consecutive runs with no reruns.

### Changes made
_(fill in)_

**Checkpoint:** ☐ Phase 3 complete → readiness **69%**

---

## Phase 4 — Application security hardening  (78% when done)

### Planned changes
- [ ] **Read CORS from one place.** `main.py:36-45` reads `CORS_ORIGINS` itself, so the production checks on `BACKEND_CORS_ORIGINS` in `core/config.py:126-139` (no `*`, must be set) never apply to the middleware. Use `settings.BACKEND_CORS_ORIGINS` in `main.py`.
- [ ] **Shorten token lifetime.** Access tokens currently last 8 hours (`ACCESS_TOKEN_EXPIRE_MINUTES=480`). Cut that to 15–60 minutes, rely on refresh tokens, and add revocation when a driver is deactivated.
- [ ] **Give each device its own key.** Every device now shares one `DIAD_API_KEY`. Issue a key per device so a lost handset can be revoked alone.
- [ ] **Rate limit the auth endpoints** (`/auth/login`, `/auth/refresh`) with the existing `slowapi` limiter. Today only advanced routing uses it.
- [ ] **Validate proof-of-delivery uploads:** maximum size, allowed image types (checked by file signature, not file extension), and filenames generated by the server.
- [ ] **Audit dependencies.** Add `pip-audit` and `npm audit --production` to CI, and fail on high or critical findings.
- [ ] **Harden the container.** Use a multi-stage Dockerfile, run as a non-root `USER`, leave `build-essential` out of the final image, and pin the base image by digest.
- [ ] **Run a security review** of the full backend (`/security-review`), and fix or formally accept every finding.

### Verify
- Starting with `ENV=production` and a weak or missing secret, `*` CORS, or no device key fails fast.
- OWASP ZAP baseline scan against staging: no high findings.
- `pip-audit` and `npm audit` are clean, or exceptions are documented.

### Changes made
_(fill in)_

**Checkpoint:** ☐ Phase 4 complete → readiness **78%**

---

## Phase 5 — Data, migrations & backups  (81% when done)

### Planned changes
- [ ] **Keep one Alembic setup.** Keep the root `alembic.ini` → `migrations/`, and remove `src/backend/alembic/` and `src/backend/alembic.ini`.
- [ ] **Rename `xxxx_add_advanced_routing_tables.py`** to a proper revision ID.
- [ ] **Test migrations in CI:** `alembic upgrade head` on an empty PostGIS database, then `alembic downgrade -1`, then upgrade again.
- [ ] **Move proof photos to S3** (`PROOF_STORAGE=s3`; `services/storage.py` already supports it, per PLAN.md Phase 1), with a retention lifecycle rule.
- [ ] **Automate Postgres backups** with daily `pg_dump` or managed snapshots, and **carry out one test restore** with timings recorded.
- [ ] **Keep a copy of the backups off this machine**, on a network share or NAS. Today there is no backup tooling (`backups/` is empty) and no mapped network drives. Copy each daily dump, and the proof-of-delivery photos until they move to S3, to the share. Keep 7 daily and 4 weekly copies, and alert if a copy is missing or older than 26 hours. *Needs from owner:* the share's UNC path (`\\server\share\...`) and an account with write access.
- [ ] **Remove ad-hoc database scripts** (`check_tables.py`, `init_spatial_db.sql`, `add_dispatcher.py`) or turn them into migrations or seed commands.

### Verify
- CI migration job is green.
- A test restore has been completed and its recovery time written down in the runbook.

### Changes made
_(fill in)_

**Checkpoint:** ☐ Phase 5 complete → readiness **81%**

---

## Phase 6 — Build & deployment pipeline  (87% when done)

### Planned changes
- [ ] **Pick one production target.** The Dockerfile mentions Railway; CI deploys to Kubernetes with Helm. Choose one and remove the other path.
- [ ] **Set `ENVIRONMENT=production` in the deployment** (Helm values or Railway variables). No Helm values file sets it, so pods run in development mode and the production startup checks in `core/config.py` (secret key, CORS, device key) never run there.
- [ ] **Add the Celery `telemetry_worker`** to the chosen deployment. It runs in `docker-compose.yml` but has no Helm template.
- [ ] **Stop exposing Postgres and Redis ports** in any production compose file or values file; they are published in `docker-compose.yml`.
- [ ] **Add a container `HEALTHCHECK`** and Kubernetes liveness/readiness probes (these depend on Phase 7's `/ready`).
- [ ] **Manage secrets** with external-secrets or sealed-secrets (the comment in `deploy/helm/.../secret.yaml` already calls for this), not values passed with `--set`.
- [ ] **Add deploy gates:** staging deploy, then smoke tests, then manual approval, then production. Write down a tested rollback (`helm rollback`).
- [ ] **Fix the CI dependency install.** CI runs `pip install --require-hashes -r requirements.txt`, but `requirements.txt` has no hashes, so that step fails. Regenerate it with `pip-compile --generate-hashes requirements.in`.
- [ ] **Split runtime and dev dependencies.** `requirements.txt` (which the Docker image installs) includes pytest, black, flake8 and coverage. It also conflicts with `requirements-dev.txt` (`pytest==7.4.3` against `pytest>=8.0.0`), so the two files can't be installed together. Keep test and lint tools only in the dev file.
- [ ] **Require CI to pass before merging** into `main`, using branch protection.

### Verify
- One push to `main` builds, signs, deploys to staging and passes smoke tests with no manual steps.
- A rollback has been practised in staging.

### Changes made
_(fill in)_

**Checkpoint:** ☐ Phase 6 complete → readiness **87%**

---

## Phase 7 — Observability & operations  (93% when done)

### Planned changes
- [ ] **Separate liveness from readiness.** `/health` (liveness) is already at `main.py:156`. Add `/ready`, which checks the database, Redis and the storage backend.
- [ ] **Use structured JSON logs with request IDs**, and turn on the existing OpenTelemetry setup (`core/tracing.py`) in staging and production.
- [ ] **Add error tracking** (Sentry or similar) for the backend, web and mobile apps.
- [ ] **Fix the monitoring exporters.** In `deploy/monitoring/docker-compose.monitoring.yml`, `redis_exporter` points at `redis:6379` on an isolated `monitoring` network. The real services are `delivery_redis` and `delivery_db` on `delivery_net`, so neither exporter can reach anything. Attach them to `delivery_net` and fix the hostnames.
- [ ] **Connect the Prometheus alerts** to a real Alertmanager receiver (email, Slack or a pager), and fire a test alert.
- [ ] **Define service levels (SLOs):** API availability, p95 latency per key endpoint, and maximum delay for telemetry ingestion.
- [ ] **Rewrite `RUNBOOK.md`** as a real runbook: start/stop, deploy, rollback, restore from backup, rotate secrets, and an on-call contact.

### Verify
- A deliberately failed database connection shows up as an alert within 5 minutes.
- Someone other than the author can follow the runbook to restore staging.

### Changes made
_(fill in)_

**Checkpoint:** ☐ Phase 7 complete → readiness **93%**

---

## Phase 8 — Client apps (web + mobile)  (96% when done)

### Planned changes
- [ ] **Choose one dashboard.** `src/web` has 66 files, `src-ui` 7 and `src/frontend` 2. Keep the live one and archive the others. Decide whether `DeliveryIntelligence.Domain` (C#) stays.
- [ ] **Add frontend CI:** lint, type-check and production build for the dashboard and mobile app.
- [ ] **Configure API URLs per environment** for the dashboard and mobile app, with no hardcoded hosts.
- [ ] **Set up a production mobile build:** an EAS production profile, signing, and the permissions schema checked against the store requirements in `ANDROID_DEPLOYMENT_RUNBOOK.md`.
- [ ] **Test on real devices** against staging, covering offline queue sync, proof capture and the background heartbeat.

### Verify
- Both apps build in CI.
- A real-device test pass against staging is recorded in `docs/`.

### Changes made
_(fill in)_

**Checkpoint:** ☐ Phase 8 complete → readiness **96%**

---

## Phase 9 — Documentation & release  (100% when done)

### Planned changes
- [ ] **Make the README status table reflect real test and deploy results.** It currently says "Operational ✅" for everything.
- [ ] **Replace `BASELINE.md`.** It describes an older branch; replace it with an up-to-date architecture overview, or delete it.
- [ ] **Run a load test** with `tests/load/locustfile.py` against staging at about 2× expected peak fleet size, and record the results against the SLOs.
- [ ] **Start a `CHANGELOG.md`** and tag `v1.0.0`.
- [ ] **Add a real support contact to every user guide.** `docs/USER_GUIDE.md`, `docs/Recommended_User_Guides`, `docs/manuals/DISPATCHER_USER_MANUAL.txt` and `docs/manuals/DRIVER_USER_MANUAL.txt` only say "contact your supervisor/administrator" or "Development team". Give the name or role, email, phone, support hours, and an after-hours or urgent route for drivers on the road. The dispatcher manual also lists `localhost` URLs for the status page and Grafana; replace them with the real addresses. *Needs from owner:* the contact details.
- [ ] **Complete a go-live checklist** with a named sign-off for security, data and operations.

### Verify
- The load test meets the SLOs.
- The go-live checklist is signed off.

### Changes made
_(fill in)_

**Checkpoint:** ☐ Phase 9 complete → readiness **100%** 🚀

---

## Recommended sequencing

- **Week 1:** Phases 0–2. Removes the immediate exposure and gives a stable, merged `main`.
- **Week 2:** Phases 3–4. A trustworthy test suite, then security fixes verified by it.
- **Week 3:** Phases 5–7. Infrastructure, deployment and operations.
- **Week 4:** Phases 8–9. Client apps, load test and launch.

Phases 0, 1 and 2 must be done in order. From Phase 3 on, data (5) and client apps (8) can run alongside the others.
