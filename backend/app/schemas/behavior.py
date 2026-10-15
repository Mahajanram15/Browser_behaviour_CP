from typing import List, Dict, Any, Literal
from pydantic import BaseModel, Field

EventTypeEnum = Literal["mouse_move", "mouse_click", "scroll", "key_meta", "navigation", "visibility"]

class BehaviorEventItem(BaseModel):
    event_type: EventTypeEnum = Field(..., description="Telemetry category")
    client_timestamp: int = Field(..., gt=0, description="Epoch ms timestamp when event occurred on client")
    event_data: Dict[str, Any] = Field(
        ...,
        description="Privacy-compliant derived dynamics (e.g. velocity, hold_duration_ms). Zero raw keystrokes."
    )

class BehaviorBatchRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=64, description="Target session identifier")
    events: List[BehaviorEventItem] = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Batched client behavioral events"
    )

class BehaviorBatchResponse(BaseModel):
    session_id: str
    processed_events: int
    status: str = "INGESTED"
