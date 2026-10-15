from datetime import datetime
from typing import List, Dict, Optional
from pydantic import BaseModel, Field

class FlaggedSessionItem(BaseModel):
    session_id: str
    risk_score: float = Field(..., ge=0.0, le=1.0)
    decision: str
    primary_reason: str
    timestamp: datetime

class DashboardStatsResponse(BaseModel):
    total_sessions: int = Field(default=0, ge=0)
    active_sessions: int = Field(default=0, ge=0)
    average_risk_score: float = Field(default=0.0, ge=0.0, le=1.0)
    decision_distribution: Dict[str, int] = Field(
        default_factory=lambda: {
            "ALLOW": 0,
            "CHALLENGE": 0,
            "RATE_LIMIT": 0,
            "BLOCK": 0,
        }
    )
    recent_flagged_sessions: List[FlaggedSessionItem] = Field(default_factory=list)
