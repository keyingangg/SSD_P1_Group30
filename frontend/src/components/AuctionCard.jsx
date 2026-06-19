import { Link } from "react-router-dom";

import CountdownTimer from "./CountdownTimer.jsx";

// Compact listing summary used in the listings grid.
export default function AuctionCard({ listing }) {
  const imageUrl = listing.image_key ? `/images/${listing.image_key}` : null;

  return (
    <Link to={`/listings/${listing.id}`} style={{ textDecoration: "none", color: "inherit" }}>
      <div className="auction-card">
        {imageUrl && (
          <div
            className="auction-card-image"
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              overflow: "hidden",
              minHeight: 80,
            }}
          >
            <img
              src={imageUrl}
              alt={listing.title}
              style={{ maxWidth: "100%", height: "auto", objectFit: "contain" }}
            />
          </div>
        )}
        <div className="auction-card-content">
          <h3>{listing.title}</h3>
          <div className="auction-card-price">
            <span className="label">Current bid:</span>
            <span className="price">${listing.current_highest_bid || listing.starting_price}</span>
          </div>
          <CountdownTimer endsAt={listing.ends_at} />
        </div>
      </div>
    </Link>
  );
}
