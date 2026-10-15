from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field

CollectionModeType = Literal["HUMAN", "AUTOMATED", "UNSPECIFIED"]

class SessionConfig(BaseModel):
    batch_interval_ms: int = Field(default=2000, description="Recommended client batch transmission interval in ms")
    sampling_rate_mouse_hz: int = Field(default=60, description="Target mouse sampling rate in Hz")

class SessionStartRequest(BaseModel):
    user_agent: str = Field(..., min_length=1, max_length=512, description="Client browser user-agent string")
    screen_resolution: Optional[str] = Field(default="1920x1080", description="Viewport resolution (e.g., '1920x1080')")
    client_timezone: Optional[str] = Field(default="UTC", description="Client timezone identifier")
    client_timestamp: int = Field(..., gt=0, description="Epoch ms timestamp from client clock")
    collection_mode: Optional[CollectionModeType] = Field(default="UNSPECIFIED", description="Controlled experiment mode: 'HUMAN' or 'AUTOMATED'")
    automation_condition: Optional[str] = Field(default=None, description="Automation condition: 'AUTOMATED_DETERMINISTIC', 'AUTOMATED_VARIABLE', or 'NONE'")
    participant_id: Optional[str] = Field(default=None, description="Optional participant or bot entity identifier for grouped evaluation")
    task_id: Optional[str] = Field(default="TASK_01", description="Identifier of the task performed, e.g. 'TASK_01'")
    label: Optional[int] = Field(default=None, description="Authoritative collection label: 0 (HUMAN), 1 (AUTOMATED)")

class SessionStartResponse(BaseModel):
    session_id: str = Field(..., description="Unique generated session identifier")
    status: str = Field(default="ACTIVE", description="Initial session state")
    start_time: datetime = Field(default_factory=datetime.utcnow, description="Server timestamp of session start")
    config: SessionConfig = Field(default_factory=SessionConfig)

class SessionEndRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=64, description="Target session identifier to finalize")
    end_reason: Optional[str] = Field(default="USER_EXIT", description="Reason for session closure")
    collection_mode: Optional[CollectionModeType] = Field(default=None, description="Optional collection mode override on completion")
    automation_condition: Optional[str] = Field(default=None, description="Optional automation condition override on completion")
    participant_id: Optional[str] = Field(default=None, description="Optional participant or bot entity identifier on completion")
    task_id: Optional[str] = Field(default=None, description="Optional task ID override on completion")
    label: Optional[int] = Field(default=None, description="Optional authoritative label on completion")

class SessionEndResponse(BaseModel):
    session_id: str
    status: str = "COMPLETED"
    duration_seconds: float = Field(..., ge=0.0, description="Total active session duration in seconds")
    total_events_captured: int = Field(default=0, ge=0)
    final_integrity_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
