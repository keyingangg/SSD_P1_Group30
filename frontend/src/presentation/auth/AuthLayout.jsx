import Logo from "../common/Logo.jsx";
import { BRAND } from "../../config/brand.js";

// Two-column layout shared by the Sign In, Create Account, and Verify Email
// screens. The left column carries the brand + headline; `children` is the
// form card rendered on the right.
export default function AuthLayout({ tagline, children }) {
  return (
    <div className="auth-wrap">
      <div className="auth-inner">
        <aside className="auth-left">
          <div className="auth-top">
            <Logo />
            <hr className="rule" />
          </div>

          <div className="auth-headline">
            <h1>
              {BRAND.headlineLine1}
              <br />
              {BRAND.headlineLine2}
            </h1>
            {tagline && <p className="auth-tagline">{tagline}</p>}
          </div>

          <div className="auth-foot">
            <hr className="rule" />
            <span>{BRAND.footer}</span>
          </div>
        </aside>

        <section className="auth-right">{children}</section>
      </div>
    </div>
  );
}
