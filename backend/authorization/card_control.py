"""
backend/authorization/card_control.py

Manages card-level controls, credit line freezes, and velocity lockouts
for accounts suspected of first-party bust-out fraud.
"""

from typing import Dict, Any, Optional
from datetime import datetime
import threading


class CardControlService:
    """
    Thread-safe service to manage card statuses and credit limits.
    """

    def __init__(self):
        self._lock = threading.Lock()
        # customer_id -> card status record
        self._cards: Dict[str, Dict[str, Any]] = {}

    def get_card_status(self, customer_id: str) -> Dict[str, Any]:
        """
        Get the current authorization status of a customer's credit lines.
        """
        with self._lock:
            if customer_id not in self._cards:
                return {
                    "customer_id": customer_id,
                    "status": "ACTIVE",
                    "credit_access": "OPEN",
                    "card_locked": False,
                    "pos_enabled": True,
                    "atm_enabled": True,
                    "online_enabled": True,
                    "updated_at": datetime.utcnow().isoformat(),
                }
            return dict(self._cards[customer_id])

    def freeze_card(
        self,
        customer_id: str,
        reason: str = "First-party bust-out risk mitigation",
        analyst_id: str = "SYSTEM_AUTO",
    ) -> Dict[str, Any]:
        """
        Freeze all card transactions and credit line access for a customer.
        """
        with self._lock:
            record = {
                "customer_id": customer_id,
                "status": "BLOCKED",
                "credit_access": "DISABLED",
                "card_locked": True,
                "pos_enabled": False,
                "atm_enabled": False,
                "online_enabled": False,
                "freeze_reason": reason,
                "analyst_id": analyst_id,
                "updated_at": datetime.utcnow().isoformat(),
            }
            self._cards[customer_id] = record
            return dict(record)

    def unfreeze_card(
        self,
        customer_id: str,
        analyst_id: str = "ANALYST_OVERRIDE",
    ) -> Dict[str, Any]:
        """
        Restore full credit line access and card authorization for a customer.
        """
        with self._lock:
            record = {
                "customer_id": customer_id,
                "status": "ACTIVE",
                "credit_access": "OPEN",
                "card_locked": False,
                "pos_enabled": True,
                "atm_enabled": True,
                "online_enabled": True,
                "unfreeze_reason": "Analyst verification complete",
                "analyst_id": analyst_id,
                "updated_at": datetime.utcnow().isoformat(),
            }
            self._cards[customer_id] = record
            return dict(record)

    def is_blocked(self, customer_id: str) -> bool:
        """
        Quick check if a customer's credit line is blocked.
        """
        with self._lock:
            card = self._cards.get(customer_id)
            return card is not None and card.get("status") == "BLOCKED"

    def list_all_blocked(self) -> list:
        """
        List all currently blocked accounts.
        """
        with self._lock:
            return [
                card for card in self._cards.values()
                if card.get("status") == "BLOCKED"
            ]


# Global singleton instance
card_control_service = CardControlService()
