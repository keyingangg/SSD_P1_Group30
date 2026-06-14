import { useState } from "react";
import { Link } from "react-router-dom";

const SGD = (n) => `S$${n.toLocaleString()}`;

const CATEGORIES = ["All", "Timepieces", "Handbags", "Jewellery", "Art"];

const MOCK_LISTINGS = [
  { id: "1", number: "041", house: "Rolex", category: "Timepieces", title: "Submariner Date Ref. 126610LN", estimateLow: 15000, estimateHigh: 22000, currentBid: 18500, bids: 14, timeLeft: "4h 22m", status: "live", img: "https://picsum.photos/seed/watch1/400/320" },
  { id: "2", number: "042", house: "Hermès", category: "Handbags", title: "Birkin 30 — Togo Gold", estimateLow: 28000, estimateHigh: 40000, currentBid: 34200, bids: 29, timeLeft: "1d 8h", status: "live", img: "https://picsum.photos/seed/bag1/400/320" },
  { id: "3", number: "043", house: "Cartier", category: "Jewellery", title: "Love Bracelet 18K Yellow Gold", estimateLow: 6000, estimateHigh: 9000, currentBid: 8800, bids: 22, timeLeft: "2d 3h", status: "live", img: "https://picsum.photos/seed/jewel1/400/320" },
  { id: "4", number: "044", house: "Patek Philippe", category: "Timepieces", title: "Calatrava Ref. 6119G", estimateLow: 60000, estimateHigh: 85000, currentBid: 72000, bids: 31, timeLeft: "5h 10m", status: "live", img: "https://picsum.photos/seed/watch2/400/320" },
  { id: "5", number: "045", house: "Bulgari", category: "Timepieces", title: "Serpenti Tourbillon", estimateLow: 70000, estimateHigh: 99000, currentBid: 88000, bids: 18, timeLeft: "3d 12h", status: "live", img: "https://picsum.photos/seed/watch3/400/320" },
  { id: "6", number: "046", house: "Louis Vuitton", category: "Handbags", title: "Capucines MM Magnolia", estimateLow: 3500, estimateHigh: 5500, currentBid: 5200, bids: 9, timeLeft: "18h 45m", status: "live", img: "https://picsum.photos/seed/bag2/400/320" },
  { id: "7", number: "047", house: "Van Cleef & Arpels", category: "Jewellery", title: "Perlée Diamonds Ring, Platinum", estimateLow: 8000, estimateHigh: 14000, currentBid: 12400, bids: 16, timeLeft: "2d 6h", status: "live", img: "https://picsum.photos/seed/jewel2/400/320" },
  { id: "8", number: "048", house: "Chanel", category: "Handbags", title: "Classic Flap, Caviar Medium", estimateLow: 7000, estimateHigh: 11000, currentBid: 9600, bids: 24, timeLeft: "22h 30m", status: "live", img: "https://picsum.photos/seed/bag3/400/320" },
  { id: "9", number: "049", house: "Audemars Piguet", category: "Timepieces", title: "Royal Oak Ref. 15500ST", estimateLow: 40000, estimateHigh: 60000, currentBid: 54000, bids: 37, timeLeft: "6h 50m", status: "live", img: "https://picsum.photos/seed/watch4/400/320" },
];

const SIDEBAR = {
  Status: ["Live Now", "Opening Soon", "Recently Closed"],
  Category: ["Timepieces", "Handbags & Leather", "Fine Jewellery", "Art & Prints", "Collectibles"],
  Estimate: ["Under S$5,000", "S$5k — S$20k", "S$20k — S$100k", "Over S$100k"],
};

export default function Home() {
  const [activeCategory, setActiveCategory] = useState("All");
  const [search, setSearch] = useState("");

  const visible = MOCK_LISTINGS.filter((l) => {
    const matchCat = activeCategory === "All" || l.category === activeCategory;
    const matchSearch = l.title.toLowerCase().includes(search.toLowerCase()) ||
      l.house.toLowerCase().includes(search.toLowerCase());
    return matchCat && matchSearch;
  });

  return (
    <>
      <div className="cat-header">
        <p className="cat-eyebrow">Season XXIII · {MOCK_LISTINGS.length} Active Listings</p>
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
                className={`cat-tab${activeCategory === c ? " active" : ""}`}
                onClick={() => setActiveCategory(c)}
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
                  <input type="radio" name={group} />
                  <span>{opt}</span>
                </label>
              ))}
            </div>
          ))}
        </aside>

        {/* Grid */}
        <div>
          <div className="cat-grid">
            {visible.map((item) => (
              <div className="lst-card" key={item.id}>
                <div className="cat-card-img-wrap">
                  <img src={item.img} alt={item.title} className="cat-card-img" />
                  {item.status === "live" && <span className="cat-card-live">● LIVE</span>}
                </div>
                <div className="lst-card-body">
                  <p className="lst-card-house">{item.house}</p>
                  <h3 className="lst-card-title">{item.title}</h3>
                  <p className="lst-card-estimate">Est. {SGD(item.estimateLow)} — {SGD(item.estimateHigh)}</p>
                  <div className="lst-card-foot">
                    <div>
                      <p className="lst-card-bid-label">current bid</p>
                      <p className="lst-card-bid">{SGD(item.currentBid)}</p>
                    </div>
                    <div className="lst-card-time">
                      <p className="lst-card-time-label">{item.bids} bids · remaining</p>
                      <p className="lst-card-time-val">{item.timeLeft}</p>
                    </div>
                  </div>
                  <Link to={`/listings/${item.id}`} className="lst-card-btn">
                    View &amp; Place Bid
                  </Link>
                </div>
              </div>
            ))}
          </div>

          {visible.length === 0 && (
            <p style={{ padding: "3rem", textAlign: "center", opacity: .5 }}>
              No listings match your search.
            </p>
          )}

          {/* Pagination (static for now) */}
          <div className="cat-pagination">
            <button className="cat-page-btn">‹</button>
            {[1, 2, 3].map((p) => (
              <button key={p} className={`cat-page-btn${p === 1 ? " active" : ""}`}>{p}</button>
            ))}
            <span className="cat-page-ellipsis">…</span>
            <button className="cat-page-btn">12</button>
            <button className="cat-page-btn">›</button>
          </div>
        </div>
      </div>
    </>
  );
}
