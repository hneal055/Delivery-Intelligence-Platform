"""
"Needs attention": everything on the platform dispatch should act on now.

The rules live in evaluate(), a plain function over rows already loaded, so
they are easy to test and to tune. load_and_evaluate() fetches the rows.
An item disappears as soon as its cause is fixed; nothing is stored.

Severity "red" = act now, "orange" = check on it.
"""
import math
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, List, Optional
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.models.sql_models import DispatchJob, Driver, LocationHistory, Package
from src.backend.services.heartbeat import heartbeat_service

LOCAL_TZ = ZoneInfo("America/Chicago")

# Starting values; change here to tune the alerts.
UNASSIGNED_WINDOW = timedelta(hours=2)   # job due this soon with no driver
OVERDUE_AFTER = timedelta(minutes=30)    # past its scheduled time, not finished
READY_WAIT = timedelta(minutes=45)       # ready for pickup, not collected
QUIET_AFTER = timedelta(minutes=10)      # driver with work has not reported
STOPPED_AFTER = timedelta(minutes=20)    # driver with packages on board not moving
STOPPED_RADIUS_M = 100
# Location rules only run in working hours: in Expo Go the phone stops
# reporting when locked, which would otherwise raise alerts all night.
WORKDAY_START_HOUR = 7
WORKDAY_END_HOUR = 19

CLOSED_JOB = {"completed", "cancelled"}
OPEN_PACKAGE = {"pending", "assigned", "loaded", "exception"}


@dataclass
class AttentionItem:
    key: str          # stable id, so the dashboard can tell new items from old
    rule: str
    severity: str     # "red" | "orange"
    title: str
    detail: str
    since: Optional[str] = None   # ISO UTC time the problem started, if known
    job_id: Optional[str] = None
    package_id: Optional[str] = None
    driver_id: Optional[str] = None


def as_utc(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def local_time(value: datetime) -> str:
    """'9:05 AM' today, 'Oct 11 9:05 AM' otherwise (Chicago time)."""
    local = value.astimezone(LOCAL_TZ)
    today = datetime.now(LOCAL_TZ).date()
    clock = local.strftime("%I:%M %p").lstrip("0")
    return clock if local.date() == today else f"{local.strftime('%b')} {local.day} {clock}"


def minutes(delta: timedelta) -> int:
    return max(0, int(delta.total_seconds() // 60))


def in_workday(now: datetime) -> bool:
    hour = now.astimezone(LOCAL_TZ).hour
    return WORKDAY_START_HOUR <= hour < WORKDAY_END_HOUR


def distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def stopped_since(points: List, now: datetime) -> Optional[datetime]:
    """Start of the current stay within STOPPED_RADIUS_M of the latest point.

    points: oldest first, each with lat, lon, timestamp. None if the latest
    point is stale (the "quiet" rule covers that) or there are no points.
    """
    if not points:
        return None
    latest = points[-1]
    if now - as_utc(latest.timestamp) > timedelta(minutes=2):
        return None
    since = as_utc(latest.timestamp)
    for p in reversed(points[:-1]):
        if distance_m(p.lat, p.lon, latest.lat, latest.lon) > STOPPED_RADIUS_M:
            break
        since = as_utc(p.timestamp)
    return since


def evaluate(
    jobs: Iterable,
    packages: Iterable,
    drivers: Iterable,
    last_seen: Dict[str, Optional[datetime]],
    points: Dict[str, List],
    now: datetime,
) -> List[AttentionItem]:
    """jobs: open jobs; packages: open packages whose job is not closed;
    last_seen: driver id -> last time the app was heard from (UTC);
    points: driver id -> recent location points, oldest first."""
    items: List[AttentionItem] = []
    names = {d.id: d.name or d.id for d in drivers}
    packages = list(packages)
    problem_packages = {p.id for p in packages if p.status == "exception"}

    def who(driver_id: Optional[str]) -> str:
        return names.get(driver_id, driver_id) if driver_id else "no driver"

    def silent_for(driver_id: str) -> Optional[timedelta]:
        seen = as_utc(last_seen.get(driver_id))
        return None if seen is None else now - seen

    # Jobs: overdue, or due soon / urgent with no driver
    for job in jobs:
        if job.status in CLOSED_JOB or job.package_id in problem_packages:
            continue  # a problem package is reported once, below
        scheduled = as_utc(job.scheduled_at)
        if scheduled and now - scheduled >= OVERDUE_AFTER:
            late = minutes(now - scheduled)
            items.append(AttentionItem(
                key=f"overdue:{job.id}", rule="overdue", severity="red",
                title=f"Overdue: {job.title}",
                detail=f"Scheduled {local_time(scheduled)} ({late} min ago), not finished; driver: {who(job.driver_id)}",
                since=scheduled.isoformat(), job_id=job.id, package_id=job.package_id, driver_id=job.driver_id,
            ))
        elif not job.driver_id and (
            job.priority == "urgent" or (scheduled is not None and scheduled - now <= UNASSIGNED_WINDOW)
        ):
            due = f"due {local_time(scheduled)}" if scheduled else "no time set"
            reason = "Urgent job" if job.priority == "urgent" else "Due soon"
            items.append(AttentionItem(
                key=f"no_driver:{job.id}", rule="no_driver", severity="red",
                title=f"No driver: {job.title}",
                detail=f"{reason}, {due}",
                since=scheduled.isoformat() if scheduled else None, job_id=job.id, package_id=job.package_id,
            ))

    # Packages: problems, ready pickups waiting
    for pkg in packages:
        where = pkg.dest_address or pkg.tracking_code or pkg.id
        if pkg.status == "exception":
            since = as_utc(pkg.updated_at)
            items.append(AttentionItem(
                key=f"problem:{pkg.id}", rule="problem", severity="red",
                title=f"Problem reported: {where}",
                detail=f"{pkg.exception_reason or 'No reason given'}; driver: {who(pkg.driver_id)}",
                since=since.isoformat() if since else None, package_id=pkg.id, driver_id=pkg.driver_id,
            ))
            continue
        ready = as_utc(pkg.ready_at)
        if not (pkg.pickup_address and ready and pkg.status in ("pending", "assigned")):
            continue
        if not pkg.driver_id:
            continue  # the job's "No driver" item covers it
        silent = silent_for(pkg.driver_id)
        if silent is None or silent >= QUIET_AFTER:
            heard = "never logged in" if silent is None else f"not heard from in {minutes(silent)} min"
            items.append(AttentionItem(
                key=f"offline_ready:{pkg.id}", rule="offline_ready", severity="orange",
                title=f"{who(pkg.driver_id)} is offline with a ready pickup",
                detail=f"Pick up at {pkg.pickup_address}; driver {heard}",
                since=ready.isoformat(), package_id=pkg.id, driver_id=pkg.driver_id,
            ))
        elif now - ready >= READY_WAIT:
            items.append(AttentionItem(
                key=f"ready_waiting:{pkg.id}", rule="ready_waiting", severity="orange",
                title=f"Ready {minutes(now - ready)} min, not picked up",
                detail=f"{pkg.pickup_address}; driver: {who(pkg.driver_id)}",
                since=ready.isoformat(), package_id=pkg.id, driver_id=pkg.driver_id,
            ))

    # Drivers with packages on board: gone quiet, or not moving
    if in_workday(now):
        on_board: Dict[str, int] = {}
        for pkg in packages:
            if pkg.status == "loaded" and pkg.driver_id:
                on_board[pkg.driver_id] = on_board.get(pkg.driver_id, 0) + 1
        for driver_id, count in on_board.items():
            load = f"{count} package{'s' if count != 1 else ''} on board"
            silent = silent_for(driver_id)
            if silent is None or silent >= QUIET_AFTER:
                heard = "has not reported a location" if silent is None else f"hasn't reported in {minutes(silent)} min"
                seen = as_utc(last_seen.get(driver_id))
                items.append(AttentionItem(
                    key=f"quiet:{driver_id}", rule="quiet", severity="orange",
                    title=f"{who(driver_id)} {heard}",
                    detail=f"{load}; the app may be closed or the phone locked",
                    since=seen.isoformat() if seen else None, driver_id=driver_id,
                ))
                continue
            since = stopped_since(points.get(driver_id, []), now)
            if since and now - since >= STOPPED_AFTER:
                items.append(AttentionItem(
                    key=f"stopped:{driver_id}", rule="stopped", severity="orange",
                    title=f"{who(driver_id)} hasn't moved in {minutes(now - since)} min",
                    detail=load,
                    since=since.isoformat(), driver_id=driver_id,
                ))

    # Red first, then oldest first
    items.sort(key=lambda i: (i.severity != "red", i.since or "9999"))
    return items


async def load_and_evaluate(db: AsyncSession, now: Optional[datetime] = None) -> List[dict]:
    now = now or datetime.now(timezone.utc)

    jobs = (await db.execute(
        select(DispatchJob).where(DispatchJob.status.notin_(CLOSED_JOB))
    )).scalars().all()

    closed_job_packages = {
        row[0] for row in (await db.execute(
            select(DispatchJob.package_id).where(
                DispatchJob.status.in_(CLOSED_JOB), DispatchJob.package_id.isnot(None)
            )
        )).all()
    }
    open_job_packages = {j.package_id for j in jobs if j.package_id}
    packages = [
        p for p in (await db.execute(
            select(Package).where(Package.status.in_(OPEN_PACKAGE))
        )).scalars().all()
        # A package whose job was closed is not open work (old test data)
        if p.id in open_job_packages or p.id not in closed_job_packages
    ]

    drivers = (await db.execute(select(Driver))).scalars().all()
    last_seen: Dict[str, Optional[datetime]] = {}
    for d in drivers:
        seen = [as_utc(d.last_updated)]
        beat = await heartbeat_service.get_last_heartbeat(d.id)
        if beat:
            seen.append(datetime.fromtimestamp(beat, tz=timezone.utc))
        seen = [s for s in seen if s is not None]
        last_seen[d.id] = max(seen) if seen else None

    on_board = {p.driver_id for p in packages if p.status == "loaded" and p.driver_id}
    points: Dict[str, List] = {}
    if on_board:
        rows = (await db.execute(
            select(LocationHistory)
            .where(LocationHistory.driver_id.in_(on_board))
            .where(LocationHistory.timestamp >= now - timedelta(minutes=90))
            .order_by(LocationHistory.timestamp.asc())
        )).scalars().all()
        for r in rows:
            points.setdefault(r.driver_id, []).append(r)

    return [asdict(i) for i in evaluate(jobs, packages, drivers, last_seen, points, now)]
