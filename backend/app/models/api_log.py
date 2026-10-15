from datetime import datetime
from sqlalchemy import Column, BigInteger, String, Integer, Float, DateTime, ForeignKey, SmallInteger, JSON
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class ApiRequestModel(Base):
    """
    Correlated backend API request telemetry.
    """
    __tablename__ = "api_requests"

    request_id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(String(64), ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False, index=True)
    sequence_number = Column(Integer, nullable=False, default=1, index=True)
    endpoint = Column(String(255), nullable=False, index=True)
    http_method = Column(String(10), nullable=False)
    status_code = Column(SmallInteger, nullable=False)
    response_time_ms = Column(Float, nullable=False)
    request_size_bytes = Column(Integer, default=0)
    response_size_bytes = Column(Integer, default=0)
    headers_fingerprint = Column(String(64), nullable=True)
    payload_structure_hash = Column(String(64), nullable=True)
    param_keys = Column(JSON, nullable=True, default=list)
    payload_keys = Column(JSON, nullable=True, default=list)
    client_timestamp = Column(BigInteger, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)

    session = relationship("SessionModel", back_populates="api_requests")

