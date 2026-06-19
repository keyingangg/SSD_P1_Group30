import CountdownTimer from "./CountdownTimer.jsx";
import { useState } from "react";

function formatDateTime(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return date.toLocaleString("en-SG", {
    timeZone: "Asia/Singapore",
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  });
}

function formatCurrency(value) {
  const number = Number(value);
  if (Number.isNaN(number)) return "-";
  return `$${number.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function buildImageList(listing) {
  if (!listing || typeof listing !== "object") return [];

  if (Array.isArray(listing.image_urls) && listing.image_urls.length) {
    return listing.image_urls.filter(Boolean);
  }

  if (Array.isArray(listing.images) && listing.images.length) {
    return listing.images.filter(Boolean);
  }

  if (listing.image_url) return [listing.image_url];

  if (listing.image_key) {
    if (/^https?:\/\//i.test(listing.image_key)) return [listing.image_key];
    return [`/images/${listing.image_key}`];
  }

  return [];
}

const DETAIL_ROW_STYLE = {
  display: "flex",
  alignItems: "flex-start",
  justifyContent: "space-between",
  gap: "1rem",
  padding: "0.7rem 0",
  borderBottom: "1px solid rgba(27,26,23,.08)",
};

export default function AuctionExtendedDetails({ listing }) {
  const [showFullDescription, setShowFullDescription] = useState(false);

  if (!listing) {
    return <p style={{ opacity: 0.65 }}>No listing details available.</p>;
  }

  const imageUrls = buildImageList(listing);
  const currentBid = listing.current_highest_bid || listing.starting_price;
  const description = listing.description || "-";
  const canToggleDescription = description !== "-";
  const statusLabel = listing.display_status || listing.status || "-";
  const showStatus = String(statusLabel).toLowerCase() !== "scheduled";

  return (
    <section
      style={{
        display: "grid",
        gap: "1.25rem",
        padding: "0.25rem",
      }}
    >
      <div
        style={{
          display: "grid",
          gap: "1.25rem",
          gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
          alignItems: "start",
        }}
      >
        <div
          style={{
            display: "grid",
            gap: "0.8rem",
            border: "1px solid rgba(27,26,23,.12)",
            borderRadius: 10,
            background: "#fff",
            padding: "0.9rem",
          }}
        >
          {imageUrls.length ? (
            imageUrls.map((url, index) => (
              <div
                key={`${url}-${index}`}
                style={{
                  border: "1px solid rgba(27,26,23,.1)",
                  borderRadius: 8,
                  overflow: "hidden",
                  background: "#f7f7f7",
                }}
              >
                <img
                  src={url}
                  alt={`${listing.title || "Item"} image ${index + 1}`}
                  style={{ width: "100%", height: 260, objectFit: "contain", display: "block" }}
                />
              </div>
            ))
          ) : (
            <p style={{ margin: 0, opacity: 0.65 }}>No images uploaded.</p>
          )}
        </div>

        <div
          style={{
            display: "grid",
            gap: "1rem",
            border: "1px solid rgba(27,26,23,.12)",
            borderRadius: 10,
            background: "#fff",
            padding: "1rem",
          }}
        >
          <header>
            <h2 style={{ margin: 0 }}>{listing.title || "Untitled Item"}</h2>
          </header>

          <div style={{ display: "grid", gap: "0.35rem" }}>
            <span style={{ opacity: 0.7, fontSize: ".9rem" }}>Category</span>
            <strong>{listing.category || "Others"}</strong>
          </div>

          {showStatus ? (
            <div style={{ display: "grid", gap: "0.35rem" }}>
              <span style={{ opacity: 0.7, fontSize: ".9rem" }}>Status</span>
              <strong>{statusLabel}</strong>
            </div>
          ) : null}

          <div style={{ display: "grid", gap: "0.3rem" }}>
            <div
              style={{
                justifySelf: "start",
                border: "none",
                background: "none",
                padding: "0",
                color: "var(--ink)",
                opacity: 0.55,
                fontSize: ".95rem",
                lineHeight: 1.65,
                display: showFullDescription ? "block" : "-webkit-box",
                WebkitLineClamp: showFullDescription ? "unset" : 2,
                WebkitBoxOrient: "vertical",
                overflow: "hidden",
              }}
            >
              {description}
            </div>

            {canToggleDescription ? (
              <button
                type="button"
                onClick={() => setShowFullDescription((prev) => !prev)}
                style={{
                  justifySelf: "start",
                  border: "none",
                  background: "none",
                  padding: "0",
                  cursor: "pointer",
                  color: "var(--ink)",
                  fontSize: "1rem",
                  textDecoration: "underline",
                  textUnderlineOffset: "0.2em",
                }}
              >
                {showFullDescription ? "Read Less" : "Read More"}
              </button>
            ) : null}
          </div>

          <div style={{ display: "grid" }}>
            <div style={DETAIL_ROW_STYLE}>
              <strong>Starts at</strong>
              <div>{formatDateTime(listing.starts_at)}</div>
            </div>

            <div style={DETAIL_ROW_STYLE}>
              <strong>Ends at</strong>
              <div>{formatDateTime(listing.ends_at)}</div>
            </div>

            <div style={DETAIL_ROW_STYLE}>
              <strong>Countdown</strong>
              <div>
                <CountdownTimer startsAt={listing.starts_at} endsAt={listing.ends_at} />
              </div>
            </div>

            <div style={DETAIL_ROW_STYLE}>
              <strong>Current highest bid</strong>
              <div>{formatCurrency(currentBid)}</div>
            </div>

            <div style={{ ...DETAIL_ROW_STYLE, borderBottom: "none", paddingBottom: 0 }}>
              <strong>Minimum increment</strong>
              <div>{formatCurrency(listing.minimum_increment)}</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
