import { useEffect, useRef, useState, useCallback } from "react";

const NON_RETRIABLE_CODES = [4001, 4003, 4004];
const BASE_RECONNECT_DELAY_MS = 1000;
const MAX_RECONNECT_DELAY_MS = 30000;
const MAX_RECONNECT_ATTEMPTS = 5;

export function useWebSocket(path) {
  const [lastMessage, setLastMessage] = useState(null);
  const [readyState, setReadyState] = useState(WebSocket.CLOSED);
  const [reconnectAttempt, setReconnectAttempt] = useState(0);
  const socketRef = useRef(null);
  const reconnectTimer = useRef(null);
  const reconnectAttemptRef = useRef(0);
  const shouldReconnectRef = useRef(true);

  const clearReconnectTimer = useCallback(() => {
    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current);
      reconnectTimer.current = null;
    }
  }, []);

  const scheduleReconnect = useCallback((connectFn) => {
    clearReconnectTimer();
    reconnectAttemptRef.current += 1;
    setReconnectAttempt(reconnectAttemptRef.current);

    const delay = Math.min(
      BASE_RECONNECT_DELAY_MS * 2 ** (reconnectAttemptRef.current - 1),
      MAX_RECONNECT_DELAY_MS,
    );

    reconnectTimer.current = setTimeout(() => {
      connectFn();
    }, delay);
  }, [clearReconnectTimer]);

  const connect = useCallback(() => {
    if (!path) return;
    if (!shouldReconnectRef.current) return;
    if (typeof navigator !== "undefined" && !navigator.onLine) {
      setReadyState(WebSocket.CLOSED);
      return;
    }

    clearReconnectTimer();
    setReadyState(WebSocket.CONNECTING);

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    // Accept either a full path ("/ws/catalogue/") or a bare listing UUID
    const wsPath = path.startsWith("/") ? path : `/ws/auctions/${path}/`;
    const url = `${protocol}//${window.location.host}${wsPath}`;
    const ws = new WebSocket(url);
    socketRef.current = ws;

    ws.onopen = () => {
      reconnectAttemptRef.current = 0;
      setReconnectAttempt(0);
      setReadyState(WebSocket.OPEN);
    };

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
      if (!shouldReconnectRef.current) return;
      if (typeof navigator !== "undefined" && !navigator.onLine) return;
      if (!NON_RETRIABLE_CODES.includes(e.code) && reconnectAttemptRef.current < MAX_RECONNECT_ATTEMPTS) {
        scheduleReconnect(connect);
      }
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [clearReconnectTimer, path, scheduleReconnect]);

  useEffect(() => {
    shouldReconnectRef.current = true;
    connect();

    return () => {
      shouldReconnectRef.current = false;
      clearReconnectTimer();
      if (socketRef.current) {
        socketRef.current.close();
        socketRef.current = null;
      }
      setReadyState(WebSocket.CLOSED);
    };
  }, [clearReconnectTimer, connect]);

  useEffect(() => {
    if (!path) return;

    const handleOffline = () => {
      clearReconnectTimer();
      setReadyState(WebSocket.CLOSED);
      if (socketRef.current) {
        socketRef.current.close();
        socketRef.current = null;
      }
    };

    const handleOnline = () => {
      if (!shouldReconnectRef.current) return;
      if (socketRef.current) return;
      connect();
    };

    window.addEventListener("offline", handleOffline);
    window.addEventListener("online", handleOnline);

    return () => {
      window.removeEventListener("offline", handleOffline);
      window.removeEventListener("online", handleOnline);
    };
  }, [clearReconnectTimer, connect, path]);

  return {
    lastMessage,
    readyState,
    reconnectAttempt,
    socket: socketRef.current,
    usingPoll: readyState !== WebSocket.OPEN,
  };
}
