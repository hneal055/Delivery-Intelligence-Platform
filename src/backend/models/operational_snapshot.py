"""
Delivery Intelligence Platform
Operational Snapshot Model

This model represents the real-time operational state
of the platform and serves as the primary payload for:

- Command Center Dashboard
- WebSocket Updates
- Readiness Engine
- Morning Operations Briefing
- Recommendation Engine
"""

from datetime import datetime

from pydantic import BaseModel


class OperationalSnapshot(BaseModel):
    # Driver Metrics
    drivers_online: int
    drivers_available: int

    # Delivery Metrics
    active_deliveries: int
    pending_deliveries: int
    completed_deliveries: int

    # Route Metrics
    active_routes: int

    # Alert Metrics
    active_alerts: int

    # Readiness
    readiness_score: float

    # Metadata
    generated_utc: datetime