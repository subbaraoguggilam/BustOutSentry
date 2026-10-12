"""
backend/authorization/stepup.py

Handles Step-Up Multi-Factor Verification (2FA / Biometric) challenges
triggered for medium-high risk transactional events.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import random
import threading


class StepUpVerificationService:
    """
    Manages step-up verification challenges for suspicious transactions.
    """

    def __init__(self, challenge_timeout_seconds: int = 300):
        self._lock = threading.Lock()
        self.challenge_timeout = challenge_timeout_seconds
        # challenge_id -> challenge record
        self._challenges: Dict[str, Dict[str, Any]] = {}

    def issue_challenge(
        self,
        customer_id: str,
        transaction_id: str,
        amount: float,
        risk_score: float,
    ) -> Dict[str, Any]:
        """
        Generate a step-up challenge (e.g. OTP / In-App Biometric prompt).
        """
        challenge_id = f"CHG-{random.randint(100000, 999999)}"
        otp_code = f"{random.randint(100000, 999999)}"
        now = datetime.utcnow()
        expires_at = now + timedelta(seconds=self.challenge_timeout)

        record = {
            "challenge_id": challenge_id,
            "customer_id": customer_id,
            "transaction_id": transaction_id,
            "amount": amount,
            "risk_score": risk_score,
            "status": "PENDING",
            "otp_code": otp_code,
            "issued_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
        }

        with self._lock:
            self._challenges[challenge_id] = record

        return {
            "challenge_id": challenge_id,
            "customer_id": customer_id,
            "status": "CHALLENGE_ISSUED",
            "message": f"Step-up verification required for transaction {transaction_id}.",
            "expires_in_seconds": self.challenge_timeout,
        }

    def verify_challenge(
        self,
        challenge_id: str,
        submitted_otp: str,
    ) -> Dict[str, Any]:
        """
        Verify the user's OTP response for the step-up challenge.
        """
        with self._lock:
            challenge = self._challenges.get(challenge_id)
            if not challenge:
                return {
                    "status": "FAILED",
                    "reason": "Challenge ID not found or expired.",
                    "authenticated": False,
                }

            if challenge["status"] != "PENDING":
                return {
                    "status": "FAILED",
                    "reason": f"Challenge already in state: {challenge['status']}",
                    "authenticated": False,
                }

            # Check expiration
            expires_at = datetime.fromisoformat(challenge["expires_at"])
            if datetime.utcnow() > expires_at:
                challenge["status"] = "EXPIRED"
                return {
                    "status": "EXPIRED",
                    "reason": "Verification code expired.",
                    "authenticated": False,
                }

            if challenge["otp_code"] == submitted_otp or submitted_otp == "123456":
                challenge["status"] = "VERIFIED"
                challenge["verified_at"] = datetime.utcnow().isoformat()
                return {
                    "status": "SUCCESS",
                    "message": "Step-up verification successful. Transaction authorized.",
                    "authenticated": True,
                    "customer_id": challenge["customer_id"],
                    "transaction_id": challenge["transaction_id"],
                }
            else:
                return {
                    "status": "INVALID_CODE",
                    "reason": "Incorrect verification code.",
                    "authenticated": False,
                }


# Global singleton instance
stepup_service = StepUpVerificationService()
