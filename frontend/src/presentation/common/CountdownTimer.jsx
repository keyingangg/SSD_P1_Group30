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
// Pass segmented={true} to render structured d/h/m/s segments instead of plain text.
export default function CountdownTimer({ startsAt, endsAt, preStartDisplay = "scheduled", segmented = false }) {
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

    // Before auction start: tick every second if showing a live countdown,
    // otherwise just wake up once when the auction starts.
    if (startMs && isBeforeStart) {
      if (preStartDisplay === "countdown") {
        timer = setInterval(() => {
          setNow(Date.now());
        }, 1000);
      } else {
        const delay = Math.max(startMs - currentNow, 0);
        startTimer = setTimeout(() => {
          setNow(Date.now());
        }, delay);
      }

      return () => {
        if (timer) clearInterval(timer);
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
    if (segmented) return <SegmentedCountdown days={0} hours={0} minutes={0} seconds={0} label="-" />;
    return <span className="countdown">-</span>;
  }

  if (startMs && now < startMs) {
    if (preStartDisplay === "countdown") {
      if (segmented) {
        return <SegmentedCountdown {...msToSegs(startMs - now)} />;
      }
      return <span className="countdown">Opening in {formatDuration(startMs - now)}</span>;
    }
    if (segmented) return <SegmentedCountdown days={0} hours={0} minutes={0} seconds={0} label="Scheduled" />;
    return <span className="countdown">Scheduled</span>;
  }

  if (now >= endMs) {
    if (segmented) return <SegmentedCountdown days={0} hours={0} minutes={0} seconds={0} label="Ended" />;
    return <span className="countdown">Ended</span>;
  }

  const remaining = endMs - now;
  if (segmented) return <SegmentedCountdown {...msToSegs(remaining)} />;
  return <span className="countdown">Ends in {formatRemaining(remaining)}</span>;
}

function msToSegs(ms) {
  const totalSeconds = Math.floor(Math.max(ms, 0) / 1000);
  return {
    days: Math.floor(totalSeconds / 86400),
    hours: Math.floor((totalSeconds % 86400) / 3600),
    minutes: Math.floor((totalSeconds % 3600) / 60),
    seconds: totalSeconds % 60,
  };
}

function pad(n) { return String(n).padStart(2, "0"); }

function SegmentedCountdown({ days, hours, minutes, seconds, label }) {
  if (label) {
    return (
      <div className="ld-countdown-segs">
        <span className="ld-seg-num" style={{ fontSize: 18 }}>{label}</span>
      </div>
    );
  }
  return (
    <div className="ld-countdown-segs">
      {days > 0 && (
        <>
          <div className="ld-seg">
            <span className="ld-seg-num">{pad(days)}</span>
            <span className="ld-seg-unit">d</span>
          </div>
          <span className="ld-seg-colon">:</span>
        </>
      )}
      <div className="ld-seg">
        <span className="ld-seg-num">{pad(hours)}</span>
        <span className="ld-seg-unit">h</span>
      </div>
      <span className="ld-seg-colon">:</span>
      <div className="ld-seg">
        <span className="ld-seg-num">{pad(minutes)}</span>
        <span className="ld-seg-unit">m</span>
      </div>
      <span className="ld-seg-colon">:</span>
      <div className="ld-seg">
        <span className="ld-seg-num">{pad(seconds)}</span>
        <span className="ld-seg-unit">s</span>
      </div>
    </div>
  );
}
