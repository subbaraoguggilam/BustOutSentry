try:
    from backend.services.risk_engine import BustOutRiskEngine
    from backend.services.risk_explanation import generate_risk_reasons
except ImportError:
    from risk_engine import BustOutRiskEngine
    from risk_explanation import generate_risk_reasons


engine = BustOutRiskEngine()


# Simulated suspicious customer
features = {
    "fraud_probability": 0.95,
    "utilization": 0.97,
    "limit_increase_48h": 6000,
    "spending_velocity_change": 3.5,
    "transaction_velocity_change": 3.0,
    "liquidity_ratio": 0.65,
    "third_party_ratio": 0.45,
    "unverified_ratio": 0.35
}


result = engine.calculate_risk_score(
    **features
)


reasons = generate_risk_reasons(
    features
)


print("\n==============================")
print("BUST-OUT RISK ENGINE")
print("==============================")

print(
    "Risk Score:",
    result["risk_score"]
)

print(
    "Risk Level:",
    result["risk_level"]
)

print(
    "Recommended Action:",
    result["recommended_action"]
)

print("\nRisk Reasons:")

for reason in reasons:
    print("-", reason)