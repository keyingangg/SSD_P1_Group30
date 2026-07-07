import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { getListingDetail } from "../../api/auctions.js";
import AuctionExtendedDetails from "../common/AuctionExtendedDetails.jsx";
import BidFeed from "../bid/BidFeed.jsx";
import BidForm from "../bid/BidForm.jsx";
import CountdownTimer from "../common/CountdownTimer.jsx";
import { useAuth } from "../../context/AuthContext.jsx";
import { useBidFeed } from "../../hooks/useBidFeed.js";
import "../../styles/listing-detail.css";

function formatSGD(value) {
  const n = Number(value);
  if (!n || Number.isNaN(n)) return "-";
  return `S$${n.toLocaleString("en-SG", { minimumFractionDigits: 0 })}`;
}

function formatDateTime(value) {
  if (!value) return "";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "";
  const date = d.toLocaleString("en-SG", {
    timeZone: "Asia/Singapore",
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
  return `${date} SGT`;
}

export default function ListingDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const isAdmin = user?.is_staff === true;
  const [listing, setListing] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [rejectedMinBid, setRejectedMinBid] = useState(null);
  const [conflictMinBid, setConflictMinBid] = useState(null);
  const [nowMs, setNowMs] = useState(() => Date.now());
  const closeSyncRef = useRef(false);
  const storageKey = `bid_placed_${id}`;
  const [lastPlacedBid, setLastPlacedBid] = useState(() => {
    const saved = localStorage.getItem(storageKey);
    return saved ? Number(saved) : null;
  });
  const { bids, lastMessage, isPolling } = useBidFeed(id);

  const refreshListing = useCallback(async () => {
    const data = await getListingDetail(id);
    setListing(data);
    return data;
  }, [id]);

  function handleBidPlaced(amount) {
    localStorage.setItem(storageKey, amount);
    setLastPlacedBid(amount);
    refreshListing();
  }

  // Dismiss the banner when someone else bids higher
  useEffect(() => {
    if (!lastPlacedBid || bids.length === 0) return;
    const topBid = Number(bids[0]?.amount);
    if (topBid > lastPlacedBid) {
      localStorage.removeItem(storageKey);
      setLastPlacedBid(null);
    }
  }, [bids]);

  useEffect(() => {
    let active = true;
    async function load() {
      setLoading(true);
      setError("");
      try {
        const data = await refreshListing();
        if (active) setListing(data);
      } catch (err) {
        if (!active) return;
        setError(err?.response?.data?.detail || "Could not load listing.");
      } finally {
        if (active) setLoading(false);
      }
    }
    load();
    return () => { active = false; };
  }, [id, refreshListing]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setNowMs(Date.now());
    }, 1000);

    return () => window.clearInterval(timer);
  }, []);

  // Handle incoming WebSocket messages
  useEffect(() => {
    if (!lastMessage) return;
    if (lastMessage.event === "bid_placed") {
      // Update price immediately without a round-trip
      setListing(prev => prev ? {
        ...prev,
        current_highest_bid: lastMessage.current_highest_bid ?? prev.current_highest_bid,
      } : prev);
    } else if (lastMessage.event === "auction_cancelled" || lastMessage.event === "auction_ended") {
      // Status change — fetch the full updated listing
      refreshListing();
    }
  }, [lastMessage]);

  // Fallback: poll listing + bids every 5 s when WebSocket is unavailable
  useEffect(() => {
    if (!id || !isPolling) return;
    const interval = setInterval(refreshListing, 5000);
    return () => clearInterval(interval);
  }, [id, isPolling]);

  const runtimeStatus = String(listing?.status || "").toLowerCase();
  const displayStatus = String(listing?.display_status || "").toLowerCase();
  const startsAtMs = listing?.starts_at ? new Date(listing.starts_at).getTime() : NaN;
  const endsAtMs = listing?.ends_at ? new Date(listing.ends_at).getTime() : NaN;

  const isClosed =
    runtimeStatus === "ended" ||
    runtimeStatus === "cancelled" ||
    (Number.isFinite(endsAtMs) && nowMs >= endsAtMs);

  const isLive =
    !isClosed &&
    (runtimeStatus === "active" || displayStatus === "live now" ||
      (Number.isFinite(startsAtMs) && Number.isFinite(endsAtMs) && startsAtMs <= nowMs && nowMs < endsAtMs));

  const category = listing?.category || null;
  const latestLiveBidAmount = Number(bids[0]?.amount);
  const hasLatestLiveBid = Number.isFinite(latestLiveBidAmount) && latestLiveBidAmount > 0;
  const currentBid = hasLatestLiveBid
    ? latestLiveBidAmount
    : (listing?.current_highest_bid || listing?.starting_price);
  const listingForBidForm = listing
    ? { ...listing, current_highest_bid: currentBid }
    : listing;

  // Closed-state user context — populated if the backend returns these fields
  const userWon = listing?.user_won === true;
  const userHighestBid = Number(listing?.user_highest_bid || 0);
  const userParticipated = userHighestBid > 0 || userWon;
  const bidCount = listing?.bid_count ?? null;
  const winnerDiff = userParticipated && !userWon && currentBid
    ? Number(currentBid) - userHighestBid
    : 0;

  const transportStatus = isPolling ? "Offline" : "";

  useEffect(() => {
    if (!Number.isFinite(endsAtMs)) {
      closeSyncRef.current = false;
      return;
    }

    if (nowMs < endsAtMs) {
      closeSyncRef.current = false;
      return;
    }

    if (closeSyncRef.current) return;
    if (runtimeStatus === "ended" || runtimeStatus === "cancelled") {
      closeSyncRef.current = true;
      return;
    }

    closeSyncRef.current = true;
    refreshListing().catch(() => {
      closeSyncRef.current = false;
    });
  }, [endsAtMs, nowMs, refreshListing, runtimeStatus]);

  useEffect(() => {
    const handleOnline = () => {
      refreshListing().catch(() => {
        /* keep existing UI until next successful sync */
      });
    };

    window.addEventListener("online", handleOnline);
    return () => window.removeEventListener("online", handleOnline);
  }, [refreshListing]);

  useEffect(() => {
    if (!isClosed) return;

    localStorage.removeItem(storageKey);
    setLastPlacedBid(null);
    setRejectedMinBid(null);
    setConflictMinBid(null);
  }, [isClosed, storageKey]);

  return (
    <main className="ld-page">
      {/* Breadcrumb */}
      <nav className="ld-breadcrumb">
        <Link to="/auctions">Auctions</Link>
        {category && (
          <>
            <span className="ld-breadcrumb-sep">›</span>
            <Link to={`/auctions?category=${encodeURIComponent(category)}`}>{category}</Link>
          </>
        )}
        {listing?.title && (
          <>
            <span className="ld-breadcrumb-sep">›</span>
            <span>{listing.title}</span>
          </>
        )}
      </nav>

      {loading && <p style={{ opacity: 0.65 }}>Loading listing…</p>}
      {error && <p className="admin-error-text">{error}</p>}

      {!loading && !error && listing && (
        <>
          {/* Header */}
          <div className="ld-header">
<h1 className="ld-header-title">{listing.title || "Untitled Item"}</h1>
            {isClosed && <span className="ld-closed-badge">{runtimeStatus === "cancelled" ? "Cancelled" : "Closed"}</span>}
            {isLive && (
              <span className="ld-live-badge">
                <span className="ld-live-dot" />
                Live
              </span>
            )}
          </div>

          {/* Body */}
          <div className="ld-body">
            <AuctionExtendedDetails listing={listing} />

            {/* Right panel */}
            <div className="ld-right">
              {/* Bid placed banner */}
              {lastPlacedBid && !rejectedMinBid && !isAdmin && !isClosed && (
                <div className="ld-bid-placed-banner">
                  <div className="ld-bid-placed-icon">✓</div>
                  <div className="ld-bid-placed-tag">BID PLACED</div>
                  <div className="ld-bid-placed-title">
                    Your bid of {formatSGD(lastPlacedBid)} is now the highest
                  </div>
                  <div className="ld-bid-placed-desc">
                    All other bidders have been notified · Live update sent via WebSocket
                  </div>
                  <div className="ld-bid-placed-divider" />
                  <div className="ld-bid-placed-row">
                    <span>Current leading bid:</span>
                    <span className="ld-bid-placed-row-amount">{formatSGD(lastPlacedBid)}</span>
                  </div>
                </div>
              )}

              {/* Bid conflict banner (HTTP 409 — race condition) */}
              {conflictMinBid && !isClosed && (
                <div className="ld-bid-conflict-banner">
                  <div className="ld-bid-conflict-icon">!</div>
                  <div className="ld-bid-conflict-tag">BID CONFLICT</div>
                  <div className="ld-bid-conflict-title">Your Bid Was Not Placed</div>
                  <div className="ld-bid-conflict-desc">
                    Another bid was server-recorded at the same time. The price has been updated — please review and try again.
                  </div>
                  <div className="ld-bid-conflict-divider" />
                  <div className="ld-bid-conflict-min">
                    <span>Minimum valid bid:</span>
                    <span className="ld-bid-conflict-min-amount">{formatSGD(conflictMinBid)}</span>
                  </div>
                </div>
              )}

              {/* Bid rejected banner */}
              {rejectedMinBid && !isClosed && (
                <div className="ld-bid-rejected-banner">
                  <div className="ld-bid-rejected-icon">!</div>
                  <div className="ld-bid-rejected-tag">BID REJECTED</div>
                  <div className="ld-bid-rejected-title">Bid Amount Too Low</div>
                  <div className="ld-bid-rejected-desc">
                    Your bid must exceed the current highest bid by the minimum increment.
                  </div>
                  <div className="ld-bid-rejected-divider" />
                  <div className="ld-bid-rejected-min">
                    <span>Minimum valid bid:</span>
                    <span className="ld-bid-rejected-min-amount">{formatSGD(rejectedMinBid)}</span>
                  </div>
                </div>
              )}

              {/* ── CANCELLED STATE (outside grey panel) ── */}
              {runtimeStatus === "cancelled" && (
                <>
                  <div className="ld-status-bar">
                    <span className="ld-status-closed">
                      <span className="ld-status-dot-grey" />
                      Auction Cancelled
                    </span>
                  </div>
                  <div className="ld-cancelled-banner">
                    <div className="ld-cancelled-icon">✕</div>
                    <p className="ld-cancelled-tag">Auction Cancelled</p>
                    <p className="ld-cancelled-title">This lot has been withdrawn</p>
                    <p className="ld-cancelled-desc">This auction was cancelled by the organiser. All bids have been voided and no charges apply.</p>
                  </div>
                  <a href="/auctions" className="ld-cta-btn" style={{ marginTop: "1rem", display: "block" }}>Browse Similar Lots</a>
                </>
              )}

              <div className="ld-panel">

                {/* ── CLOSED STATE ── */}
                {isClosed && runtimeStatus !== "cancelled" ? (
                  <>
                    {/* Status bar */}
                    <div className="ld-status-bar">
                      <span className="ld-status-closed">
                        <span className="ld-status-dot-grey" />
                        Auction Closed
                      </span>
                      {listing.ends_at && (
                        <>
                          <span className="ld-status-sep">·</span>
                          <span className="ld-status-info">{formatDateTime(listing.ends_at)}</span>
                        </>
                      )}
                    </div>

                    <>
                        {/* Hammer price */}
                        <div className="ld-panel-section">
                          <div className="ld-bid-label">Hammer Price</div>
                          <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: "1rem" }}>
                            <div className="ld-bid-number">{formatSGD(currentBid)}</div>
                            {bidCount !== null && (
                              <div className="ld-bid-count">{bidCount} bids placed</div>
                            )}
                          </div>
                        </div>

                        {/* User-specific banner */}
                        {userWon && (
                          <div className="ld-panel-section">
                            <div className="ld-banner-win">
                              <span className="ld-banner-win-dot" />
                              <span>
                                Congratulations — you placed the winning bid of {formatSGD(currentBid)}.
                                Complete checkout to claim this lot within 72 hours.
                              </span>
                            </div>
                            <div style={{ marginTop: 14 }}>
                              <a href="#checkout" className="ld-cta-btn">Proceed to Checkout →</a>
                              <p className="ld-cta-note">Payment must be completed within 72 hours of auction close</p>
                              <a href="/auctions" className="ld-cta-link">Browse Similar Lots</a>
                            </div>
                          </div>
                        )}

                        {userParticipated && !userWon && (
                          <div className="ld-panel-section">
                            <div className="ld-banner-outbid">
                              <span className="ld-banner-outbid-dot" />
                              <span>
                                You were outbid. Your final offer of {formatSGD(userHighestBid)} did not win this lot.
                                The hammer price was {formatSGD(currentBid)}.
                              </span>
                            </div>
                            <div className="ld-your-bid-section">
                              <div className="ld-your-bid-label-sm">Your Highest Bid</div>
                              <div className="ld-your-bid-row">
                                <span className="ld-your-bid-number">{formatSGD(userHighestBid)}</span>
                                {winnerDiff > 0 && (
                                  <span className="ld-your-bid-note">Winning bid was {formatSGD(winnerDiff)} higher</span>
                                )}
                              </div>
                            </div>
                            <div style={{ marginTop: 14 }}>
                              <a href="/auctions" className="ld-cta-btn">Browse Similar Lots</a>
                              <p className="ld-cta-note">Discover other lots in {category || "Auctions"} matching your interest</p>
                            </div>
                          </div>
                        )}

                        {!userParticipated && (
                          <div className="ld-panel-section">
                            <a href="/auctions" className="ld-cta-btn">Browse Similar Lots</a>
                          </div>
                        )}

                        {/* Final bid history */}
                        <div className="ld-panel-section">
                          <div className="ld-history-header">
                            <span className="ld-history-title">Final Bid History</span>
                            <span className="ld-history-note">All bids are final</span>
                          </div>
                          <BidFeed listingId={id} isClosed={isClosed} userHighestBid={userHighestBid} />
                        </div>
                    </>
                  </>
                ) : !isClosed ? (
                  /* ── LIVE / UPCOMING STATE ── */
                  <>
                    {/* Status bar */}
                    <div className={`ld-status-bar${isLive ? " ld-status-bar--live" : ""}`}>
                      {isLive ? (
                        <>
                          <span className="ld-status-live">
                            <span className="ld-status-dot" />
                            Auction Live
                          </span>
                          <span className="ld-status-sep">·</span>
                          <span className="ld-status-info" style={{ color: isPolling ? "#b8a04a" : "#3a7d55" }}>{isPolling ? "Polling (5s)" : "Live updates"}</span>
                        </>
                      ) : (
                        <>
                          <span className="ld-status-upcoming">
                            <span className="ld-status-dot-gold" />
                            Upcoming
                          </span>
                          <span className="ld-status-sep">·</span>
                          <span className="ld-status-info">Bidding not yet open</span>
                        </>
                      )}
                    </div>

                    {/* Estimate */}
                    {listing.starting_price && (
                      <div className="ld-panel-section">
                        <span className="ld-estimate">
                          Estimate: <span>{formatSGD(listing.starting_price)}</span>
                          {listing.estimate_high && <> — <span>{formatSGD(listing.estimate_high)}</span></>}
                        </span>
                      </div>
                    )}

                    {/* Countdown */}
                    <div className="ld-panel-section ld-countdown-section">
                      <div className="ld-countdown-label">
                        {isLive ? "Auction Closes In" : "Auction Opens In"}
                      </div>
                      <CountdownTimer
                        startsAt={listing.starts_at}
                        endsAt={listing.ends_at}
                        preStartDisplay="countdown"
                        segmented
                      />
                    </div>

                    {isLive ? (
                      <>
                        {/* Current highest bid */}
                        <div className="ld-panel-section">
                          <div className="ld-bid-label">Current Highest Bid</div>
                          <div className="ld-bid-number">{formatSGD(currentBid)}</div>
                          {listing.minimum_increment && (
                            <div className="ld-bid-meta">
                              <span>Minimum next bid: {formatSGD(Number(currentBid || 0) + Number(listing.minimum_increment))}</span>
                              <span className="ld-bid-meta-sep">·</span>
                              <span>Increment: {formatSGD(listing.minimum_increment)}</span>
                            </div>
                          )}
                        </div>

                        {/* Bid form — hidden for admins */}
                        {!isAdmin && (
                          <div className="ld-panel-section">
                            <BidForm
                              listingId={id}
                              listing={listingForBidForm}
                              onBidPlaced={(amt) => { setRejectedMinBid(null); setConflictMinBid(null); handleBidPlaced(amt); }}
                              onBidRejected={(minBid) => { setConflictMinBid(null); setRejectedMinBid(minBid); }}
                              onBidConflict={(minBid) => { setRejectedMinBid(null); setConflictMinBid(minBid); refreshListing(); }}
                            />
                          </div>
                        )}

                        {/* Live bid history */}
                        <div className="ld-panel-section">
                          <BidFeed bids={bids} isClosed={false} userHighestBid={0} />
                        </div>
                      </>
                    ) : (
                      <>
                        {/* Starting bid */}
                        <div className="ld-panel-section">
                          <div className="ld-bid-label">Starting Bid</div>
                          <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: "1rem" }}>
                            <div className="ld-bid-number">{formatSGD(listing.starting_price)}</div>
                            {listing.minimum_increment && (
                              <div className="ld-bid-count">Bid increment: {formatSGD(listing.minimum_increment)}</div>
                            )}
                          </div>
                        </div>

                        {/* Opens info banner */}
                        {listing.starts_at && (
                          <div className="ld-panel-section">
                            <div className="ld-banner-upcoming">
                              <span className="ld-banner-upcoming-dot" />
                              <span>
                                Bidding opens {formatDateTime(listing.starts_at)}.<br />
                                Add to Watchlist to be notified when this lot opens.
                              </span>
                            </div>
                          </div>
                        )}

                        {/* Lot schedule */}
                        <div className="ld-panel-section">
                          <div className="ld-schedule-card">
                            <div className="ld-schedule-title">Lot Schedule</div>
                            <hr className="ld-schedule-divider" />
                            <div className="ld-schedule-table">
                              {listing.starts_at && (
                                <><span className="ld-schedule-label">Opens</span><span className="ld-schedule-value">{formatDateTime(listing.starts_at)}</span></>
                              )}
                              {listing.ends_at && (
                                <><span className="ld-schedule-label">Closes</span><span className="ld-schedule-value">{formatDateTime(listing.ends_at)}</span></>
                              )}
                              {listing.starting_price && (
                                <><span className="ld-schedule-label">Starting Bid</span><span className="ld-schedule-value">{formatSGD(listing.starting_price)}</span></>
                              )}
                              {listing.minimum_increment && (
                                <><span className="ld-schedule-label">Increment</span><span className="ld-schedule-value">{formatSGD(listing.minimum_increment)}</span></>
                              )}
                              {listing.condition && (
                                <><span className="ld-schedule-label">Condition</span><span className="ld-schedule-value">{listing.condition}</span></>
                              )}
                              <span className="ld-schedule-label">Reserve</span>
                              <span className="ld-schedule-value" style={{ fontWeight: 700 }}>Confidential</span>
                            </div>
                          </div>
                        </div>
                      </>
                    )}
                  </>
                ) : null}
              </div>
            </div>
          </div>
        </>
      )}
    </main>
  );
}
