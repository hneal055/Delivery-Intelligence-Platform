# tests/load/locustfile.py
# Run locally:  locust -f tests/load/locustfile.py --host http://localhost:8002
# Run headless: locust -f tests/load/locustfile.py --host http://localhost:8002 \
#               --users 50 --spawn-rate 5 --run-time 2m --headless \
#               --html tests/load/report.html
#
# Targets: health, auth, delivery list, routing, dispatch — the platform hot paths.
# Baseline SLOs (set --stop-timeout 120):
#   p95 < 500 ms for reads
#   p99 < 2 s   for write/ML endpoints
#   Error rate < 1%

import json
import random
from locust import HttpUser, TaskSet, task, between, events

# ---------------------------------------------------------------------------
# Shared state
# ---------------------------------------------------------------------------
_token: str | None = None   # populated once by the first user to log in

TEST_CREDENTIALS = {
    "username": "loadtest@example.com",
    "password": "LoadTest1!",
}

DRIVER_IDS = list(range(1, 21))      # assume seeded drivers 1-20
PACKAGE_IDS = list(range(1, 101))    # assume seeded packages 1-100


# ---------------------------------------------------------------------------
# Task sets
# ---------------------------------------------------------------------------
class PublicTasks(TaskSet):
    """Unauthenticated endpoints — health probes, token acquisition."""

    @task(5)
    def health(self):
        with self.client.get("/health", name="/health", catch_response=True) as r:
            if r.status_code != 200:
                r.failure(f"health returned {r.status_code}")

    @task(1)
    def obtain_token(self):
        """POST /auth/token — exercises JWT issuance + bcrypt verify."""
        resp = self.client.post(
            "/auth/token",
            data=TEST_CREDENTIALS,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            name="/auth/token",
        )
        if resp.status_code == 200:
            global _token
            _token = resp.json().get("access_token")


class AuthenticatedTasks(TaskSet):
    """Authenticated read/write mix — mirrors a typical dispatcher session."""

    token: str | None = None

    def on_start(self):
        global _token
        if _token:
            self.token = _token
        else:
            # Acquire our own token on first run
            resp = self.client.post(
                "/auth/token",
                data=TEST_CREDENTIALS,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                name="/auth/token (setup)",
            )
            if resp.status_code == 200:
                self.token = resp.json().get("access_token")
                _token = self.token

    def _auth(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    # ── Reads (frequent) ────────────────────────────────────────────────────

    @task(10)
    def list_deliveries(self):
        self.client.get("/delivery/recent-proofs", headers=self._auth(), name="/delivery/recent-proofs")

    @task(8)
    def tracking_status(self):
        pkg_id = random.choice(PACKAGE_IDS)
        self.client.get(f"/tracking/{pkg_id}", headers=self._auth(), name="/tracking/[id]")

    @task(6)
    def driver_list(self):
        self.client.get("/dispatch/drivers", headers=self._auth(), name="/dispatch/drivers")

    @task(5)
    def me(self):
        self.client.get("/auth/users/me", headers=self._auth(), name="/auth/users/me")

    @task(4)
    def analytics_summary(self):
        self.client.get("/analytics/summary", headers=self._auth(), name="/analytics/summary")

    # ── ML / compute (less frequent but heavier) ───────────────────────────

    @task(2)
    def route_optimize(self):
        payload = {
            "driver_id": random.choice(DRIVER_IDS),
            "delivery_ids": random.sample(PACKAGE_IDS, k=min(5, len(PACKAGE_IDS))),
        }
        self.client.post(
            "/routing/optimize",
            json=payload,
            headers=self._auth(),
            name="/routing/optimize",
        )

    @task(1)
    def dispatch_assign(self):
        payload = {
            "driver_id": random.choice(DRIVER_IDS),
            "package_id": random.choice(PACKAGE_IDS),
        }
        self.client.post(
            "/dispatch/assign",
            json=payload,
            headers=self._auth(),
            name="/dispatch/assign",
        )


# ---------------------------------------------------------------------------
# User classes
# ---------------------------------------------------------------------------
class PublicUser(HttpUser):
    """Simulates anonymous health-check traffic (monitoring, load balancer probes)."""
    tasks = [PublicTasks]
    wait_time = between(1, 3)
    weight = 1


class DispatcherUser(HttpUser):
    """Simulates an authenticated dispatcher: heavy read, occasional write."""
    tasks = [AuthenticatedTasks]
    wait_time = between(0.5, 2)
    weight = 4


class DriverAppUser(HttpUser):
    """Simulates the mobile driver app: frequent tracking updates, occasional routing."""
    tasks = {AuthenticatedTasks: 1}
    wait_time = between(2, 5)
    weight = 3


# ---------------------------------------------------------------------------
# Custom result hooks
# ---------------------------------------------------------------------------
@events.quitting.add_listener
def on_quitting(environment, **kwargs):
    """Fail CI if p95 > 500 ms or error rate > 1%."""
    stats = environment.runner.stats.total
    if stats.num_requests == 0:
        return
    p95 = stats.get_response_time_percentile(0.95)
    error_rate = stats.fail_ratio
    if p95 and p95 > 500:
        print(f"\n[LOAD] FAIL — p95 latency {p95:.0f} ms exceeds 500 ms SLO")
        environment.process_exit_code = 1
    if error_rate > 0.01:
        print(f"\n[LOAD] FAIL — error rate {error_rate:.1%} exceeds 1% SLO")
        environment.process_exit_code = 1
