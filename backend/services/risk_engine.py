import numpy as np


class BustOutRiskEngine:

    def __init__(self):
        pass

    def calculate_risk_score(
        self,
        fraud_probability,
        utilization,
        limit_increase_48h,
        spending_velocity_change,
        transaction_velocity_change,
        liquidity_ratio,
        third_party_ratio,
        unverified_ratio
    ):

        # ---------------------------------------
        # 1. ML RISK
        # ---------------------------------------

        ml_score = fraud_probability * 60


        # ---------------------------------------
        # 2. CREDIT UTILIZATION
        # ---------------------------------------

        if utilization >= 0.95:
            utilization_score = 15

        elif utilization >= 0.85:
            utilization_score = 10

        elif utilization >= 0.70:
            utilization_score = 5

        else:
            utilization_score = 0


        # ---------------------------------------
        # 3. CREDIT LIMIT INCREASE
        # ---------------------------------------

        if limit_increase_48h > 5000:
            limit_score = 10

        elif limit_increase_48h > 2000:
            limit_score = 7

        elif limit_increase_48h > 0:
            limit_score = 3

        else:
            limit_score = 0


        # ---------------------------------------
        # 4. SPENDING VELOCITY
        # ---------------------------------------

        if spending_velocity_change >= 3:
            spending_score = 8

        elif spending_velocity_change >= 2:
            spending_score = 5

        elif spending_velocity_change >= 1.5:
            spending_score = 3

        else:
            spending_score = 0


        # ---------------------------------------
        # 5. TRANSACTION VELOCITY
        # ---------------------------------------

        if transaction_velocity_change >= 3:
            transaction_score = 5

        elif transaction_velocity_change >= 2:
            transaction_score = 3

        else:
            transaction_score = 0


        # ---------------------------------------
        # 6. LIQUIDITY BEHAVIOR
        # ---------------------------------------

        if liquidity_ratio >= 0.50:
            liquidity_score = 7

        elif liquidity_ratio >= 0.25:
            liquidity_score = 4

        else:
            liquidity_score = 0


        # ---------------------------------------
        # 7. THIRD-PARTY PAYMENTS
        # ---------------------------------------

        if third_party_ratio >= 0.40:
            third_party_score = 5

        elif third_party_ratio >= 0.20:
            third_party_score = 3

        else:
            third_party_score = 0


        # ---------------------------------------
        # 8. UNVERIFIED PAYMENTS
        # ---------------------------------------

        if unverified_ratio >= 0.30:
            unverified_score = 5

        elif unverified_ratio >= 0.10:
            unverified_score = 3

        else:
            unverified_score = 0


        # ---------------------------------------
        # FINAL SCORE
        # ---------------------------------------

        risk_score = (
            ml_score
            + utilization_score
            + limit_score
            + spending_score
            + transaction_score
            + liquidity_score
            + third_party_score
            + unverified_score
        )


        risk_score = min(
            max(risk_score, 0),
            100
        )


        # ---------------------------------------
        # RISK LEVEL
        # ---------------------------------------

        if risk_score <= 30:
            risk_level = "LOW"

        elif risk_score <= 50:
            risk_level = "MONITOR"

        elif risk_score <= 70:
            risk_level = "STEP_UP_VERIFICATION"

        elif risk_score <= 85:
            risk_level = "MERCHANT_CASHOUT_REVIEW"

        else:
            risk_level = "HIGH_RISK_INVESTIGATION"


        # ---------------------------------------
        # RECOMMENDED ACTION
        # ---------------------------------------

        if risk_score <= 30:

            action = (
                "Allow transaction normally"
            )

        elif risk_score <= 50:

            action = (
                "Monitor account behavior"
            )

        elif risk_score <= 70:

            action = (
                "Require additional verification"
            )

        elif risk_score <= 85:

            action = (
                "Place merchant cash-out activity "
                "under 24-hour review"
            )

        else:

            action = (
                "Escalate to fraud investigation "
                "and apply strong verification"
            )


        return {
            "risk_score": round(risk_score, 2),
            "risk_level": risk_level,
            "recommended_action": action
        }