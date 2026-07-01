import { useBidFeed } from "../hooks/useBidFeed.js";

export function timeAgo(timestamp) {
  if (!timestamp) return "";
  const diffMs = Date.now() - new Date(timestamp).getTime();
  const diffSec = Math.floor(diffMs / 1000);
  if (diffSec < 10) return "now";
  if (diffSec < 60) return `${diffSec}s ago`;
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  return `${Math.floor(diffMin / 60)}h ago`;
}

function formatSGD(n) {
  return `S$${Number(n).toLocaleString("en-SG", { minimumFractionDigits: 0 })}`;
}

export default function BidFeed({ listingId, bids: bidsProp, isClosed = false, userHighestBid = 0 }) {
  const { bids: fetchedBids, readyState } = useBidFeed(bidsProp == null ? listingId : null);
  const bids = bidsProp ?? fetchedBids;
  const liveTransportLabel = readyState === WebSocket.OPEN
    ? "Live updates via WebSocket"
    : "WebSocket reconnecting - fallback: REST polling every 5s";

  return (
    <div>
      {!isClosed && (
        <div className="ld-history-header">
          <span className="ld-history-title">Bid History</span>
          <span className="ld-history-live">
            <span className="ld-history-live-dot" />
            LIVE
          </span>
        </div>
      )}

      {bids.length === 0 ? (
        <p className="ld-history-empty">
          {isClosed ? "No bids were placed." : "No bids yet. Be the first to bid."}
        </p>
      ) : (
        <div className="ld-bid-rows">
          {bids.slice(0, 6).map((bid, i) => {
            const isWinner = isClosed && i === 0;
            const isHighest = !isClosed && i === 0;
            const isTop = isWinner || isHighest;
            const isYourBid = isClosed && !isWinner && userHighestBid > 0 && Number(bid.amount) === userHighestBid;
            return (
              <div key={bid.id ?? i} className={`ld-bid-row${isTop ? " ld-bid-row--top" : ""}${isYourBid ? " ld-bid-row--yours" : ""}`}>
                <span className={`ld-bid-row-rank${isTop ? " top" : ""}`}>
                  #{bids.length - i}
                </span>
                <span className={`ld-bid-row-name${isYourBid ? " yours" : ""}`}>{bid.anonymous_identifier ?? bid.bidder ?? "—"}</span>
                {isWinner && <span className="ld-bid-row-badge ld-bid-row-badge--winner">WINNER</span>}
                {isHighest && <span className="ld-bid-row-badge ld-bid-row-badge--highest">Highest</span>}
                {isYourBid && <span className="ld-bid-row-badge ld-bid-row-badge--yours">YOUR BID</span>}
                <span className={`ld-bid-row-amount${isTop ? " top" : ""}${isYourBid ? " yours" : ""}`}>
                  {formatSGD(bid.amount)}
                </span>
                {!isClosed && (
                  <span className="ld-bid-row-time">{timeAgo(bid.submitted_at)}</span>
                )}
              </div>
            );
          })}
        </div>
      )}

      {!isClosed && (
        <p className="ld-history-footer">
          {liveTransportLabel}
        </p>
      )}
    </div>
  );
}
