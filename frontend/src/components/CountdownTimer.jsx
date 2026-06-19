import { useEffect, useMemo, useState } from "react";

function formatRemaining(ms) {
  if (ms <= 0) return "Ended";

  const totalSeconds = Math.floor(ms / 1000);
  const days = Math.floor(totalSeconds / 86400);
  const hours = Math.floor((totalSeconds % 86400) / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  if (days > 0) return `${days}d ${hours}h ${minutes}m ${seconds}s`;
  return `${hours}h ${minutes}m ${seconds}s`;
}

// Displays a live countdown to the auction end time.
export default function CountdownTimer({ endsAt }) {
  const targetMs = useMemo(() => {
    const parsed = endsAt ? new Date(endsAt).getTime() : NaN;
    return Number.isNaN(parsed) ? null : parsed;
  }, [endsAt]);

  const [now, setNow] = useState(Date.now());

  useEffect(() => {
    if (!targetMs) return undefined;

    const timer = setInterval(() => {
      setNow(Date.now());
    }, 1000);

    return () => clearInterval(timer);
  }, [targetMs]);

  if (!targetMs) {
    return <span className="countdown">-</span>;
  }

  const remaining = targetMs - now;
  return <span className="countdown">{formatRemaining(remaining)}</span>;
}
