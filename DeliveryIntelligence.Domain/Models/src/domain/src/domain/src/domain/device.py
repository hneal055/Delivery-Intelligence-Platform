from datetime import datetime

from pydantic import BaseModel


class Device(BaseModel):
    device_id: str

    driver_id: str

    device_type: str

    app_version: str

    battery_level: int

    gps_enabled: bool

    is_online: bool

    last_heartbeat_utc: datetime