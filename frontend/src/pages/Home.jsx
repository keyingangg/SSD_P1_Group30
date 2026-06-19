import { useState, useEffect } from "react";
import { getListings } from "../api/auctions.js";
import AuctionCard from "../components/AuctionCard.jsx";
import { getCategoryOptions } from "../config/categories.js";

const CATEGORIES = ["All", ...getCategoryOptions()];

const SIDEBAR = {
  Status: ["All", "Live Now", "Opening soon"],
  Category: ["All", ...getCategoryOptions()],
  Estimate: ["Under S$5,000", "S$5k — S$20k", "S$20k — S$100k", "Over S$100k"],
};

const STATUS_FILTER_VALUES = {
  All: "All",
  "Live Now": "active",
  "Opening soon": "scheduled",
};

export default function Home() {
  const [listings, setListings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeCategory, setActiveCategory] = useState("All");
  const [search, setSearch] = useState("");
  const [sidebarStatus, setSidebarStatus] = useState("All");
  const [sidebarCategory, setSidebarCategory] = useState("All");

  useEffect(() => {
    getListings().then(setListings).catch(console.error).finally(() => setLoading(false));
  }, []);

  const visible = listings.filter((l) => {
    const matchSearch = l.title.toLowerCase().includes(search.toLowerCase());
    const matchSidebarStatus =
      sidebarStatus === "All" || String(l.status || "").toLowerCase() === sidebarStatus.toLowerCase();
    const matchSidebarCategory =
      sidebarCategory === "All" || String(l.category || "").toLowerCase() === sidebarCategory.toLowerCase();
    return matchSearch && matchSidebarStatus && matchSidebarCategory;
  });

  return (
    <>
      <div className="cat-header">
        <p className="cat-eyebrow">Auction Catalogue · {visible.length} Listings</p>
        <h1 className="cat-title">Auction Catalogue</h1>

        <div className="cat-controls">
          <input
            className="cat-search"
            placeholder="Search by brand, item, listing number..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <div className="cat-tabs">
            {CATEGORIES.map((c) => (
              <button
                key={c}
                type="button"
                className={`cat-tab${activeCategory === c ? " active" : ""}`}
                onClick={() => {
                  setActiveCategory(c);
                  setSidebarCategory(c);
                }}
              >
                {c === "All" ? "All Listings" : c}
              </button>
            ))}
          </div>
          <select className="cat-sort">
            <option>Ending soonest</option>
            <option>Highest bid</option>
            <option>Lowest estimate</option>
            <option>Most bids</option>
          </select>
        </div>
      </div>

      <div className="cat-layout">
        {/* Sidebar */}
        <aside className="cat-sidebar">
          <p className="cat-sidebar-title" style={{ fontSize: ".72rem", letterSpacing: ".1em", opacity: .4, textTransform: "uppercase", marginBottom: "1.25rem" }}>Refine</p>
          {Object.entries(SIDEBAR).map(([group, options]) => (
            <div className="cat-sidebar-section" key={group}>
              <p className="cat-sidebar-title">{group}</p>
              {options.map((opt) => (
                <label className="cat-filter-option" key={opt}>
                  <input
                    type="radio"
                    name={group}
                    checked={
                      group === "Category"
                        ? sidebarCategory === opt
                        : group === "Status"
                          ? sidebarStatus === (STATUS_FILTER_VALUES[opt] || opt)
                          : false
                    }
                    onChange={() => {
                      if (group === "Category") setSidebarCategory(opt);
                      if (group === "Status") setSidebarStatus(STATUS_FILTER_VALUES[opt] || opt);
                    }}
                  />
                  <span>{opt}</span>
                </label>
              ))}
            </div>
          ))}
        </aside>

        {/* Grid */}
        <div>
          <div className="cat-grid">
            {loading ? (
              <p style={{ padding: "3rem", textAlign: "center", opacity: 0.5 }}>Loading listings…</p>
            ) : visible.length > 0 ? (
              visible.map((listing) => (
                <AuctionCard key={listing.id} listing={listing} />
              ))
            ) : (
              <p style={{ padding: "3rem", textAlign: "center", opacity: 0.5 }}>
                No listings match your search.
              </p>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
