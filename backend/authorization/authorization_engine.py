"""
backend/authorization/authorization_engine.py

Core real-time Transaction Authorization Engine.
Evaluates incoming card authorizations against behavioral bust-out risk,
active card freeze states, and executes automated mitigations.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from .card_control import card_control_service
from .stepup import stepup_service
from .cashout_review import cashout_review_service
from backend.services.risk_engine import BustOutRiskEngine


class AuthorizationDecision(str, Enum):
    APPROVED = "APPROVED"
    STEP_UP_REQUIRED = "STEP_UP_REQUIRED"
    HELD_FOR_REVIEW = "HELD_FOR_REVIEW"
    DECLINED_BLOCKED = "DECLINED_BLOCKED"


@dataclass
class AuthorizationRequest:
    transaction_id: str
    customer_id: str
    card_number: str
    amount: float
    merchant_name: str
    merchant_category: str
    features: Optional[Dict[str, Any]] = None


@dataclass
class AuthorizationResponse:
    transaction_id: str
    customer_id: str
    decision: AuthorizationDecision
    risk_score: float
    risk_level: str
    action_taken: str
    message: str
    timestamp: str
    details: Optional[Dict[str, Any]] = None


class AuthorizationEngine:
    """
    Evaluates real-time card authorizations and executes policy decisions.
    """

    def __init__(self, risk_engine: Optional[BustOutRiskEngine] = None):
        self.risk_engine = risk_engine or BustOutRiskEngine()

    def process_authorization(
        self,
        request: AuthorizationRequest,
        fraud_probability: float = 0.0,
    ) -> AuthorizationResponse:
        """
        Evaluate an incoming transaction request and return an authorization decision.
        """
        now = datetime.utcnow().isoformat()
        cid = request.customer_id
        features = request.features or {}

        # 1. Check if the card/account is explicitly frozen/blocked
        if card_control_service.is_blocked(cid):
            return AuthorizationResponse(
                transaction_id=request.transaction_id,
                customer_id=cid,
                decision=AuthorizationDecision.DECLINED_BLOCKED,
                risk_score=99.0,
                risk_level="HIGH_RISK_INVESTIGATION",
                action_taken="DECLINE_CARD_FROZEN",
                message="Transaction declined: Account credit access is frozen due to high fraud risk.",
                timestamp=now,
                details={"blocked": True},
            )

        # 2. Extract behavioral metrics from features
        utilization = float(features.get("utilization", 0.0))
        limit_increase_48h = float(features.get("limit_increase_48h", 0.0))
        spending_velocity_change = float(features.get("spending_velocity_change", 1.0))
        transaction_velocity_change = float(features.get("transaction_velocity_change", 1.0))
        liquidity_ratio = float(features.get("liquidity_spending_ratio", 0.0))
        third_party_ratio = float(features.get("third_party_ratio", 0.0))
        unverified_ratio = float(features.get("unverified_ratio", 0.0))

        # 3. Calculate Hybrid Risk Score
        try:
            risk_score = self.risk_engine.calculate_risk_score(
                fraud_probability=fraud_probability,
                utilization=utilization,
                limit_increase_48h=limit_increase_48h,
                spending_velocity_change=spending_velocity_change,
                transaction_velocity_change=transaction_velocity_change,
                liquidity_ratio=liquidity_ratio,
                third_party_ratio=third_party_ratio,
                unverified_ratio=unverified_ratio,
            )
        except Exception:
            # Safe default fallback
            risk_score = fraud_probability * 100

        # 4. Decision Matrix Execution
        if risk_score >= 85.0:
            # Critical risk: Decline transaction and automatically freeze the card
            card_control_service.freeze_card(
                customer_id=cid,
                reason=f"Automated block triggered: Risk score {risk_score:.1f}/100 exceeds threshold.",
                analyst_id="AUTH_ENGINE_AUTO",
            )
            return AuthorizationResponse(
                transaction_id=request.transaction_id,
                customer_id=cid,
                decision=AuthorizationDecision.DECLINED_BLOCKED,
                risk_score=round(risk_score, 2),
                risk_level="HIGH_RISK_INVESTIGATION",
                action_taken="AUTOMATED_CARD_FREEZE",
                message="Transaction declined and credit line frozen due to critical bust-out probability.",
                timestamp=now,
                details={"auto_blocked": True},
            )

        elif risk_score >= 70.0:
            # Merchant Cash-out review: hold transaction for 24-hour review
            review_info = cashout_review_service.queue_for_review(
                customer_id=cid,
                transaction_id=request.transaction_id,
                amount=request.amount,
                merchant_name=request.merchant_name,
                risk_score=risk_score,
            )
            return AuthorizationResponse(
                transaction_id=request.transaction_id,
                customer_id=cid,
                decision=AuthorizationDecision.HELD_FOR_REVIEW,
                risk_score=round(risk_score, 2),
                risk_level="MERCHANT_CASHOUT_REVIEW",
                action_taken="24_HOUR_CASHOUT_HOLD",
                message="Transaction placed on temporary 24-hour hold for merchant cash-out verification.",
                timestamp=now,
                details=review_info,
            )

        elif risk_score >= 50.0:
            # Step-up verification: issue 2FA challenge
            challenge_info = stepup_service.issue_challenge(
                customer_id=cid,
                transaction_id=request.transaction_id,
                amount=request.amount,
                risk_score=risk_score,
            )
            return AuthorizationResponse(
                transaction_id=request.transaction_id,
                customer_id=cid,
                decision=AuthorizationDecision.STEP_UP_REQUIRED,
                risk_score=round(risk_score, 2),
                risk_level="STEP_UP_VERIFICATION",
                action_taken="ISSUE_2FA_CHALLENGE",
                message="Step-up 2FA authentication challenge required to authorize this charge.",
                timestamp=now,
                details=challenge_info,
            )

        else:
            # Normal baseline activity: approve transaction
            return AuthorizationResponse(
                transaction_id=request.transaction_id,
                customer_id=cid,
                decision=AuthorizationDecision.APPROVED,
                risk_score=round(risk_score, 2),
                risk_level="MONITOR" if risk_score >= 30 else "LOW",
                action_taken="ALLOW_NORMALLY",
                message="Transaction authorized normally.",
                timestamp=now,
            )


# Global singleton instance
authorization_engine = AuthorizationEngine()
