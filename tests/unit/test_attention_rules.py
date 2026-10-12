"""Needs-attention rules (services/attention.evaluate) on plain rows."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace as Row

import pytest

from src.backend.services import attention
from src.backend.services.attention import evaluate

# 10:00 AM Chicago (CDT, UTC-5): inside working hours
NOW = datetime(2026, 10, 12, 15, 0, tzinfo=timezone.utc)
NIGHT = datetime(2026, 10, 13, 4, 0, tzinfo=timezone.utc)  # 11 PM Chicago


def job(id="j1", title="Job", status="pending", priority="medium", driver_id=None,
        scheduled_at=None, package_id=None):
    return Row(id=id, title=title, status=status, priority=priority, driver_id=driver_id,
               scheduled_at=scheduled_at, package_id=package_id)


def pkg(id="p1", status="assigned", driver_id="driver1", pickup_address=None, ready_at=None,
        dest_address="8338 S SAGINAW AVE", exception_reason=None, updated_at=None):
    return Row(id=id, status=status, driver_id=driver_id, pickup_address=pickup_address,
               ready_at=ready_at, dest_address=dest_address, tracking_code="CCC-TEST0001",
               exception_reason=exception_reason, updated_at=updated_at)


DRIVERS = [Row(id="driver1", name="driver1"), Row(id="driver2", name="driver2")]


def point(minutes_ago, lat=41.7434, lon=-87.5603, now=NOW):
    return Row(lat=lat, lon=lon, timestamp=now - timedelta(minutes=minutes_ago))


def rules(items):
    return [i.rule for i in items]


def run(jobs=(), packages=(), last_seen=None, points=None, now=NOW):
    return evaluate(jobs, packages, DRIVERS, last_seen or {}, points or {}, now)


def test_all_clear():
    assert run() == []


def test_unassigned_job_due_soon_is_red():
    items = run(jobs=[job(scheduled_at=NOW + timedelta(hours=1))])
    assert rules(items) == ["no_driver"]
    assert items[0].severity == "red"


def test_unassigned_job_later_today_is_not_flagged():
    assert run(jobs=[job(scheduled_at=NOW + timedelta(hours=5))]) == []


def test_unassigned_urgent_job_flagged_without_time():
    assert rules(run(jobs=[job(priority="urgent")])) == ["no_driver"]


def test_overdue_job_reported_once_even_without_driver():
    items = run(jobs=[job(scheduled_at=NOW - timedelta(minutes=45))])
    assert rules(items) == ["overdue"]
    assert "no driver" in items[0].detail


def test_job_not_overdue_within_grace():
    assert run(jobs=[job(driver_id="driver1", status="assigned",
                         scheduled_at=NOW - timedelta(minutes=20))]) == []


def test_closed_jobs_ignored():
    assert run(jobs=[job(status="completed", scheduled_at=NOW - timedelta(hours=3))]) == []


def test_problem_package_is_red_and_job_not_double_counted():
    items = run(
        jobs=[job(driver_id="driver1", status="assigned", scheduled_at=NOW - timedelta(hours=1), package_id="p1")],
        packages=[pkg(status="exception", exception_reason="Business closed")],
    )
    assert rules(items) == ["problem"]
    assert "Business closed" in items[0].detail


def test_ready_pickup_waiting_with_online_driver():
    items = run(
        packages=[pkg(pickup_address="1 S State St", ready_at=NOW - timedelta(minutes=50))],
        last_seen={"driver1": NOW - timedelta(minutes=1)},
    )
    assert rules(items) == ["ready_waiting"]
    assert items[0].severity == "orange"


def test_ready_pickup_recent_is_fine():
    assert run(
        packages=[pkg(pickup_address="1 S State St", ready_at=NOW - timedelta(minutes=10))],
        last_seen={"driver1": NOW - timedelta(minutes=1)},
    ) == []


def test_ready_pickup_with_offline_driver():
    items = run(packages=[pkg(pickup_address="1 S State St", ready_at=NOW - timedelta(minutes=5))])
    assert rules(items) == ["offline_ready"]
    assert "never logged in" in items[0].detail


def test_ready_pickup_without_driver_left_to_job_rule():
    assert run(packages=[pkg(driver_id=None, status="pending", pickup_address="1 S State St",
                             ready_at=NOW - timedelta(hours=1))]) == []


def test_quiet_driver_with_packages_on_board():
    items = run(packages=[pkg(status="loaded")], last_seen={"driver1": NOW - timedelta(minutes=25)})
    assert rules(items) == ["quiet"]
    assert "25 min" in items[0].title


def test_reporting_driver_is_not_quiet():
    assert run(packages=[pkg(status="loaded")], last_seen={"driver1": NOW - timedelta(minutes=1)},
               points={"driver1": [point(1)]}) == []


def test_stopped_driver():
    pts = [point(m) for m in range(30, -1, -1)]  # same spot for 30 min
    items = run(packages=[pkg(status="loaded")], last_seen={"driver1": NOW},
                points={"driver1": pts})
    assert rules(items) == ["stopped"]
    assert "30 min" in items[0].title


def test_moving_driver_is_not_stopped():
    # Moved ~1 km five minutes ago
    pts = [point(m, lat=41.73) for m in range(30, 5, -1)] + [point(m) for m in range(5, -1, -1)]
    assert run(packages=[pkg(status="loaded")], last_seen={"driver1": NOW},
               points={"driver1": pts}) == []


def test_location_rules_off_at_night():
    assert run(packages=[pkg(status="loaded")], last_seen={"driver1": NIGHT - timedelta(hours=2)},
               now=NIGHT) == []


def test_red_items_listed_first():
    items = run(
        jobs=[job(id="j9", priority="urgent")],
        packages=[pkg(id="p2", status="loaded")],
        last_seen={"driver1": NOW - timedelta(minutes=30)},
    )
    assert [i.severity for i in items] == ["red", "orange"]


def test_naive_times_are_treated_as_utc():
    items = run(jobs=[job(scheduled_at=(NOW - timedelta(minutes=45)).replace(tzinfo=None))])
    assert rules(items) == ["overdue"]


@pytest.mark.parametrize("hour_utc,expected", [(11, False), (12, True), (23, True), (0, False)])
def test_workday_hours_chicago(hour_utc, expected):
    # 12:00 UTC = 7 AM CDT (start); 00:00 UTC = 7 PM CDT (end, exclusive)
    assert attention.in_workday(datetime(2026, 10, 12, hour_utc, 0, tzinfo=timezone.utc)) is expected


# --- deliver-by -----------------------------------------------------------------

def promised(deliver_in_min, **kw):
    p = pkg(**kw)
    p.deliver_by = NOW + timedelta(minutes=deliver_in_min)
    return p


def test_late_package_is_red():
    items = run(packages=[promised(-15)])
    assert rules(items) == ["late"]
    assert items[0].severity == "red" and "15 min ago" in items[0].detail


def test_due_soon_is_orange():
    items = run(packages=[promised(20)])
    assert rules(items) == ["due_soon"]
    assert "Due in 20 min" in items[0].title


def test_deliver_by_later_is_quiet():
    assert run(packages=[promised(90)]) == []


def test_promised_package_skips_scheduled_overdue_rule():
    items = run(
        jobs=[job(driver_id="driver1", status="assigned", scheduled_at=NOW - timedelta(hours=1), package_id="p1")],
        packages=[promised(60)],
    )
    assert items == []


def test_late_unassigned_reported_once_as_late():
    items = run(
        jobs=[job(priority="urgent", package_id="p1")],
        packages=[promised(-5, driver_id=None, status="pending")],
    )
    assert rules(items) == ["late"]
    assert "no driver" in items[0].detail


def test_problem_package_not_also_late():
    assert rules(run(packages=[promised(-30, status="exception")])) == ["problem"]
