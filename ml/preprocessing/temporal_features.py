import pandas as pd
import numpy as np
import os

# ============================================================
# PATHS
# ============================================================

TRANSACTION_PATH = "ml/data/bustout_transactions.csv"
CREDIT_PATH = "ml/data/credit_history.csv"
LABEL_PATH = "ml/data/labels.csv"

OUTPUT_PATH = "ml/data/processed/temporal_features.csv"


# ============================================================
# LOAD DATA
# ============================================================

print("Loading transaction data...")

transactions = pd.read_csv(
    TRANSACTION_PATH,
    parse_dates=["timestamp"]
)

print("Transactions:", transactions.shape)

print("Loading credit history...")

credit = pd.read_csv(
    CREDIT_PATH,
    parse_dates=["timestamp"]
)

print("Credit history:", credit.shape)

print("Loading labels...")

labels = pd.read_csv(LABEL_PATH)

print("Labels:", labels.shape)


# ============================================================
# SORT DATA
# ============================================================

transactions = transactions.sort_values(
    ["customer_id", "timestamp"]
).reset_index(drop=True)

credit = credit.sort_values(
    ["customer_id", "timestamp"]
).reset_index(drop=True)


# ============================================================
# HELPER FUNCTION
# ============================================================

def calculate_window_features(customer_txns, snapshot_time):

    features = {}

    # --------------------------------------------------------
    # Only transactions BEFORE the snapshot
    # --------------------------------------------------------

    historical = customer_txns[
        customer_txns["timestamp"] <= snapshot_time
    ].copy()

    # --------------------------------------------------------
    # Time windows
    # --------------------------------------------------------

    windows = {
        "1h": pd.Timedelta(hours=1),
        "6h": pd.Timedelta(hours=6),
        "24h": pd.Timedelta(hours=24),
        "48h": pd.Timedelta(hours=48)
    }

    for name, duration in windows.items():

        start_time = snapshot_time - duration

        window = historical[
            historical["timestamp"] > start_time
        ]

        # ----------------------------------------------------
        # Transaction velocity
        # ----------------------------------------------------

        features[f"txn_count_{name}"] = len(window)

        # ----------------------------------------------------
        # Spending velocity
        # ----------------------------------------------------

        features[f"spend_{name}"] = window["amount"].sum()

        features[f"avg_transaction_{name}"] = (
            window["amount"].mean()
            if len(window) > 0
            else 0
        )

        features[f"max_transaction_{name}"] = (
            window["amount"].max()
            if len(window) > 0
            else 0
        )

        # ----------------------------------------------------
        # High liquidity activity
        # ----------------------------------------------------

        liquidity_categories = [
            "cash_advance",
            "atm",
            "high_liquidity",
            "money_transfer"
        ]

        liquidity_mask = (
            window["merchant_category"]
            .astype(str)
            .str.lower()
            .isin(liquidity_categories)
        )

        features[f"high_liquidity_count_{name}"] = (
            liquidity_mask.sum()
        )

        features[f"high_liquidity_amount_{name}"] = (
            window.loc[liquidity_mask, "amount"].sum()
        )

        # ----------------------------------------------------
        # Third-party payments
        # ----------------------------------------------------

        third_party_mask = (
            window["payment_source"]
            .astype(str)
            .str.lower()
            .isin([
                "third_party",
                "third-party",
                "external",
                "bank_transfer"
            ])
        )

        features[f"third_party_count_{name}"] = (
            third_party_mask.sum()
        )

        features[f"third_party_amount_{name}"] = (
            window.loc[third_party_mask, "amount"].sum()
        )

        # ----------------------------------------------------
        # Unverified payments
        # ----------------------------------------------------

        unverified_mask = (
            window["payment_verified"].astype(str) != "1"
        )

        features[f"unverified_count_{name}"] = (
            unverified_mask.sum()
        )

        features[f"unverified_amount_{name}"] = (
            window.loc[unverified_mask, "amount"].sum()
        )

        # ----------------------------------------------------
        # POS / ATM behavior
        # ----------------------------------------------------

        terminal = (
            window["terminal_type"]
            .astype(str)
            .str.lower()
        )

        features[f"pos_count_{name}"] = (
            terminal.str.contains("pos").sum()
        )

        features[f"atm_count_{name}"] = (
            terminal.str.contains("atm").sum()
        )

    # ========================================================
    # CURRENT CREDIT UTILIZATION
    # ========================================================

    available_snapshot = historical.tail(1)

    if len(available_snapshot) > 0:

        latest = available_snapshot.iloc[0]

        credit_limit = latest["credit_limit"]
        current_balance = latest["current_balance"]
        available_credit = latest["available_credit"]

        if credit_limit > 0:

            features["credit_limit"] = credit_limit

            features["current_balance"] = current_balance

            features["available_credit"] = available_credit

            features["utilization"] = (
                current_balance / credit_limit
            )

        else:

            features["credit_limit"] = 0
            features["current_balance"] = 0
            features["available_credit"] = 0
            features["utilization"] = 0

    else:

        features["credit_limit"] = 0
        features["current_balance"] = 0
        features["available_credit"] = 0
        features["utilization"] = 0

    return features


# ============================================================
# BUILD CUSTOMER SNAPSHOTS
# ============================================================

print("\nCreating 48-hour snapshots...")

records = []

customers = transactions["customer_id"].unique()

for i, customer_id in enumerate(customers):

    customer_txns = transactions[
        transactions["customer_id"] == customer_id
    ].copy()

    if len(customer_txns) == 0:
        continue

    # --------------------------------------------------------
    # Final observed transaction
    # --------------------------------------------------------

    final_transaction_time = customer_txns["timestamp"].max()

    # --------------------------------------------------------
    # 48-hour early-warning snapshot
    # --------------------------------------------------------

    snapshot_time = (
        final_transaction_time
        - pd.Timedelta(hours=48)
    )

    # --------------------------------------------------------
    # Temporal features
    # --------------------------------------------------------

    features = calculate_window_features(
        customer_txns,
        snapshot_time
    )

    features["customer_id"] = customer_id

    features["snapshot_time"] = snapshot_time

    features["final_transaction_time"] = (
        final_transaction_time
    )

    # --------------------------------------------------------
    # Credit-limit changes BEFORE snapshot
    # --------------------------------------------------------

    customer_credit = credit[
        (credit["customer_id"] == customer_id)
        &
        (credit["timestamp"] <= snapshot_time)
    ].copy()

    if len(customer_credit) > 0:

        # Last known limit increase
        customer_credit["limit_increase"] = (
            customer_credit["new_credit_limit"]
            - customer_credit["old_credit_limit"]
        )

        recent_24h = customer_credit[
            customer_credit["timestamp"]
            >= snapshot_time - pd.Timedelta(hours=24)
        ]

        recent_48h = customer_credit[
            customer_credit["timestamp"]
            >= snapshot_time - pd.Timedelta(hours=48)
        ]

        recent_7d = customer_credit[
            customer_credit["timestamp"]
            >= snapshot_time - pd.Timedelta(days=7)
        ]

        features["limit_increase_24h"] = (
            recent_24h["limit_increase"].clip(lower=0).sum()
        )

        features["limit_increase_48h"] = (
            recent_48h["limit_increase"].clip(lower=0).sum()
        )

        features["limit_increase_7d"] = (
            recent_7d["limit_increase"].clip(lower=0).sum()
        )

        features["limit_change_count_7d"] = (
            len(recent_7d)
        )

        features["total_limit_change"] = (
            customer_credit["limit_increase"]
            .clip(lower=0)
            .sum()
        )

    else:

        features["limit_increase_24h"] = 0
        features["limit_increase_48h"] = 0
        features["limit_increase_7d"] = 0
        features["limit_change_count_7d"] = 0
        features["total_limit_change"] = 0

    records.append(features)

    if (i + 1) % 50 == 0:

        print(
            f"Processed {i + 1}/{len(customers)} customers"
        )


# ============================================================
# CREATE DATAFRAME
# ============================================================

print("\nCreating temporal feature dataframe...")

temporal_df = pd.DataFrame(records)


# ============================================================
# ADD LABELS
# ============================================================

temporal_df = temporal_df.merge(
    labels[
        [
            "customer_id",
            "risk_stage",
            "is_bustout"
        ]
    ],
    on="customer_id",
    how="left"
)


# ============================================================
# BEHAVIORAL CHANGE FEATURES
# ============================================================

temporal_df["spending_velocity_change"] = (
    temporal_df["spend_24h"]
    /
    (temporal_df["spend_48h"] / 2 + 1)
)

temporal_df["transaction_velocity_change"] = (
    temporal_df["txn_count_24h"]
    /
    (temporal_df["txn_count_48h"] / 2 + 1)
)

temporal_df["liquidity_spending_ratio"] = (
    temporal_df["high_liquidity_amount_24h"]
    /
    (temporal_df["spend_24h"] + 1)
)

temporal_df["third_party_ratio"] = (
    temporal_df["third_party_amount_24h"]
    /
    (temporal_df["spend_24h"] + 1)
)

temporal_df["unverified_ratio"] = (
    temporal_df["unverified_amount_24h"]
    /
    (temporal_df["spend_24h"] + 1)
)


# ============================================================
# CLEAN NUMERIC VALUES
# ============================================================

numeric_columns = temporal_df.select_dtypes(
    include=[np.number]
).columns

temporal_df[numeric_columns] = (
    temporal_df[numeric_columns]
    .replace([np.inf, -np.inf], np.nan)
    .fillna(0)
)


# ============================================================
# SAVE
# ============================================================

os.makedirs(
    "ml/data/processed",
    exist_ok=True
)

temporal_df.to_csv(
    OUTPUT_PATH,
    index=False
)


# ============================================================
# SUMMARY
# ============================================================

print("\n======================================")
print("TEMPORAL FEATURE ENGINEERING COMPLETE")
print("======================================")

print("Shape:", temporal_df.shape)

print("\nBust-out distribution:")

print(
    temporal_df["is_bustout"]
    .value_counts()
)

print("\nFeatures:")

print(
    temporal_df.columns.tolist()
)

print("\nSaved to:")

print(OUTPUT_PATH)