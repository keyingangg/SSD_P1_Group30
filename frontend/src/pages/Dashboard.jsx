import { useEffect, useMemo, useState } from "react";

import { getUserDashboard } from "../api/auctions.js";

function formatDateTime(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return date.toLocaleString();
}

function formatMoney(value) {
  if (value === null || value === undefined) return "-";
  const numeric = Number(value);
  if (Number.isNaN(numeric)) return "-";
  return `S$${numeric.toFixed(2)}`;
}

export default function Dashboard() {
  const [data, setData] = useState({
    active_bids: [],
    won_auctions: [],
    payment_status: {
      total_orders: 0,
      counts_by_status: {},
      pending_payment_auctions: [],
    },
    auction_history: [],
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let isMounted = true;

    async function loadDashboard() {
      try {
        setLoading(true);
        setError("");
        const payload = await getUserDashboard();
        if (isMounted) {
          setData(payload);
        }
      } catch (err) {
        const detail = err?.response?.data?.detail;
        if (isMounted) {
          setError(detail || "Unable to load dashboard data.");
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    }

    loadDashboard();
    return () => {
      isMounted = false;
    };
  }, []);

  const paymentRows = useMemo(() => {
    const statusMap = data.payment_status?.counts_by_status || {};
    return Object.entries(statusMap).map(([status, count]) => ({
      status,
      count,
    }));
  }, [data.payment_status]);

  return (
    <main className="dashboard-page">
      <section className="dashboard-hero">
        <p className="eyebrow">Account Overview</p>
        <h1>My Dashboard</h1>
        <p className="dashboard-subtitle">
          Track active bids, won auctions, and payment progress.
        </p>
      </section>

      {loading ? <p className="dashboard-note">Loading dashboard...</p> : null}
      {error ? <p className="form-error">{error}</p> : null}

      {!loading && !error ? (
        <div className="dashboard-grid">
          <section className="dashboard-panel">
            <h2>Active Bids</h2>
            {data.active_bids.length === 0 ? (
              <p className="dashboard-note">No active bids yet.</p>
            ) : (
              <div className="dashboard-table-wrap">
                <table className="dashboard-table">
                  <thead>
                    <tr>
                      <th>Listing</th>
                      <th>My Latest Bid</th>
                      <th>Current Highest</th>
                      <th>Ends At</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.active_bids.map((item) => (
                      <tr key={item.listing_id}>
                        <td>{item.title}</td>
                        <td>{formatMoney(item.user_latest_bid_amount)}</td>
                        <td>{formatMoney(item.current_highest_bid)}</td>
                        <td>{formatDateTime(item.ends_at)}</td>
                        <td>
                          {item.is_currently_winning ? "Highest bidder" : "Outbid"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <section className="dashboard-panel">
            <h2>Won Auctions</h2>
            {data.won_auctions.length === 0 ? (
              <p className="dashboard-note">No won auctions yet.</p>
            ) : (
              <div className="dashboard-table-wrap">
                <table className="dashboard-table">
                  <thead>
                    <tr>
                      <th>Listing</th>
                      <th>Winning Amount</th>
                      <th>Ended At</th>
                      <th>Payment</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.won_auctions.map((item) => (
                      <tr key={item.listing_id}>
                        <td>{item.title}</td>
                        <td>{formatMoney(item.winning_amount)}</td>
                        <td>{formatDateTime(item.ended_at)}</td>
                        <td>{item.payment_status}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <section className="dashboard-panel">
            <h2>Payment Status</h2>
            <p className="dashboard-note">
              Total winning orders: {data.payment_status.total_orders}
            </p>
            {paymentRows.length === 0 ? (
              <p className="dashboard-note">No payment records yet.</p>
            ) : (
              <ul className="dashboard-stats-list">
                {paymentRows.map((row) => (
                  <li key={row.status}>
                    <span>{row.status}</span>
                    <strong>{row.count}</strong>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="dashboard-panel dashboard-panel-wide">
            <h2>Auction History</h2>
            {data.auction_history.length === 0 ? (
              <p className="dashboard-note">No auction history yet.</p>
            ) : (
              <div className="dashboard-table-wrap">
                <table className="dashboard-table">
                  <thead>
                    <tr>
                      <th>Listing</th>
                      <th>Result</th>
                      <th>My Bid Count</th>
                      <th>Latest Bid</th>
                      <th>Final Price</th>
                      <th>Ended At</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.auction_history.map((item) => (
                      <tr key={item.listing_id}>
                        <td>{item.title}</td>
                        <td>{item.result}</td>
                        <td>{item.user_bid_count}</td>
                        <td>{formatMoney(item.user_latest_bid_amount)}</td>
                        <td>{formatMoney(item.final_price)}</td>
                        <td>{formatDateTime(item.ends_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </div>
      ) : null}
    </main>
  );
}
