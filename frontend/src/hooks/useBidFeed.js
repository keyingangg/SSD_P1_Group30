import { useEffect, useRef, useState } from "react";

import { getListingBids } from "../api/auctions.js";

export function useBidFeed(listingId) {
  const [bids, setBids] = useState([]);
  const intervalRef = useRef(null);

  async function fetchBids() {
    try {
      const data = await getListingBids(listingId);
      setBids(data);
    } catch {
      // silently ignore polling errors
    }
  }

  useEffect(() => {
    if (!listingId) return () => {};
    fetchBids();
    intervalRef.current = setInterval(fetchBids, 5000);
    return () => clearInterval(intervalRef.current);
  }, [listingId]);

  return { bids, refresh: fetchBids };
}
