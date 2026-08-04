from fastapi import APIRouter

from app.models.http.errors import HealthStatusResponse

router = APIRouter()


@router.get("/health", response_model=HealthStatusResponse)
async def health() -> HealthStatusResponse:
    return HealthStatusResponse()
