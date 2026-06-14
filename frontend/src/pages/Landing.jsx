import { Link, Navigate } from "react-router-dom";

import Logo from "../components/Logo.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { BRAND } from "../config/brand.js";

const SGD = (n) => `S$${n.toLocaleString()}`;

const HIGHLIGHTS = [
  {
    id: "1", house: "Rolex", category: "Timepieces",
    title: "Submariner Date Ref. 126610LN",
    estimateLow: 15000, estimateHigh: 22000,
    currentBid: 18500, bids: 14, timeLeft: "4h 22m",
    img: "https://picsum.photos/seed/luxwatch1/800/600",
  },
  {
    id: "2", house: "Hermès", category: "Handbags",
    title: "Birkin 30 — Togo Gold",
    estimateLow: 28000, estimateHigh: 40000,
    currentBid: 34200, bids: 29, timeLeft: "1d 8h",
    img: "https://picsum.photos/seed/luxbag1/600/450",
  },
  {
    id: "3", house: "Patek Philippe", category: "Timepieces",
    title: "Calatrava Ref. 6119G",
    estimateLow: 60000, estimateHigh: 85000,
    currentBid: 72000, bids: 31, timeLeft: "5h 10m",
    img: "https://picsum.photos/seed/luxwatch2/600/450",
  },
];

const STEPS = [
  { num: "01", title: "Create & Verify Account", desc: "Register free. Email verification and optional MFA protect your account from day one." },
  { num: "02", title: "Browse Authenticated Listings", desc: "Every item carries verified provenance documentation. Filter by house, price, or closing time." },
  { num: "03", title: "Bid in Real Time", desc: "WebSocket-powered live bidding. Your position updates instantly — no refreshing required." },
  { num: "04", title: "Win & Collect Securely", desc: "Stripe-tokenised checkout. Zero raw card data on our servers. Arranged delivery worldwide." },
];

const SECURITY = [
  { title: "Email Verification", desc: "Accounts activate only after email confirmation." },
  { title: "WebSocket Origin Validation", desc: "Live bid channels validate Origin headers — CSRF blocked." },
  { title: "TOTP / MFA", desc: "Two-factor authentication available for all accounts." },
  { title: "Stripe Elements", desc: "Card data tokenised client-side. Zero raw numbers on our servers." },
  { title: "Breach Password Check", desc: "Passwords screened against known leak databases." },
  { title: "IDOR Protection", desc: "Session-bound data access. Your data is yours alone." },
];

export default function Landing() {
  const { user, loading } = useAuth();

  if (loading) return null;
  if (user) return <Navigate to="/auctions" replace />;

  return (
    <div className="lp-wrap">

      {/* Header */}
      <header className="lp-header">
        <Link to="/"><Logo /></Link>
        <nav className="lp-header-nav">
          <Link to="/login" className="lp-nav-link">Sign In</Link>
          <Link to="/register" className="lp-nav-link gold btn-gold" style={{ color: "#fff" }}>
            Create Account
          </Link>
        </nav>
      </header>

      {/* Stats bar */}
      <div className="lp-stats">
        {[
          { value: "1,240+", label: "Active Listings" },
          { value: "S$4.2M", label: "Traded This Season" },
          { value: "48,500", label: "Registered Bidders" },
          { value: "100%", label: "Provenance Verified" },
        ].map((s) => (
          <div className="lp-stat" key={s.label}>
            <div className="lp-stat-value">{s.value}</div>
            <div className="lp-stat-label">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Hero */}
      <section className="lp-hero">
        <div className="lp-hero-text">
          <p className="lp-hero-eyebrow">Live Auction · Season XXIII</p>
          <h1 className="lp-hero-title">Extraordinary Objects.<br />Exceptional Bids.</h1>
          <p className="lp-hero-sub">
            Authenticated provenance. Real-time competitive bidding.
            Curated for those who demand the finest.
          </p>
          <div className="lp-hero-actions">
            <Link to="/register" className="btn-gold">View Current Auctions</Link>
            <Link to="/register" className="btn-outline">Register to Bid</Link>
          </div>
          <p className="lp-hero-badges">+ SSL · MFA · PDPA · Stripe Payments</p>
        </div>

        <div>
          <div className="lp-featured-card">
            <img
              src="https://picsum.photos/seed/luxfeatured/800/450"
              alt="Featured listing"
              className="lp-featured-img"
            />
            <div className="lp-featured-body">
              <p className="lp-featured-eyebrow">Patek Philippe · Lot 401</p>
              <h3 className="lp-featured-title">Nautilus Ref. 5711/1A-011</h3>
              <p className="lp-featured-ref">Ref 2023 · Unworn · Full Set</p>
              <div className="lp-featured-meta">
                <div>
                  <p className="lp-meta-label">Current Bid</p>
                  <p className="lp-meta-value">S$142,500</p>
                  <p style={{ fontSize: ".7rem", opacity: .5, marginTop: ".2rem" }}>31 bids</p>
                </div>
                <div>
                  <p className="lp-meta-label">Closes In</p>
                  <p className="lp-meta-value clock">2d 14h 32m</p>
                  <p style={{ fontSize: ".7rem", opacity: .5, marginTop: ".2rem" }}>Bidding open</p>
                </div>
              </div>
              <Link to="/register" className="btn-gold" style={{ display: "block", textAlign: "center" }}>
                Register &amp; Bid on This Listing
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Current Season Highlights */}
      <section className="lp-section" style={{ paddingTop: 0 }}>
        <div className="lp-section-header">
          <div>
            <p className="lp-section-eyebrow">Live Auctions</p>
            <h2 className="lp-section-title">Current Season Highlights</h2>
          </div>
          <Link to="/register" className="lp-browse-link">Browse all 124 listings →</Link>
        </div>

        <div className="lp-highlights">
          {/* Large featured card */}
          <div className="lst-card large">
            <img src={HIGHLIGHTS[0].img} alt={HIGHLIGHTS[0].title} className="lst-card-img" style={{ aspectRatio: "4/3" }} />
            <div className="lst-card-body">
              <p className="lst-card-house">{HIGHLIGHTS[0].house}</p>
              <h3 className="lst-card-title">{HIGHLIGHTS[0].title}</h3>
              <p className="lst-card-estimate">
                Est. {SGD(HIGHLIGHTS[0].estimateLow)} — {SGD(HIGHLIGHTS[0].estimateHigh)}
              </p>
              <div className="lst-card-foot">
                <div>
                  <p className="lst-card-bid-label">current bid</p>
                  <p className="lst-card-bid">{SGD(HIGHLIGHTS[0].currentBid)}</p>
                </div>
                <div className="lst-card-time">
                  <p className="lst-card-time-label">{HIGHLIGHTS[0].bids} bids · remaining</p>
                  <p className="lst-card-time-val">{HIGHLIGHTS[0].timeLeft}</p>
                </div>
              </div>
              <Link to="/register" className="lst-card-btn">View &amp; Place Bid</Link>
            </div>
          </div>

          {/* Two smaller cards */}
          <div className="lp-highlight-side">
            {HIGHLIGHTS.slice(1).map((item) => (
              <div className="lst-card" key={item.id}>
                <img src={item.img} alt={item.title} className="lst-card-img" />
                <div className="lst-card-body">
                  <p className="lst-card-house">{item.house}</p>
                  <h3 className="lst-card-title">{item.title}</h3>
                  <p className="lst-card-estimate">
                    Est. {SGD(item.estimateLow)} — {SGD(item.estimateHigh)}
                  </p>
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
                  <Link to="/register" className="lst-card-btn">View &amp; Place Bid</Link>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Process */}
      <section className="lp-section" style={{ paddingTop: 0 }}>
        <p className="lp-section-eyebrow">Process</p>
        <h2 className="lp-section-title" style={{ marginBottom: "2rem" }}>From Registration to Collection</h2>
        <div className="lp-process-grid">
          {STEPS.map((s) => (
            <div className="lp-step" key={s.num}>
              <div className="lp-step-num">{s.num}</div>
              <h4 className="lp-step-title">{s.title}</h4>
              <p className="lp-step-desc">{s.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Security */}
      <div className="lp-security-wrap">
        <div className="lp-security-inner">
          <div>
            <h2 className="lp-security-title">Security Engineered<br />for Trust.</h2>
            <p className="lp-security-sub">
              Every design decision — from breached password detection to
              WebSocket origin validation — exists to protect your assets and identity.
            </p>
          </div>
          <div className="lp-security-grid">
            {SECURITY.map((f) => (
              <div className="lp-sec-feat" key={f.title}>
                <h4>{f.title}</h4>
                <p>{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Testimonial */}
      <div className="lp-testimonial">
        <span className="lp-quote-mark">"</span>
        <p className="lp-quote-text">
          {BRAND.name} gave me the confidence to bid on a S$120,000 Patek Philippe.
          The provenance documentation and real-time bidding made the entire experience
          completely transparent.
        </p>
        <p className="lp-quote-attr">— Wei Liang T., Verified Collector · Singapore</p>
      </div>

      {/* CTA */}
      <div className="lp-cta-wrap">
        <div className="lp-cta-inner">
          <h2 className="lp-cta-title">Begin Bidding on Exceptional Pieces</h2>
          <p className="lp-cta-sub">
            Join 48,500+ collectors. Your account is free. Authentication takes under two minutes.
          </p>
          <div className="lp-cta-actions">
            <Link to="/register" className="btn-gold">Create Your Account</Link>
            <Link to="/login" className="lp-link-light">Sign In</Link>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="lp-footer">
        <div className="lp-footer-inner">
          <div className="lp-footer-brand">
            <Logo />
            <p className="lp-footer-tagline">
              Exclusive Auctions for Discerning Collectors.<br />
              Registered in Singapore · Est. {BRAND.established}
            </p>
          </div>
          <div className="lp-footer-col">
            <h5>Platform</h5>
            <ul>
              <li><Link to="/register">Browse Auctions</Link></li>
              <li><Link to="/register">Private Sales</Link></li>
              <li><Link to="/register">How It Works</Link></li>
              <li><Link to="/register">Provenance Policy</Link></li>
            </ul>
          </div>
          <div className="lp-footer-col">
            <h5>Company</h5>
            <ul>
              <li><Link to="/register">About {BRAND.name}</Link></li>
              <li><Link to="/register">Careers</Link></li>
              <li><Link to="/register">Press Room</Link></li>
              <li><Link to="/register">Contact Us</Link></li>
            </ul>
          </div>
          <div className="lp-footer-col">
            <h5>Legal</h5>
            <ul>
              <li><Link to="/register">Terms of Service</Link></li>
              <li><Link to="/register">Privacy Policy</Link></li>
              <li><Link to="/register">Cookie Policy</Link></li>
              <li><Link to="/register">PDPA Compliance</Link></li>
            </ul>
          </div>
        </div>
        <div className="lp-footer-bottom">
          <span>©2024 {BRAND.name} Pte. Ltd. All rights reserved.</span>
          <span>SSL Secured · PDPA Compliant</span>
        </div>
      </footer>
    </div>
  );
}
