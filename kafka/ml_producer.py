import json
import time
from pathlib import Path

import pandas as pd
from kafka import KafkaProducer


# ============================================================
# BUSTOUTSENTRY - KAFKA ML PRODUCER
# ============================================================

print("=" * 70)
print("BUSTOUTSENTRY - KAFKA ML PRODUCER")
print("=" * 70)


# ============================================================
# PROJECT PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

DATA_PATH = (
    ROOT
    / "ml"
    / "data"
    / "processed"
    / "temporal_features.csv"
)


# ============================================================
# KAFKA CONFIGURATION
# ============================================================

KAFKA_SERVER = "localhost:9092"
TOPIC = "transactions"


# ============================================================
# LOAD DATASET
# ============================================================

print("\nLoading temporal feature dataset...")

if not DATA_PATH.exists():

    print("\nERROR: Dataset not found.")
    print(f"Expected location:")
    print(DATA_PATH)

    raise FileNotFoundError(DATA_PATH)


df = pd.read_csv(DATA_PATH)

print("Dataset loaded successfully.")

print(f"Number of customers/events : {len(df)}")
print(f"Number of features         : {len(df.columns)}")

print("\nDataset columns:")
print(list(df.columns))


# ============================================================
# CLEAN DATA
# ============================================================

# Replace NaN and infinite values
df = df.replace([float("inf"), float("-inf")], 0)

df = df.fillna(0)


# ============================================================
# CREATE KAFKA PRODUCER
# ============================================================

print("\nConnecting to Kafka...")

try:

    producer = KafkaProducer(
        bootstrap_servers=KAFKA_SERVER,

        value_serializer=lambda value:
            json.dumps(value).encode("utf-8"),

        # Wait for broker acknowledgement
        acks="all",

        # Retry failed sends
        retries=5
    )

except Exception as e:

    print("\nERROR: Could not connect to Kafka.")
    print(e)

    print("\nMake sure Kafka is running with:")
    print("docker ps")

    raise


print("Connected to Kafka successfully.")
print(f"Kafka server : {KAFKA_SERVER}")
print(f"Kafka topic  : {TOPIC}")


# ============================================================
# SEND EVENTS
# ============================================================

print("\nStarting event streaming...")
print("-" * 70)


total_events = len(df)
successful_events = 0
failed_events = 0


for index, row in df.iterrows():

    # --------------------------------------------------------
    # Convert pandas row to dictionary
    # --------------------------------------------------------

    event = row.to_dict()


    # --------------------------------------------------------
    # Clean values for JSON
    # --------------------------------------------------------

    cleaned_event = {}

    for key, value in event.items():

        if pd.isna(value):

            cleaned_event[key] = 0

        else:

            # Convert NumPy numeric types
            # to standard Python types
            if hasattr(value, "item"):

                try:
                    value = value.item()
                except Exception:
                    pass

            cleaned_event[key] = value


    # --------------------------------------------------------
    # Customer ID
    # --------------------------------------------------------

    customer_id = cleaned_event.get(
        "customer_id",
        f"UNKNOWN_{index}"
    )


    # --------------------------------------------------------
    # Send event to Kafka
    # --------------------------------------------------------

    try:

        future = producer.send(
            TOPIC,
            key=str(customer_id).encode("utf-8"),
            value=cleaned_event
        )

        # Wait for Kafka acknowledgement
        future.get(timeout=10)

        successful_events += 1


        # ----------------------------------------------------
        # Display progress
        # ----------------------------------------------------

        print(
            f"[{index + 1}/{total_events}] "
            f"Sent customer={customer_id}"
        )


        # ----------------------------------------------------
        # Delay to simulate real-time streaming
        # ----------------------------------------------------

        time.sleep(0.2)


    except Exception as e:

        failed_events += 1

        print(
            f"ERROR sending customer "
            f"{customer_id}: {e}"
        )


# ============================================================
# FLUSH REMAINING EVENTS
# ============================================================

print("\nWaiting for Kafka to finish processing...")

producer.flush()


# ============================================================
# CLOSE PRODUCER
# ============================================================

producer.close()


# ============================================================
# FINAL REPORT
# ============================================================

print("\n")
print("=" * 70)
print("KAFKA STREAMING COMPLETE")
print("=" * 70)

print(f"Total events       : {total_events}")
print(f"Successful events  : {successful_events}")
print(f"Failed events      : {failed_events}")

print(f"\nKafka topic        : {TOPIC}")
print(f"Kafka server       : {KAFKA_SERVER}")

print("=" * 70)
print("Producer stopped.")
print("=" * 70)