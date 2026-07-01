import { useEffect, useRef, useState } from "react";

const RECONNECT_DELAYS = [1000, 2000, 4000]; // 3 attempts before falling back

// path: full WS path, e.g. "/ws/auctions/<id>/" or "/ws/catalogue/"
export function useWebSocket(path) {
  const [lastMessage, setLastMessage] = useState(null);
  const [usingPoll, setUsingPoll] = useState(false);
  const socketRef = useRef(null);
  const retriesRef = useRef(0);
  const timerRef = useRef(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    if (!path) return;

    mountedRef.current = true;
    retriesRef.current = 0;
    setUsingPoll(false);

    function connect() {
      if (!mountedRef.current) return;

      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const host = import.meta.env.VITE_WS_HOST || window.location.host;
      const ws = new WebSocket(`${protocol}//${host}${path}`);
      socketRef.current = ws;

      ws.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data);
          if (mountedRef.current) setLastMessage(data);
        } catch {
          // ignore malformed frames
        }
      };

      ws.onclose = () => {
        if (!mountedRef.current) return;
        if (retriesRef.current < RECONNECT_DELAYS.length) {
          const delay = RECONNECT_DELAYS[retriesRef.current++];
          timerRef.current = setTimeout(connect, delay);
        } else {
          // All retries exhausted — fall back to REST polling
          setUsingPoll(true);
        }
      };

      ws.onerror = () => ws.close();
    }

    connect();

    return () => {
      mountedRef.current = false;
      clearTimeout(timerRef.current);
      if (socketRef.current) {
        socketRef.current.onclose = null; // suppress reconnect on intentional unmount
        socketRef.current.close();
      }
    };
  }, [path]);

  return { lastMessage, usingPoll };
}
