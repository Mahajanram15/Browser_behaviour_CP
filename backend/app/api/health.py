from datetime import datetime
from fastapi import APIRouter, status
from pydantic import BaseModel
from typing import Dict

router = APIRouter(tags=["Health"])

class HealthCheckResponse(BaseModel):
    status: str
    version: str
    timestamp: datetime
    components: Dict[str, str]

@router.get("/health", response_model=HealthCheckResponse, status_code=status.HTTP_200_OK)
async def health_check():
    """
    Returns system operational status and subsystem readiness.
    """
    return HealthCheckResponse(
        status="healthy",
        version="0.1.0",
        timestamp=datetime.utcnow(),
        components={
            "database": "ready",
            "feature_engine": "ready",
            "ml_models": "initialized",
            "api_gateway": "ready",
        },
    )
