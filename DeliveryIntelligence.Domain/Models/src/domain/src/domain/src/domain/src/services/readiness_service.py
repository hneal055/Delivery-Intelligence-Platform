from datetime import datetime

from src.domain.readiness_score import ReadinessScore


class ReadinessService:

    def calculate(
        self,
        people: float,
        fleet: float,
        technology: float,
        delivery: float
    ) -> ReadinessScore:

        overall = (
            (people * 0.40)
            + (fleet * 0.30)
            + (technology * 0.20)
            + (delivery * 0.10)
        )

        if overall >= 90:
            status = "READY"
        elif overall >= 75:
            status = "CAUTION"
        else:
            status = "NOT_READY"

        return ReadinessScore(
            overall_score=round(overall, 2),
            people_score=people,
            fleet_score=fleet,
            technology_score=technology,
            delivery_score=delivery,
            status=status,
            calculated_utc=datetime.utcnow()
        )