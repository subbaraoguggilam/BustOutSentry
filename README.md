# BustOutSentry

**Real-time AI-Powered Bust-Out Fraud & Credit Risk Detection System**

BustOutSentry is an end-to-end fintech fraud operations platform designed to detect **bust-out credit card fraud** in real time. By combining streaming event processing, temporal sliding-window feature engineering, gradient-boosted ML inference, and a behavioral risk scoring engine, BustOutSentry catches fraudsters before funds are permanently lost.

---

## 🛡️ What is Bust-Out Fraud?

Bust-out fraud is an intentional, coordinated credit abuse scheme where an individual or syndicate:
1. **Builds Legitimacy**: Opens revolving credit lines and maintains regular transaction activity and timely payments over months to establish trust and high credit scores.
2. **Secures Credit Expansions**: Requests substantial credit limit increases.
3. **Executes Velocity Cash-Out**: Over a compressed window (24–72 hours), charges the cards to maximum limits across high-liquidity merchants (cash advances, money transfers, gift cards, electronics) or unverified third-party bank payments.
4. **Abandons the Account**: Defaults completely, leaving the financial institution with unrecoverable write-offs.

Traditional rule engines fail because the account appears in "good standing" until the bust-out occurs. BustOutSentry identifies the subtle behavioral anomaly signatures and velocity shifts right at the point of cash-out.

---

## 🏛️ System Architecture

```
                                  ┌────────────────────────┐
                                  │   Kafka Producer       │
                                  │ (Transaction Stream)   │
                                  └──────────┬─────────────┘
                                             │
                                             ▼
                                  ┌────────────────────────┐
                                  │  Apache Kafka Broker   │
                                  │  Topic: "transactions" │
                                  └──────────┬─────────────┘
                                             │
                                             ▼
┌───────────────────────────┐     ┌────────────────────────┐
│  Temporal Feature Windows │ ──> │   Kafka ML Consumer    │
│  (1h, 6h, 24h, 48h)       │     │ (XGBoost + Risk Engine)│
└───────────────────────────┘     └──────────┬─────────────┘
                                             │ HTTP POST /internal/alerts
                                             ▼
                                  ┌────────────────────────┐
                                  │    FastAPI Backend     │
                                  │     (/score, /alerts)  │
                                  └──────────┬─────────────┘
                                             │ Polling / REST
                                             ▼
                                  ┌────────────────────────┐
                                  │ React 19 Ops Dashboard │
                                  │  (Live Signals & Tiers)│
                                  └────────────────────────┘
```

---

## 🚀 Key Modules

- **Streaming Layer (`kafka/`)**:
  - Apache Kafka 3.8.0 containerized broker via KRaft mode.
  - Streaming producers (`producer.py`, `ml_producer.py`) simulating high-velocity transactions and temporal event feeds.
  - Real-time consumer (`ml_consumer.py`) scoring each event through the ML pipeline and forwarding alerts to FastAPI.

- **Machine Learning Layer (`ml/`)**:
  - **Temporal Feature Engineering**: Sliding time windows calculating 1h, 6h, 24h, and 48h transaction velocity, spending velocity, liquidity spending, and unverified payment ratios.
  - **Temporal XGBoost Model**: Trained with scale-position weighting to tackle severe class imbalance in bust-out datasets.
  - **Model Explainability**: SHAP TreeExplainer integration (`ml/explainability/shap_explainer.py`) producing feature importance and customer-level diagnostic attributions.

- **Risk Engine (`backend/services/risk_engine.py`)**:
  - Computes a comprehensive **0–100 Risk Score**:
    - **60% Weight**: Machine Learning predicted fraud probability.
    - **40% Weight**: Behavioral heuristic signals (utilization spike, 48h limit increases, spending acceleration, high-liquidity merchant ratios, unverified/third-party payments).
  - Categorizes accounts into operational risk tiers:
    - `0 – 30`: **LOW** (Allow transaction)
    - `31 – 50`: **MONITOR** (Silent account monitoring)
    - `51 – 70`: **STEP_UP_VERIFICATION** (Require MFA / ID check)
    - `71 – 85`: **MERCHANT_CASHOUT_REVIEW** (Hold merchant disbursement for 24h)
    - `86 – 100`: **HIGH_RISK_INVESTIGATION** (Strong verification + fraud escalation)

- **Operations Dashboard (`frontend/`)**:
  - Modern, responsive React 19 + Vite interface.
  - Real-time alert feed with automated background polling.
  - In-depth customer inspection with signal progress bars and natural-language risk reasons.
  - Graceful fallback to buffer mode when the backend is offline.

---

## 📁 Repository Structure

```
bustoutsentry/
├── backend/
│   ├── api/
│   │   └── main.py                 # FastAPI application & endpoints
│   └── services/
│       ├── risk_engine.py          # Hybrid risk scoring algorithm
│       ├── risk_explanation.py     # Rule-based diagnostic generator
│       ├── live_results.py         # In-memory thread-safe alert buffer
│       └── test_risk_engine.py     # Functional test for risk scoring
├── kafka/
│   ├── producer.py                 # Basic transaction producer
│   ├── consumer.py                 # Basic event consumer
│   ├── ml_producer.py              # Temporal feature streaming producer
│   └── ml_consumer.py              # ML scoring consumer with API bridge
├── ml/
│   ├── artifacts/                  # Trained models (.pkl) & feature importance
│   ├── data/                       # Raw & processed CSV datasets
│   ├── explainability/             # SHAP explainability analysis
│   ├── models/                     # XGBoost training scripts
│   └── preprocessing/              # Feature engineering & sliding windows
├── frontend/
│   ├── src/
│   │   ├── App.jsx                 # Operations Dashboard component
│   │   ├── App.css                 # Dark-themed dashboard styling
│   │   └── main.jsx                # Application root
│   └── package.json
├── docker-compose.yml              # Kafka KRaft cluster definition
├── requirements.txt                # Python backend & ML dependencies
└── .env.example                    # Environment variable template
```

---

## ⚡ Getting Started

### 1. Start Apache Kafka
Launch Kafka with Docker Compose:
```bash
docker compose up -d
```
Verify the container is healthy:
```bash
docker ps
```

### 2. Configure Python Environment
Create and activate a virtual environment, then install dependencies:
```bash
# Create venv (if not already created)
python -m venv .venv

# Activate venv (Windows PowerShell)
.venv\Scripts\Activate.ps1

# Install requirements
pip install -r requirements.txt
```

### 3. Launch Backend API
Start the FastAPI server on port 8000:
```bash
uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload
```
Open interactive Swagger documentation at: [http://localhost:8000/docs](http://localhost:8000/docs)

### 4. Start Frontend Dashboard
From the root or `frontend` directory:
```bash
cd frontend
npm install
npm run dev
```
Open the dashboard in your browser at `http://localhost:5173`.

### 5. Stream Transactions
To stream transactions through Kafka and see alerts pop up live on the dashboard:
```bash
# Terminal 1: Start ML Consumer
python -m kafka.ml_consumer

# Terminal 2: Stream Events with ML Producer
python -m kafka.ml_producer
```

---

## 🔌 API Reference

### `GET /health`
Returns the status of the service, model loading state, and feature count.

### `POST /score`
Scores an incoming customer transaction / feature vector.
```json
{
  "customer_id": "C00421",
  "utilization": 0.95,
  "limit_increase_48h": 6000,
  "spending_velocity_change": 3.2,
  "transaction_velocity_change": 2.5,
  "liquidity_spending_ratio": 0.55,
  "third_party_ratio": 0.40,
  "unverified_ratio": 0.25
}
```

### `GET /alerts`
Retrieves all buffered live alerts generated by the Kafka consumer or scoring engine.

### `POST /internal/alerts`
Internal webhook endpoint used by `kafka/ml_consumer.py` to ingest scored events into the dashboard feed.
