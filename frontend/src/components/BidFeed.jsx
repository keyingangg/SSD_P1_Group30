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
  const { bids: fetchedBids } = useBidFeed(bidsProp == null ? listingId : null);
  const bids = bidsProp ?? fetchedBids;

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
          {bids.slice(0, 5).map((bid, i) => {
            const isWinner = isClosed && i === 0;
            const isHighest = !isClosed && i === 0;
            const isTop = isWinner || isHighest;
            return (
              <div key={bid.id ?? i} className={`ld-bid-row${isTop ? " ld-bid-row--top" : ""}`}>
                <span className={`ld-bid-row-rank${isTop ? " top" : ""}`}>
                  #{bids.length - i}
                </span>
                <span className="ld-bid-row-name">{bid.anonymous_identifier ?? bid.bidder ?? "—"}</span>
                {isWinner && <span className="ld-bid-row-badge ld-bid-row-badge--winner">Winner</span>}
                {isHighest && <span className="ld-bid-row-badge ld-bid-row-badge--highest">Highest</span>}
                <span className={`ld-bid-row-amount${isTop ? " top" : ""}`}>
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
          Live updates via WebSocket · Fallback: REST polling every 5s
        </p>
      )}
    </div>
  );
}
