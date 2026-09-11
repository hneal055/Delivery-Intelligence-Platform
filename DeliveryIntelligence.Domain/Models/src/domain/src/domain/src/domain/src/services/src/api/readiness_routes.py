from fastapi import APIRouter

from src.services.readiness_service import ReadinessService

router = APIRouter()

service = ReadinessService()


@router.get("/readiness")
def get_readiness():

    return service.calculate(
        people=95,
        fleet=91,
        technology=100,
        delivery=88
    )
``