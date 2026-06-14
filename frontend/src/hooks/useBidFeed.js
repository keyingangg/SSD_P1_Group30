import { useState } from "react";

import { useWebSocket } from "./useWebSocket.js";

// Combines the live WebSocket feed with a REST polling fallback so bid
// updates continue even if the socket drops during an active auction.
export function useBidFeed(listingId) {
  const [bids, setBids] = useState([]);
  const { lastMessage } = useWebSocket(listingId);

  // TODO: append/merge lastMessage into bids; if socket is unavailable,
  // poll the REST endpoint at intervals not exceeding 5 seconds.

  return { bids };
}
