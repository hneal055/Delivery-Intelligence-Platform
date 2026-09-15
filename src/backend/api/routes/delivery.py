from fastapi import APIRouter

router = APIRouter(
    prefix="/delivery",
    tags=["delivery"],
)


@router.get("/health")
async def health():
    return {
        "status": "ok"
    }