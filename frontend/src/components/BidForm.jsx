import { useEffect, useMemo, useState } from "react";
import { submitBid } from "../api/auctions.js";

export default function BidForm({ listingId, listing, onSubmit }) {
  const [amount, setAmount] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const runtimeStatus = String(listing?.status || "").toLowerCase();
  const displayStatus = String(listing?.display_status || "").toLowerCase();
  const nowMs = Date.now();
  const startsAtMs = listing?.starts_at ? new Date(listing.starts_at).getTime() : NaN;
  const endsAtMs = listing?.ends_at ? new Date(listing.ends_at).getTime() : NaN;

  const isWithinAuctionWindow =
    Number.isFinite(startsAtMs) &&
    Number.isFinite(endsAtMs) &&
    startsAtMs <= nowMs &&
    nowMs < endsAtMs;

  const isDefinitelyInactive = ["draft", "cancelled", "ended"].includes(runtimeStatus);
  const isActive =
    !isDefinitelyInactive &&
    (runtimeStatus === "active" || displayStatus === "live now" || isWithinAuctionWindow);

  const currentHighestBid = Number(listing?.current_highest_bid || 0);
  const startingPrice = Number(listing?.starting_price || 0);
  const minimumIncrement = Number(listing?.minimum_increment || 0);

  const minimumAllowedBid = useMemo(() => {
    const effectiveHighest = currentHighestBid > 0 ? currentHighestBid : startingPrice;
    const minBid = effectiveHighest + minimumIncrement;
    return Number.isFinite(minBid) && minBid > 0 ? minBid : 0;
  }, [currentHighestBid, minimumIncrement, startingPrice]);

  useEffect(() => {
    if (minimumAllowedBid > 0) {
      setAmount((prev) => (prev ? prev : minimumAllowedBid.toFixed(2)));
    }
  }, [listingId, minimumAllowedBid]);

  const quickIncrements = useMemo(() => {
    if (minimumIncrement <= 0) return [];
    return [1, 2, 4].map((mult) => minimumIncrement * mult);
  }, [minimumIncrement]);

  const applyQuick = (inc) => {
    const base = currentHighestBid > 0 ? currentHighestBid : startingPrice;
    setAmount((base + inc).toFixed(2));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (!isActive) {
      setError("Bidding is available only when the auction is live.");
      return;
    }
    if (!amount) {
      setError("Please enter your bid amount.");
      return;
    }
    if (minimumAllowedBid > 0 && Number(amount) < minimumAllowedBid) {
      setError(`Bid must be at least $${minimumAllowedBid.toFixed(2)}.`);
      return;
    }

    try {
      setSubmitting(true);
      await submitBid(listingId, amount);
      setSuccess("Bid submitted successfully.");
      setAmount(minimumAllowedBid > 0 ? minimumAllowedBid.toFixed(2) : "");
      if (typeof onSubmit === "function") onSubmit();
    } catch (err) {
      setError(err?.response?.data?.detail || "Unable to submit bid.");
    } finally {
      setSubmitting(false);
    }
  };

  const formatSGD = (n) => `S$${Number(n).toLocaleString("en-SG", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;

  return (
    <form onSubmit={handleSubmit}>
      {/* YOUR BID label */}
      <div className="ld-your-bid-label">Your Bid (SGD)</div>

      {/* Input row */}
      <div className="ld-input-wrap">
        <span className="ld-input-prefix">S$</span>
        <input
          id="bid-amount"
          type="number"
          min={minimumAllowedBid > 0 ? minimumAllowedBid.toFixed(2) : "0"}
          step="0.01"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          placeholder={minimumAllowedBid > 0 ? minimumAllowedBid.toFixed(2) : "0.00"}
          disabled={!isActive || submitting}
        />
        <span className="ld-input-min-label">min. bid</span>
      </div>

      {/* Quick increment buttons */}
      {quickIncrements.length > 0 && (
        <div className="ld-quick-btns">
          {quickIncrements.map((inc) => (
            <button
              key={inc}
              type="button"
              className="ld-quick-btn"
              onClick={() => applyQuick(inc)}
              disabled={!isActive || submitting}
            >
              +{formatSGD(inc)}
            </button>
          ))}
          <button
            type="button"
            className="ld-quick-btn"
            onClick={() => setAmount("")}
            disabled={!isActive || submitting}
          >
            Custom
          </button>
        </div>
      )}

      {/* Place bid button */}
      {runtimeStatus !== "ended" && (
        <button
          type="submit"
          className="ld-place-bid-btn"
          disabled={!isActive || submitting}
        >
          {submitting ? "Submitting…" : "Place Bid"}
        </button>
      )}

      {runtimeStatus === "ended" && (
        <p style={{ margin: "0 0 8px", color: "#6b7280", fontSize: 13 }}>Auction has ended.</p>
      )}

      {!isActive && runtimeStatus !== "ended" && (
        <p style={{ margin: "0 0 8px", color: "#6b7280", fontSize: 12 }}>
          Auction not live yet. Bidding opens at start time.
        </p>
      )}

      <p className="ld-bid-footnote">Bids are binding contracts · Authentication required</p>

      {error && <div className="ld-bid-msg-error">{error}</div>}
      {success && <div className="ld-bid-msg-success">{success}</div>}
    </form>
  );
}
