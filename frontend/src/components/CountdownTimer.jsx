import { useEffect, useMemo, useState } from "react";

function formatDuration(ms) {
  const safeMs = Math.max(ms, 0);
  const totalSeconds = Math.floor(safeMs / 1000);
  const days = Math.floor(totalSeconds / 86400);
  const hours = Math.floor((totalSeconds % 86400) / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  if (days > 0) return `${days}d ${hours}h ${minutes}m ${seconds}s`;
  return `${hours}h ${minutes}m ${seconds}s`;
}

function formatRemaining(ms) {
  if (ms <= 0) return "Ended";
  return formatDuration(ms);
}

// Displays countdown only while auction is live (between start and end).
export default function CountdownTimer({ startsAt, endsAt, preStartDisplay = "scheduled" }) {
  const startMs = useMemo(() => {
    const parsed = startsAt ? new Date(startsAt).getTime() : NaN;
    return Number.isNaN(parsed) ? null : parsed;
  }, [startsAt]);

  const endMs = useMemo(() => {
    const parsed = endsAt ? new Date(endsAt).getTime() : NaN;
    return Number.isNaN(parsed) ? null : parsed;
  }, [endsAt]);

  const [now, setNow] = useState(Date.now());
  const isBeforeStart = Boolean(startMs && now < startMs);

  useEffect(() => {
    if (!endMs) return undefined;

    let timer;
    let startTimer;
    const currentNow = Date.now();

    // Before auction start: do not run countdown ticks.
    if (startMs && isBeforeStart) {
      const delay = Math.max(startMs - currentNow, 0);
      startTimer = setTimeout(() => {
        setNow(Date.now());
      }, delay);

      return () => {
        if (startTimer) clearTimeout(startTimer);
      };
    }

    timer = setInterval(() => {
      setNow(Date.now());
    }, 1000);

    return () => {
      if (timer) clearInterval(timer);
      if (startTimer) clearTimeout(startTimer);
    };
  }, [startMs, endMs, isBeforeStart]);

  if (!endMs) {
    return <span className="countdown">-</span>;
  }

  if (startMs && now < startMs) {
    if (preStartDisplay === "countdown") {
      return <span className="countdown">Opening in {formatDuration(startMs - now)}</span>;
    }
    return <span className="countdown">Scheduled</span>;
  }

  if (now >= endMs) {
    return <span className="countdown">Ended</span>;
  }

  const remaining = endMs - now;
  return <span className="countdown">Ends in {formatRemaining(remaining)}</span>;
}
