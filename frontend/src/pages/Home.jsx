import { useState, useEffect } from "react";
import { getListings } from "../api/auctions.js";
import AuctionCard from "../components/AuctionCard.jsx";

const FILTER_TABS = [
  "All Lots",
  "Watches",
  "Handbag",
  "Fine Art & Collectibles",
  "Fashion & Apparel",
  "Accessories",
  "Perfumes",
  "Wines & Spirits",
  "Home Decor & Furniture",
  "Others",
];

const DB_CATEGORIES = [
  "Handbag",
  "Watches",
  "Perfumes",
  "Fashion & Apparel",
  "Accessories",
  "Fine Art & Collectibles",
  "Wines & Spirits",
  "Home Decor & Furniture",
  "Others",
];

const ESTIMATE_RANGES = [
  { label: "Under S$5,000",     min: 0,      max: 5000 },
  { label: "S$5k — S$20k",     min: 5000,   max: 20000 },
  { label: "S$20k — S$100k",   min: 20000,  max: 100000 },
  { label: "Over S$100k",       min: 100000, max: Infinity },
];

const SIDEBAR_GROUPS = {
  STATUS: {
    options: ["Live Now", "Scheduled", "Ended"],
    activeDefault: null,
  },
  CATEGORY: {
    options: DB_CATEGORIES,
    activeDefault: null,
  },
  ESTIMATE: {
    options: ESTIMATE_RANGES.map((r) => r.label),
    activeDefault: null,
  },
};

const ITEMS_PER_PAGE = 9;

export default function Home() {
  const [listings, setListings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [activeTab, setActiveTab] = useState("All Lots");
  const [page, setPage] = useState(1);
  const [sideFilters, setSideFilters] = useState({
    STATUS: null,
    CATEGORY: null,
    ESTIMATE: null,
  });

  useEffect(() => {
    getListings().then(setListings).catch(console.error).finally(() => setLoading(false));
  }, []);

  const visible = listings.filter((l) => {
    if (search && !l.title.toLowerCase().includes(search.toLowerCase())) return false;

    if (activeTab !== "All Lots" && l.category !== activeTab) return false;

    if (sideFilters.STATUS) {
      const statusMap = { "Live Now": "active", "Scheduled": "scheduled", "Ended": "ended" };
      if (l.status !== statusMap[sideFilters.STATUS]) return false;
    }

    if (sideFilters.CATEGORY && l.category !== sideFilters.CATEGORY) return false;

    if (sideFilters.ESTIMATE) {
      const range = ESTIMATE_RANGES.find((r) => r.label === sideFilters.ESTIMATE);
      if (range) {
        const price = parseFloat(l.current_highest_bid) || parseFloat(l.starting_price) || 0;
        if (price < range.min || price >= range.max) return false;
      }
    }

    return true;
  });

  const totalPages = Math.max(1, Math.ceil(visible.length / ITEMS_PER_PAGE));
  const paged = visible.slice((page - 1) * ITEMS_PER_PAGE, page * ITEMS_PER_PAGE);

  function buildPageNums(total, cur) {
    if (total <= 5) return Array.from({ length: total }, (_, i) => i + 1);
    const pages = [1, 2, 3];
    if (!pages.includes(total)) pages.push("…", total);
    return pages;
  }

  return (
    <div className="cat-wrap">

      {/* Page Header */}
      <div className="cat-page-header">
        <div className="cat-header-accent" />
        <div className="cat-header-inner">
          <p className="cat-header-eyebrow">SEASON XXIII · {visible.length} ACTIVE LOTS</p>
          <h1 className="cat-header-title">Auction Catalogue</h1>
        </div>
      </div>

      {/* Filter Strip */}
      <div className="cat-filter-strip">
        <div className="cat-filter-inner">
          <div className="cat-search-wrap">
            <svg className="cat-search-icon" width="16" height="16" viewBox="0 0 16 16" fill="none">
              <circle cx="6.5" cy="6.5" r="5" stroke="#1E1E1E" strokeWidth="1.5" />
              <path d="M10.5 10.5L14 14" stroke="#1E1E1E" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
            <input
              className="cat-search"
              placeholder="Search by brand, item, lot number..."
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            />
          </div>
          <div className="cat-tabs">
            {FILTER_TABS.map((tab) => (
              <button
                key={tab}
                type="button"
                className={`cat-tab${activeTab === tab ? " active" : ""}`}
                onClick={() => { setActiveTab(tab); setPage(1); }}
              >
                {tab}
              </button>
            ))}
          </div>
          <select className="cat-sort">
            <option>Ending soonest ▾</option>
            <option>Highest bid</option>
            <option>Lowest estimate</option>
            <option>Most bids</option>
          </select>
        </div>
      </div>

      {/* Body */}
      <div className="cat-body">

        {/* Sidebar */}
        <aside className="cat-sidebar">
          <div className="cat-sidebar-accent" />
          <p className="cat-refine-label">REFINE</p>
          {Object.entries(SIDEBAR_GROUPS).map(([group, { options }]) => (
            <div className="cat-sb-group" key={group}>
              <p className="cat-sb-group-label">{group}</p>
              <div className="cat-sb-rule" />
              {options.map((opt) => {
                const isActive = sideFilters[group] === opt;
                return (
                  <button
                    key={opt}
                    type="button"
                    className={`cat-sb-opt${isActive ? " active" : ""}`}
                    onClick={() => { setSideFilters((f) => ({ ...f, [group]: isActive ? null : opt })); setPage(1); }}
                  >
                    <span className="cat-sb-radio">{isActive ? "●" : "○"}</span>
                    {opt}
                  </button>
                );
              })}
            </div>
          ))}
        </aside>

        {/* Grid */}
        <div className="cat-grid-wrap">
          <div className="cat-grid">
            {loading ? (
              <p className="cat-empty">Loading listings…</p>
            ) : paged.length > 0 ? (
              paged.map((listing, i) => (
                <AuctionCard
                  key={listing.id}
                  listing={listing}
                  index={(page - 1) * ITEMS_PER_PAGE + i + 1}
                />
              ))
            ) : (
              <p className="cat-empty">No listings match your search.</p>
            )}
          </div>

          {/* Pagination */}
          {!loading && visible.length > 0 && (
            <div className="cat-pagination">
              <div className="cat-pag-rule" />
              <div className="cat-pag-btns">
                <button
                  className="cat-pag-btn"
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                >←</button>
                {buildPageNums(totalPages, page).map((p, i) =>
                  p === "…"
                    ? <span key={`e${i}`} className="cat-pag-ellipsis">·</span>
                    : <button
                        key={p}
                        className={`cat-pag-btn${page === p ? " active" : ""}`}
                        onClick={() => setPage(p)}
                      >{p}</button>
                )}
                <button
                  className="cat-pag-btn"
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                >→</button>
              </div>
            </div>
          )}
        </div>

      </div>
    </div>
  );
}
