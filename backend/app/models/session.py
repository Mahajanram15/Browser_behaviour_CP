from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class SessionModel(Base):
    __tablename__ = "sessions"

    session_id = Column(String(64), primary_key=True, index=True)
    user_agent = Column(Text, nullable=False)
    ip_hash = Column(String(64), nullable=False)
    start_time = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), default="ACTIVE", nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    behavior_events = relationship("BehaviorEventModel", back_populates="session", cascade="all, delete-orphan")
    api_requests = relationship("ApiRequestModel", back_populates="session", cascade="all, delete-orphan")
    features = relationship("BehaviorFeatureModel", back_populates="session", cascade="all, delete-orphan")
    risk_scores = relationship("RiskScoreModel", back_populates="session", cascade="all, delete-orphan")
    security_actions = relationship("SecurityActionModel", back_populates="session", cascade="all, delete-orphan")
