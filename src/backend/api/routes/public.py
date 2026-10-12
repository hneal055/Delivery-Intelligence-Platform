"""
Public package tracking for customers: /track/<tracking code> (nginx sends
it here as /public/track/<code>). No login. Shows only what a customer needs:
status, times, the street it's going to and the promised time; never names,
phone numbers, instructions, photos or where the van is.

Tracking codes are 8 random characters from a 31-letter alphabet (about
850 billion combinations) and the page is rate-limited per visitor.
"""
import html
from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.api.limiter import limiter
from src.backend.core.config import settings
from src.backend.core.database import get_db
from src.backend.models.sql_models import DeliveryProof, Package
from src.backend.services.customer_updates import street

router = APIRouter(prefix="/public", tags=["public"])

LOCAL_TZ = ZoneInfo("America/Chicago")
HEADERS = {
    "X-Robots-Tag": "noindex, nofollow",  # keep tracking pages out of search engines
    "Cache-Control": "no-store",
    "Referrer-Policy": "no-referrer",
}


def _when(value: Optional[datetime]) -> str:
    if value is None:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    local = value.astimezone(LOCAL_TZ)
    clock = local.strftime("%I:%M %p").lstrip("0")
    today = datetime.now(LOCAL_TZ).date()
    return clock if local.date() == today else f"{local.strftime('%a %b')} {local.day}, {clock}"


def _page(title: str, body: str) -> str:
    company = html.escape(settings.COMPANY_NAME)
    phone = html.escape(settings.COMPANY_PHONE)
    contact = f'<p class="muted">Questions? Call {company} at <a href="tel:{phone}">{phone}</a>.</p>' if phone else ""
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>{html.escape(title)} · {company}</title>
<style>
body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;margin:0;background:#f4f6f8;color:#1a1d21}}
main{{max-width:480px;margin:0 auto;padding:24px 16px}}
.brand{{font-weight:700;font-size:18px;margin-bottom:16px}}
.card{{background:#fff;border-radius:12px;padding:20px;box-shadow:0 1px 3px rgba(0,0,0,.08)}}
h1{{font-size:22px;margin:0 0 4px}}
.code{{font-family:ui-monospace,Menlo,monospace;color:#555;font-size:14px}}
ol{{list-style:none;padding:0;margin:20px 0 0}}
li{{display:flex;gap:12px;padding:10px 0;border-top:1px solid #eee}}
.dot{{width:14px;height:14px;border-radius:50%;margin-top:3px;flex:none;background:#d0d5db}}
.done .dot{{background:#2f9e44}} .now .dot{{background:#1c7ed6}} .bad .dot{{background:#e03131}}
.step{{font-weight:600}} .muted{{color:#666;font-size:14px}}
.late{{color:#e03131;font-weight:600}}
</style></head>
<body><main><div class="brand">{company}</div>{body}{contact}</main></body></html>"""


def _not_found() -> HTMLResponse:
    body = """<div class="card"><h1>Package not found</h1>
<p class="muted">Check the tracking code in your text or email. Codes look like CCC-7K3QX9M2.</p></div>"""
    return HTMLResponse(_page("Package not found", body), status_code=404, headers=HEADERS)


@router.get("/track/{code}", response_class=HTMLResponse, include_in_schema=False)
@limiter.limit("30/minute")
async def track_package(request: Request, code: str, db: AsyncSession = Depends(get_db)):
    code = code.strip().upper()
    if not code.startswith("CCC-") or len(code) > 20:
        return _not_found()
    package = (await db.execute(select(Package).where(Package.tracking_code == code))).scalars().first()
    if package is None:
        return _not_found()

    delivered_at = (await db.execute(
        select(func.min(DeliveryProof.captured_at)).where(DeliveryProof.package_id == package.id)
    )).scalar()

    status = package.status
    delivered = status == "delivered"
    on_the_way = status == "loaded"
    problem = status == "exception"

    if delivered:
        headline = f"Delivered {_when(delivered_at)}".strip()
    elif problem:
        headline = "Delivery attempt unsuccessful"
    elif on_the_way:
        headline = "Out for delivery"
    else:
        headline = "Scheduled"

    def step(css: str, title: str, detail: str = "") -> str:
        extra = f'<div class="muted">{html.escape(detail)}</div>' if detail else ""
        return f'<li class="{css}"><span class="dot"></span><div><div class="step">{html.escape(title)}</div>{extra}</div></li>'

    steps = [step("done", "Order received", _when(package.created_at))]
    if on_the_way or delivered:
        steps.append(step("done" if delivered else "now", "Picked up · on its way", _when(package.loaded_at)))
    else:
        steps.append(step("", "Picked up · on its way"))
    if delivered:
        steps.append(step("done", "Delivered", _when(delivered_at)))
    elif problem:
        steps.append(step("bad", "Not delivered yet", "We couldn't complete the delivery. We'll be in touch."))
    else:
        steps.append(step("", "Delivered"))

    promise = ""
    if package.deliver_by and not delivered:
        late = datetime.now(timezone.utc) > (
            package.deliver_by if package.deliver_by.tzinfo else package.deliver_by.replace(tzinfo=timezone.utc)
        )
        promise = (
            f'<p class="{"late" if late else "muted"}">Expected by {html.escape(_when(package.deliver_by))}'
            f'{" (running late)" if late else ""}</p>'
        )
    where = street(package)
    destination = f'<p class="muted">To: {html.escape(where)}</p>' if where else ""

    body = f"""<div class="card">
<h1>{html.escape(headline)}</h1>
<div class="code">{html.escape(code)}</div>
{destination}{promise}
<ol>{''.join(steps)}</ol>
</div>"""
    return HTMLResponse(_page(f"Tracking {code}", body), headers=HEADERS)
