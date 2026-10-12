"""
backend/authorization/cashout_review.py

Manages 24-hour holds and analyst review queues for high-risk
merchant cash-out and liquidity extraction events.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import threading


class CashoutReviewService:
    """
    Manages pending merchant cash-out reviews and delayed authorizations.
    """

    def __init__(self):
        self._lock = threading.Lock()
        # review_id -> review record
        self._reviews: Dict[str, Dict[str, Any]] = {}

    def queue_for_review(
        self,
        customer_id: str,
        transaction_id: str,
        amount: float,
        merchant_name: str,
        risk_score: float,
        hold_hours: int = 24,
    ) -> Dict[str, Any]:
        """
        Place a transaction into the 24-hour merchant cash-out review queue.
        """
        review_id = f"REV-{customer_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        now = datetime.utcnow()
        hold_until = now + timedelta(hours=hold_hours)

        record = {
            "review_id": review_id,
            "customer_id": customer_id,
            "transaction_id": transaction_id,
            "amount": amount,
            "merchant_name": merchant_name,
            "risk_score": risk_score,
            "status": "UNDER_REVIEW",
            "hold_until": hold_until.isoformat(),
            "queued_at": now.isoformat(),
            "decision": None,
            "analyst_notes": None,
        }

        with self._lock:
            self._reviews[review_id] = record

        return {
            "review_id": review_id,
            "status": "HELD_FOR_REVIEW",
            "hold_duration_hours": hold_hours,
            "hold_until": hold_until.isoformat(),
            "message": f"Transaction of ${amount:,.2f} at {merchant_name} held for 24-hour risk review.",
        }

    def list_pending_reviews(self) -> List[Dict[str, Any]]:
        """
        List all transactions currently pending analyst cash-out review.
        """
        with self._lock:
            return [
                dict(r) for r in self._reviews.values()
                if r.get("status") == "UNDER_REVIEW"
            ]

    def resolve_review(
        self,
        review_id: str,
        decision: str,  # "APPROVED" or "REJECTED"
        analyst_id: str,
        notes: str = "",
    ) -> Dict[str, Any]:
        """
        Approve or reject a transaction in the cash-out review queue.
        """
        with self._lock:
            review = self._reviews.get(review_id)
            if not review:
                return {
                    "status": "ERROR",
                    "message": f"Review ID {review_id} not found.",
                }

            review["status"] = "RESOLVED"
            review["decision"] = decision
            review["analyst_id"] = analyst_id
            review["analyst_notes"] = notes
            review["resolved_at"] = datetime.utcnow().isoformat()

            return {
                "status": "SUCCESS",
                "review_id": review_id,
                "decision": decision,
                "message": f"Review {review_id} resolved with decision: {decision}.",
            }


# Global singleton instance
cashout_review_service = CashoutReviewService()
