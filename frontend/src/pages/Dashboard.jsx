import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { getUserDashboard } from "../api/auctions.js";
import { useAuth } from "../context/AuthContext.jsx";

function formatSGD(value) {
  const n = Number(value);
  if (!n || Number.isNaN(n)) return "-";
  return `S$${n.toLocaleString("en-SG", { minimumFractionDigits: 0 })}`;
}

function formatDate(value) {
  if (!value) return "-";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "-";
  return d.toLocaleDateString("en-SG", { day: "numeric", month: "short", year: "numeric" });
}

function timeUntil(value) {
  if (!value) return "-";
  const ms = new Date(value).getTime() - Date.now();
  if (ms <= 0) return "Ended";
  const totalMin = Math.floor(ms / 60000);
  const days = Math.floor(totalMin / 1440);
  const hours = Math.floor((totalMin % 1440) / 60);
  const mins = totalMin % 60;
  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${mins}m`;
  return `${mins}m`;
}

const ORDER_STEPS = ["Payment Confirmed", "Processing", "Dispatched", "Out for Delivery", "Delivered"];

function orderStepIndex(status) {
  const s = String(status || "").toLowerCase();
  if (s === "delivered") return 5;
  if (s === "out_for_delivery" || s === "out for delivery") return 4;
  if (s === "dispatched") return 3;
  if (s === "processing") return 2;
  if (s === "paid") return 1;
  return 0;
}

function paymentBadgeClass(status) {
  const s = String(status || "").toLowerCase();
  if (s === "pending" || s === "payment_required") return "db-badge--payment";
  if (s === "paid") return "db-badge--paid";
  if (s === "dispatched") return "db-badge--dispatched";
  if (s === "delivered") return "db-badge--delivered";
  return "db-badge--payment";
}

function paymentBadgeLabel(status) {
  const s = String(status || "").toLowerCase();
  if (s === "pending" || s === "payment_required") return "Payment Required";
  if (s === "paid") return "Paid";
  if (s === "dispatched") return "Dispatched";
  if (s === "delivered") return "Delivered";
  return status || "Pending";
}

const TABS = ["Overview", "Active Bids", "Won Auctions", "Order Status", "Account Settings"];

export default function Dashboard() {
  const { user } = useAuth();
  const [data, setData] = useState({
    active_bids: [],
    won_auctions: [],
    payment_status: { total_orders: 0, counts_by_status: {}, pending_payment_auctions: [] },
    auction_history: [],
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState(0);

  useEffect(() => {
    let mounted = true;
    async function load() {
      try {
        setLoading(true);
        setError("");
        const payload = await getUserDashboard();
        if (mounted) setData(payload);
      } catch (err) {
        if (mounted) setError(err?.response?.data?.detail || "Unable to load dashboard data.");
      } finally {
        if (mounted) setLoading(false);
      }
    }
    load();
    return () => { mounted = false; };
  }, []);

  const displayName = user?.display_name || user?.email?.split("@")[0] || "Member";

  const totalAcquired = useMemo(
    () => data.won_auctions.reduce((sum, w) => sum + Number(w.winning_amount || 0), 0),
    [data.won_auctions]
  );

  const pendingPaymentCount = useMemo(
    () => data.payment_status?.pending_payment_auctions?.length || 0,
    [data.payment_status]
  );

  const joinedDate = useMemo(() => {
    if (!user?.date_joined) return null;
    const d = new Date(user.date_joined);
    return d.toLocaleDateString("en-SG", { month: "long", year: "numeric" });
  }, [user]);

  return (
    <main className="db-page">
      {/* Header */}
      <div className="db-header">
        <p className="db-eyebrow"><span className="db-eyebrow-rule" />Member Dashboard</p>
        <h1 className="db-name">Collection</h1>
        <div className="db-meta">
          {user?.id && <span>Member #{String(user.id).padStart(5, "0")}</span>}
          {joinedDate && <><span className="db-meta-sep">·</span><span>Joined {joinedDate}</span></>}
          <span className="db-meta-sep">·</span>
          <span className="db-meta-verified">Verified</span>
          {user?.mfa_enabled && (
            <><span className="db-meta-sep">·</span><span className="db-meta-mfa">MFA Active</span></>
          )}
        </div>
      </div>

      {/* Stat cards */}
      <div className="db-stats">
        <div className="db-stat">
          <p className="db-stat-label">Active Bids</p>
          <p className="db-stat-number">{data.active_bids.length}</p>
          <p className="db-stat-sub">Lots you're bidding on</p>
        </div>
        <div className="db-stat">
          <p className="db-stat-label">Auctions Won</p>
          <p className="db-stat-number">{data.won_auctions.length}</p>
          <p className="db-stat-sub">Total lots acquired</p>
        </div>
        <div className={`db-stat${pendingPaymentCount > 0 ? " db-stat--alert" : ""}`}>
          {pendingPaymentCount > 0 && <span className="db-stat-alert-dot" />}
          <p className={`db-stat-label${pendingPaymentCount > 0 ? " db-stat-label--alert" : ""}`}>Payment Due</p>
          <p className="db-stat-number">{pendingPaymentCount}</p>
          <p className="db-stat-sub">Checkout within 72h</p>
        </div>
        <div className="db-stat">
          <p className="db-stat-label">Total Acquired</p>
          <p className="db-stat-number db-stat-number--gold">{formatSGD(totalAcquired)}</p>
          <p className="db-stat-sub">Lifetime auction value</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="db-tabs">
        {TABS.map((tab, i) => (
          <button
            key={tab}
            type="button"
            className={`db-tab${i === activeTab ? " active" : ""}`}
            onClick={() => setActiveTab(i)}
          >
            {tab}
          </button>
        ))}
      </div>

      {loading && <p className="db-empty">Loading dashboard…</p>}
      {error && <p className="form-error">{error}</p>}

      {!loading && !error && (
        <>
          {/* Active Bids */}
          <div className="db-section">
            <div className="db-section-header">
              <h2 className="db-section-title">Active Bids</h2>
            </div>
            {data.active_bids.length === 0 ? (
              <p className="db-empty">No active bids yet.</p>
            ) : (
              <div className="db-bid-cards">
                {data.active_bids.map((bid) => (
                  <div
                    key={bid.listing_id}
                    className={`db-bid-card${bid.is_currently_winning ? "" : " db-bid-card--outbid"}`}
                  >
                    <div className="db-bid-thumb">
                      {bid.image_url && <img src={bid.image_url} alt={bid.title} />}
                    </div>
                    <div className="db-bid-info">
                      <p className="db-bid-lot">LOT {String(bid.listing_id).padStart(3, "0")}</p>
                      <p className="db-bid-title">{bid.title}</p>
                      <p className="db-bid-amounts">
                        My bid: <strong>{formatSGD(bid.user_latest_bid_amount)}</strong>
                        {" · "}Current: <strong>{formatSGD(bid.current_highest_bid)}</strong>
                      </p>
                    </div>
                    <div className="db-bid-closes">Closes: {timeUntil(bid.ends_at)}</div>
                    <div className="db-bid-status">
                      {bid.is_currently_winning ? (
                        <span className="db-badge db-badge--winning">Winning</span>
                      ) : (
                        <>
                          <span className="db-badge db-badge--outbid">Outbid</span>
                          <Link to={`/listings/${bid.listing_id}`} className="db-raise-btn">
                            Raise Bid →
                          </Link>
                        </>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Won Auctions & Order Status */}
          <div className="db-section">
            <div className="db-section-header">
              <h2 className="db-section-title">Won Auctions &amp; Order Status</h2>
              <span className="db-section-meta">Fulfilment status updated by SecureBid · Read-only</span>
            </div>
            {data.won_auctions.length === 0 ? (
              <p className="db-empty">No won auctions yet.</p>
            ) : (
              <div className="db-won-cards">
                {data.won_auctions.map((won) => {
                  const stepIdx = orderStepIndex(won.payment_status);
                  const isPending = stepIdx === 0;
                  return (
                    <div key={won.listing_id} className="db-won-card">
                      <div className="db-won-card-main">
                        <div className="db-won-thumb">
                          {won.image_url && <img src={won.image_url} alt={won.title} />}
                        </div>
                        <div className="db-won-info">
                          <p className="db-won-lot">LOT {String(won.listing_id).padStart(3, "0")}</p>
                          <p className="db-won-title">{won.title}</p>
                          <p className="db-won-date">Won {formatDate(won.ended_at)}</p>
                        </div>
                        <div className="db-won-price">{formatSGD(won.winning_amount)}</div>
                        <div className="db-won-actions">
                          <span className={`db-badge ${paymentBadgeClass(won.payment_status)}`}>
                            {paymentBadgeLabel(won.payment_status)}
                          </span>
                          {isPending ? (
                            <Link to={`/checkout/${won.order_id || won.listing_id}`} className="db-checkout-btn">
                              Checkout →
                            </Link>
                          ) : (
                            <Link to={`/checkout/${won.order_id || won.listing_id}`} className="db-view-btn">
                              View Order
                            </Link>
                          )}
                        </div>
                      </div>

                      {/* Order tracker (only when paid/beyond) */}
                      {stepIdx > 0 && (
                        <div className="db-order-status">
                          <p className="db-order-label">Order Status</p>
                          <div style={{ display: "flex", alignItems: "flex-start", gap: 0 }}>
                            <div className="db-order-track" style={{ flex: 1 }}>
                              {ORDER_STEPS.map((step, i) => {
                                const done = i + 1 < stepIdx;
                                const current = i + 1 === stepIdx;
                                return (
                                  <div
                                    key={step}
                                    className={`db-order-step${done ? " db-order-step--done" : ""}${current ? " db-order-step--current" : ""}`}
                                  >
                                    <div className="db-order-dot" />
                                    <span className="db-order-step-name">{step}</span>
                                  </div>
                                );
                              })}
                            </div>
                            <Link to={`/checkout/${won.order_id || won.listing_id}`} className="db-order-view-link">
                              View full order details →
                            </Link>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Auction History */}
          <div className="db-history">
            <div className="db-section-header">
              <h2 className="db-section-title">Auction History</h2>
              <Link to="/auctions" className="db-section-link">View all</Link>
            </div>
            <div className="db-history-bar">
              <span>{data.won_auctions.length} auctions won</span>
              <span className="db-history-sep">·</span>
              <span>{data.active_bids.length} active bids</span>
              <span className="db-history-sep">·</span>
              <span>{formatSGD(totalAcquired)} total acquisitions{joinedDate ? ` since ${joinedDate}` : ""}</span>
              <span className="db-history-sep">·</span>
              <span>Account in good standing</span>
            </div>
          </div>
        </>
      )}
    </main>
  );
}
