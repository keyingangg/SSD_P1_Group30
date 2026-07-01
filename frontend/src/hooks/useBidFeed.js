import { useEffect, useRef, useState } from "react";

import { getListingBids } from "../api/auctions.js";
import { useWebSocket } from "./useWebSocket.js";

const POLL_INTERVAL_MS = 5000;

function asBidLike(message) {
  if (!message || typeof message !== "object") return null;

  // Normalised bid_placed event (sent by bid_engine._broadcast_bid)
  if (message.event === "bid_placed" && message.amount != null) {
    return {
      id: message.bid_id ?? message.id,
      anonymous_identifier: message.anonymous_identifier,
      amount: String(message.amount),
      submitted_at: message.submitted_at,
      is_winning: message.is_winning,
    };
  }

  // Legacy fallback: message only carries current_highest_bid
  if (message.current_highest_bid != null) {
    return {
      id: message.bid_id ?? message.id,
      anonymous_identifier: message.anonymous_identifier,
      amount: String(message.current_highest_bid),
      submitted_at: message.submitted_at ?? new Date().toISOString(),
      is_winning: false,
    };
  }

  return null;
}

function upsertBid(prev, bidLike) {
  const next = [bidLike, ...prev];
  const seen = new Set();

  return next.filter((bid) => {
    const key = bid.id ?? `${bid.amount}-${bid.submitted_at}-${bid.anonymous_identifier ?? "anon"}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

export function useBidFeed(listingId) {
  const [bids, setBids] = useState([]);
  const { lastMessage, readyState, reconnectAttempt } = useWebSocket(listingId);
  const pollTimer = useRef(null);
  const isRequestInFlight = useRef(false);

  useEffect(() => {
    setBids([]);
  }, [listingId]);

  const refreshFromRest = async () => {
    if (!listingId || isRequestInFlight.current) return;

    isRequestInFlight.current = true;
    try {
      const data = await getListingBids(listingId);
      if (Array.isArray(data)) {
        setBids(data);
      }
    } catch {
      /* network error - try again on next interval */
    } finally {
      isRequestInFlight.current = false;
    }
  };

  // Initial load
  useEffect(() => {
    if (!listingId) return;
    refreshFromRest();
  }, [listingId]);

  // When a bid_placed WebSocket message arrives, re-fetch the full ordered list
  useEffect(() => {
    refreshFromRest();
  }, [listingId]);

  // Append new WebSocket messages to the bid list.
  useEffect(() => {
    const bidLike = asBidLike(lastMessage);
    if (!bidLike) return;

    setBids((prev) => upsertBid(prev, bidLike));
  }, [lastMessage]);

  // REST polling fallback when WebSocket is unavailable. Interval capped at 5s.
  useEffect(() => {
    if (readyState === WebSocket.OPEN || !listingId) return;

    refreshFromRest();
    pollTimer.current = setInterval(refreshFromRest, POLL_INTERVAL_MS);
    return () => clearInterval(pollTimer.current);
  }, [readyState, listingId]);

  return {
    bids,
    readyState,
    reconnectAttempt,
    isPolling: readyState !== WebSocket.OPEN,
  };
}
