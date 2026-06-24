import { useBidFeed } from "../hooks/useBidFeed.js";

function timeAgo(timestamp) {
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

export default function BidFeed({ listingId, isClosed = false, userHighestBid = 0 }) {
  const { bids } = useBidFeed(listingId);

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
          {bids.map((bid, i) => {
            const isWinner = isClosed && i === 0;
            const isYourBid = userHighestBid > 0 && Number(bid.amount) === userHighestBid;
            return (
              <div key={bid.id ?? i} className="ld-bid-row">
                <span className={`ld-bid-row-rank${isWinner ? " winner" : isYourBid ? " yourbid" : ""}`}>
                  #{bids.length - i}
                </span>
                <span className="ld-bid-row-name">{bid.bidder ?? "—"}</span>
                {isWinner && <span className="ld-bid-row-winner">Winner</span>}
                {isYourBid && !isWinner && <span className="ld-bid-row-yourbid">Your Bid</span>}
                <span className={`ld-bid-row-amount${isWinner ? " winner" : isYourBid ? " yourbid" : ""}`}>
                  {formatSGD(bid.amount)}
                </span>
                {!isClosed && (
                  <span className="ld-bid-row-time">{timeAgo(bid.created_at)}</span>
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
