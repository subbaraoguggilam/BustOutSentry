import json
import pickle
import requests
from pathlib import Path

import numpy as np
from kafka import KafkaConsumer

from backend.services.risk_engine import BustOutRiskEngine
from backend.services.risk_explanation import generate_risk_reasons
from backend.services.live_results import live_results


# ============================================================
# BUSTOUTSENTRY - KAFKA ML CONSUMER
# ============================================================

print("=" * 70)
print("BUSTOUTSENTRY - KAFKA ML CONSUMER")
print("=" * 70)


# ============================================================
# PROJECT PATH
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

MODEL_PATH = ROOT / "ml" / "artifacts" / "temporal_xgboost.pkl"

FEATURE_PATH = (
    ROOT
    / "ml"
    / "artifacts"
    / "temporal_feature_names.pkl"
)


# ============================================================
# LOAD XGBOOST MODEL
# ============================================================

print("\nLoading XGBoost model...")

try:

    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)

    with open(FEATURE_PATH, "rb") as f:
        feature_names = pickle.load(f)

except FileNotFoundError as e:

    print("\nERROR: ML artifact not found.")
    print(e)

    print("\nExpected files:")

    print(MODEL_PATH)
    print(FEATURE_PATH)

    raise


print("XGBoost model loaded successfully.")

print(
    f"Expected ML features: {len(feature_names)}"
)


# ============================================================
# CREATE RISK ENGINE
# ============================================================

try:

    risk_engine = BustOutRiskEngine()

    print(
        "Risk Engine initialized successfully."
    )

except Exception as e:

    print("\nERROR: Could not initialize Risk Engine.")

    print(e)

    raise


# ============================================================
# KAFKA CONFIGURATION
# ============================================================

KAFKA_SERVER = "localhost:9092"

TOPIC = "transactions"
API_ALERTS_URL = "http://localhost:8000/internal/alerts"


# ============================================================
# CREATE KAFKA CONSUMER
# ============================================================

print("\nConnecting to Kafka...")

try:

    consumer = KafkaConsumer(

        TOPIC,

        bootstrap_servers=KAFKA_SERVER,

        auto_offset_reset="earliest",

        enable_auto_commit=True,

        group_id="bustoutsentry-ml",

        value_deserializer=lambda x:
            json.loads(
                x.decode("utf-8")
            )
    )

except Exception as e:

    print("\nERROR: Could not connect to Kafka.")

    print(e)

    print(
        "\nMake sure Kafka is running:"
    )

    print(
        "docker ps"
    )

    raise


print("Kafka consumer connected successfully.")

print(
    f"Kafka server : {KAFKA_SERVER}"
)

print(
    f"Kafka topic  : {TOPIC}"
)

print("\nWaiting for transaction events...")

print("=" * 70)


# ============================================================
# SCORE EVENT
# ============================================================

def score_event(event):

    customer_id = event.get(
        "customer_id",
        "UNKNOWN"
    )


    # ========================================================
    # BUILD FEATURE VECTOR
    # ========================================================

    features = []


    for feature in feature_names:

        value = event.get(
            feature,
            0
        )


        # Handle None
        if value is None:

            value = 0


        # Convert to float
        try:

            value = float(value)

        except (
            TypeError,
            ValueError
        ):

            value = 0.0


        # Handle NaN
        if np.isnan(value):

            value = 0.0


        features.append(value)


    # ========================================================
    # CONVERT TO NUMPY ARRAY
    # ========================================================

    X = np.array(
        features,
        dtype=float
    ).reshape(
        1,
        -1
    )


    # ========================================================
    # XGBOOST PREDICTION
    # ========================================================

    fraud_probability = float(
        model.predict_proba(X)[0][1]
    )


    # ========================================================
    # EXTRACT RISK FEATURES
    # ========================================================

    utilization = float(
        event.get(
            "utilization",
            0
        )
    )


    limit_increase_48h = float(
        event.get(
            "limit_increase_48h",
            0
        )
    )


    spending_velocity_change = float(
        event.get(
            "spending_velocity_change",
            0
        )
    )


    transaction_velocity_change = float(
        event.get(
            "transaction_velocity_change",
            0
        )
    )


    liquidity_ratio = float(
        event.get(
            "liquidity_spending_ratio",
            0
        )
    )


    third_party_ratio = float(
        event.get(
            "third_party_ratio",
            0
        )
    )


    unverified_ratio = float(
        event.get(
            "unverified_ratio",
            0
        )
    )


    # ========================================================
    # RISK ENGINE
    # ========================================================

    risk_result = risk_engine.calculate_risk_score(

        fraud_probability=fraud_probability,

        utilization=utilization,

        limit_increase_48h=limit_increase_48h,

        spending_velocity_change=
            spending_velocity_change,

        transaction_velocity_change=
            transaction_velocity_change,

        liquidity_ratio=
            liquidity_ratio,

        third_party_ratio=
            third_party_ratio,

        unverified_ratio=
            unverified_ratio
    )


    # ========================================================
    # CREATE RESULT
    # ========================================================

    result = {

        "customer_id":
            customer_id,

        "fraud_probability":
            fraud_probability,

        "risk_score":
            risk_result.get(
                "risk_score",
                0
            ),

        "risk_level":
            risk_result.get(
                "risk_level",
                "UNKNOWN"
            ),

        "recommended_action":
            risk_result.get(
                "recommended_action",
                "No action"
            ),

        "utilization":
            utilization,

        "limit_increase_48h":
            limit_increase_48h,

        "spending_velocity_change":
            spending_velocity_change,

        "transaction_velocity_change":
            transaction_velocity_change,

        "liquidity_ratio":
            liquidity_ratio,

        "third_party_ratio":
            third_party_ratio,

        "unverified_ratio":
            unverified_ratio,

        "risk_reasons":
            generate_risk_reasons({
                "utilization": utilization,
                "limit_increase_48h": limit_increase_48h,
                "spending_velocity_change": spending_velocity_change,
                "transaction_velocity_change": transaction_velocity_change,
                "liquidity_ratio": liquidity_ratio,
                "third_party_ratio": third_party_ratio,
                "unverified_ratio": unverified_ratio
            }),

        "behavioral_signals": {
            "utilization": round(utilization, 4),
            "limit_increase_48h": round(limit_increase_48h, 2),
            "spending_velocity_change": round(spending_velocity_change, 4),
            "transaction_velocity_change": round(transaction_velocity_change, 4),
            "liquidity_spending_ratio": round(liquidity_ratio, 4),
            "third_party_ratio": round(third_party_ratio, 4),
            "unverified_ratio": round(unverified_ratio, 4)
        },

        # Synthetic dataset label.
        # Used only for evaluation/demo.
        "actual_label":
            event.get(
                "is_bustout"
            )
    }


    return result


# ============================================================
# DISPLAY RESULT
# ============================================================

def display_result(result):

    print("\n")

    print("=" * 70)

    print("NEW CREDIT RISK EVENT")

    print("=" * 70)


    print(
        f"Customer ID          : "
        f"{result['customer_id']}"
    )


    print(
        f"Fraud Probability    : "
        f"{result['fraud_probability']:.4f}"
    )


    print(
        f"Risk Score           : "
        f"{result['risk_score']}"
    )


    print(
        f"Risk Level           : "
        f"{result['risk_level']}"
    )


    print(
        f"Recommended Action   : "
        f"{result['recommended_action']}"
    )


    # ========================================================
    # BEHAVIORAL SIGNALS
    # ========================================================

    print("\nBehavioral Signals")

    print("-" * 40)


    print(
        f"Credit Utilization   : "
        f"{result['utilization']:.4f}"
    )


    print(
        f"Limit Increase 48h   : "
        f"{result['limit_increase_48h']:.2f}"
    )


    print(
        f"Spending Velocity    : "
        f"{result['spending_velocity_change']:.2f}"
    )


    print(
        f"Transaction Velocity : "
        f"{result['transaction_velocity_change']:.2f}"
    )


    print(
        f"Liquidity Ratio      : "
        f"{result['liquidity_ratio']:.4f}"
    )


    print(
        f"Third-Party Ratio    : "
        f"{result['third_party_ratio']:.4f}"
    )


    print(
        f"Unverified Ratio     : "
        f"{result['unverified_ratio']:.4f}"
    )


    # ========================================================
    # SYNTHETIC LABEL
    # ========================================================

    if result["actual_label"] is not None:

        print("\nSynthetic Evaluation")

        print("-" * 40)

        print(
            f"Actual Bust-Out Label: "
            f"{result['actual_label']}"
        )


    print("=" * 70)


# ============================================================
# KAFKA EVENT LOOP
# ============================================================

try:

    for message in consumer:

        event = message.value


        try:

            # ------------------------------------------------
            # Run ML + Risk Engine
            # ------------------------------------------------

            result = score_event(
                event
            )


            # ------------------------------------------------
            # Store result for FastAPI & forward via HTTP
            # ------------------------------------------------

            live_results.add(
                result
            )

            try:
                requests.post(
                    API_ALERTS_URL,
                    json=result,
                    timeout=1.5
                )
            except Exception:
                # Backend may be starting up or offline; continue processing
                pass


            # ------------------------------------------------
            # Display result
            # ------------------------------------------------

            display_result(
                result
            )


        except Exception as event_error:

            print("\n")

            print("=" * 70)

            print("ERROR PROCESSING KAFKA EVENT")

            print("=" * 70)

            print(
                event_error
            )

            print(
                "Consumer will continue "
                "with the next event."
            )


except KeyboardInterrupt:

    print("\n")

    print("=" * 70)

    print("Kafka consumer stopped by user.")

    print("=" * 70)


finally:

    consumer.close()

    print(
        "Kafka consumer connection closed."
    )