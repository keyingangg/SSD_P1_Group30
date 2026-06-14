import { useEffect, useRef, useState } from "react";

// Establishes a WebSocket connection for a listing's live bid feed.
export function useWebSocket(listingId) {
  const [lastMessage, setLastMessage] = useState(null);
  const socketRef = useRef(null);

  useEffect(() => {
    // TODO: open ws connection to /ws/auctions/<listingId>/,
    // handle onmessage -> setLastMessage, and reconnect on close.
    return () => {
      // TODO: close socket on unmount.
    };
  }, [listingId]);

  return { lastMessage, socket: socketRef.current };
}
