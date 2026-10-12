import React, { useState, useEffect } from "react";
import "./CustomerPortal.css";

// ============================================================
// INITIAL REALISTIC BANKING DATA
// ============================================================

const INITIAL_ACCOUNTS = [
  {
    type: "Savings Account",
    accountNumber: "XXXX XXXX 4821",
    rawNumber: "00140100004821",
    branch: "Indiranagar Branch, Bangalore",
    ifsc: "APEX0001042",
    availableBalance: 184320.75,
    ledgerBalance: 184320.75,
    currency: "INR"
  },
  {
    type: "Current Account",
    accountNumber: "XXXX XXXX 9104",
    rawNumber: "00140200009104",
    branch: "Indiranagar Branch, Bangalore",
    ifsc: "APEX0001042",
    availableBalance: 412650.00,
    ledgerBalance: 435150.00,
    currency: "INR"
  }
];

const INITIAL_TRANSACTIONS = [
  {
    id: "TXN101",
    date: "30 Sep 2026",
    narration: "UPI/3021/SWIGGY_BANGALORE/PAYMENT",
    refNo: "REF8192039481",
    debit: 485.00,
    credit: null,
    balance: 184320.75
  },
  {
    id: "TXN102",
    date: "29 Sep 2026",
    narration: "ATM WDL/SBI ATM 100FT RD/BLR",
    refNo: "ATM9820194827",
    debit: 10000.00,
    credit: null,
    balance: 184805.75
  },
  {
    id: "TXN103",
    date: "28 Sep 2026",
    narration: "NEFT-CR-INFOSYS TECHNOLOGIES-SALARY SEP26",
    refNo: "N26092800192841",
    debit: null,
    credit: 165000.00,
    balance: 194805.75
  },
  {
    id: "TXN104",
    date: "27 Sep 2026",
    narration: "IMPS/P2A/9845012345/HOUSE RENT/BANGALORE",
    refNo: "IMPS7729104812",
    debit: 35000.00,
    credit: null,
    balance: 29805.75
  },
  {
    id: "TXN105",
    date: "25 Sep 2026",
    narration: "POS/9412/AMAZON RETAIL INDIA/MUMBAI",
    refNo: "POS8819203810",
    debit: 3499.00,
    credit: null,
    balance: 64805.75
  },
  {
    id: "TXN106",
    date: "24 Sep 2026",
    narration: "BILLDESK/BESCOM ELECTRICITY BILL/AUG-SEP",
    refNo: "BD99281726351",
    debit: 2140.00,
    credit: null,
    balance: 68304.75
  },
  {
    id: "TXN107",
    date: "22 Sep 2026",
    narration: "ACH DR/HDFC LIFE INSURANCE-PREMIUM",
    refNo: "ACH3391028471",
    debit: 24000.00,
    credit: null,
    balance: 70444.75
  },
  {
    id: "TXN108",
    date: "20 Sep 2026",
    narration: "UPI/3019/SHELL PETROL PUMP/AUTOMOTIVE",
    refNo: "UPI7729104811",
    debit: 3500.00,
    credit: null,
    balance: 94444.75
  },
  {
    id: "TXN109",
    date: "18 Sep 2026",
    narration: "FD INT CR/PERIODIC Q2 INTEREST CREDIT",
    refNo: "INT9910283741",
    debit: null,
    credit: 8950.00,
    balance: 97944.75
  },
  {
    id: "TXN110",
    date: "15 Sep 2026",
    narration: "NEFT-DR-KUMAR HOME APPLIANCES/PURCHASE",
    refNo: "N26091500482910",
    debit: 18500.00,
    credit: null,
    balance: 88994.75
  }
];

const BENEFICIARIES = [
  { id: "BEN1", name: "Ananya Sharma", bank: "HDFC Bank", accountNumber: "XXXX XXXX 1092", ifsc: "HDFC000124" },
  { id: "BEN2", name: "Ramesh Verma", bank: "State Bank of India", accountNumber: "XXXX XXXX 4911", ifsc: "SBIN000491" },
  { id: "BEN3", name: "Vikas Realtors Pvt Ltd", bank: "ICICI Bank", accountNumber: "XXXX XXXX 8832", ifsc: "ICIC000088" },
  { id: "BEN4", name: "BESCOM Utility Board", bank: "Apex Trust Bank", accountNumber: "XXXX XXXX 3310", ifsc: "APEX0001042" }
];

// Helper to format currency in Indian numbering (e.g. 1,84,320.75)
function formatINR(val) {
  if (val === null || val === undefined || isNaN(val)) return "-";
  return "₹ " + Number(val).toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  });
}

export default function CustomerPortal({ onSwitchToOps }) {
  // Session countdown timer starting at 9 minutes 42 seconds (582 seconds)
  const [secondsLeft, setSecondsLeft] = useState(582);
  const [hideBalance, setHideBalance] = useState(true);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Financial States
  const [accounts, setAccounts] = useState(INITIAL_ACCOUNTS);
  const [transactions, setTransactions] = useState(INITIAL_TRANSACTIONS);

  // Quick Transfer Form States
  const [fromAccount, setFromAccount] = useState("0");
  const [beneficiary, setBeneficiary] = useState("");
  const [transferMode, setTransferMode] = useState("IMPS");
  const [amount, setAmount] = useState("");
  const [remarks, setRemarks] = useState("");
  const [errors, setErrors] = useState({});
  const [isConfirming, setIsConfirming] = useState(false);
  const [successReceipt, setSuccessReceipt] = useState(null);

  // Pagination for Transactions Table
  const [page, setPage] = useState(1);
  const rowsPerPage = 5;
  const totalPages = Math.ceil(transactions.length / rowsPerPage);
  const paginatedTransactions = transactions.slice(
    (page - 1) * rowsPerPage,
    page * rowsPerPage
  );

  // Session timer countdown effect
  useEffect(() => {
    const timer = setInterval(() => {
      setSecondsLeft((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const formatTimer = (totalSec) => {
    const m = Math.floor(totalSec / 60);
    const s = totalSec % 60;
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  // Form Validation & Step 1 Proceed
  const handleProceedTransfer = (e) => {
    e.preventDefault();
    const newErrors = {};

    if (!fromAccount) newErrors.fromAccount = "Please select source account";
    if (!beneficiary) newErrors.beneficiary = "Please select a registered beneficiary";

    const numAmount = parseFloat(amount);
    if (!amount || isNaN(numAmount) || numAmount <= 0) {
      newErrors.amount = "Enter a valid amount greater than 0";
    } else {
      const selectedAcc = accounts[parseInt(fromAccount, 10)];
      if (selectedAcc && numAmount > selectedAcc.availableBalance) {
        newErrors.amount = `Insufficient balance. Available: ${formatINR(selectedAcc.availableBalance)}`;
      }
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    setErrors({});
    setIsConfirming(true);
  };

  // Final Submission Step 2 (Execution)
  const handleConfirmTransfer = () => {
    const numAmount = parseFloat(amount);
    const accIndex = parseInt(fromAccount, 10);
    const selectedAcc = accounts[accIndex];
    const benObj = BENEFICIARIES.find((b) => b.id === beneficiary);

    // Update account balances
    const updatedAccounts = [...accounts];
    const newBal = selectedAcc.availableBalance - numAmount;
    updatedAccounts[accIndex] = {
      ...selectedAcc,
      availableBalance: newBal,
      ledgerBalance: newBal
    };
    setAccounts(updatedAccounts);

    // Generate reference and record new transaction
    const refNumber = `${transferMode}${Date.now().toString().slice(-8)}`;
    const newTxn = {
      id: `TXN${Date.now()}`,
      date: "30 Sep 2026",
      narration: `${transferMode}/P2A/${benObj?.name || "BENEFICIARY"}/${remarks || "FUNDS TRANSFER"}`,
      refNo: refNumber,
      debit: numAmount,
      credit: null,
      balance: newBal
    };

    setTransactions([newTxn, ...transactions]);

    // Set receipt and close modal
    setSuccessReceipt({
      refNumber,
      amount: numAmount,
      beneficiary: benObj?.name,
      mode: transferMode,
      date: new Date().toLocaleString("en-IN", {
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit"
      })
    });

    setIsConfirming(false);
    handleResetForm();
  };

  const handleResetForm = () => {
    setBeneficiary("");
    setAmount("");
    setRemarks("");
    setErrors({});
  };

  return (
    <div className="bank-portal">
      {/* ============================================================
          1. TOP UTILITY BAR
          ============================================================ */}
      <header className="bank-utility-bar">
        <div className="bank-brand-block">
          <div className="bank-logo-icon">A</div>
          <span className="bank-title">APEX TRUST BANK</span>
          <span className="bank-portal-tag">Personal Internet Banking</span>
        </div>

        <div className="bank-utility-links">
          <span className="bank-utility-item cust-id">Cust ID: **4910</span>

          <span
            className={`bank-utility-item timer ${secondsLeft < 180 ? "urgent" : ""}`}
            title="Auto logout upon expiry for security"
          >
            Session expires in {formatTimer(secondsLeft)}
          </span>

          <a href="#help" className="bank-utility-link">
            Help
          </a>
          <a href="#contact" className="bank-utility-link">
            Contact Us
          </a>
          <a href="#security" className="bank-utility-link">
            Security Tips
          </a>

          {onSwitchToOps && (
            <button
              onClick={onSwitchToOps}
              className="bank-utility-btn"
              style={{ borderColor: "#FFC107", color: "#FFC107" }}
              title="Open the internal fraud operations investigation panel"
            >
              Fraud Ops View
            </button>
          )}

          <button
            className="bank-utility-btn"
            onClick={() => alert("Logged out securely. Session ended.")}
          >
            Logout
          </button>
        </div>
      </header>

      {/* ============================================================
          2. MAIN NAVIGATION BAR
          ============================================================ */}
      <nav className="bank-main-nav">
        <button
          className="mobile-nav-toggle"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
        >
          ☰ Banking Menu
        </button>

        <ul className={`nav-menu-list ${mobileMenuOpen ? "mobile-open" : ""}`}>
          <li className="nav-item active">
            <a href="#accounts" className="nav-link">
              Accounts
            </a>
            <div className="nav-dropdown">
              <a href="#savings" className="nav-dropdown-link">
                Savings Accounts
              </a>
              <a href="#current" className="nav-dropdown-link">
                Current Accounts
              </a>
              <a href="#term-deposits" className="nav-dropdown-link">
                Term Deposits
              </a>
              <a href="#statements" className="nav-dropdown-link">
                Download e-Statement
              </a>
            </div>
          </li>

          <li className="nav-item">
            <a href="#transfers" className="nav-link">
              Payments & Transfers
            </a>
            <div className="nav-dropdown">
              <a href="#quick-transfer" className="nav-dropdown-link">
                Quick Transfer (IMPS)
              </a>
              <a href="#neft" className="nav-dropdown-link">
                NEFT / RTGS Transfer
              </a>
              <a href="#manage-beneficiaries" className="nav-dropdown-link">
                Manage Beneficiaries
              </a>
              <a href="#recurring-payments" className="nav-dropdown-link">
                Standing Instructions
              </a>
            </div>
          </li>

          <li className="nav-item">
            <a href="#cards" className="nav-link">
              Cards
            </a>
            <div className="nav-dropdown">
              <a href="#credit-cards" className="nav-dropdown-link">
                Credit Card Summary
              </a>
              <a href="#debit-cards" className="nav-dropdown-link">
                Debit Card Controls
              </a>
              <a href="#pin-gen" className="nav-dropdown-link">
                Instant PIN Generation
              </a>
              <a href="#block-card" className="nav-dropdown-link">
                Block / Hotlist Card
              </a>
            </div>
          </li>

          <li className="nav-item">
            <a href="#deposits" className="nav-link">
              Deposits
            </a>
          </li>

          <li className="nav-item">
            <a href="#loans" className="nav-link">
              Loans
            </a>
          </li>

          <li className="nav-item">
            <a href="#investments" className="nav-link">
              Investments
            </a>
          </li>

          <li className="nav-item">
            <a href="#services" className="nav-link">
              Services
            </a>
          </li>

          <li className="nav-item">
            <a href="#statements" className="nav-link">
              Statements
            </a>
          </li>
        </ul>
      </nav>

      {/* ============================================================
          3. BREADCRUMB & GREETING STRIP
          ============================================================ */}
      <div className="bank-sub-header">
        <div className="bank-breadcrumb">
          <span>Home</span>
          <span className="crumb-separator">&gt;</span>
          <span>Accounts</span>
          <span className="crumb-separator">&gt;</span>
          <span className="crumb-active">Account Summary</span>
        </div>

        <div className="bank-user-welcome">
          Welcome, <strong>Mr. Rajesh K. Sharma</strong>
          <span className="bank-last-login">
            Last login: 30 Sep 2026, 18:42 IST | IP: 103.21.***.42
          </span>
        </div>
      </div>

      {/* ============================================================
          4. MAIN LAYOUT: SIDEBAR + CONTENT PANELS
          ============================================================ */}
      <div className="bank-layout-container">
        {/* 4A. LEFT SIDEBAR */}
        <aside className="bank-sidebar">
          <div className="sidebar-panel">
            <div className="sidebar-header">Quick Access</div>
            <ul className="sidebar-menu">
              <li className="active">
                <a href="#summary" className="sidebar-link">
                  Account Summary
                </a>
              </li>
              <li>
                <a href="#transfer" className="sidebar-link">
                  Fund Transfer
                </a>
              </li>
              <li>
                <a href="#billpay" className="sidebar-link">
                  Bill Pay & Recharge
                </a>
              </li>
              <li>
                <a href="#beneficiaries" className="sidebar-link">
                  Beneficiary Management
                </a>
              </li>
              <li>
                <a href="#cheque" className="sidebar-link">
                  Cheque Book Request
                </a>
              </li>
              <li>
                <a href="#estatement" className="sidebar-link">
                  Download Statement
                </a>
              </li>
              <li>
                <a href="#profile" className="sidebar-link">
                  Profile & Security Settings
                </a>
              </li>
            </ul>
          </div>

          <div className="sidebar-panel">
            <div className="sidebar-header">24x7 Helpdesk</div>
            <div className="sidebar-quick-help">
              <strong>Toll-Free Customer Care</strong>
              1800-425-9900 / 1800-11-2211
              <br />
              <br />
              <strong>Suspicious Activity?</strong>
              SMS <code>BLOCK</code> to 567676 to immediately freeze online access.
            </div>
          </div>
        </aside>

        {/* 4B. MAIN CONTENT AREA */}
        <main className="bank-content-area">
          {/* SUCCESS BANNER UPON TRANSFER */}
          {successReceipt && (
            <div
              className="bank-panel"
              style={{
                borderLeft: "4px solid var(--bank-credit)",
                backgroundColor: "#F4FAF6",
                padding: "12px 16px",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center"
              }}
            >
              <div>
                <strong style={{ color: "var(--bank-credit)", display: "block" }}>
                  Payment Transferred Successfully
                </strong>
                <span style={{ fontSize: "12px", color: "var(--bank-text-secondary)" }}>
                  Ref No: <strong>{successReceipt.refNumber}</strong> | Amount:{" "}
                  <strong>{formatINR(successReceipt.amount)}</strong> to{" "}
                  <strong>{successReceipt.beneficiary}</strong> via {successReceipt.mode} on{" "}
                  {successReceipt.date}.
                </span>
              </div>
              <button
                className="btn-bank-secondary"
                style={{ padding: "4px 10px", fontSize: "11px" }}
                onClick={() => setSuccessReceipt(null)}
              >
                Dismiss
              </button>
            </div>
          )}

          {/* PANEL 1: ACCOUNT SUMMARY TABLE */}
          <section className="bank-panel">
            <div className="panel-header-strip">
              <div style={{ display: "flex", alignItems: "center" }}>
                <h3 className="panel-title">Operative Accounts Summary</h3>
                <button
                  className="balance-toggle-btn"
                  onClick={() => setHideBalance(!hideBalance)}
                >
                  [{hideBalance ? "Show Balance" : "Hide Balance"}]
                </button>
              </div>
              <a href="#all-accounts" className="panel-action-link">
                View Account Details
              </a>
            </div>

            <div className="panel-body no-padding">
              <div className="table-responsive">
                <table className="bank-table">
                  <thead>
                    <tr>
                      <th>Account Type</th>
                      <th>Account Number</th>
                      <th>Branch & IFSC</th>
                      <th className="amount-col">Available Balance</th>
                      <th className="amount-col">Ledger Balance</th>
                      <th style={{ textAlign: "center" }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {accounts.map((acc, idx) => (
                      <tr key={idx}>
                        <td>
                          <strong>{acc.type}</strong>
                        </td>
                        <td className="account-number">{acc.accountNumber}</td>
                        <td style={{ fontSize: "12px", color: "var(--bank-text-secondary)" }}>
                          {acc.branch}
                          <br />
                          <span style={{ color: "var(--bank-text-muted)" }}>{acc.ifsc}</span>
                        </td>
                        <td className="amount-col" style={{ fontWeight: 700, color: "var(--bank-navy)" }}>
                          {hideBalance ? "₹ ••••••••" : formatINR(acc.availableBalance)}
                        </td>
                        <td className="amount-col">
                          {hideBalance ? "₹ ••••••••" : formatINR(acc.ledgerBalance)}
                        </td>
                        <td className="action-cell" style={{ textAlign: "center" }}>
                          <a href="#statement">Statement</a>
                          <span className="action-separator">|</span>
                          <a href="#details">Details</a>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </section>

          {/* PANEL 2: RECENT TRANSACTIONS TABLE */}
          <section className="bank-panel">
            <div className="panel-header-strip">
              <h3 className="panel-title">Recent Transactions (Account: XXXX XXXX 4821)</h3>
              <div style={{ display: "flex", gap: "10px" }}>
                <a
                  href="#download-pdf"
                  className="panel-action-link"
                  onClick={(e) => {
                    e.preventDefault();
                    alert("Statement download initiated (PDF format).");
                  }}
                >
                  Download PDF
                </a>
                <span style={{ color: "#ADB5BD" }}>|</span>
                <a
                  href="#download-xls"
                  className="panel-action-link"
                  onClick={(e) => {
                    e.preventDefault();
                    alert("Statement export initiated (Excel XLS format).");
                  }}
                >
                  Download Excel
                </a>
              </div>
            </div>

            <div className="panel-body no-padding">
              <div className="table-responsive">
                <table className="bank-table">
                  <thead>
                    <tr>
                      <th style={{ width: "95px" }}>Date</th>
                      <th>Description / Narration</th>
                      <th>Ref / UTR No.</th>
                      <th className="amount-col">Debit (Dr)</th>
                      <th className="amount-col">Credit (Cr)</th>
                      <th className="amount-col">Balance</th>
                    </tr>
                  </thead>
                  <tbody>
                    {paginatedTransactions.map((tx) => (
                      <tr key={tx.id}>
                        <td style={{ whiteSpace: "nowrap", fontSize: "12px" }}>{tx.date}</td>
                        <td style={{ fontSize: "12.5px" }}>
                          <code>{tx.narration}</code>
                        </td>
                        <td className="ref-no" style={{ fontSize: "11px", color: "var(--bank-text-muted)" }}>
                          {tx.refNo}
                        </td>
                        <td className="amount-col debit">
                          {tx.debit ? formatINR(tx.debit) : "-"}
                        </td>
                        <td className="amount-col credit">
                          {tx.credit ? formatINR(tx.credit) : "-"}
                        </td>
                        <td className="amount-col" style={{ fontWeight: 600 }}>
                          {hideBalance ? "₹ ••••••••" : formatINR(tx.balance)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* TABLE PAGINATION */}
              <div className="table-toolbar">
                <span>
                  Showing {(page - 1) * rowsPerPage + 1} to{" "}
                  {Math.min(page * rowsPerPage, transactions.length)} of {transactions.length} entries
                </span>
                <div className="pagination-controls">
                  <button
                    className="page-btn"
                    disabled={page === 1}
                    onClick={() => setPage(page - 1)}
                  >
                    Previous
                  </button>
                  {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
                    <button
                      key={p}
                      className={`page-btn ${page === p ? "active" : ""}`}
                      onClick={() => setPage(p)}
                    >
                      {p}
                    </button>
                  ))}
                  <button
                    className="page-btn"
                    disabled={page === totalPages}
                    onClick={() => setPage(page + 1)}
                  >
                    Next
                  </button>
                </div>
              </div>
            </div>
          </section>

          {/* PANEL 3: QUICK TRANSFER FORM */}
          <section className="bank-panel">
            <div className="panel-header-strip">
              <h3 className="panel-title">Quick Fund Transfer (Third-Party / Intra-Bank)</h3>
              <span style={{ fontSize: "11px", color: "var(--bank-text-muted)" }}>
                Fields marked with <span style={{ color: "var(--bank-debit)" }}>*</span> are mandatory
              </span>
            </div>

            <div className="panel-body">
              <form className="bank-form" onSubmit={handleProceedTransfer}>
                <div className="form-grid">
                  {/* From Account */}
                  <div className="form-group">
                    <label className="form-label">
                      Debit Account Number <span className="required-star">*</span>
                    </label>
                    <select
                      className={`form-select ${errors.fromAccount ? "error" : ""}`}
                      value={fromAccount}
                      onChange={(e) => setFromAccount(e.target.value)}
                    >
                      {accounts.map((acc, index) => (
                        <option key={index} value={index}>
                          {acc.type} - {acc.accountNumber} (Avail: {formatINR(acc.availableBalance)})
                        </option>
                      ))}
                    </select>
                    {errors.fromAccount && <span className="form-error-msg">{errors.fromAccount}</span>}
                  </div>

                  {/* Beneficiary */}
                  <div className="form-group">
                    <label className="form-label">
                      Payee / Beneficiary <span className="required-star">*</span>
                    </label>
                    <select
                      className={`form-select ${errors.beneficiary ? "error" : ""}`}
                      value={beneficiary}
                      onChange={(e) => setBeneficiary(e.target.value)}
                    >
                      <option value="">-- Select Registered Beneficiary --</option>
                      {BENEFICIARIES.map((ben) => (
                        <option key={ben.id} value={ben.id}>
                          {ben.name} ({ben.bank} - {ben.accountNumber})
                        </option>
                      ))}
                    </select>
                    {errors.beneficiary && <span className="form-error-msg">{errors.beneficiary}</span>}
                  </div>

                  {/* Transfer Mode */}
                  <div className="form-group">
                    <label className="form-label">Transfer Type</label>
                    <div className="transfer-mode-group">
                      <label className="mode-radio-label">
                        <input
                          type="radio"
                          name="mode"
                          value="IMPS"
                          checked={transferMode === "IMPS"}
                          onChange={(e) => setTransferMode(e.target.value)}
                        />
                        IMPS (24x7 Instant)
                      </label>
                      <label className="mode-radio-label">
                        <input
                          type="radio"
                          name="mode"
                          value="NEFT"
                          checked={transferMode === "NEFT"}
                          onChange={(e) => setTransferMode(e.target.value)}
                        />
                        NEFT (Batched)
                      </label>
                      <label className="mode-radio-label">
                        <input
                          type="radio"
                          name="mode"
                          value="RTGS"
                          checked={transferMode === "RTGS"}
                          onChange={(e) => setTransferMode(e.target.value)}
                        />
                        RTGS (&gt; ₹2 Lakhs)
                      </label>
                    </div>
                  </div>

                  {/* Amount */}
                  <div className="form-group">
                    <label className="form-label">
                      Amount (INR) <span className="required-star">*</span>
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      placeholder="0.00"
                      className={`form-input ${errors.amount ? "error" : ""}`}
                      value={amount}
                      onChange={(e) => setAmount(e.target.value)}
                    />
                    {errors.amount ? (
                      <span className="form-error-msg">{errors.amount}</span>
                    ) : (
                      <span className="form-helper">Daily transaction limit remaining: ₹ 5,00,000.00</span>
                    )}
                  </div>

                  {/* Remarks */}
                  <div className="form-group full-width">
                    <label className="form-label">Remarks / Purpose (Optional)</label>
                    <input
                      type="text"
                      maxLength={50}
                      placeholder="e.g. Consultancy Fee / Personal Transfer"
                      className="form-input"
                      value={remarks}
                      onChange={(e) => setRemarks(e.target.value)}
                    />
                    <span className="form-helper">Max 50 alphanumeric characters.</span>
                  </div>
                </div>

                <div className="form-actions">
                  <button type="submit" className="btn-bank-primary">
                    Proceed
                  </button>
                  <button
                    type="button"
                    className="btn-bank-secondary"
                    onClick={handleResetForm}
                  >
                    Reset
                  </button>
                </div>
              </form>
            </div>
          </section>

          {/* PANEL 4: CARDS & DEPOSITS PANEL */}
          <section className="bank-panel">
            <div className="panel-header-strip">
              <h3 className="panel-title">Cards & Deposit Accounts</h3>
              <a href="#services" className="panel-action-link">
                Manage Portfolio
              </a>
            </div>

            <div className="panel-body">
              <div className="cards-deposits-grid">
                {/* Credit Card Box */}
                <div className="sub-panel-box">
                  <h4>Apex Signature Visa Credit Card</h4>
                  <div className="detail-row">
                    <span className="detail-label">Card Number:</span>
                    <span className="detail-value tabular-nums">4532 XXXX XXXX 8912</span>
                  </div>
                  <div className="detail-row">
                    <span className="detail-label">Total Credit Limit:</span>
                    <span className="detail-value">{formatINR(350000)}</span>
                  </div>
                  <div className="detail-row">
                    <span className="detail-label">Available Credit Limit:</span>
                    <span className="detail-value highlight">{formatINR(242850)}</span>
                  </div>
                  <div className="detail-row">
                    <span className="detail-label">Current Outstanding:</span>
                    <span className="detail-value">{formatINR(107150)}</span>
                  </div>
                  <div className="detail-row">
                    <span className="detail-label">Payment Due Date:</span>
                    <span className="detail-value" style={{ color: "var(--bank-debit)" }}>
                      12 Oct 2026 (Min Due: ₹ 5,350)
                    </span>
                  </div>
                  <div style={{ marginTop: "10px", display: "flex", gap: "10px" }}>
                    <button
                      className="btn-bank-primary"
                      style={{ padding: "4px 12px", fontSize: "12px" }}
                      onClick={() => alert("Redirecting to Credit Card Bill Payment gateway.")}
                    >
                      Pay Bill
                    </button>
                    <button
                      className="btn-bank-secondary"
                      style={{ padding: "4px 12px", fontSize: "12px" }}
                      onClick={() => alert("Card controls: Domestic/International limits active.")}
                    >
                      Card Controls
                    </button>
                  </div>
                </div>

                {/* Term Deposits Box */}
                <div className="sub-panel-box">
                  <h4>Fixed & Recurring Deposits</h4>
                  <div className="detail-row">
                    <span className="detail-label">Fixed Deposit (FD/8820194):</span>
                    <span className="detail-value">{formatINR(500000)}</span>
                  </div>
                  <div className="detail-row">
                    <span className="detail-label">Interest Rate & Maturity:</span>
                    <span className="detail-value">7.25% p.a. | 15 Mar 2027</span>
                  </div>
                  <div className="detail-row">
                    <span className="detail-label">Maturity Value:</span>
                    <span className="detail-value highlight">{formatINR(574210)}</span>
                  </div>
                  <div style={{ margin: "8px 0", borderTop: "1px dashed #E0E0E0" }}></div>
                  <div className="detail-row">
                    <span className="detail-label">Recurring Deposit (RD/9910283):</span>
                    <span className="detail-value">₹ 15,000 / month</span>
                  </div>
                  <div className="detail-row">
                    <span className="detail-label">Accumulated Principal:</span>
                    <span className="detail-value">{formatINR(180000)}</span>
                  </div>
                  <div style={{ marginTop: "10px" }}>
                    <a href="#open-fd" className="panel-action-link">
                      + Open New Term Deposit
                    </a>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* PANEL 5: IMPORTANT NOTICES & ALERTS */}
          <section className="bank-panel">
            <div className="panel-header-strip">
              <h3 className="panel-title">Important Customer Bulletins & Regulatory Advisories</h3>
            </div>
            <div className="panel-body">
              <div className="notices-list">
                <div className="notice-item alert">
                  <span className="notice-date">[30 Sep 2026]</span>
                  <span>
                    <strong>Security Advisory:</strong> Apex Trust Bank never asks for OTP, CVV, NetBanking
                    passwords, or card PIN over phone, email, or SMS. Please do not share sensitive credentials
                    with anyone.
                  </span>
                </div>

                <div className="notice-item">
                  <span className="notice-date">[28 Sep 2026]</span>
                  <span>
                    <strong>Scheduled Maintenance:</strong> Core Internet Banking and Mobile Banking systems will
                    undergo routine scheduled maintenance on Sunday, 05 Oct 2026 between 01:00 AM and 04:00 AM
                    IST. ATM and Card services will function normally.
                  </span>
                </div>

                <div className="notice-item">
                  <span className="notice-date">[15 Sep 2026]</span>
                  <span>
                    <strong>Mandatory Periodic KYC:</strong> As per regulatory requirements, kindly ensure your KYC
                    details and Form 60/PAN are updated before 31 Dec 2026 via our online portal or your home
                    branch.
                  </span>
                </div>
              </div>
            </div>
          </section>
        </main>
      </div>

      {/* ============================================================
          CONFIRMATION MODAL (TWO-STEP TRANSACTION VERIFICATION)
          ============================================================ */}
      {isConfirming && (
        <div className="bank-modal-overlay">
          <div className="bank-modal">
            <div className="bank-modal-header">Verification & Confirmation - Fund Transfer</div>

            <div className="bank-modal-body">
              <p style={{ margin: "0 0 10px 0", color: "var(--bank-text-secondary)" }}>
                Please review the transfer details carefully before final authorization.
              </p>

              <table className="confirm-details-table">
                <tbody>
                  <tr>
                    <td>Debit Account:</td>
                    <td>{accounts[parseInt(fromAccount, 10)]?.accountNumber}</td>
                  </tr>
                  <tr>
                    <td>Payee Name:</td>
                    <td>{BENEFICIARIES.find((b) => b.id === beneficiary)?.name}</td>
                  </tr>
                  <tr>
                    <td>Payee Bank & Account:</td>
                    <td>
                      {BENEFICIARIES.find((b) => b.id === beneficiary)?.bank} -{" "}
                      {BENEFICIARIES.find((b) => b.id === beneficiary)?.accountNumber}
                    </td>
                  </tr>
                  <tr>
                    <td>Transfer Amount:</td>
                    <td style={{ color: "var(--bank-navy)" }}>{formatINR(parseFloat(amount))}</td>
                  </tr>
                  <tr>
                    <td>Transfer Mode:</td>
                    <td>{transferMode}</td>
                  </tr>
                  <tr>
                    <td>Transaction Fee:</td>
                    <td>₹ 0.00 (Nil)</td>
                  </tr>
                  <tr>
                    <td>Remarks:</td>
                    <td>{remarks || "Not specified"}</td>
                  </tr>
                </tbody>
              </table>

              <div className="confirm-warning-box">
                Funds will be debited immediately from your operative account. Once submitted, this transfer
                cannot be reversed.
              </div>
            </div>

            <div className="bank-modal-footer">
              <button
                type="button"
                className="btn-bank-secondary"
                onClick={() => setIsConfirming(false)}
              >
                Back / Cancel
              </button>
              <button
                type="button"
                className="btn-bank-primary"
                onClick={handleConfirmTransfer}
              >
                Confirm & Authorize
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ============================================================
          5. INSTITUTIONAL FOOTER
          ============================================================ */}
      <footer className="bank-footer">
        <div className="footer-security-banner">
          IMPORTANT SECURITY NOTICE: Never share your NetBanking password, OTP, CVV, or ATM PIN with anyone. Bank
          officials will never ask for confidential authentication credentials.
        </div>

        <div className="footer-main">
          <div className="footer-links-row">
            <a href="#privacy">Privacy Policy</a>
            <span>|</span>
            <a href="#terms">Terms & Conditions</a>
            <span>|</span>
            <a href="#security">Security Guidelines</a>
            <span>|</span>
            <a href="#grievance">Grievance Redressal</a>
            <span>|</span>
            <a href="#interest">Interest Rates & Service Charges</a>
            <span>|</span>
            <a href="#rbi">RBI Kehta Hai / Financial Literacy</a>
          </div>

          <div className="footer-regulatory-text">
            Apex Trust Bank Limited is a licensed Scheduled Commercial Bank regulated by the Reserve Bank of India
            (RBI). Deposits with the bank are insured up to ₹ 5,00,000 by the Deposit Insurance and Credit
            Guarantee Corporation (DICGC). Corporate Identity Number (CIN): L65110KA1994PLC012345.
          </div>

          <div className="footer-copyright">
            © {new Date().getFullYear()} Apex Trust Bank Ltd. All rights reserved. Best viewed in 1024x768 resolution or above.
          </div>
        </div>
      </footer>
    </div>
  );
}
