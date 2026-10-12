def generate_risk_reasons(features):

    reasons = []

    if features.get("utilization", 0) >= 0.85:
        reasons.append(
            "Credit utilization has become unusually high."
        )

    if features.get("limit_increase_48h", 0) > 0:
        reasons.append(
            "Credit limit increased shortly before the suspicious activity."
        )

    if features.get("spending_velocity_change", 0) >= 2:
        reasons.append(
            "Spending velocity increased sharply."
        )

    if features.get("transaction_velocity_change", 0) >= 2:
        reasons.append(
            "Transaction frequency increased sharply."
        )

    if features.get("liquidity_ratio", 0) >= 0.25:
        reasons.append(
            "Spending shifted toward high-liquidity transaction categories."
        )

    if features.get("third_party_ratio", 0) >= 0.20:
        reasons.append(
            "A significant portion of activity involves third-party payment sources."
        )

    if features.get("unverified_ratio", 0) >= 0.10:
        reasons.append(
            "Unverified payment activity increased."
        )

    if not reasons:
        reasons.append(
            "No major behavioral anomaly detected."
        )

    return reasons