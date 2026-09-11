"""
Delivery Intelligence Platform
V4 Operational State Service

Aggregates operational data from platform services into
a single Command Center snapshot.

Consumers:

- Command Center Dashboard
- WebSocket Updates
- Readiness Engine
- Morning Operations Briefing
- Recommendation Engine
"""

from datetime import datetime

from sqlalchemy import func, select

from src.backend.core.database import AsyncSessionLocal
from src.backend.models.operational_snapshot import OperationalSnapshot
from src.backend.models.sql_models import (
    Driver,
    Package,
)
from src.backend.services.heartbeat import heartbeat_service
from src.backend.services.readiness_service import readiness_service


class OperationalStateService:

    async def get_snapshot(self) -> OperationalSnapshot:
        """
        Generate a real-time operational snapshot.
        """

        drivers_online = await self._drivers_online()

        drivers_available = await self._drivers_available()

        active_deliveries = await self._active_deliveries()

        pending_deliveries = await self._pending_deliveries()

        completed_deliveries = await self._completed_deliveries()

        active_routes = await self._active_routes()

        active_alerts = await self._active_alerts()

        readiness_score = await self._readiness_score(
            drivers_online=drivers_online,
            drivers_available=drivers_available,
            active_deliveries=active_deliveries,
            pending_deliveries=pending_deliveries,
            active_routes=active_routes,
        )

        return OperationalSnapshot(
            drivers_online=drivers_online,
            drivers_available=drivers_available,
            active_deliveries=active_deliveries,
            pending_deliveries=pending_deliveries,
            completed_deliveries=completed_deliveries,
            active_routes=active_routes,
            active_alerts=active_alerts,
            readiness_score=readiness_score,
            generated_utc=datetime.utcnow(),
        )

    async def _drivers_online(self) -> int:
        """
        Live value from Heartbeat Service.
        """

        return await heartbeat_service.get_online_count()

    async def _drivers_available(self) -> int:
        """
        Count active drivers in the database.
        """

        async with AsyncSessionLocal() as db:

            result = await db.execute(
                select(func.count())
                .select_from(Driver)
                .where(Driver.status == "active")
            )

            return result.scalar() or 0

    async def _active_deliveries(self) -> int:
        """
        Count packages currently out for delivery.
        """

        async with AsyncSessionLocal() as db:

            result = await db.execute(
                select(func.count())
                .select_from(Package)
                .where(
                    Package.status.in_(
                        [
                            "out_for_delivery",
                            "assigned",
                            "in_progress",
                        ]
                    )
                )
            )

            return result.scalar() or 0

    async def _pending_deliveries(self) -> int:
        """
        Count packages waiting for delivery.
        """

        async with AsyncSessionLocal() as db:

            result = await db.execute(
                select(func.count())
                .select_from(Package)
                .where(Package.status == "pending")
            )

            return result.scalar() or 0

    async def _completed_deliveries(self) -> int:
        """
        Count delivered packages.
        """

        async with AsyncSessionLocal() as db:

            result = await db.execute(
                select(func.count())
                .select_from(Package)
                .where(Package.status == "delivered")
            )

            return result.scalar() or 0

    async def _active_routes(self) -> int:
        """
        Placeholder until routing metrics are integrated.
        """

        return 0

    async def _active_alerts(self) -> int:
        """
        Placeholder until alert framework is implemented.
        """

        return 0

    async def _readiness_score(
        self,
        drivers_online: int,
        drivers_available: int,
        active_deliveries: int,
        pending_deliveries: int,
        active_routes: int,
    ) -> float:
        """
        Calculate operational readiness.

        Uses ReadinessService so readiness logic
        remains centralized.
        """

        people_score = min(
            100.0,
            float(drivers_available * 2),
        )

        fleet_score = 90.0

        technology_score = 100.0

        delivery_score = (
            100.0
            if pending_deliveries == 0
            else max(
                50.0,
                100.0 - pending_deliveries,
            )
        )

        readiness = await readiness_service.calculate(
            people_score=people_score,
            fleet_score=fleet_score,
            technology_score=technology_score,
            delivery_score=delivery_score,
        )

        return readiness["overall_score"]


operational_state_service = OperationalStateService()