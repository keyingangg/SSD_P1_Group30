import { BRAND } from "../config/brand.js";

// Brand mark: gold "LB" tile + wordmark + established year.
export default function Logo() {
  return (
    <div className="logo">
      <span className="logo-mark">{BRAND.mark}</span>
      <span className="logo-text">
        <span className="logo-name">{BRAND.name.toUpperCase()}</span>
        <span className="logo-est">EST. {BRAND.established}</span>
      </span>
    </div>
  );
}
