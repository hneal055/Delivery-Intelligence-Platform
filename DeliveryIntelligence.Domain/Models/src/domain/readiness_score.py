from datetime import datetime
from pydantic import BaseModel


class ReadinessScore(BaseModel):
    overall_score: float
    people_score: float
    fleet_score: float
    technology_score: float
    delivery_score: float

    status: str

    calculated_utc: datetime
`