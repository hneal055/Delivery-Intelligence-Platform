"""
Delivery Intelligence Platform
V4 Readiness Service

Calculates operational readiness from
people, fleet, technology, and delivery metrics.
"""

from datetime import datetime


class ReadinessService:

    async def calculate(
        self,
        people_score: float,
        fleet_score: float,
        technology_score: float,
        delivery_score: float,
    ) -> dict:

        overall_score = (
            people_score * 0.40
            + fleet_score * 0.30
            + technology_score * 0.20
            + delivery_score * 0.10
        )

        return {
            "overall_score": round(overall_score, 2),
            "people_score": people_score,
            "fleet_score": fleet_score,
            "technology_score": technology_score,
            "delivery_score": delivery_score,
            "status": self._determine_status(overall_score),
            "calculated_utc": datetime.utcnow().isoformat(),
        }

    def _determine_status(
        self,
        score: float,
    ) -> str:

        if score >= 90:
            return "READY"

        if score >= 75:
            return "CAUTION"

        return "NOT_READY"


readiness_service = ReadinessService()