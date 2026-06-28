import { useEffect, useRef, useState } from "react";

import { useWebSocket } from "./useWebSocket.js";

const POLL_INTERVAL_MS = 5000;

export function useBidFeed(listingId) {
  const [bids, setBids] = useState([]);
  const { lastMessage, readyState } = useWebSocket(listingId);
  const pollTimer = useRef(null);

  // Append new WebSocket messages to the bid list.
  useEffect(() => {
    if (lastMessage) {
      setBids((prev) => [lastMessage, ...prev]);
    }
  }, [lastMessage]);

  // REST polling fallback when WebSocket is unavailable.
  useEffect(() => {
    if (readyState === WebSocket.OPEN || !listingId) return;

    const poll = async () => {
      try {
        const res = await fetch(`/api/auctions/${listingId}/`);
        if (!res.ok) return;
        const data = await res.json();
        if (data.current_highest_bid) {
          setBids((prev) => {
            const latest = prev[0];
            if (latest && latest.current_highest_bid === String(data.current_highest_bid)) {
              return prev;
            }
            return [
              {
                listing_id: String(data.id),
                current_highest_bid: String(data.current_highest_bid),
                submitted_at: new Date().toISOString(),
              },
              ...prev,
            ];
          });
        }
      } catch {
        /* network error — retry next interval */
      }
    };

    poll();
    pollTimer.current = setInterval(poll, POLL_INTERVAL_MS);
    return () => clearInterval(pollTimer.current);
  }, [readyState, listingId]);

  return { bids, readyState };
}
