import { useEffect, useMemo, useState } from "react";
import { submitBid } from "../api/auctions.js";

// Bid amount input and submit control for an active auction.
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

  const startingPrice = Number(listing?.starting_price || 0);
  const currentHighestBid = Number(listing?.current_highest_bid || 0);
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
      if (typeof onSubmit === "function") {
        onSubmit();
      }
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setError(detail || "Unable to submit bid.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      style={{
        border: "1px solid rgba(27,26,23,.12)",
        borderRadius: 10,
        background: "#fff",
        padding: "1rem",
        display: "grid",
        gap: "0.7rem",
      }}
    >
      <h3 style={{ margin: 0 }}>Place a bid</h3>
      {!isActive ? (
        <p style={{ margin: 0, color: "#6b7280" }}>
          {runtimeStatus === "ended" ? "Auction has ended." : "Auction not live yet. Bidding opens at the start time."}
        </p>
      ) : null}

      {runtimeStatus !== "ended" && (
        <>
          {listing?.minimum_increment ? (
            <p style={{ margin: 0, color: "#6b7280", fontSize: ".9rem" }}>
              Minimum increment: ${Number(listing.minimum_increment).toFixed(2)}
            </p>
          ) : null}

          {minimumAllowedBid > 0 ? (
            <p style={{ margin: 0, color: "#6b7280", fontSize: ".9rem" }}>
              Suggested minimum bid (from start price/current bid): ${minimumAllowedBid.toFixed(2)}
            </p>
          ) : null}

          <div style={{ display: "grid", gap: "0.45rem" }}>
            <label htmlFor="bid-amount">Your bid amount</label>
            <input
              id="bid-amount"
              type="number"
              min={minimumAllowedBid > 0 ? minimumAllowedBid.toFixed(2) : "0"}
              step="0.01"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder={minimumAllowedBid > 0 ? minimumAllowedBid.toFixed(2) : "0.00"}
              disabled={!isActive || submitting}
              style={{
                padding: "0.65rem 0.7rem",
                borderRadius: 8,
                border: "1px solid rgba(27,26,23,.2)",
              }}
            />
          </div>

          <button
            type="submit"
            disabled={!isActive || submitting}
            style={{
              justifySelf: "start",
              padding: "0.6rem 0.9rem",
              borderRadius: 8,
              border: "none",
              background: isActive ? "var(--gold, #c2a15a)" : "#d1d5db",
              color: isActive ? "#fff" : "#374151",
              cursor: !isActive || submitting ? "not-allowed" : "pointer",
              fontWeight: 600,
            }}
          >
            {submitting ? "Submitting..." : "Place Bid"}
          </button>
        </>
      )}

      {error ? (
        <p style={{ margin: 0, color: "#b91c1c", fontSize: ".9rem" }}>{error}</p>
      ) : null}
      {success ? (
        <p style={{ margin: 0, color: "#166534", fontSize: ".9rem" }}>{success}</p>
      ) : null}
    </form>
  );
}
