from datetime import datetime
from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey, Float, Text, JSON
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class RiskScoreModel(Base):
    """
    Fused multi-signal behavioral risk calculations.
    """
    __tablename__ = "risk_scores"

    score_id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(String(64), ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False, index=True)
    browser_score = Column(Float, nullable=False, default=0.0)
    api_anomaly_score = Column(Float, nullable=False, default=0.0)
    api_structure_score = Column(Float, nullable=False, default=0.0)
    sequence_score = Column(Float, nullable=False, default=0.0)
    frequency_score = Column(Float, nullable=False, default=0.0)
    cross_layer_inconsistency_score = Column(Float, nullable=False, default=0.0)
    behavioral_integrity_score = Column(Float, nullable=False, default=0.0, index=True)
    evaluated_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)

    session = relationship("SessionModel", back_populates="risk_scores")
    security_actions = relationship("SecurityActionModel", back_populates="risk_score")

class SecurityActionModel(Base):
    """
    Security policy decisions (ALLOW, CHALLENGE, RATE_LIMIT, BLOCK).
    """
    __tablename__ = "security_actions"

    action_id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(String(64), ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False, index=True)
    score_id = Column(BigInteger, ForeignKey("risk_scores.score_id", ondelete="SET NULL"), nullable=True)
    decision = Column(String(20), nullable=False, index=True)
    reason = Column(Text, nullable=False)
    shap_contributions = Column(JSON, default=dict)
    rule_triggers = Column(JSON, default=list)
    enacted_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)

    session = relationship("SessionModel", back_populates="security_actions")
    risk_score = relationship("RiskScoreModel", back_populates="security_actions")
