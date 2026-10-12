import pandas as pd
import numpy as np


HIGH_LIQUIDITY = {
    "cash_advance",
    "atm_cash",
    "money_transfer",
    "quasi_cash",
    "prepaid_giftcard",
    "jewelry",
    "electronics"
}


def create_features(
    transaction_file,
    credit_history_file,
    customer_history_file,
    labels_file
):

    # --------------------------------------------------
    # 1. LOAD DATA
    # --------------------------------------------------

    tx = pd.read_csv(transaction_file)
    credit = pd.read_csv(credit_history_file)
    customers = pd.read_csv(customer_history_file)
    labels = pd.read_csv(labels_file)

    # Convert timestamps
    tx["timestamp"] = pd.to_datetime(tx["timestamp"])
    credit["timestamp"] = pd.to_datetime(credit["timestamp"])

    # Sort
    tx = tx.sort_values(["customer_id", "timestamp"])
    credit = credit.sort_values(["customer_id", "timestamp"])

    # --------------------------------------------------
    # 2. BASIC TRANSACTION FEATURES
    # --------------------------------------------------

    tx["is_purchase"] = (tx["amount"] > 0).astype(int)
    tx["is_payment"] = (tx["amount"] < 0).astype(int)

    tx["abs_amount"] = tx["amount"].abs()

    tx["is_high_liquidity"] = (
        tx["merchant_category"]
        .isin(HIGH_LIQUIDITY)
        .astype(int)
    )

    tx["is_unverified"] = (
        (tx["payment_verified"] == 0)
        &
        (tx["payment_source"] != "card")
    ).astype(int)

    tx["is_third_party"] = (
        tx["payment_source"] == "third_party_bank"
    ).astype(int)

    # --------------------------------------------------
    # 3. CUSTOMER TRANSACTION FEATURES
    # --------------------------------------------------

    feature_list = []

    for customer_id, group in tx.groupby("customer_id"):

        group = group.sort_values("timestamp").copy()

        purchases = group[group["amount"] > 0]
        payments = group[group["amount"] < 0]

        features = {
            "customer_id": customer_id,

            # -----------------------------
            # Transaction volume
            # -----------------------------

            "transaction_count":
                len(group),

            "purchase_count":
                len(purchases),

            "payment_count":
                len(payments),

            # -----------------------------
            # Spending
            # -----------------------------

            "total_spending":
                purchases["amount"].sum(),

            "average_transaction":
                purchases["amount"].mean()
                if len(purchases) else 0,

            "max_transaction":
                purchases["amount"].max()
                if len(purchases) else 0,

            # -----------------------------
            # Credit utilization
            # -----------------------------

            "max_utilization":
                (
                    group["current_balance"]
                    / group["credit_limit"].replace(0, np.nan)
                ).max(),

            "average_utilization_observed":
                (
                    group["current_balance"]
                    / group["credit_limit"].replace(0, np.nan)
                ).mean(),

            # -----------------------------
            # Liquidity / cash-out
            # -----------------------------

            "high_liquidity_count":
                group["is_high_liquidity"].sum(),

            "high_liquidity_amount":
                group.loc[
                    group["is_high_liquidity"] == 1,
                    "abs_amount"
                ].sum(),

            "high_liquidity_ratio":
                group["is_high_liquidity"].mean(),

            # -----------------------------
            # Third-party payments
            # -----------------------------

            "third_party_payment_count":
                group["is_third_party"].sum(),

            "unverified_payment_count":
                group["is_unverified"].sum(),

            # -----------------------------
            # Credit exhaustion
            # -----------------------------

            "minimum_available_credit":
                group["available_credit"].min(),

            "credit_depletion":
                (
                    group["credit_limit"].iloc[0]
                    - group["available_credit"].min()
                ),

            # -----------------------------
            # Merchant behavior
            # -----------------------------

            "unique_merchant_categories":
                group["merchant_category"].nunique(),

            "high_liquidity_merchant_categories":
                group.loc[
                    group["is_high_liquidity"] == 1,
                    "merchant_category"
                ].nunique(),

            # -----------------------------
            # Terminal behavior
            # -----------------------------

            "offline_pos_count":
                (group["terminal_type"] == "offline_pos").sum(),

            "atm_count":
                (group["terminal_type"] == "atm").sum(),

            # -----------------------------
            # Verification
            # -----------------------------

            "verified_payment_ratio":
                group["payment_verified"].mean(),

        }

        feature_list.append(features)

    features = pd.DataFrame(feature_list)

    # --------------------------------------------------
    # 4. CREDIT LIMIT FEATURES
    # --------------------------------------------------

    credit_features = []

    for customer_id, group in credit.groupby("customer_id"):

        group = group.sort_values("timestamp").copy()

        group["limit_increase"] = (
            group["new_credit_limit"]
            - group["old_credit_limit"]
        )

        group["limit_increase_ratio"] = np.where(
            group["old_credit_limit"] > 0,
            group["limit_increase"]
            / group["old_credit_limit"],
            0
        )

        non_opening = group[
            group["limit_change_reason"] != "account_opening"
        ]

        credit_features.append({
            "customer_id": customer_id,

            "limit_change_count":
                len(non_opening),

            "total_limit_increase":
                non_opening["limit_increase"].sum(),

            "max_limit_increase":
                non_opening["limit_increase"].max()
                if len(non_opening) else 0,

            "average_limit_increase_ratio":
                non_opening["limit_increase_ratio"].mean()
                if len(non_opening) else 0,

            "customer_request_count":
                (
                    non_opening["limit_change_reason"]
                    == "customer_request"
                ).sum(),

            "income_update_count":
                (
                    non_opening["limit_change_reason"]
                    == "income_update"
                ).sum(),
        })

    credit_features = pd.DataFrame(credit_features)

    # --------------------------------------------------
    # 5. CUSTOMER HISTORY
    # --------------------------------------------------

    customer_features = customers[
        [
            "customer_id",
            "account_age_months",
            "credit_score",
            "average_monthly_spend",
            "average_utilization"
        ]
    ].copy()

    # --------------------------------------------------
    # 6. MERGE EVERYTHING
    # --------------------------------------------------

    data = features.merge(
        credit_features,
        on="customer_id",
        how="left"
    )

    data = data.merge(
        customer_features,
        on="customer_id",
        how="left"
    )

    data = data.merge(
        labels,
        on="customer_id",
        how="left"
    )

    # --------------------------------------------------
    # 7. BEHAVIORAL DEVIATION FEATURES
    # --------------------------------------------------

    data["spending_vs_baseline"] = (
        data["total_spending"]
        /
        (data["average_monthly_spend"] + 1)
    )

    data["utilization_vs_baseline"] = (
        data["max_utilization"]
        /
        (data["average_utilization"] + 0.01)
    )

    data["liquidity_spending_ratio"] = (
        data["high_liquidity_amount"]
        /
        (data["total_spending"] + 1)
    )

    data["limit_growth_ratio"] = (
        data["total_limit_increase"]
        /
        (data["credit_score"] + 1)
    )

    # --------------------------------------------------
    # 8. CLEAN DATA
    # --------------------------------------------------

    data = data.replace(
        [np.inf, -np.inf],
        np.nan
    )

    data = data.fillna(0)

    return data


if __name__ == "__main__":

    data = create_features(
        "ml/data/bustout_transactions.csv",
        "ml/data/credit_history.csv",
        "ml/data/customer_history.csv",
        "ml/data/labels.csv"
    )

    print("\nFeature dataset:")
    print(data.shape)

    print("\nColumns:")
    print(data.columns.tolist())

    print("\nLabel distribution:")
    print(data["is_bustout"].value_counts())

    data.to_csv(
        "ml/data/processed/customer_features.csv",
        index=False
    )

    print(
        "\nSaved: "
        "ml/data/processed/customer_features.csv"
    )