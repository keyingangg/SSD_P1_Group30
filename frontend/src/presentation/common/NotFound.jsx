import { Link } from "react-router-dom";

import { BRAND } from "../../config/brand.js";
import "../../styles/not-found.css";

export default function NotFound() {
  return (
    <main className="nf-page">
      <div className="nf-frame">

        {/* Catalogue header */}
        <div className="nf-meta">
          <span>{BRAND.name.toUpperCase()} · EST. {BRAND.established}</span>
          <span>PRIVATE AUCTION CATALOGUE</span>
        </div>

        <div className="nf-rule" />

        {/* Withdrawn lot */}
        <div className="nf-lot-section">
          <p className="nf-lot-label">LOT</p>
          <p className="nf-number">404</p>
          <p className="nf-status">Withdrawn from Catalogue</p>
        </div>

        <div className="nf-rule" />

        {/* Copy */}
        <div className="nf-copy-section">
          <h1 className="nf-heading">This lot could not be located</h1>
          <p className="nf-body">
            The page you requested does not exist in our catalogue.
            It may have been removed, relocated, or the address was entered incorrectly.
          </p>
          <Link to="/" className="nf-cta">Return to the Auction Floor</Link>
        </div>

        {/* Footer */}
        <div className="nf-foot">{BRAND.footer}</div>

      </div>
    </main>
  );
}
