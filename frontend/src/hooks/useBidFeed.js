import { useEffect, useRef, useState } from "react";

import { getListingBids } from "../api/auctions.js";
import { useWebSocket } from "./useWebSocket.js";

export function useBidFeed(listingId) {
  const [bids, setBids] = useState([]);
  const intervalRef = useRef(null);
  const { lastMessage, usingPoll } = useWebSocket(listingId ? `/ws/auctions/${listingId}/` : null);

  async function fetchBids() {
    try {
      const data = await getListingBids(listingId);
      setBids(data);
    } catch {
      // silently ignore polling errors
    }
  }

  // Initial load
  useEffect(() => {
    if (!listingId) return;
    fetchBids();
  }, [listingId]);

  // When a bid_placed WebSocket message arrives, re-fetch the full ordered list
  useEffect(() => {
    if (!lastMessage || lastMessage.event !== "bid_placed") return;
    fetchBids();
  }, [lastMessage]);

  // Only poll when WebSocket has fallen back
  useEffect(() => {
    if (!listingId || !usingPoll) return;
    intervalRef.current = setInterval(fetchBids, 5000);
    return () => clearInterval(intervalRef.current);
  }, [listingId, usingPoll]);

  return { bids, lastMessage, usingPoll, refresh: fetchBids };
}
