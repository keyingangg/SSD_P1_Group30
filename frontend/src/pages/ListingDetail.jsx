import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { getListingDetail } from "../api/auctions.js";
import AuctionExtendedDetails from "../components/AuctionExtendedDetails.jsx";
import BidFeed from "../components/BidFeed.jsx";
import BidForm from "../components/BidForm.jsx";

// Single listing view: details, live bid feed, bid form, and countdown.
export default function ListingDetail() {
  const { id } = useParams();
  const [listing, setListing] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function refreshListing() {
    const data = await getListingDetail(id);
    setListing(data);
  }

  useEffect(() => {
    let active = true;

    async function load() {
      setLoading(true);
      setError("");
      try {
        const data = await getListingDetail(id);
        if (active) setListing(data);
      } catch (err) {
        if (!active) return;
        const message = err?.response?.data?.detail || "Could not load listing.";
        setError(message);
      } finally {
        if (active) setLoading(false);
      }
    }

    load();
    return () => {
      active = false;
    };
  }, [id]);

  return (
    <main style={{ padding: "1.25rem", display: "grid", gap: "1rem" }}>
      <div>
        <Link
          to="/auctions"
          style={{
            display: "inline-block",
            textDecoration: "none",
            color: "var(--ink)",
            border: "none",
            borderRadius: 0,
            padding: ".45rem .75rem",
            background: "transparent",
            fontSize: ".9rem",
          }}
        >
          Back to Auctions
        </Link>
      </div>
      {loading ? <p>Loading listing details...</p> : null}
      {error ? <p className="admin-error-text">{error}</p> : null}
      {!loading && !error ? <AuctionExtendedDetails listing={listing} /> : null}
      <BidFeed listingId={id} />
      <BidForm listingId={id} listing={listing} onSubmit={refreshListing} />
    </main>
  );
}
