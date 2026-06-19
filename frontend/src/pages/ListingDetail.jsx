import { useParams } from "react-router-dom";

import BidFeed from "../components/BidFeed.jsx";
import BidForm from "../components/BidForm.jsx";
import CountdownTimer from "../components/CountdownTimer.jsx";

// Single listing view: details, live bid feed, bid form, and countdown.
export default function ListingDetail() {
  const { id } = useParams();

  // TODO: fetch listing detail via getListingDetail(id).
  return (
    <main>
      {/* TODO: listing details */}
      <CountdownTimer endsAt={null} />
      <BidFeed listingId={id} />
      <BidForm listingId={id} />
    </main>
  );
}
