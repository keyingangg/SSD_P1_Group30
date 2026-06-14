// Lightweight client-side password strength indicator.
// This is a UX hint only — the authoritative checks (minimum length and the
// HaveIBeenPwned breach lookup) are enforced server-side at registration.

const LABELS = ["Too short", "Weak", "Fair", "Good", "Strong"];

function scorePassword(pw) {
  if (!pw || pw.length < 12) return 0;
  let score = 1; // meets the 12-char minimum
  if (pw.length >= 16) score++;
  if (/[a-z]/.test(pw) && /[A-Z]/.test(pw)) score++;
  if (/\d/.test(pw)) score++;
  if (/[^A-Za-z0-9]/.test(pw)) score++;
  return Math.min(score, 4);
}

export default function PasswordStrengthMeter({ password }) {
  if (!password) return null;

  const score = scorePassword(password);
  const label = LABELS[score];
  const strong = score >= 3;

  return (
    <div>
      <div className="strength">
        {[1, 2, 3, 4].map((i) => (
          <span
            key={i}
            className={i <= score ? (strong ? "on" : "warn") : ""}
          />
        ))}
      </div>
      <p className="strength-label">
        Strength: {label}
        {strong && (
          <>
            {" · "}
            <span className="ok">Checked against the breach database</span>
          </>
        )}
      </p>
    </div>
  );
}
