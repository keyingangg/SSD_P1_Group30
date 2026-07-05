# Automated tests

This project's tests are split across two locations, for a technical reason —
see below.

## Backend

**Location:** `testing/backend/`
**Run:** `cd testing/backend && pytest --tb=short -v`
**Framework:** pytest + pytest-django, hitting real Django views/ORM/DB (a test
Postgres database) via DRF's `APIClient`.

## Frontend

**Location:** colocated with the source files they test, e.g.
`frontend/src/components/ProtectedRoute.test.jsx` sits next to
`ProtectedRoute.jsx`.
**Run:** `cd frontend && npm test`
**Framework:** Vitest + React Testing Library.

### Why aren't frontend tests here in `testing/` too?

We tried it — moving them into `testing/frontend/` broke on a real constraint,
not a preference: Node resolves npm packages (`react-router-dom`,
`@testing-library/*`, etc.) by walking **up** the directory tree from the
file that imports them, looking for a `node_modules` folder at each level.
Since those packages are installed in `frontend/node_modules`, any test file
living outside the `frontend/` tree can never find them — walking up from
`testing/frontend/...` reaches `testing/`, then the repo root, and never
passes through `frontend/node_modules` on the way. This isn't a Vite config
setting we missed; it's how Node module resolution works, and it means
frontend tests **must** live inside `frontend/` to resolve their own
dependencies. Colocating them next to the source file they test is the
standard convention for exactly this reason, not just a style choice.

Both suites run automatically in CI (`.github/workflows/ci.yml`, jobs
`backend-test` and `frontend-test`) on every push.
