import { Link } from "react-router-dom";

// 404 page.
export default function NotFound() {
  return (
    <main>
      <h1>404 — Page Not Found</h1>
      <Link to="/">Return home</Link>
    </main>
  );
}
