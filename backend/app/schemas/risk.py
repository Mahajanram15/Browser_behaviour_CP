from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, Field

SecurityDecisionType = Literal["ALLOW", "CHALLENGE", "RATE_LIMIT", "BLOCK"]

class RiskSignals(BaseModel):
    browser_score: float = Field(..., ge=0.0, le=1.0, description="XGBoost browser behavior anomaly score")
    api_anomaly_score: float = Field(..., ge=0.0, le=1.0, description="FastText + FAISS semantic distance score")
    api_structure_score: float = Field(..., ge=0.0, le=1.0, description="API structural cluster anomaly score")
    sequence_score: float = Field(..., ge=0.0, le=1.0, description="Markov sequence transition anomaly score")
    frequency_score: float = Field(..., ge=0.0, le=1.0, description="API frequency & rate anomaly score")
    cross_layer_discordance: float = Field(..., ge=0.0, le=1.0, description="Browser-to-Backend divergence metric")

class RiskDecision(BaseModel):
    action: SecurityDecisionType = Field(..., description="Actionable security policy determination")
    reason: str = Field(..., description="Primary justification summary")
    enacted_at: datetime = Field(default_factory=datetime.utcnow)

class RiskResponse(BaseModel):
    session_id: str
    behavioral_integrity_score: float = Field(..., ge=0.0, le=1.0, description="Consolidated risk score [0.0 - 1.0]")
    signals: RiskSignals
    decision: RiskDecision
    last_evaluated_at: datetime

class ShapFeatureContribution(BaseModel):
    feature_name: str
    feature_value: float
    shap_value: float
    description: str

class RuleTrigger(BaseModel):
    rule_id: str
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    message: str

class ExplanationResponse(BaseModel):
    session_id: str
    behavioral_integrity_score: float = Field(..., ge=0.0, le=1.0)
    decision: SecurityDecisionType
    shap_contributions: List[ShapFeatureContribution] = Field(default_factory=list)
    rule_triggers: List[RuleTrigger] = Field(default_factory=list)
