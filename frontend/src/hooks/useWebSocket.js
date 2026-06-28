import { useEffect, useRef, useState, useCallback } from "react";

const NON_RETRIABLE_CODES = [4001, 4003, 4004];
const RECONNECT_DELAY_MS = 3000;

export function useWebSocket(listingId) {
  const [lastMessage, setLastMessage] = useState(null);
  const [readyState, setReadyState] = useState(WebSocket.CONNECTING);
  const socketRef = useRef(null);
  const reconnectTimer = useRef(null);

  const connect = useCallback(() => {
    if (!listingId) return;

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${protocol}//${window.location.host}/ws/auctions/${listingId}/`;
    const ws = new WebSocket(url);
    socketRef.current = ws;

    ws.onopen = () => setReadyState(WebSocket.OPEN);

    ws.onmessage = (e) => {
      try {
        setLastMessage(JSON.parse(e.data));
      } catch {
        /* ignore malformed frames */
      }
    };

    ws.onclose = (e) => {
      setReadyState(WebSocket.CLOSED);
      socketRef.current = null;
      if (!NON_RETRIABLE_CODES.includes(e.code)) {
        reconnectTimer.current = setTimeout(connect, RECONNECT_DELAY_MS);
      }
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [listingId]);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimer.current);
      if (socketRef.current) socketRef.current.close();
    };
  }, [connect]);

  return { lastMessage, readyState, socket: socketRef.current };
}
