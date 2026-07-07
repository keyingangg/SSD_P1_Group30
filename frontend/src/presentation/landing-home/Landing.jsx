import { Link, Navigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext.jsx";
import { BRAND } from "../config/brand.js";
import { getListings } from "../api/auctions.js";

const SGD = (n) => `S$${Number(n).toLocaleString()}`;

function timeRemaining(isoString) {
  if (!isoString) return null;
  const diff = Math.floor((new Date(isoString).getTime() - Date.now()) / 1000);
  if (diff <= 0) return null;
  const d = Math.floor(diff / 86400);
  const h = Math.floor((diff % 86400) / 3600);
  const m = Math.floor((diff % 3600) / 60);
  if (d > 0) return `${d}d ${h}h`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

const STEPS = [
  { num: "01", title: "Create & Verify Account", desc: "Register free. Email verification and optional MFA protect your account from day one.", arrow: true },
  { num: "02", title: "Browse Authenticated Lots", desc: "Every item carries verified provenance documentation. Filter by house, price, or closing time.", arrow: true },
  { num: "03", title: "Bid in Real Time", desc: "WebSocket-powered live bidding. Your position updates instantly — no refreshing required.", arrow: true },
  { num: "04", title: "Win & Collect Securely", desc: "Stripe-tokenised checkout. Zero raw card data on our servers. Arranged delivery worldwide.", arrow: false },
];

const SEC_LEFT = [
  { title: "Email Verification", desc: "Accounts activate only after email confirmation." },
  { title: "TOTP / MFA", desc: "Two-factor authentication available for all accounts." },
  { title: "Breach Password Check", desc: "Passwords screened against known leak databases." },
];
const SEC_RIGHT = [
  { title: "WebSocket Origin Validation", desc: "Live bid channels validate Origin headers — CSRF blocked." },
  { title: "Stripe Elements", desc: "Card data tokenised client-side. Zero raw numbers on our servers." },
  { title: "IDOR Protection", desc: "Session-bound data access. Your data is yours alone." },
];

export default function Landing() {
  const { user, loading } = useAuth();
  const [listings, setListings] = useState([]);

  useEffect(() => {
    getListings().then((data) => {
      // Prefer active listings first, then scheduled, then ended
      const sorted = [...data].sort((a, b) => {
        const order = { active: 0, scheduled: 1, ended: 2 };
        return (order[a.status] ?? 3) - (order[b.status] ?? 3);
      });
      setListings(sorted);
    }).catch(() => {});
  }, []);

  const featured = listings[0] ?? null;
  const highlights = listings.slice(0, 3);
  const totalLots = listings.length;

  if (loading) return null;
  if (user) return <Navigate to="/auctions" replace />;

  return (
    <div className="lp-wrap">

      {/* ── Navbar ── */}
      <div className="lp-nav-outer">
      <header className="lp-nav">
        <div className="lp-nav-logo">
          <span className="lp-logo-mark">SB</span>
          <span className="lp-logo-text">
            <span className="lp-logo-name">{BRAND.name.toUpperCase()}</span>
            <span className="lp-logo-est">EST. {BRAND.established}</span>
          </span>
        </div>
        <nav className="lp-nav-links">
          <Link to="/register" className="lp-nl">Auctions</Link>
          <Link to="/register" className="lp-nl">Private Sales</Link>
          <Link to="/register" className="lp-nl">Jewellery</Link>
          <Link to="/register" className="lp-nl">Watches</Link>
          <Link to="/register" className="lp-nl">About</Link>
        </nav>
        <div className="lp-nav-actions">
          <Link to="/login" className="lp-nl">Sign In</Link>
          <Link to="/register" className="lp-nav-register">Register</Link>
        </div>
      </header>
      </div>

      {/* ── Stats Strip ── */}
      <div className="lp-stats-outer">
      <div className="lp-stats-strip">
        <div className="lp-stat">
          <div className="lp-stat-value">{totalLots > 0 ? `${totalLots}+` : "—"}</div>
          <div className="lp-stat-label">Active Lots</div>
        </div>
        <div className="lp-stat-div" />
        <div className="lp-stat">
          <div className="lp-stat-value">S$4.2M</div>
          <div className="lp-stat-label">Traded This Season</div>
        </div>
        <div className="lp-stat-div" />
        <div className="lp-stat">
          <div className="lp-stat-value">48,500</div>
          <div className="lp-stat-label">Registered Bidders</div>
        </div>
        <div className="lp-stat-div" />
        <div className="lp-stat">
          <div className="lp-stat-value">100%</div>
          <div className="lp-stat-label">Provenance Verified</div>
        </div>
      </div>
      </div>

      {/* ── Hero ── */}
      <section className="lp-hero">
        <div className="lp-hero-left">
          <p className="lp-hero-eyebrow">LIVE AUCTION · SEASON XXIII</p>
          <h1 className="lp-hero-title">
            Extraordinary Objects. Exceptional Bids.
          </h1>
          <div className="lp-hero-rule" />
          <div className="lp-hero-actions">
            <Link to="/register" className="lp-btn-primary">View Current Auctions</Link>
            <Link to="/register" className="lp-btn-outline">Register to Bid</Link>
          </div>
          <p className="lp-hero-badges">
            <span className="lp-green-dot" />
            SSL · MFA · PDPA · Stripe Payments
          </p>
          <p className="lp-hero-sub">
            Authenticated provenance. Real-time competitive bidding.
            Reserved for those who demand the finest.
          </p>
        </div>

        <div className="lp-hero-vdiv" />

        <div className="lp-hero-right">
          {featured && (
            <>
              <div className="lp-fc">
                <div className="lp-fc-img-wrap">
                  {featured.image_url
                    ? <img src={featured.image_url} alt={featured.title} className="lp-fc-img" />
                    : <div className="lp-fc-img" style={{ background: "#e8e5df" }} />
                  }
                  <span className="lp-lot-badge">LOT 001</span>
                  {featured.status === "active" && (
                    <span className="lp-live-tag">
                      <span className="lp-live-dot" />LIVE
                    </span>
                  )}
                </div>
                <div className="lp-fc-info">
                  <p className="lp-fc-house">{(featured.category || "").toUpperCase()}</p>
                  <h3 className="lp-fc-title">{featured.title}</h3>
                  <p className="lp-fc-ref">{featured.description?.slice(0, 60) || ""}</p>
                </div>
              </div>
              <div className="lp-bid-panel">
                <div className="lp-bid-col">
                  <p className="lp-bp-label">CURRENT BID</p>
                  <p className="lp-bp-amount">{SGD(featured.current_highest_bid || featured.starting_price)}</p>
                  <p className="lp-bp-sub">{featured.bid_count ?? 0} bids</p>
                </div>
                <div className="lp-bp-vdiv" />
                <div className="lp-bid-col">
                  <p className="lp-bp-label">CLOSES IN</p>
                  <p className="lp-bp-time">{timeRemaining(featured.ends_at) ?? "—"}</p>
                  <p className="lp-bp-sub">{featured.status === "active" ? "Bidding open" : featured.status}</p>
                </div>
                <Link to="/register" className="lp-bp-btn">Register &amp; Bid on This Lot</Link>
              </div>
            </>
          )}
        </div>
      </section>

      {/* ── Current Season Highlights ── */}
      <section className="lp-hl-section">
        <div className="lp-hl-inner">
          <div className="lp-hl-top-rule" />
          <div className="lp-hl-header">
            <div>
              <p className="lp-eyebrow">LIVE AUCTIONS</p>
              <h2 className="lp-section-h2">Current Season Highlights</h2>
            </div>
            <Link to="/register" className="lp-browse-link">Browse all {totalLots} lots →</Link>
          </div>
          <div className="lp-hl-bot-rule" />

          <div className="lp-hl-grid">
            {/* Large card */}
            {highlights[0] && (
              <div className="lp-hlc-large">
                <div className="lp-hl-img-wrap">
                  {highlights[0].image_url
                    ? <img src={highlights[0].image_url} alt={highlights[0].title} className="lp-hl-img" />
                    : <div className="lp-hl-img" style={{ background: "#e8e5df" }} />
                  }
                  <span className="lp-lot-badge">LOT 001</span>
                </div>
                <div className="lp-hlc-body">
                  <p className="lp-hlc-house">{highlights[0].category}</p>
                  <h3 className="lp-hlc-title">{highlights[0].title}</h3>
                  <p className="lp-hlc-est">Starting bid: {SGD(highlights[0].starting_price)}</p>
                  <div className="lp-hlc-rule" />
                  <div className="lp-hlc-foot">
                    <p className="lp-hlc-bid">{SGD(highlights[0].current_highest_bid || highlights[0].starting_price)}</p>
                    <p className="lp-hlc-time">{timeRemaining(highlights[0].ends_at) ?? "—"}</p>
                    <p className="lp-hlc-bids">{highlights[0].bid_count ?? 0} bids</p>
                  </div>
                  <Link to="/register" className="lp-hlc-btn">View Lot &amp; Bid</Link>
                </div>
              </div>
            )}

            {/* Right stack — two horizontal cards */}
            {highlights.length > 1 && (
              <div className="lp-hl-stack">
                {highlights.slice(1).map((item, i) => (
                  <div className="lp-hlc-small" key={item.id}>
                    <div className="lp-hls-img-wrap">
                      {item.image_url
                        ? <img src={item.image_url} alt={item.title} className="lp-hls-img" />
                        : <div className="lp-hls-img" style={{ background: "#e8e5df" }} />
                      }
                      <span className="lp-lot-badge sm">LOT {String(i + 2).padStart(3, "0")}</span>
                    </div>
                    <div className="lp-hls-vdiv" />
                    <div className="lp-hls-body">
                      <p className="lp-hlc-house">{item.category}</p>
                      <h3 className="lp-hlc-title">{item.title}</h3>
                      <p className="lp-hlc-est">Starting bid: {SGD(item.starting_price)}</p>
                      <div className="lp-hlc-rule" />
                      <div className="lp-hls-foot">
                        <div>
                          <p className="lp-hlc-bid">{SGD(item.current_highest_bid || item.starting_price)}</p>
                          <p className="lp-hls-bid-label">current bid</p>
                        </div>
                        <div>
                          <p className="lp-hlc-time">{timeRemaining(item.ends_at) ?? "—"}</p>
                          <p className="lp-hls-bid-label">remaining</p>
                        </div>
                        <p className="lp-hlc-bids">{item.bid_count ?? 0} bids</p>
                      </div>
                      <Link to="/register" className="lp-hlc-btn">View Lot &amp; Place Bid</Link>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </section>

      {/* ── How It Works / Process ── */}
      <section className="lp-process-section">
        <div className="lp-process-inner">
          <p className="lp-eyebrow">PROCESS</p>
          <h2 className="lp-section-h2">From Registration to Collection</h2>
          <div className="lp-process-grid">
            {STEPS.map((s) => (
              <div className="lp-step" key={s.num}>
                <div className="lp-step-num">{s.num}</div>
                <div className="lp-step-divider" />
                <h4 className="lp-step-title">{s.title}</h4>
                <p className="lp-step-desc">{s.desc}</p>
                {s.arrow && <span className="lp-step-arrow">→</span>}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Security ── */}
      <section className="lp-sec-section">
        <div className="lp-sec-inner">
          <div className="lp-sec-left">
            <h2 className="lp-sec-title">Security Engineered for Trust.</h2>
            <div className="lp-sec-rule" />
            <p className="lp-sec-sub">
              Every design decision — from breached password detection to
              WebSocket origin validation — exists to protect your assets and identity.
            </p>
          </div>
          <div className="lp-sec-vdiv" />
          <div className="lp-sec-right">
            <div className="lp-sec-col">
              {SEC_LEFT.map((f, i) => (
                <div className="lp-sf" key={f.title}>
                  <span className="lp-sf-dot" />
                  <div className="lp-sf-body">
                    <h4 className="lp-sf-title">{f.title}</h4>
                    <p className="lp-sf-desc">{f.desc}</p>
                    {i < SEC_LEFT.length - 1 && <div className="lp-sf-rule" />}
                  </div>
                </div>
              ))}
            </div>
            <div className="lp-sec-col">
              {SEC_RIGHT.map((f, i) => (
                <div className="lp-sf" key={f.title}>
                  <span className="lp-sf-dot" />
                  <div className="lp-sf-body">
                    <h4 className="lp-sf-title">{f.title}</h4>
                    <p className="lp-sf-desc">{f.desc}</p>
                    {i < SEC_RIGHT.length - 1 && <div className="lp-sf-rule" />}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── Quote ── */}
      <div className="lp-quote">
        <span className="lp-quote-mark">"</span>
        <p className="lp-quote-text">
          SecureBid gave me the confidence to bid on a S$120,000 Patek Philippe. The provenance
          documentation and real-time bidding made the entire experience completely transparent.
        </p>
        <p className="lp-quote-attr">— Wei Liang T., Verified Collector · Singapore</p>
      </div>

      {/* ── CTA Banner ── */}
      <div className="lp-cta">
        <h2 className="lp-cta-title">Begin Bidding on Exceptional Pieces</h2>
        <p className="lp-cta-sub">
          Join 48,500+ collectors. Your account is free. Authentication takes under two minutes.
        </p>
        <div className="lp-cta-actions">
          <Link to="/register" className="lp-cta-primary">Create Your Account</Link>
          <Link to="/login" className="lp-cta-outline">Sign In</Link>
        </div>
      </div>

      {/* ── Footer ── */}
      <footer className="lp-footer">
        <div className="lp-footer-top-accent" />
        <div className="lp-footer-inner">
          <div className="lp-footer-brand">
            <div className="lp-footer-logo">
              <span className="lp-logo-mark sm">SB</span>
              <span className="lp-logo-name sm">{BRAND.name.toUpperCase()}</span>
            </div>
            <p className="lp-footer-tag1">Exclusive Auctions for Discerning Collectors</p>
            <p className="lp-footer-tag2">Registered in Singapore · Est. {BRAND.established}</p>
          </div>
          {[
            { heading: "Platform", links: ["Browse Auctions", "Private Sales", "How It Works", "Provenance Policy"] },
            { heading: "Company", links: ["About SecureBid", "Careers", "Press Room", "Contact Us"] },
            { heading: "Legal", links: ["Terms of Service", "Privacy Policy", "Cookie Policy", "PDPA Compliance"] },
          ].map((col) => (
            <div className="lp-footer-col" key={col.heading}>
              <h5>{col.heading}</h5>
              <div className="lp-footer-col-rule" />
              <ul>
                {col.links.map((l) => <li key={l}><Link to="/register">{l}</Link></li>)}
              </ul>
            </div>
          ))}
        </div>
        <div className="lp-footer-bottom">
          <span>©2024 SecureBid Pte. Ltd. All rights reserved.</span>
          <span>SSL Secured · PDPA Compliant · PCI DSS</span>
        </div>
      </footer>
    </div>
  );
}
