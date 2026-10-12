"""
Keeping the customer informed: the public tracking link and two texts to
the recipient's phone, "out for delivery" (driver picked it up) and
"delivered". Each text is sent at most once per package; the
texted_*_at columns are stamped in the request, the text goes out in the
background so a slow SMS service never delays the driver.
"""
from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import BackgroundTasks

from src.backend.core.config import settings
from src.backend.models.sql_models import Package
from src.backend.services.sms import normalize_us_phone, send_sms, sms_enabled

LOCAL_TZ = ZoneInfo("America/Chicago")


def tracking_url(package: Package) -> Optional[str]:
    if not package.tracking_code:
        return None
    return f"{settings.PUBLIC_BASE_URL.rstrip('/')}/track/{package.tracking_code}"


def street(package: Package) -> str:
    """'8338 S SAGINAW AVE, CHICAGO, IL, 60617' -> '8338 S Saginaw Ave'."""
    first = (package.dest_address or "").split(",")[0].strip()
    return first.title() if first.isupper() else first


def clock(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    local = value.astimezone(LOCAL_TZ)
    return local.strftime("%I:%M %p").lstrip("0")


def out_for_delivery_text(package: Package) -> str:
    where = street(package)
    due = f", expected by {clock(package.deliver_by)}" if package.deliver_by else ""
    link = tracking_url(package)
    return (
        f"{settings.COMPANY_NAME}: your package{' for ' + where if where else ''} is out for delivery{due}."
        + (f" Track it: {link}" if link else "")
        + " Reply STOP to opt out."
    )


def delivered_text(package: Package, delivered_at: datetime) -> str:
    where = street(package)
    link = tracking_url(package)
    return (
        f"{settings.COMPANY_NAME}: your package{' to ' + where if where else ''} was delivered at {clock(delivered_at)}."
        + (f" Details: {link}" if link else "")
    )


def _queue(background_tasks: BackgroundTasks, package: Package, body: str) -> bool:
    phone = normalize_us_phone(package.recipient_phone)
    if not phone or not sms_enabled():
        return False
    background_tasks.add_task(send_sms, phone, body)
    return True


def queue_out_for_delivery(background_tasks: BackgroundTasks, package: Package) -> None:
    """Call when the package goes into the van. Commit afterwards."""
    if package.texted_out_at:
        return
    if _queue(background_tasks, package, out_for_delivery_text(package)):
        package.texted_out_at = datetime.now(timezone.utc)


def queue_delivered(background_tasks: BackgroundTasks, package: Package, delivered_at: datetime) -> None:
    """Call when delivery is confirmed. Commit afterwards."""
    if package.texted_delivered_at:
        return
    if _queue(background_tasks, package, delivered_text(package, delivered_at)):
        package.texted_delivered_at = datetime.now(timezone.utc)
