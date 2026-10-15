from datetime import datetime
from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey, Float, Integer, JSON
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class BehaviorEventModel(Base):
    """
    Stores batched behavioral events.
    PRIVACY GUARANTEE: Never stores raw keystrokes or text values.
    """
    __tablename__ = "behavior_events"

    event_id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(String(64), ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(32), nullable=False, index=True)
    client_timestamp = Column(BigInteger, nullable=False, index=True)
    server_timestamp = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)
    event_data = Column(JSON, nullable=False)

    session = relationship("SessionModel", back_populates="behavior_events")

class BehaviorFeatureModel(Base):
    """
    Statistical feature vectors calculated across sliding temporal windows.
    """
    __tablename__ = "behavior_features"

    feature_id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(String(64), ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False, index=True)
    window_start = Column(DateTime(timezone=True), nullable=False)
    window_end = Column(DateTime(timezone=True), nullable=False)

    # Mouse dynamics
    mouse_velocity_mean = Column(Float, default=0.0)
    mouse_velocity_std = Column(Float, default=0.0)
    mouse_acceleration_mean = Column(Float, default=0.0)
    mouse_direction_changes = Column(Integer, default=0)
    mouse_path_straightness = Column(Float, default=0.0)

    # Click dynamics
    click_count = Column(Integer, default=0)
    click_interval_mean = Column(Float, default=0.0)
    click_interval_std = Column(Float, default=0.0)
    double_click_count = Column(Integer, default=0)

    # Keystroke dynamics (Statistical metadata only)
    typing_speed_cps = Column(Float, default=0.0)
    key_hold_mean_ms = Column(Float, default=0.0)
    key_hold_std_ms = Column(Float, default=0.0)
    inter_key_interval_mean_ms = Column(Float, default=0.0)
    backspace_rate = Column(Float, default=0.0)
    paste_count = Column(Integer, default=0)

    # Scroll dynamics
    scroll_count = Column(Integer, default=0)
    scroll_velocity_mean = Column(Float, default=0.0)
    scroll_direction_reversals = Column(Integer, default=0)

    # Sequence dynamics
    time_between_actions_mean_ms = Column(Float, default=0.0)
    repeated_pattern_ratio = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    session = relationship("SessionModel", back_populates="features")
