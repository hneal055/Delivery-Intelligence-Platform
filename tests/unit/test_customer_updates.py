"""Customer texts: phone handling, wording, once per event, off unless set up."""
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.backend.core.config import settings
from src.backend.services import customer_updates as cu
from src.backend.services.sms import normalize_us_phone


@pytest.mark.parametrize("raw,expected", [
    ("(312) 555-0142", "+13125550142"),
    ("312.555.0142", "+13125550142"),
    ("1-312-555-0142", "+13125550142"),
    ("+1 312 555 0142", "+13125550142"),
    ("555-0142", None),
    ("012 555 0142", None),
    ("", None),
    (None, None),
])
def test_normalize_us_phone(raw, expected):
    assert normalize_us_phone(raw) == expected


def pkg(**kw):
    base = dict(
        tracking_code="CCC-TEST2345", dest_address="8338 S SAGINAW AVE, CHICAGO, IL, 60617",
        recipient_phone="(312) 555-0142", deliver_by=None,
        texted_out_at=None, texted_delivered_at=None,
    )
    base.update(kw)
    return SimpleNamespace(**base)


@pytest.fixture
def texts_on(monkeypatch):
    monkeypatch.setattr(settings, "TWILIO_ACCOUNT_SID", "AC123")
    monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", "token")
    monkeypatch.setattr(settings, "TWILIO_FROM_NUMBER", "+13125550100")
    monkeypatch.setattr(settings, "PUBLIC_BASE_URL", "https://dip.example.com")


def test_out_for_delivery_wording(texts_on):
    text = cu.out_for_delivery_text(pkg(deliver_by=datetime(2026, 10, 12, 19, 20, tzinfo=timezone.utc)))
    assert "out for delivery" in text
    assert "8338 S Saginaw Ave" in text
    assert "expected by 2:20 PM" in text  # Chicago time
    assert "https://dip.example.com/track/CCC-TEST2345" in text
    assert "Reply STOP" in text


def test_delivered_wording(texts_on):
    text = cu.delivered_text(pkg(), datetime(2026, 10, 12, 17, 14, tzinfo=timezone.utc))
    assert "delivered at 12:14 PM" in text


def test_out_for_delivery_sent_once(texts_on):
    tasks, p = MagicMock(), pkg()
    cu.queue_out_for_delivery(tasks, p)
    cu.queue_out_for_delivery(tasks, p)
    assert tasks.add_task.call_count == 1
    assert tasks.add_task.call_args.args[1] == "+13125550142"
    assert p.texted_out_at is not None


def test_delivered_sent_once(texts_on):
    tasks, p = MagicMock(), pkg()
    now = datetime.now(timezone.utc)
    cu.queue_delivered(tasks, p, now)
    cu.queue_delivered(tasks, p, now)
    assert tasks.add_task.call_count == 1
    assert p.texted_delivered_at is not None


def test_nothing_sent_when_texts_not_set_up(monkeypatch):
    monkeypatch.setattr(settings, "TWILIO_ACCOUNT_SID", "")
    tasks, p = MagicMock(), pkg()
    cu.queue_out_for_delivery(tasks, p)
    tasks.add_task.assert_not_called()
    assert p.texted_out_at is None  # can still go out once texts are set up


def test_nothing_sent_without_a_usable_phone(texts_on):
    tasks, p = MagicMock(), pkg(recipient_phone="call the front desk")
    cu.queue_out_for_delivery(tasks, p)
    tasks.add_task.assert_not_called()
