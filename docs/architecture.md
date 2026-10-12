# BustOutSentry System Architecture & Design Specification

## 1. Architectural Overview

BustOutSentry addresses **bust-out fraud** through an asynchronous, event-driven, hybrid-intelligence architecture. Traditional fraud systems evaluate transactions independently against historical rules or single static scorecards, which consistently misses bust-out fraud because:
1. Historical accounts exhibit pristine behavior for months prior to the incident.
2. The bust-out attack is a coordinated multi-transaction surge executed across high-liquidity channels over a 24 to 72-hour period.

BustOutSentry captures this pattern by maintaining **sliding temporal windows** (1h, 6h, 24h, 48h) and combining predictive ML inference with a heuristic behavioral penalty engine.

```
+-----------------------------------------------------------------------------------+
|                              EVENT INGESTION LAYER                                |
|                                                                                   |
|  [POS/ATM Transactions]  [Credit Limit Increases]  [Payment Submissions]          |
|                           │                          │                            |
|                           ▼                          ▼                            |
|                Apache Kafka Broker (Topic: "transactions")                        |
+----------------------------------------┬------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
|                        TEMPORAL PROCESSING & INFERENCE                            |
|                                                                                   |
|  Sliding Window Aggregation (1h, 6h, 24h, 48h):                                   |
|   - Spend velocity: Σ(amount) / window                                            |
|   - Transaction count velocity: count(txns) / window                              |
|   - Liquidity category exposure: % spending on quasi-cash, ATM, gift cards        |
|   - Payment integrity: % unverified payments & third-party routing                |
|                                         │                                         |
|                                         ▼                                         |
|  XGBoost Classifier (Class-Imbalance Weighted `scale_pos_weight`):                |
|   - Yields: Fraud Probability P(bustout) ∈ [0.0, 1.0]                             |
+----------------------------------------┬------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
|                        HYBRID RISK SCORING ENGINE                                 |
|                                                                                   |
|  Risk Score S ∈ [0, 100]:                                                         |
|    S = 60 * P(bustout)                                                            |
|      + Utilization_Score (up to 15 pts)                                           |
|      + Credit_Limit_Increase_Score (up to 10 pts)                                  |
|      + Spending_Velocity_Score (up to 8 pts)                                      |
|      + Transaction_Velocity_Score (up to 5 pts)                                   |
|      + Liquidity_Category_Score (up to 7 pts)                                     |
|      + Third_Party_Payment_Score (up to 5 pts)                                    |
|      + Unverified_Payment_Score (up to 5 pts)                                     |
+----------------------------------------┬------------------------------------------+
                                         │
                   ┌─────────────────────┴─────────────────────┐
                   ▼                                           ▼
+--------------------------------------+   +--------------------------------------+
|          DECISION & DISPATCH         |   |         OPERATIONS DASHBOARD         |
|                                      |   |                                      |
|  [0 - 30]   ALLOW                    |   |  - Real-time alert stream            |
|  [31 - 50]  MONITOR                  |   |  - Behavioral signal visualization   |
|  [51 - 70]  STEP-UP AUTHENTICATION   |   |  - SHAP diagnostic explanations      |
|  [71 - 85]  24H CASHOUT HOLD         |   |  - Automated polling & failover      |
|  [86 - 100] FRAUD ESCALATION         |   |                                      |
+--------------------------------------+   +--------------------------------------+
```

---

## 2. Temporal Feature Engineering (`ml/preprocessing/temporal_features.py`)

To distinguish legitimate card utilization spikes (such as holiday shopping or vacation travel) from fraudulent bust-out cash-outs, the feature engineering pipeline constructs asymmetric multi-window aggregations:

- **1-Hour Window**: Captures immediate burst activity (e.g. repeated cash advances at ATMs or point-of-sale terminals within minutes).
- **6-Hour Window**: Detects rapid sequential shopping across distinct merchant categories.
- **24-Hour Window**: Compares daily spending against 30-day baseline moving averages to measure velocity acceleration (`spending_velocity_change`).
- **48-Hour Window**: Captures the temporal proximity between a credit-limit increase approval (`limit_increase_48h`) and the initiation of maximum drawdown.

### High-Liquidity Identification
Transactions are evaluated against MCCs (Merchant Category Codes) and descriptions indicating immediately convertible value:
- `6011` / `6010`: Financial Institutions – Automated Cash Disbursements / Manual Cash
- `4829`: Wire Transfers and Money Orders
- `quasi_cash`, `gift cards`, `luxury electronics`, `jewelry`

---

## 3. Mathematical Scoring Formulation (`backend/services/risk_engine.py`)

The total risk score $S$ is normalized to the domain $[0, 100]$:

$$S = \min\left(100, \max\left(0, S_{\text{ML}} + S_{\text{util}} + S_{\text{limit}} + S_{\text{velocity}} + S_{\text{liquidity}} + S_{\text{source}}\right)\right)$$

Where:
- $S_{\text{ML}} = 60 \times P_{\text{XGBoost}}(\text{bustout})$
- $S_{\text{util}} \in \{0, 5, 10, 15\}$ based on utilization thresholds:
  - $\ge 95\% \to 15$
  - $\ge 85\% \to 10$
  - $\ge 70\% \to 5$
- $S_{\text{limit}} \in \{0, 3, 7, 10\}$ based on limit increase in prior 48h:
  - $> \$5,000 \to 10$
  - $> \$2,000 \to 7$
  - $> 0 \to 3$
- $S_{\text{velocity}}$: Spending velocity change (up to 8) + Transaction count velocity change (up to 5)
- $S_{\text{liquidity}}$: Liquidity ratio $\ge 50\% \to 7$, $\ge 25\% \to 4$
- $S_{\text{source}}$: Third-party payment ratio (up to 5) + Unverified payment ratio (up to 5)

---

## 4. Operational Tiers & Actions

| Tier Range | Level Name | Operational Action | System Response |
| :--- | :--- | :--- | :--- |
| `0 – 30` | **LOW** | Normal Execution | Authorize without friction |
| `31 – 50` | **MONITOR** | Account Telemetry | Log behavioral profile, increase telemetry sampling |
| `51 – 70` | **STEP_UP_VERIFICATION** | Risk Mitigation | Trigger Out-Of-Band (OOB) MFA, biometric challenge |
| `71 – 85` | **MERCHANT_CASHOUT_REVIEW** | Disbursement Hold | Place merchant settlement / cash-out on 24-hour escrow hold |
| `86 – 100` | **HIGH_RISK_INVESTIGATION** | Account Freeze | Restrict card limits, freeze lines, route to fraud investigation unit |
