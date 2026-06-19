import { Link, Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import { BRAND } from "../config/brand.js";

const SGD = (n) => `S$${n.toLocaleString()}`;

const HIGHLIGHTS = [
  {
    id: "1", lot: "042", house: "Rolex",
    title: "Submariner Date Ref. 126610LN",
    estimateLow: 15000, estimateHigh: 22000,
    currentBid: 18500, bids: 14, timeLeft: "4h 22m",
    img: "https://picsum.photos/seed/luxwatch1/800/600",
  },
  {
    id: "2", lot: "043", house: "Hermès",
    title: "Birkin 30 — Togo Gold",
    estimateLow: 28000, estimateHigh: 40000,
    currentBid: 34200, bids: 28, timeLeft: "1d 8h",
    img: "https://picsum.photos/seed/luxbag1/600/450",
  },
  {
    id: "3", lot: "044", house: "Patek Philippe",
    title: "Calatrava Ref. 6119G",
    estimateLow: 60000, estimateHigh: 85000,
    currentBid: 72000, bids: 31, timeLeft: "5h 10m",
    img: "https://picsum.photos/seed/luxwatch2/600/450",
  },
];

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
  if (loading) return null;
  if (user) return <Navigate to="/auctions" replace />;

  return (
    <div className="lp-wrap">

      {/* ── Navbar ── */}
      <header className="lp-nav">
        <div className="lp-nav-logo">
          <span className="lp-logo-mark">LB</span>
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

      {/* ── Stats Strip ── */}
      <div className="lp-stats-strip">
        <div className="lp-stat">
          <div className="lp-stat-value">1,240+</div>
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
          {/* Featured lot card */}
          <div className="lp-fc">
            <div className="lp-fc-img-wrap">
              <img
                src="https://picsum.photos/seed/luxfeatured/800/600"
                alt="Featured lot"
                className="lp-fc-img"
              />
              <span className="lp-lot-badge">LOT 001</span>
              <span className="lp-live-tag">
                <span className="lp-live-dot" />LIVE
              </span>
            </div>
            <div className="lp-fc-info">
              <p className="lp-fc-house">PATEK PHILIPPE</p>
              <h3 className="lp-fc-title">Nautilus Ref. 5711/1A-011</h3>
              <p className="lp-fc-ref">Ref 2023 · Unworn · Full Set</p>
            </div>
          </div>
          {/* Bid panel — separate card below */}
          <div className="lp-bid-panel">
            <div className="lp-bid-col">
              <p className="lp-bp-label">CURRENT BID</p>
              <p className="lp-bp-amount">S$142,500</p>
              <p className="lp-bp-sub">31 bids</p>
            </div>
            <div className="lp-bp-vdiv" />
            <div className="lp-bid-col">
              <p className="lp-bp-label">CLOSES IN</p>
              <p className="lp-bp-time">2d 14h 32m</p>
              <p className="lp-bp-sub">Bidding open</p>
            </div>
            <Link to="/register" className="lp-bp-btn">Register &amp; Bid on This Lot</Link>
          </div>
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
            <Link to="/register" className="lp-browse-link">Browse all 124 lots →</Link>
          </div>
          <div className="lp-hl-bot-rule" />

          <div className="lp-hl-grid">
            {/* Large card */}
            <div className="lp-hlc-large">
              <div className="lp-hl-img-wrap">
                <img src={HIGHLIGHTS[0].img} alt={HIGHLIGHTS[0].title} className="lp-hl-img" />
                <span className="lp-lot-badge">LOT {HIGHLIGHTS[0].lot}</span>
              </div>
              <div className="lp-hlc-body">
                <p className="lp-hlc-house">{HIGHLIGHTS[0].house}</p>
                <h3 className="lp-hlc-title">{HIGHLIGHTS[0].title}</h3>
                <p className="lp-hlc-est">Estimate: {SGD(HIGHLIGHTS[0].estimateLow)} — {SGD(HIGHLIGHTS[0].estimateHigh)}</p>
                <div className="lp-hlc-rule" />
                <div className="lp-hlc-foot">
                  <p className="lp-hlc-bid">{SGD(HIGHLIGHTS[0].currentBid)}</p>
                  <p className="lp-hlc-time">{HIGHLIGHTS[0].timeLeft}</p>
                  <p className="lp-hlc-bids">{HIGHLIGHTS[0].bids} bids</p>
                </div>
                <Link to="/register" className="lp-hlc-btn">View Lot &amp; Bid</Link>
              </div>
            </div>

            {/* Right stack — two horizontal cards */}
            <div className="lp-hl-stack">
              {HIGHLIGHTS.slice(1).map((item) => (
                <div className="lp-hlc-small" key={item.id}>
                  <div className="lp-hls-img-wrap">
                    <img src={item.img} alt={item.title} className="lp-hls-img" />
                    <span className="lp-lot-badge sm">LOT {item.lot}</span>
                  </div>
                  <div className="lp-hls-body">
                    <p className="lp-hlc-house">{item.house}</p>
                    <h3 className="lp-hlc-title">{item.title}</h3>
                    <p className="lp-hlc-est">Estimate: {SGD(item.estimateLow)} — {SGD(item.estimateHigh)}</p>
                    <div className="lp-hlc-rule" />
                    <div className="lp-hls-foot">
                      <div>
                        <p className="lp-hlc-bid">{SGD(item.currentBid)}</p>
                        <p className="lp-hls-bid-label">current bid</p>
                      </div>
                      <div>
                        <p className="lp-hlc-time">{item.timeLeft}</p>
                        <p className="lp-hls-bid-label">remaining</p>
                      </div>
                      <p className="lp-hlc-bids">{item.bids} bids</p>
                    </div>
                    <Link to="/register" className="lp-hlc-btn">View Lot &amp; Place Bid</Link>
                  </div>
                </div>
              ))}
            </div>
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
          LuxBid gave me the confidence to bid on a S$120,000 Patek Philippe. The provenance
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
              <span className="lp-logo-mark sm">LB</span>
              <span className="lp-logo-name sm">{BRAND.name.toUpperCase()}</span>
            </div>
            <p className="lp-footer-tag1">Exclusive Auctions for Discerning Collectors</p>
            <p className="lp-footer-tag2">Registered in Singapore · Est. {BRAND.established}</p>
          </div>
          {[
            { heading: "Platform", links: ["Browse Auctions", "Private Sales", "How It Works", "Provenance Policy"] },
            { heading: "Company", links: ["About LuxBid", "Careers", "Press Room", "Contact Us"] },
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
          <span>©2024 LuxBid Pte. Ltd. All rights reserved.</span>
          <span>SSL Secured · PDPA Compliant · PCI DSS</span>
        </div>
      </footer>
    </div>
  );
}
