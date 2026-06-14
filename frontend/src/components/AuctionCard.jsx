import { Link } from "react-router-dom";

import CountdownTimer from "./CountdownTimer.jsx";

// Compact listing summary used in the listings grid.
export default function AuctionCard({ listing }) {
  // TODO: render title, current highest bid, countdown, and link to detail.
  return (
    <div className="auction-card">
      {/* TODO */}
      <Link to={listing ? `/listings/${listing.id}` : "#"}>View</Link>
    </div>
  );
}
