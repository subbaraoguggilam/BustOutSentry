# backend/api/main.py

from pathlib import Path
from typing import Any, Dict

import pickle

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.services.live_results import live_results
from backend.services.risk_engine import BustOutRiskEngine
from backend.authorization import (
    card_control_service,
    authorization_engine,
    AuthorizationRequest,
)


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

MODEL_PATH = PROJECT_ROOT / "ml" / "artifacts" / "temporal_xgboost.pkl"
FEATURE_NAMES_PATH = (
    PROJECT_ROOT / "ml" / "artifacts" / "temporal_feature_names.pkl"
)


# ============================================================
# LOAD ML MODEL
# ============================================================

model = None
feature_names = []

try:
    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)

    with open(FEATURE_NAMES_PATH, "rb") as f:
        feature_names = pickle.load(f)

    print("==============================================")
    print("BustOutSentry ML Model Loaded Successfully")
    print("==============================================")
    print(f"Model: {MODEL_PATH}")
    print(f"Number of features: {len(feature_names)}")

except Exception as e:
    print("==============================================")
    print("WARNING: ML MODEL COULD NOT BE LOADED")
    print("==============================================")
    print(f"Error: {e}")


# ============================================================
# RISK ENGINE
# ============================================================

risk_engine = BustOutRiskEngine()


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="BustOutSentry API",
    description=(
        "Real-time behavioral fraud detection API "
        "for first-party credit-card bust-out detection."
    ),
    version="1.0.0",
)


# ============================================================
# CORS
# ============================================================
# Allows React/Vite running on localhost:5173
# to communicate with FastAPI running on localhost:8000.

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_feature_value(
    data: Dict[str, Any],
    feature_name: str,
    default: float = 0.0
) -> float:
    """
    Safely retrieve a numerical feature from incoming data.
    """

    value = data.get(feature_name, default)

    try:
        if value is None:
            return default

        return float(value)

    except (ValueError, TypeError):
        return default


def get_risk_level(score: float) -> str:
    """
    Convert 0-100 risk score into risk level.
    """

    if score <= 30:
        return "LOW"

    elif score <= 50:
        return "MONITOR"

    elif score <= 70:
        return "STEP_UP_VERIFICATION"

    elif score <= 85:
        return "MERCHANT_CASHOUT_REVIEW"

    else:
        return "HIGH_RISK_INVESTIGATION"


def get_recommended_action(risk_level: str) -> str:
    """
    Convert risk level into recommended security action.
    """

    actions = {
        "LOW": "ALLOW_NORMALLY",

        "MONITOR": (
            "MONITOR_CUSTOMER_BEHAVIOR"
        ),

        "STEP_UP_VERIFICATION": (
            "REQUIRE_ADDITIONAL_VERIFICATION"
        ),

        "MERCHANT_CASHOUT_REVIEW": (
            "24_HOUR_MERCHANT_CASHOUT_REVIEW"
        ),

        "HIGH_RISK_INVESTIGATION": (
            "STRONG_VERIFICATION_AND_FRAUD_INVESTIGATION"
        ),
    }

    return actions.get(
        risk_level,
        "MONITOR_CUSTOMER_BEHAVIOR"
    )


def generate_risk_reasons(data: Dict[str, Any]) -> list:
    """
    Generate human-readable explanations
    from important behavioral risk signals.
    """

    reasons = []

    utilization = get_feature_value(
        data,
        "utilization"
    )

    limit_increase_48h = get_feature_value(
        data,
        "limit_increase_48h"
    )

    spending_velocity_change = get_feature_value(
        data,
        "spending_velocity_change"
    )

    transaction_velocity_change = get_feature_value(
        data,
        "transaction_velocity_change"
    )

    liquidity_ratio = get_feature_value(
        data,
        "liquidity_spending_ratio"
    )

    third_party_ratio = get_feature_value(
        data,
        "third_party_ratio"
    )

    unverified_ratio = get_feature_value(
        data,
        "unverified_ratio"
    )

    # -----------------------------------------
    # Credit utilization
    # -----------------------------------------

    if utilization >= 0.95:
        reasons.append(
            f"Very high credit utilization ({utilization * 100:.1f}%)"
        )

    elif utilization >= 0.85:
        reasons.append(
            f"High credit utilization ({utilization * 100:.1f}%)"
        )

    elif utilization >= 0.70:
        reasons.append(
            f"Elevated credit utilization ({utilization * 100:.1f}%)"
        )

    # -----------------------------------------
    # Credit-limit increase
    # -----------------------------------------

    if limit_increase_48h > 5000:
        reasons.append(
            f"Large credit-limit increase in the last 48 hours "
            f"({limit_increase_48h:.0f})"
        )

    elif limit_increase_48h > 0:
        reasons.append(
            "Recent credit-limit increase detected"
        )

    # -----------------------------------------
    # Spending velocity
    # -----------------------------------------

    if spending_velocity_change >= 3:
        reasons.append(
            f"Spending velocity increased significantly "
            f"({spending_velocity_change:.1f}x)"
        )

    elif spending_velocity_change >= 2:
        reasons.append(
            f"Spending velocity increased "
            f"({spending_velocity_change:.1f}x)"
        )

    # -----------------------------------------
    # Transaction velocity
    # -----------------------------------------

    if transaction_velocity_change >= 3:
        reasons.append(
            f"Transaction velocity increased significantly "
            f"({transaction_velocity_change:.1f}x)"
        )

    elif transaction_velocity_change >= 2:
        reasons.append(
            f"Transaction velocity increased "
            f"({transaction_velocity_change:.1f}x)"
        )

    # -----------------------------------------
    # Liquidity
    # -----------------------------------------

    if liquidity_ratio >= 0.50:
        reasons.append(
            f"High-liquidity spending represents "
            f"{liquidity_ratio * 100:.1f}% of recent activity"
        )

    elif liquidity_ratio >= 0.25:
        reasons.append(
            f"Elevated liquidity-related spending "
            f"({liquidity_ratio * 100:.1f}%)"
        )

    # -----------------------------------------
    # Third-party payments
    # -----------------------------------------

    if third_party_ratio >= 0.40:
        reasons.append(
            f"High third-party payment activity "
            f"({third_party_ratio * 100:.1f}%)"
        )

    elif third_party_ratio >= 0.20:
        reasons.append(
            f"Elevated third-party payment activity "
            f"({third_party_ratio * 100:.1f}%)"
        )

    # -----------------------------------------
    # Unverified payments
    # -----------------------------------------

    if unverified_ratio >= 0.30:
        reasons.append(
            f"High unverified payment activity "
            f"({unverified_ratio * 100:.1f}%)"
        )

    elif unverified_ratio >= 0.10:
        reasons.append(
            f"Elevated unverified payment activity "
            f"({unverified_ratio * 100:.1f}%)"
        )

    # -----------------------------------------
    # Default explanation
    # -----------------------------------------

    if not reasons:
        reasons.append(
            "No major behavioral risk indicators detected"
        )

    return reasons


# ============================================================
# ROOT ENDPOINT
# ============================================================

@app.get("/")
def root():
    return {
        "application": "BustOutSentry",
        "description": (
            "Real-time behavioral fraud detection "
            "and first-party bust-out risk system"
        ),
        "status": "running",
        "model_loaded": model is not None,
        "feature_count": len(feature_names),
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health_check():

    return {
        "status": "healthy",
        "service": "BustOutSentry FastAPI",
        "model_loaded": model is not None,
        "feature_count": len(feature_names),
    }


# ============================================================
# SCORE REQUEST
# ============================================================

@app.post("/score")
def score_customer(data: Dict[str, Any]):

    if model is None:
        raise HTTPException(
            status_code=503,
            detail="ML model is not loaded."
        )

    customer_id = data.get(
        "customer_id",
        "UNKNOWN"
    )

    # --------------------------------------------------------
    # Some clients may send:
    #
    # {
    #     "customer_id": "C000421",
    #     "features": {...}
    # }
    #
    # Others may send the features directly.
    # This code supports both.
    # --------------------------------------------------------

    if isinstance(data.get("features"), dict):

        features = data["features"]

    else:

        features = {
            key: value
            for key, value in data.items()
            if key != "customer_id"
        }

    # --------------------------------------------------------
    # Create feature vector in EXACT model feature order
    # --------------------------------------------------------

    feature_vector = []

    for feature_name in feature_names:

        value = features.get(
            feature_name,
            0
        )

        try:

            if value is None:
                value = 0

            value = float(value)

        except (ValueError, TypeError):

            value = 0

        feature_vector.append(value)

    # --------------------------------------------------------
    # XGBoost prediction
    # --------------------------------------------------------

    try:

        probabilities = model.predict_proba(
            [feature_vector]
        )[0]

        fraud_probability = float(
            probabilities[1]
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Model prediction failed: {str(e)}"
        )

    # --------------------------------------------------------
    # Behavioral signals
    # --------------------------------------------------------

    utilization = get_feature_value(
        features,
        "utilization"
    )

    limit_increase_48h = get_feature_value(
        features,
        "limit_increase_48h"
    )

    spending_velocity_change = get_feature_value(
        features,
        "spending_velocity_change"
    )

    transaction_velocity_change = get_feature_value(
        features,
        "transaction_velocity_change"
    )

    liquidity_ratio = get_feature_value(
        features,
        "liquidity_spending_ratio"
    )

    third_party_ratio = get_feature_value(
        features,
        "third_party_ratio"
    )

    unverified_ratio = get_feature_value(
        features,
        "unverified_ratio"
    )

    # --------------------------------------------------------
    # Hybrid Risk Engine
    # --------------------------------------------------------

    try:

        risk_score = risk_engine.calculate_risk_score(
            fraud_probability=fraud_probability,
            utilization=utilization,
            limit_increase_48h=limit_increase_48h,
            spending_velocity_change=spending_velocity_change,
            transaction_velocity_change=transaction_velocity_change,
            liquidity_ratio=liquidity_ratio,
            third_party_ratio=third_party_ratio,
            unverified_ratio=unverified_ratio,
        )

        risk_score = float(risk_score)

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Risk engine failed: {str(e)}"
        )

    # --------------------------------------------------------
    # Risk level
    # --------------------------------------------------------

    risk_level = get_risk_level(
        risk_score
    )

    # --------------------------------------------------------
    # Recommended action
    # --------------------------------------------------------

    recommended_action = get_recommended_action(
        risk_level
    )

    # --------------------------------------------------------
    # Human-readable explanations
    # --------------------------------------------------------

    risk_reasons = generate_risk_reasons(
        features
    )

    # --------------------------------------------------------
    # Final response
    # --------------------------------------------------------

    result = {

        "customer_id": customer_id,

        "fraud_probability": round(
            fraud_probability,
            4
        ),

        "fraud_probability_percent": round(
            fraud_probability * 100,
            2
        ),

        "risk_score": round(
            risk_score,
            2
        ),

        "risk_level": risk_level,

        "recommended_action": recommended_action,

        "risk_reasons": risk_reasons,

        "behavioral_signals": {

            "utilization": utilization,

            "limit_increase_48h": (
                limit_increase_48h
            ),

            "spending_velocity_change": (
                spending_velocity_change
            ),

            "transaction_velocity_change": (
                transaction_velocity_change
            ),

            "liquidity_spending_ratio": (
                liquidity_ratio
            ),

            "third_party_ratio": (
                third_party_ratio
            ),

            "unverified_ratio": (
                unverified_ratio
            ),
        },
    }

    # --------------------------------------------------------
    # Store result in FastAPI process
    # --------------------------------------------------------

    live_results.add(
        result
    )

    return result


# ============================================================
# DEMO ALERTS (returned when no live Kafka data is available)
# ============================================================

DEMO_ALERTS = [
    {
        "customer_id": "C00421",
        "fraud_probability": 0.982,
        "fraud_probability_percent": 98.2,
        "risk_score": 94,
        "risk_level": "HIGH_RISK_INVESTIGATION",
        "recommended_action": "STRONG_VERIFICATION_AND_FRAUD_INVESTIGATION",
        "risk_reasons": [
            "Very high credit utilization (96.0%)",
            "Large credit-limit increase in the last 48 hours (10000)",
            "Spending velocity increased significantly (3.4x)",
        ],
        "behavioral_signals": {
            "utilization": 0.96,
            "limit_increase_48h": 10000,
            "spending_velocity_change": 3.4,
            "transaction_velocity_change": 2.8,
            "liquidity_spending_ratio": 0.61,
            "third_party_ratio": 0.43,
            "unverified_ratio": 0.32,
        },
    },
    {
        "customer_id": "C00318",
        "fraud_probability": 0.810,
        "fraud_probability_percent": 81.0,
        "risk_score": 79,
        "risk_level": "MERCHANT_CASHOUT_REVIEW",
        "recommended_action": "24_HOUR_MERCHANT_CASHOUT_REVIEW",
        "risk_reasons": [
            "High credit utilization (91.0%)",
            "Recent credit-limit increase detected",
            "Spending velocity increased (2.7x)",
            "Elevated liquidity-related spending (48.0%)",
        ],
        "behavioral_signals": {
            "utilization": 0.91,
            "limit_increase_48h": 3500,
            "spending_velocity_change": 2.7,
            "transaction_velocity_change": 2.2,
            "liquidity_spending_ratio": 0.48,
            "third_party_ratio": 0.25,
            "unverified_ratio": 0.17,
        },
    },
    {
        "customer_id": "C00142",
        "fraud_probability": 0.630,
        "fraud_probability_percent": 63.0,
        "risk_score": 64,
        "risk_level": "STEP_UP_VERIFICATION",
        "recommended_action": "REQUIRE_ADDITIONAL_VERIFICATION",
        "risk_reasons": [
            "High credit utilization (86.0%)",
            "Recent credit-limit increase detected",
            "Spending velocity increased (2.1x)",
            "Elevated liquidity-related spending (31.0%)",
        ],
        "behavioral_signals": {
            "utilization": 0.86,
            "limit_increase_48h": 2000,
            "spending_velocity_change": 2.1,
            "transaction_velocity_change": 1.9,
            "liquidity_spending_ratio": 0.31,
            "third_party_ratio": 0.19,
            "unverified_ratio": 0.11,
        },
    },
    {
        "customer_id": "C00281",
        "fraud_probability": 0.310,
        "fraud_probability_percent": 31.0,
        "risk_score": 42,
        "risk_level": "MONITOR",
        "recommended_action": "MONITOR_CUSTOMER_BEHAVIOR",
        "risk_reasons": [
            "Elevated credit utilization (72.0%)",
            "Recent credit-limit increase detected",
        ],
        "behavioral_signals": {
            "utilization": 0.72,
            "limit_increase_48h": 1000,
            "spending_velocity_change": 1.6,
            "transaction_velocity_change": 1.5,
            "liquidity_spending_ratio": 0.18,
            "third_party_ratio": 0.12,
            "unverified_ratio": 0.08,
        },
    },
]


# In-memory store for blocked customers
blocked_customers: Dict[str, Dict[str, Any]] = {}


# ============================================================
# GET ALL LIVE ALERTS (excluding blocked customers)
# ============================================================

@app.get("/alerts")
def get_alerts():

    raw_alerts = live_results.get_all()

    # If no live Kafka data, use demo alerts
    source_alerts = raw_alerts if raw_alerts else DEMO_ALERTS

    # Filter out customers who have been blocked
    active_alerts = [
        a for a in source_alerts
        if a.get("customer_id") not in blocked_customers
    ]

    return {
        "count": len(active_alerts),
        "alerts": active_alerts,
        "blocked_count": len(blocked_customers),
    }


# ============================================================
# GET BLOCKED CUSTOMERS
# ============================================================

@app.get("/customers/blocked")
def get_blocked_customers():
    return {
        "count": len(blocked_customers),
        "customers": list(blocked_customers.values()),
    }


# ============================================================
# BLOCK CUSTOMER
# ============================================================

@app.post("/customers/{customer_id}/block")
def block_customer(customer_id: str, payload: Dict[str, Any] = None):
    payload = payload or {}
    
    # Check demo alerts or live alerts to gather customer info if available
    customer_info = None
    all_known = live_results.get_all() + DEMO_ALERTS
    for item in all_known:
        if item.get("customer_id") == customer_id:
            customer_info = dict(item)
            break
            
    if not customer_info:
        customer_info = {
            "customer_id": customer_id,
            "risk_score": payload.get("risk_score", 90),
            "risk_level": payload.get("risk_level", "HIGH_RISK_INVESTIGATION"),
            "fraud_probability": payload.get("fraud_probability", 0.95),
            "recommended_action": "STRONG_VERIFICATION_AND_FRAUD_INVESTIGATION",
            "risk_reasons": ["High bust-out risk score mitigation action applied."],
        }
        
    blocked_record = {
        **customer_info,
        "status": "BLOCKED",
        "credit_access": "DISABLED",
        "blocked_at": payload.get("blocked_at", "Just now"),
        "blocked_reason": payload.get("reason", "Proactive bust-out risk mitigation. Credit transactions suspended."),
    }
    
    blocked_customers[customer_id] = blocked_record
    card_control_service.freeze_card(customer_id, reason=blocked_record["blocked_reason"])
    
    return {
        "status": "success",
        "message": f"Customer {customer_id} blocked and credit lines frozen.",
        "customer": blocked_record,
    }


# ============================================================
# UNBLOCK CUSTOMER
# ============================================================

@app.post("/customers/{customer_id}/unblock")
def unblock_customer(customer_id: str):
    if customer_id in blocked_customers:
        del blocked_customers[customer_id]
        
    card_control_service.unfreeze_card(customer_id)
        
    return {
        "status": "success",
        "message": f"Customer {customer_id} unblocked. Credit access restored and returned to active monitoring.",
        "customer_id": customer_id,
        "status_code": "ACTIVE",
    }


# ============================================================
# TRANSACTION AUTHORIZATION (CARD PROCESSOR INTERFACE)
# ============================================================

@app.post("/authorize")
def authorize_transaction(payload: Dict[str, Any]):
    """
    Real-time Card Transaction Authorization endpoint.
    Evaluates risk and executes ALLOW / STEP_UP / HOLD / BLOCK decision.
    """
    cid = payload.get("customer_id", "UNKNOWN")
    req = AuthorizationRequest(
        transaction_id=payload.get("transaction_id", f"TXN-{cid[:4]}"),
        customer_id=cid,
        card_number=payload.get("card_number", "•••• 0000"),
        amount=float(payload.get("amount", 0.0)),
        merchant_name=payload.get("merchant_name", "Standard Merchant"),
        merchant_category=payload.get("merchant_category", "RETAIL"),
        features=payload.get("features", {}),
    )
    
    fraud_prob = float(payload.get("fraud_probability", 0.0))
    resp = authorization_engine.process_authorization(req, fraud_probability=fraud_prob)
    
    return {
        "transaction_id": resp.transaction_id,
        "customer_id": resp.customer_id,
        "decision": resp.decision.value,
        "risk_score": resp.risk_score,
        "risk_level": resp.risk_level,
        "action_taken": resp.action_taken,
        "message": resp.message,
        "timestamp": resp.timestamp,
        "details": resp.details,
    }


# ============================================================
# GET LATEST ALERT
# ============================================================

@app.get("/alerts/latest")
def get_latest_alert():

    result = live_results.get_latest()

    if result is None:

        return {
            "message": "No alerts available",
            "alert": None,
        }

    return result


# ============================================================
# RECEIVE ALERTS FROM KAFKA CONSUMER
# ============================================================
#
# IMPORTANT:
#
# Kafka consumer and FastAPI run as separate processes.
# Therefore they cannot directly share the same in-memory
# live_results object.
#
# The Kafka consumer should POST each processed result to:
#
# POST http://localhost:8000/internal/alerts
#
# FastAPI then stores it in its own live_results object.
# React reads it through GET /alerts.
#
# ============================================================

@app.post("/internal/alerts")
def receive_internal_alert(
    alert: Dict[str, Any]
):

    if not alert:

        raise HTTPException(
            status_code=400,
            detail="Empty alert received."
        )

    # Store the alert in FastAPI memory

    live_results.add(
        alert
    )

    return {
        "status": "success",
        "message": "Alert received successfully",
        "customer_id": alert.get(
            "customer_id",
            "UNKNOWN"
        ),
    }


# ============================================================
# DELETE / CLEAR ALERTS
# ============================================================
#
# Useful during testing.
#
# ============================================================

@app.delete("/alerts")
def clear_alerts():

    # Accessing the internal deque through the class is avoided.
    # We simply recreate the contents by removing each item if
    # the implementation exposes the deque.
    #
    # This endpoint is mainly for development/testing.

    try:

        with live_results.lock:

            live_results.results.clear()

        return {
            "status": "success",
            "message": "All alerts cleared.",
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Could not clear alerts: {str(e)}"
        )


# ============================================================
# STARTUP MESSAGE
# ============================================================

@app.on_event("startup")
async def startup_event():

    print("")
    print("================================================")
    print("       BustOutSentry API Started")
    print("================================================")
    print("API:      http://localhost:8000")
    print("Docs:     http://localhost:8000/docs")
    print("Health:   http://localhost:8000/health")
    print("Alerts:   http://localhost:8000/alerts")
    print("================================================")
    print("")