import { useBidFeed } from "../hooks/useBidFeed.js";

// Displays the live, anonymised bid feed for a listing.
export default function BidFeed({ listingId }) {
  const { bids } = useBidFeed(listingId);

  // TODO: render anonymised bid updates (e.g. "Bidder #4729 - $1,200").
  return <ul className="bid-feed">{/* TODO */}</ul>;
}
