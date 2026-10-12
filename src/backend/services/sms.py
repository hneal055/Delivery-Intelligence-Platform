"""
Text messages through Twilio's REST API (no SDK needed).

Off until TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN and a sender
(TWILIO_FROM_NUMBER or TWILIO_MESSAGING_SERVICE_SID) are set: send_sms()
then logs and returns False without contacting anyone.
"""
import logging
import re
from typing import Optional

import httpx

from src.backend.core.config import settings

logger = logging.getLogger(__name__)


def sms_enabled() -> bool:
    return bool(
        settings.TWILIO_ACCOUNT_SID
        and settings.TWILIO_AUTH_TOKEN
        and (settings.TWILIO_FROM_NUMBER or settings.TWILIO_MESSAGING_SERVICE_SID)
    )


def normalize_us_phone(raw: Optional[str]) -> Optional[str]:
    """'(312) 555-0142' -> '+13125550142'; None if it isn't a US number."""
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10 or digits[0] in "01":
        return None
    return f"+1{digits}"


async def send_sms(to: str, body: str) -> bool:
    """Send one text. True if Twilio accepted it."""
    if not sms_enabled():
        logger.info("Texts are not set up; not sending to %s", to[:-4] + "****")
        return False
    data = {"To": to, "Body": body}
    if settings.TWILIO_MESSAGING_SERVICE_SID:
        data["MessagingServiceSid"] = settings.TWILIO_MESSAGING_SERVICE_SID
    else:
        data["From"] = settings.TWILIO_FROM_NUMBER
    url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_ACCOUNT_SID}/Messages.json"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                url, data=data, auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            )
    except httpx.HTTPError as exc:
        logger.warning("Text to %s failed: %s", to[:-4] + "****", exc)
        return False
    if response.status_code >= 300:
        logger.warning(
            "Twilio refused text to %s: %s %s", to[:-4] + "****", response.status_code, response.text[:200]
        )
        return False
    return True
