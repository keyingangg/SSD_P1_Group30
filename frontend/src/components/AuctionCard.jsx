import { Link } from "react-router-dom";
import CountdownTimer from "./CountdownTimer.jsx";

const SGD = (n) => n != null ? `S$${Number(n).toLocaleString()}` : null;

function lotNum(id) {
  return "LOT " + String(id).padStart(3, "0");
}

export default function AuctionCard({ listing, index }) {
  const imageUrl = listing.image_key || null;
  const isLive = String(listing.display_status || listing.status || "").toLowerCase() === "active";
  const bid = listing.current_highest_bid || listing.starting_price;
  const house = listing.brand || listing.house || listing.category || "";

  return (
    <Link to={`/listings/${listing.id}`} className="ac-card-link">
      <div className="ac-card">

        {/* Image */}
        <div className="ac-img-wrap">
          {imageUrl
            ? <img src={imageUrl} alt={listing.title} className="ac-img" />
            : <div className="ac-img ac-img-placeholder" />
          }
          <span className="ac-lot-badge">{lotNum(index ?? listing.id)}</span>
          {isLive && (
            <span className="ac-live-badge">
              <span className="ac-live-dot" />LIVE
            </span>
          )}
        </div>

        {/* Body */}
        <div className="ac-body">
          <p className="ac-house">{house.toUpperCase()}</p>
          <h3 className="ac-title">{listing.title}</h3>
          {(listing.estimate_low || listing.estimate_high) && (
            <p className="ac-estimate">
              Est. {SGD(listing.estimate_low)} — {SGD(listing.estimate_high)}
            </p>
          )}
          <div className="ac-rule" />
          <div className="ac-bid-row">
            <div>
              <p className="ac-bid">{SGD(bid)}</p>
              <p className="ac-bid-label">current bid</p>
            </div>
            <div className="ac-time-col">
              <CountdownTimer
                startsAt={listing.starts_at}
                endsAt={listing.ends_at}
                preStartDisplay="countdown"
              />
              <p className="ac-bid-label">remaining</p>
            </div>
          </div>
          <button className="ac-btn">View Lot &amp; Bid</button>
        </div>

      </div>
    </Link>
  );
}
