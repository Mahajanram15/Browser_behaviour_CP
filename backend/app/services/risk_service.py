from datetime import datetime
from typing import Dict, Any, Optional
from backend.app.schemas.risk import (
    RiskResponse,
    RiskSignals,
    RiskDecision,
    ExplanationResponse,
    ShapFeatureContribution,
    RuleTrigger,
)
from backend.app.schemas.dashboard import DashboardStatsResponse, FlaggedSessionItem
from backend.app.services.session_service import session_service

class RiskService:
    """
    Risk service orchestrating cross-layer behavioral score retrieval and explainability summaries.
    """
    def __init__(self):
        self._mock_risk_store: Dict[str, Dict[str, Any]] = {}

    async def get_risk_score(self, session_id: str) -> RiskResponse:
        now = datetime.utcnow()
        session = session_service.get_session(session_id)

        # Baseline foundation signals (will connect to ML engines in Phases 3-6)
        browser_score = 0.12
        api_score = 0.08
        api_struct_score = 0.05
        seq_score = 0.10
        freq_score = 0.04
        cross_disc = abs(browser_score - api_score)
        integrity_score = round(
            0.35 * browser_score + 0.25 * api_score + 0.20 * seq_score + 0.10 * api_struct_score + 0.10 * freq_score,
            3
        )

        decision_action = "ALLOW"
        reason = "Normal correlated human motor dynamics and standard API traversal patterns."

        if integrity_score >= 0.70:
            decision_action = "BLOCK"
            reason = "High cross-layer discordance: simulated browser events with rapid API extraction."
        elif integrity_score >= 0.35:
            decision_action = "CHALLENGE"
            reason = "Moderate behavioral anomaly detected: elevated inter-key timing uniformity."

        return RiskResponse(
            session_id=session_id,
            behavioral_integrity_score=integrity_score,
            signals=RiskSignals(
                browser_score=browser_score,
                api_anomaly_score=api_score,
                api_structure_score=api_struct_score,
                sequence_score=seq_score,
                frequency_score=freq_score,
                cross_layer_discordance=round(cross_disc, 3),
            ),
            decision=RiskDecision(
                action=decision_action,
                reason=reason,
                enacted_at=now,
            ),
            last_evaluated_at=now,
        )

    async def get_explanation(self, session_id: str) -> ExplanationResponse:
        risk = await self.get_risk_score(session_id)

        shap_contributions = [
            ShapFeatureContribution(
                feature_name="mouse_velocity_std",
                feature_value=12.4,
                shap_value=0.08,
                description="Natural variance in cursor trajectory velocity."
            ),
            ShapFeatureContribution(
                feature_name="inter_key_interval_mean_ms",
                feature_value=135.2,
                shap_value=0.04,
                description="Organic keyboard flight-time cadence."
            ),
            ShapFeatureContribution(
                feature_name="cross_layer_discordance",
                feature_value=risk.signals.cross_layer_discordance,
                shap_value=0.02,
                description="Coherence between user interaction events and backend API dispatches."
            ),
        ]

        rules = []
        if risk.behavioral_integrity_score >= 0.35:
            rules.append(
                RuleTrigger(
                    rule_id="RULE_BEHAVIORAL_DEVIATION",
                    severity="MEDIUM",
                    message="Trajectory straightness exceeds standard human baseline."
                )
            )

        return ExplanationResponse(
            session_id=session_id,
            behavioral_integrity_score=risk.behavioral_integrity_score,
            decision=risk.decision.action,
            shap_contributions=shap_contributions,
            rule_triggers=rules,
        )

    async def get_dashboard_stats(self) -> DashboardStatsResponse:
        sessions = session_service.get_all_sessions()
        total = max(len(sessions), 1)
        active = sum(1 for s in sessions.values() if s.get("status") == "ACTIVE")

        return DashboardStatsResponse(
            total_sessions=total,
            active_sessions=active,
            average_risk_score=0.18,
            decision_distribution={
                "ALLOW": total,
                "CHALLENGE": 0,
                "RATE_LIMIT": 0,
                "BLOCK": 0,
            },
            recent_flagged_sessions=[],
        )

risk_service = RiskService()
