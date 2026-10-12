import React, { useState, useEffect, useCallback } from "react";
import {
  ShieldAlert,
  Activity,
  Users,
  AlertTriangle,
  ShieldCheck,
  Clock,
  Search,
  RefreshCw,
  Radio,
  Ban,
  CheckCircle2,
  Lock,
  Unlock,
  UserX,
  UserCheck
} from "lucide-react";

import "./App.css";

const BACKEND_API = "http://localhost:8000";

const mockAlerts = [
  {
    customer_id: "C00421",
    fraud_probability: 0.982,
    risk_score: 94,
    risk_level: "HIGH_RISK_INVESTIGATION",
    recommended_action: "Strong verification + fraud investigation",
    behavioral_signals: {
      utilization: 0.97,
      limit_increase_48h: 7500,
      spending_velocity_change: 3.4,
      transaction_velocity_change: 2.8,
      liquidity_spending_ratio: 0.61,
      third_party_ratio: 0.43,
      unverified_ratio: 0.32
    },
    risk_reasons: [
      "Credit utilization is extremely high (97.0%).",
      "Large credit-limit increase detected within 48 hours ($7,500).",
      "Spending velocity has increased sharply (3.4x).",
      "High proportion of liquidity-related spending (61.0%)."
    ]
  },
  {
    customer_id: "C00318",
    fraud_probability: 0.81,
    risk_score: 79,
    risk_level: "MERCHANT_CASHOUT_REVIEW",
    recommended_action: "Review merchant cash-out for 24 hours",
    behavioral_signals: {
      utilization: 0.91,
      limit_increase_48h: 3500,
      spending_velocity_change: 2.7,
      transaction_velocity_change: 2.2,
      liquidity_spending_ratio: 0.48,
      third_party_ratio: 0.25,
      unverified_ratio: 0.17
    },
    risk_reasons: [
      "Credit utilization has increased significantly (91.0%).",
      "Recent credit-limit increase detected ($3,500).",
      "Elevated liquidity-related spending detected (48.0%)."
    ]
  },
  {
    customer_id: "C00142",
    fraud_probability: 0.63,
    risk_score: 64,
    risk_level: "STEP_UP_VERIFICATION",
    recommended_action: "Require additional verification",
    behavioral_signals: {
      utilization: 0.86,
      limit_increase_48h: 2000,
      spending_velocity_change: 2.1,
      transaction_velocity_change: 1.9,
      liquidity_spending_ratio: 0.31,
      third_party_ratio: 0.19,
      unverified_ratio: 0.11
    },
    risk_reasons: [
      "Credit utilization has increased significantly (86.0%).",
      "Spending velocity is significantly above normal (2.1x).",
      "Elevated liquidity-related spending detected (31.0%)."
    ]
  },
  {
    customer_id: "C00281",
    fraud_probability: 0.31,
    risk_score: 42,
    risk_level: "MONITOR",
    recommended_action: "Monitor account",
    behavioral_signals: {
      utilization: 0.72,
      limit_increase_48h: 1000,
      spending_velocity_change: 1.6,
      transaction_velocity_change: 1.5,
      liquidity_spending_ratio: 0.18,
      third_party_ratio: 0.12,
      unverified_ratio: 0.08
    },
    risk_reasons: [
      "Credit utilization has increased significantly (72.0%).",
      "Recent credit-limit increase detected ($1,000)."
    ]
  }
];

function App() {
  const [alerts, setAlerts] = useState(mockAlerts);
  const [blockedCustomers, setBlockedCustomers] = useState([]);
  const [selectedCustomer, setSelectedCustomer] = useState(mockAlerts[0]);
  const [search, setSearch] = useState("");
  const [isLive, setIsLive] = useState(false);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState("active"); // "active" or "blocked"
  const [notification, setNotification] = useState(null);

  const intervalRef = React.useRef(null);
  const blockedIdsRef = React.useRef(new Set());

  useEffect(() => {
    blockedIdsRef.current = new Set(blockedCustomers.map((c) => c.customer_id));
  }, [blockedCustomers]);

  const showNotification = (message, type = "success") => {
    setNotification({ message, type });
    setTimeout(() => {
      setNotification(null);
    }, 4000);
  };

  const stopPolling = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  };

  const startPolling = () => {
    if (!intervalRef.current) {
      intervalRef.current = setInterval(doFetch, 3000);
    }
  };

  const doFetch = async () => {
    try {
      setLoading(true);
      const res = await fetch(`${BACKEND_API}/alerts`, { method: "GET" });
      if (res.ok) {
        const data = await res.json();
        setIsLive(true);
        startPolling();

        if (data && Array.isArray(data.alerts)) {
          const source = data.alerts.length > 0 ? data.alerts : mockAlerts;
          const activeOnly = source.filter(
            (a) => !blockedIdsRef.current.has(a.customer_id)
          );
          setAlerts(activeOnly);

          setSelectedCustomer((prev) => {
            if (!prev) return activeOnly[0] || null;
            if (blockedIdsRef.current.has(prev.customer_id)) return prev;
            const found = activeOnly.find((a) => a.customer_id === prev.customer_id);
            return found || activeOnly[0] || prev;
          });
        }
        return;
      }
      setIsLive(false);
    } catch {
      setIsLive(false);
      stopPolling();
    } finally {
      setLoading(false);
    }
  };

  const fetchAlerts = doFetch;

  useEffect(() => {
    doFetch();
    return () => stopPolling();
  }, []);

  // BLOCK CUSTOMER
  const handleBlockCustomer = async (customerToBlock, reason) => {
    if (!customerToBlock) return;
    const cid = customerToBlock.customer_id;
    const blockTimestamp = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) + " IST, " + new Date().toLocaleDateString();
    const defaultReason = reason || "Proactive first-party bust-out risk mitigation. Credit transactions suspended.";

    const blockedEntry = {
      ...customerToBlock,
      status: "BLOCKED",
      credit_access: "DISABLED",
      blocked_at: blockTimestamp,
      blocked_reason: defaultReason
    };

    setAlerts((prev) => prev.filter((a) => a.customer_id !== cid));
    setBlockedCustomers((prev) => {
      const exists = prev.some((c) => c.customer_id === cid);
      return exists ? prev : [blockedEntry, ...prev];
    });

    setSelectedCustomer(blockedEntry);

    try {
      await fetch(`${BACKEND_API}/customers/${cid}/block`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          risk_score: customerToBlock.risk_score,
          risk_level: customerToBlock.risk_level,
          fraud_probability: customerToBlock.fraud_probability,
          reason: defaultReason,
          blocked_at: blockTimestamp
        })
      });
    } catch {}

    showNotification(`🚫 Customer ${cid} blocked. Credit transactions disabled and removed from active alerts.`, "danger");
  };

  // UNBLOCK CUSTOMER (preserves exact risk score)
  const handleUnblockCustomer = async (cid) => {
    const unblockedTarget = blockedCustomers.find((c) => c.customer_id === cid) || selectedCustomer;
    if (!unblockedTarget) return;

    const exactRiskScore = unblockedTarget.risk_score;
    const exactFraudProb = unblockedTarget.fraud_probability;
    const exactRiskLevel = unblockedTarget.risk_level;
    const exactSignals = unblockedTarget.behavioral_signals;
    const exactReasons = unblockedTarget.risk_reasons;
    const exactAction = unblockedTarget.recommended_action;

    const restoredEntry = {
      ...unblockedTarget,
      risk_score: exactRiskScore,
      fraud_probability: exactFraudProb,
      risk_level: exactRiskLevel,
      behavioral_signals: exactSignals,
      risk_reasons: exactReasons,
      recommended_action: exactAction,
      status: "ACTIVE",
      credit_access: "OPEN"
    };

    setBlockedCustomers((prev) => prev.filter((c) => c.customer_id !== cid));
    setAlerts((prev) => {
      const exists = prev.some((a) => a.customer_id === cid);
      return exists ? prev.map((a) => (a.customer_id === cid ? restoredEntry : a)) : [restoredEntry, ...prev];
    });

    setSelectedCustomer(restoredEntry);
    setActiveTab("active");

    try {
      await fetch(`${BACKEND_API}/customers/${cid}/unblock`, {
        method: "POST"
      });
    } catch {}

    showNotification(
      `✅ Customer ${cid} unblocked. Maintained Risk Score: ${Math.round(exactRiskScore)}/100. Credit access restored & returned to active alerts.`,
      "success"
    );
  };

  // BLOCK ALL HIGH RISK
  const handleBlockAllHighRisk = () => {
    const highRiskList = alerts.filter(
      (a) => a.risk_score >= 70 || a.risk_level === "HIGH_RISK_INVESTIGATION" || a.risk_level === "MERCHANT_CASHOUT_REVIEW"
    );

    if (highRiskList.length === 0) {
      showNotification("No high-risk accounts currently pending in active alerts.", "info");
      return;
    }

    const blockTimestamp = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) + " IST, " + new Date().toLocaleDateString();

    const newBlocked = highRiskList.map((item) => ({
      ...item,
      status: "BLOCKED",
      credit_access: "DISABLED",
      blocked_at: blockTimestamp,
      blocked_reason: "Batch bust-out mitigation containment."
    }));

    const highRiskIds = new Set(highRiskList.map((c) => c.customer_id));

    setAlerts((prev) => prev.filter((a) => !highRiskIds.has(a.customer_id)));
    setBlockedCustomers((prev) => [...newBlocked, ...prev.filter((p) => !highRiskIds.has(p.customer_id))]);

    showNotification(`🚫 Blocked ${highRiskList.length} high-risk customer credit facilities.`, "danger");
  };

  const filteredAlerts = alerts.filter((alert) =>
    (alert.customer_id || "")
      .toLowerCase()
      .includes(search.toLowerCase())
  );

  const filteredBlocked = blockedCustomers.filter((customer) =>
    (customer.customer_id || "")
      .toLowerCase()
      .includes(search.toLowerCase())
  );

  const highRiskCount = alerts.filter(
    (a) => (a.risk_score >= 86) || (a.risk_level === "HIGH_RISK_INVESTIGATION")
  ).length;

  const reviewCount = alerts.filter(
    (a) => a.risk_level === "MERCHANT_CASHOUT_REVIEW" || a.risk_level === "STEP_UP_VERIFICATION"
  ).length;

  const totalMonitored = 500;
  const blockedCount = blockedCustomers.length;

  const signals = selectedCustomer ? (
    selectedCustomer.behavioral_signals || {
      utilization: selectedCustomer.utilization ?? 0,
      limit_increase_48h: selectedCustomer.limit_increase_48h ?? 0,
      spending_velocity_change: selectedCustomer.spending_velocity_change ?? 0,
      transaction_velocity_change: selectedCustomer.transaction_velocity_change ?? 0,
      liquidity_spending_ratio: selectedCustomer.liquidity_spending_ratio ?? 0,
      third_party_ratio: selectedCustomer.third_party_ratio ?? 0,
      unverified_ratio: selectedCustomer.unverified_ratio ?? 0
    }
  ) : {
    utilization: 0,
    limit_increase_48h: 0,
    spending_velocity_change: 0,
    transaction_velocity_change: 0,
    liquidity_spending_ratio: 0,
    third_party_ratio: 0,
    unverified_ratio: 0
  };

  const riskReasons = (selectedCustomer?.risk_reasons && selectedCustomer.risk_reasons.length > 0)
    ? selectedCustomer.risk_reasons
    : ["Standard baseline transaction pattern. No critical anomalies flagged."];

  const currentIsBlocked = selectedCustomer && blockedCustomers.some((c) => c.customer_id === selectedCustomer.customer_id);

  return (
    <div className="app">
      {/* TOAST NOTIFICATION */}
      {notification && (
        <div className={`notification-toast ${notification.type}`}>
          {notification.type === "danger" ? <Ban size={16} /> : <CheckCircle2 size={16} />}
          <span>{notification.message}</span>
        </div>
      )}

      {/* HEADER */}
      <header className="header">
        <div className="brand">
          <div className="brand-icon">
            <ShieldAlert size={24} />
          </div>
          <div>
            <h1>BustOutSentry</h1>
            <p>AI Credit Risk & Fraud Detection Operations</p>
          </div>
        </div>

        <div
          className="system-status"
          style={{
            borderColor: isLive ? "rgba(16, 185, 129, 0.3)" : "rgba(245, 158, 11, 0.3)",
            background: isLive ? "rgba(16, 185, 129, 0.08)" : "rgba(245, 158, 11, 0.08)",
            color: isLive ? "#34d399" : "#fbbf24"
          }}
        >
          <span
            className="status-dot"
            style={{
              backgroundColor: isLive ? "#10b981" : "#f59e0b"
            }}
          ></span>
          {isLive ? "LIVE STREAM CONNECTED" : "DEMO / OFFLINE MODE"}
          <span className="divider"></span>
          {isLive ? <Radio size={14} /> : <Activity size={14} />}
          {isLive ? "Real-time Kafka" : "Simulated Buffer"}
        </div>
      </header>

      {/* MAIN DASHBOARD */}
      <main className="dashboard">
        {/* PAGE TITLE & ACTIONS */}
        <div className="page-title">
          <div>
            <h2>Fraud Operations Dashboard</h2>
            <p>Real-time behavioral monitoring, bust-out containment & credit authorization controls</p>
          </div>

          <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
            {highRiskCount > 0 && (
              <button
                className="btn-danger-action"
                onClick={handleBlockAllHighRisk}
                title="Immediately block all high-risk accounts and freeze credit lines"
              >
                <Ban size={14} />
                Block All High Risk ({highRiskCount})
              </button>
            )}

            <button
              className="refresh-button"
              onClick={fetchAlerts}
              disabled={loading}
            >
              <RefreshCw
                size={14}
                style={{
                  animation: loading ? "spin 1s linear infinite" : "none"
                }}
              />
              {loading ? "Refreshing..." : "Refresh"}
            </button>
          </div>
        </div>

        {/* STAT CARDS */}
        <section className="stats-grid">
          <StatCard
            icon={<Users />}
            title="Monitored Customers"
            value={totalMonitored}
            subtitle="Active portfolio"
          />

          <StatCard
            icon={<ShieldAlert />}
            title="Active High Risk"
            value={highRiskCount}
            subtitle="Immediate action required"
            danger={highRiskCount > 0}
          />

          <StatCard
            icon={<Clock />}
            title="Under Review"
            value={reviewCount}
            subtitle="Cash-out & Step-up alerts"
          />

          <StatCard
            icon={<UserX />}
            title="Blocked Accounts"
            value={blockedCount}
            subtitle="Credit transactions frozen"
            isBlockedStat={blockedCount > 0}
          />
        </section>

        {/* CONTENT GRID */}
        <section className="content-grid">
          {/* LEFT PANEL: ALERTS & BLOCKED TABS */}
          <div className="panel alerts-panel">
            {/* TAB SELECTOR HEADER */}
            <div className="panel-tabs">
              <button
                className={`tab-btn ${activeTab === "active" ? "active" : ""}`}
                onClick={() => {
                  setActiveTab("active");
                  if (alerts.length > 0 && (!selectedCustomer || currentIsBlocked)) {
                    setSelectedCustomer(alerts[0]);
                  }
                }}
              >
                <ShieldAlert size={14} />
                Active Alerts ({alerts.length})
              </button>

              <button
                className={`tab-btn tab-blocked ${activeTab === "blocked" ? "active" : ""}`}
                onClick={() => {
                  setActiveTab("blocked");
                  if (blockedCustomers.length > 0) {
                    setSelectedCustomer(blockedCustomers[0]);
                  }
                }}
              >
                <Ban size={14} />
                Blocked Customers ({blockedCustomers.length})
              </button>
            </div>

            {/* SEARCH */}
            <div className="search-box">
              <Search size={15} />
              <input
                placeholder={activeTab === "active" ? "Search active alert customer ID..." : "Search blocked customer ID..."}
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>

            {/* TAB CONTENT: ACTIVE ALERTS */}
            {activeTab === "active" && (
              <div className="alert-list">
                {filteredAlerts.length === 0 ? (
                  <div className="empty-state">
                    <CheckCircle2 size={36} color="var(--ok-text)" />
                    <strong>No Active Risk Alerts</strong>
                    <p>
                      {alerts.length === 0
                        ? "All high-risk customer accounts have been blocked and contained from credit transactions."
                        : "No customer records match your current search query."}
                    </p>
                    {blockedCustomers.length > 0 && (
                      <button
                        className="btn-link"
                        onClick={() => setActiveTab("blocked")}
                      >
                        View {blockedCustomers.length} Blocked Customer{blockedCustomers.length > 1 ? "s" : ""} →
                      </button>
                    )}
                  </div>
                ) : (
                  filteredAlerts.map((alert) => {
                    const isSelected = selectedCustomer?.customer_id === alert.customer_id;
                    const isHigh = alert.risk_score >= 80 || alert.risk_level === "HIGH_RISK_INVESTIGATION";

                    return (
                      <div
                        key={alert.customer_id}
                        className={`alert-item ${isSelected ? "selected" : ""} ${isHigh ? "item-high-risk" : ""}`}
                        onClick={() => setSelectedCustomer(alert)}
                      >
                        <div className="alert-customer">
                          <div className={`customer-avatar ${isHigh ? "avatar-danger" : ""}`}>
                            {(alert.customer_id || "UK").slice(-2)}
                          </div>
                          <div>
                            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                              <strong>{alert.customer_id}</strong>
                              <span className="status-badge-active">ACTIVE</span>
                            </div>
                            <span className="alert-sub">
                              Fraud prob{" "}
                              {alert.fraud_probability !== undefined
                                ? (Number(alert.fraud_probability) * 100).toFixed(1)
                                : "0.0"}
                              %
                            </span>
                          </div>
                        </div>

                        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                          <div className="alert-score">
                            <strong>{Math.round(alert.risk_score || 0)}</strong>
                            <span>
                              {(alert.risk_level || "UNKNOWN")
                                .replaceAll("_", " ")
                                .toLowerCase()}
                            </span>
                          </div>

                          <button
                            className="btn-quick-block"
                            title={`Block ${alert.customer_id} immediately`}
                            onClick={(e) => {
                              e.stopPropagation();
                              handleBlockCustomer(alert);
                            }}
                          >
                            <Ban size={13} />
                            Block
                          </button>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            )}

            {/* TAB CONTENT: BLOCKED CUSTOMERS */}
            {activeTab === "blocked" && (
              <div className="alert-list">
                {filteredBlocked.length === 0 ? (
                  <div className="empty-state">
                    <ShieldCheck size={36} color="var(--accent)" />
                    <strong>No Blocked Customers</strong>
                    <p>
                      All customer credit facilities are currently operating under standard risk monitoring.
                    </p>
                  </div>
                ) : (
                  filteredBlocked.map((customer) => {
                    const isSelected = selectedCustomer?.customer_id === customer.customer_id;

                    return (
                      <div
                        key={customer.customer_id}
                        className={`alert-item blocked-item ${isSelected ? "selected" : ""}`}
                        onClick={() => setSelectedCustomer(customer)}
                      >
                        <div className="alert-customer">
                          <div className="customer-avatar avatar-blocked">
                            <Lock size={14} />
                          </div>
                          <div>
                            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                              <strong>{customer.customer_id}</strong>
                              <span className="status-badge-blocked">BLOCKED</span>
                            </div>
                            <span className="alert-sub">
                              Frozen at {customer.blocked_at || "Recent"}
                            </span>
                          </div>
                        </div>

                        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                          <div className="alert-score">
                            <strong style={{ color: "var(--danger-text)" }}>
                              {Math.round(customer.risk_score || 0)}
                            </strong>
                            <span style={{ color: "var(--danger-text)" }}>CREDIT FROZEN</span>
                          </div>

                          <button
                            className="btn-quick-unblock"
                            title={`Unblock ${customer.customer_id} and restore credit access`}
                            onClick={(e) => {
                              e.stopPropagation();
                              handleUnblockCustomer(customer.customer_id);
                            }}
                          >
                            <Unlock size={13} />
                            Unblock
                          </button>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            )}
          </div>

          {/* RIGHT PANEL: CUSTOMER RISK ANALYSIS & INVESTIGATION */}
          <div className="panel analysis-panel">
            {selectedCustomer ? (
              <>
                <div className="panel-header" style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <div>
                    <h3>Customer Risk Investigation</h3>
                    <p>Behavioral anomaly assessment & mitigation controls</p>
                  </div>

                  <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                    <span className="customer-id">{selectedCustomer.customer_id}</span>
                    {currentIsBlocked ? (
                      <span className="status-pill-blocked">
                        <Lock size={12} /> BLOCKED
                      </span>
                    ) : (
                      <span className="status-pill-active">
                        <CheckCircle2 size={12} /> ACTIVE
                      </span>
                    )}
                  </div>
                </div>

                {/* STATUS CALLOUT & ACTION BANNER */}
                {currentIsBlocked ? (
                  <div className="block-status-banner blocked-mode">
                    <div className="banner-text">
                      <div className="banner-title">
                        <Lock size={16} />
                        <strong>CREDIT TRANSACTIONS DISABLED — ACCOUNT BLOCKED</strong>
                      </div>
                      <p>
                        This customer's credit line and card authorizations have been frozen to prevent bust-out losses.
                        {selectedCustomer.blocked_at && ` (Action logged: ${selectedCustomer.blocked_at})`}
                      </p>
                    </div>

                    <button
                      className="btn-unblock-main"
                      onClick={() => handleUnblockCustomer(selectedCustomer.customer_id)}
                    >
                      <UserCheck size={16} />
                      Unblock Customer & Restore Credit Access
                    </button>
                  </div>
                ) : (
                  <div className="block-status-banner active-mode">
                    <div className="banner-text">
                      <div className="banner-title">
                        <ShieldAlert size={16} />
                        <strong>ACTIVE MONITORING — CREDIT ACCESS OPEN</strong>
                      </div>
                      <p>
                        Review behavioral signals below. If bust-out or merchant cash-out behavior is detected, block immediately to disable credit transactions.
                      </p>
                    </div>

                    <button
                      className="btn-block-main"
                      onClick={() => handleBlockCustomer(selectedCustomer)}
                    >
                      <UserX size={16} />
                      Block Customer & Freeze Credit Lines
                    </button>
                  </div>
                )}

                {/* SCORE & PROBABILITY */}
                <div className="risk-summary">
                  <div className="risk-score">
                    <span>Risk Score</span>
                    <strong>{Math.round(selectedCustomer.risk_score || 0)}</strong>
                    <small>/ 100 Risk Index</small>
                  </div>

                  <div className="fraud-probability">
                    <span>Fraud Probability</span>
                    <strong>
                      {selectedCustomer.fraud_probability !== undefined
                        ? (Number(selectedCustomer.fraud_probability) * 100).toFixed(1)
                        : "0.0"}
                      %
                    </strong>
                    <small>Bust-Out Probability</small>
                  </div>
                </div>

                {/* RISK LEVEL */}
                <div className="risk-level">
                  <span>Risk Classification</span>
                  <strong>
                    {(selectedCustomer.risk_level || "UNKNOWN").replaceAll("_", " ")}
                  </strong>
                </div>

                {/* BEHAVIORAL SIGNALS */}
                <h4>Behavioral Anomaly Signals</h4>

                <Signal
                  name="Credit Utilization"
                  value={(signals.utilization || 0) * 100}
                  suffix="%"
                />

                <Signal
                  name="Recent Limit Increase (48h)"
                  value={signals.limit_increase_48h || 0}
                  prefix="$"
                />

                <Signal
                  name="Spending Velocity Shift"
                  value={signals.spending_velocity_change || 0}
                  suffix="×"
                />

                <Signal
                  name="Transaction Velocity Shift"
                  value={signals.transaction_velocity_change || 0}
                  suffix="×"
                />

                <Signal
                  name="Liquidity / Cash-Out Spending"
                  value={(signals.liquidity_spending_ratio || 0) * 100}
                  suffix="%"
                />

                <Signal
                  name="Third-Party Payments"
                  value={(signals.third_party_ratio || 0) * 100}
                  suffix="%"
                />

                <Signal
                  name="Unverified Payments"
                  value={(signals.unverified_ratio || 0) * 100}
                  suffix="%"
                />

                {/* EXPLANATIONS */}
                <div className="explanation">
                  <h4>
                    <AlertTriangle size={15} />
                    Risk Engine Diagnostic Rationale
                  </h4>
                  <ul>
                    {riskReasons.map((reason, index) => (
                      <li key={index}>{reason}</li>
                    ))}
                  </ul>
                </div>

                {/* RECOMMENDED ACTION */}
                <div className="recommended-action">
                  <span>Recommended Action</span>
                  <strong>
                    {currentIsBlocked
                      ? "CREDIT FROZEN — AWAITING ANALYST INVESTIGATION & UNBLOCK APPROVAL"
                      : (selectedCustomer.recommended_action || "Monitor account")}
                  </strong>
                </div>
              </>
            ) : (
              <div className="empty-analysis-state">
                <ShieldCheck size={40} color="var(--accent)" />
                <h4>No Account Selected</h4>
                <p>Select an account from the active alerts or blocked list to inspect behavioral signals and manage authorization controls.</p>
              </div>
            )}
          </div>
        </section>
      </main>
    </div>
  );
}

/* ============================================================
   STAT CARD COMPONENT
   ============================================================ */
function StatCard({ icon, title, value, subtitle, danger, isBlockedStat }) {
  return (
    <div className={`stat-card ${danger ? "danger" : ""} ${isBlockedStat ? "stat-blocked" : ""}`}>
      <div className="stat-icon">{icon}</div>
      <div className="stat-content">
        <span>{title}</span>
        <strong>{value}</strong>
        <small>{subtitle}</small>
      </div>
    </div>
  );
}

/* ============================================================
   SIGNAL METER COMPONENT
   ============================================================ */
function Signal({ name, value, suffix = "", prefix = "" }) {
  const numVal = typeof value === "number" ? value : 0;
  const percentage =
    suffix === "%"
      ? Math.min(100, Math.max(0, numVal))
      : Math.min(100, Math.max(0, (numVal / 5) * 100));

  return (
    <div className="signal">
      <div className="signal-header">
        <span>{name}</span>
        <strong>
          {prefix}
          {typeof value === "number" ? value.toFixed(1) : value}
          {suffix}
        </strong>
      </div>
      <div className="signal-bar">
        <div className="signal-fill" style={{ width: `${percentage}%` }} />
      </div>
    </div>
  );
}

export default App;