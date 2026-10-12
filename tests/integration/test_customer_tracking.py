"""Public tracking page and the customer texts on scan / delivery."""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from src.backend.core.config import settings
from src.backend.models.sql_models import DeliveryProof
from src.backend.services import customer_updates
from tests.integration.conftest import int_db_seed_package

CODE = "CCC-TRACK234"


async def seed(db, **fields):
    p = await int_db_seed_package(db, status=fields.pop("status", "assigned"))
    p.tracking_code = CODE
    p.dest_address = "8338 S SAGINAW AVE, CHICAGO, IL, 60617"
    p.recipient_name = "Jane Customer"
    p.recipient_phone = "(312) 555-0142"
    p.delivery_instructions = "Gate code 4321"
    for k, v in fields.items():
        setattr(p, k, v)
    await db.commit()
    return p


# --- public page -----------------------------------------------------------------

@pytest.mark.asyncio
async def test_scheduled_package_page(int_client_anon):
    client, db = int_client_anon[0], int_client_anon[1]
    await seed(db, deliver_by=datetime.now(timezone.utc) + timedelta(hours=2))
    resp = await client.get(f"/public/track/{CODE}")
    assert resp.status_code == 200
    page = resp.text
    assert "Scheduled" in page and CODE in page
    assert "8338 S Saginaw Ave" in page
    assert "Expected by" in page
    assert resp.headers["x-robots-tag"].startswith("noindex")


@pytest.mark.asyncio
async def test_page_never_shows_private_details(int_client_anon):
    client, db = int_client_anon[0], int_client_anon[1]
    await seed(db)
    page = (await client.get(f"/public/track/{CODE}")).text
    for private in ("Jane Customer", "555-0142", "Gate code", "4321"):
        assert private not in page


@pytest.mark.asyncio
async def test_delivered_page_shows_time(int_client_anon):
    client, db = int_client_anon[0], int_client_anon[1]
    p = await seed(db, status="delivered", loaded_at=datetime.now(timezone.utc) - timedelta(minutes=30))
    db.add(DeliveryProof(package_id=p.id, driver_id="driver1", photo_key="x.jpg",
                         captured_at=datetime.now(timezone.utc)))
    await db.commit()
    page = (await client.get(f"/public/track/{CODE.lower()}")).text  # code is case-insensitive
    assert "Delivered" in page and "Picked up" in page


@pytest.mark.asyncio
@pytest.mark.parametrize("code", ["CCC-NOPE2345", "anything", "CCC-" + "X" * 40])
async def test_unknown_code_is_404(int_client_anon, code):
    client = int_client_anon[0]
    resp = await client.get(f"/public/track/{code}")
    assert resp.status_code == 404
    assert "Package not found" in resp.text


# --- texts ---------------------------------------------------------------------

@pytest.fixture
def texts_on(monkeypatch):
    monkeypatch.setattr(settings, "TWILIO_ACCOUNT_SID", "AC123")
    monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", "token")
    monkeypatch.setattr(settings, "TWILIO_FROM_NUMBER", "+13125550100")
    sent = AsyncMock(return_value=True)
    monkeypatch.setattr(customer_updates, "send_sms", sent)
    return sent


@pytest.mark.asyncio
async def test_scan_texts_out_for_delivery_once(int_client_driver, texts_on):
    client, db, _ = int_client_driver
    p = await seed(db)
    for _ in range(2):  # a second scan must not text again
        resp = await client.post("/delivery/scan", json={"barcode": CODE, "scan_type": "manual"})
        assert resp.status_code == 200
    assert texts_on.await_count == 1
    to, body = texts_on.await_args.args
    assert to == "+13125550142" and "out for delivery" in body and CODE in body
    await db.refresh(p)
    assert p.texted_out_at is not None


@pytest.mark.asyncio
async def test_scan_without_texts_set_up_sends_nothing(int_client_driver, monkeypatch):
    monkeypatch.setattr(settings, "TWILIO_ACCOUNT_SID", "")
    sent = AsyncMock()
    monkeypatch.setattr(customer_updates, "send_sms", sent)
    client, db, _ = int_client_driver
    await seed(db)
    resp = await client.post("/delivery/scan", json={"barcode": CODE, "scan_type": "manual"})
    assert resp.status_code == 200
    sent.assert_not_awaited()
