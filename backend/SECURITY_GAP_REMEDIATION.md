# Security Gap Remediation — SecureBid Platform

**Source:** SFR/FSR/NFSR traceability review (gap analysis against the project's security requirements).
**Scope:** 10 of 12 identified gaps closed in code; 2 reviewed and left as documented deployment decisions (see [§4](#4-review-only--not-coded)).

---

## 1. Summary

| # | ID | Gap | Status |
|---|----|-----|--------|
| 1 | SFR-05b | Account deletion didn't block users with unpaid winning bids | ✅ Fixed |
| 2 | SFR-11d | Listing search/filter was entirely client-side | ✅ Fixed |
| 3 | FSR-IN-05 | HTTP 415 responses leaked the client-supplied Content-Type | ✅ Fixed |
| 4 | NFSR-AV-03 | No explicit HTTP method allowlist on sensitive views | ✅ Fixed (scoped) |
| 5 | — | CSP / Referrer-Policy / Permissions-Policy headers were a no-op stub | ✅ Fixed |
| 6 | NFSR-AC-07 | Payment audit logs missing session ID / listing ID | ✅ Fixed |
| 7 | FSR-C-07 | No admin "kill live session" action | ✅ Fixed |
| 8 | NFSR-AC-04 / FSR-IN-09 | No job re-verifying audit log row hashes | ✅ Fixed |
| 9 | FSR-AC-07 / NFSR-AC-05 | No bid-rate anomaly alerting (only a hard throttle) | ✅ Fixed |
| 10 | FSR-AC-09 | No automated retention policy verification | ✅ Fixed (reporting only, by design) |
| 11 | NFSR-IN-04 | `scan_for_malware()` was a no-op TODO | ✅ Fixed |
| 12 | NFSR-C-01/C-06, NFSR-AZ-06 | `SECURE_SSL` escape hatch; RLS on user-data tables | 📋 Reviewed, not coded |

---

## 2. Two decisions made with the project owner

- **Malware scan failure mode: fails closed.** If the ClamAV daemon is unreachable, the upload is rejected rather than let through unscanned.
- **Retention policy (FSR-AC-09): verification/reporting, not a purge job.** `AuditLog.save()` already rejects updates and no app registers `AuditLog` in Django admin, so there is no delete path today — the ≥5yr (payment) / ≥3yr (audit) floor is structurally satisfied. Building an active purge mechanism was judged unnecessary since nothing currently threatens the floor.

---

## 3. Changes by item

### 1. SFR-05b — Block deletion with unpaid orders
`backend/accounts/views.py` (`DeleteAccountView.post`) now checks for a `payments.Order` with `fulfillment_status="pending_payment"` for the requesting user and returns 400 if found, before proceeding to anonymisation.

### 2. SFR-11d — Server-side listing search/filter
- New `ListingSearchQuerySerializer` in `backend/auctions/serializers.py` validates `q`, `category`, `status`, `min_price`, `max_price`, and an `ordering` allowlist (never a raw field name).
- `ListingListView.get` (`backend/auctions/views.py`) validates query params through it and applies the filters to the existing queryset.

### 3. FSR-IN-05 — Explicit 415 handling
`backend/core/exceptions.py`'s `custom_exception_handler` now returns a generic `{"detail": "Unsupported content type."}` for `UnsupportedMediaType` instead of DRF's default message, which echoed the client-supplied Content-Type back into the response body.

### 4. NFSR-AV-03 — Explicit HTTP method allowlists (scoped)
Every view in the project is already a DRF `APIView` defining only the methods it needs — undefined verbs already 405 automatically, so a blanket mechanical edit across ~20+ view classes would have been a no-op diff. Added explicit `http_method_names` only to the five most security-sensitive views as documentation-grade reinforcement: `LoginView`, `BidSubmitView` (kept `delete`/`patch` in the allowlist so `BidImmutableMixin`'s reject-and-log handlers still fire), `DeleteAccountView`, `AdminUserDetailView`, `StripeWebhookView`.

### 5. Security headers middleware
`backend/core/middleware.py`'s `SecurityHeadersMiddleware` now sets `Content-Security-Policy` (scoped to `'self'` plus the Supabase storage origin for images), `Referrer-Policy: strict-origin-when-cross-origin`, and a restrictive `Permissions-Policy`. Uncommented in `backend/securebid/settings/base.py`'s `MIDDLEWARE`. (`X-Content-Type-Options` was already set by Django's own `SecurityMiddleware`, so it wasn't duplicated.)

### 6. NFSR-AC-07 — Payment audit log context
All `log_action(...)` call sites in `backend/payments/views.py` now include `session_id` and `listing_id` inside `metadata` (which already feeds the SHA-256 row hash, so this is safe for historical rows — see item 8). The Stripe webhook handler (`StripeWebhookView._handle_payment_succeeded`) now threads the calling IP through from `request.META.get("REMOTE_ADDR")`; `session_id` is explicitly `None` there with a comment explaining it's a server-to-server call with no browser session.

### 7. Admin session termination
New `AdminTerminateSessionsView` (`backend/accounts/views.py`) at `POST /api/accounts/admin/users/<uuid:user_id>/terminate-sessions/`, reusing the existing `invalidate_all_user_sessions()` helper and a shared `_get_admin_target()` guard (refactored out of `AdminUserDetailView` so both views use the same self/superuser/anonymised-target checks).

### 8. Hash verification job
`backend/core/management/commands/verify_audit_log_hashes.py` recomputes each `AuditLog` row's SHA-256 hash from its own stored fields and compares it to the stored `row_hash`, skipping the `[PII_ANONYMISED]` marker rows. Exits non-zero on any mismatch so it can gate a cron alert.

**Note:** running this against the dev database surfaced 37 pre-existing rows with a blank `row_hash` (`bid_placed`, `ORDER_FULFILLMENT_UPDATED`, `ORDER_PAID`, `listing_cancelled` actions) — these were created through a path that bypassed `log_action()` (likely seed/demo data). This is a real finding the tool correctly surfaced, not a false positive from this change. Worth tracking down the source of that data separately.

### 9. Bid-rate anomaly alerting
`backend/auctions/management/commands/detect_bid_anomalies.py` flags any user with more than `--threshold` (default 20) bids in the last `--window` (default 1) minutes, sends `send_bid_anomaly_email` (new helper in `backend/auctions/emails.py`, modeled on the existing account-lockout email), and writes a `bid_anomaly_detected` audit entry. Added a `Bid(bidder, submitted_at)` composite index via migration `auctions/migrations/0005_bid_bid_bidder_submitted_idx.py` since the query runs frequently and no such index existed.

### 10. Retention policy verification
`backend/core/management/commands/verify_retention_policy.py` reports row counts/ages for the general audit log and payment-specific log (via `PAYMENT_ACTIONS`), and confirms the append-only/no-admin-registration invariant that makes the retention floor structural rather than enforced by a purge job.

### 11. Malware scanning
`backend/core/validators.py`'s `scan_for_malware()` now connects to a ClamAV daemon via `clamd.ClamdNetworkSocket` (host/port from new `CLAMD_HOST`/`CLAMD_PORT` settings, defaulting to `localhost:3310`), scans the upload with `instream()`, and raises `ValidationError` on either a positive match **or** any connection/scan failure (fail-closed, per the confirmed decision). Added `clamd==1.0.2` to `requirements.txt`. **Requires an actual ClamAV daemon running and reachable** — this wasn't provisioned as part of this change; without one, image uploads will be rejected.

---

## 4. Review-only — not coded

- **`SECURE_SSL` escape hatch** (`backend/securebid/settings/production.py`): intentional and documented (raw-IP EC2 deployment note in the comment). Left as-is; a startup warning log when disabled in production was considered but not added.
- **RLS on `users`/`orders`/`bids`/`listings`**: the frontend never talks to Supabase directly (confirmed no `@supabase/supabase-js` dependency and no direct calls) — only the Django ORM touches these tables, through one fixed `DB_USER` role. Postgres RLS is designed for multi-role access (e.g. Supabase PostgREST); in this backend-mediated architecture it would be redundant with Django's own view-level authorization, provided `DB_USER` is genuinely least-privilege and not `BYPASSRLS`/superuser. Recommended a deployment-time check (`SELECT rolbypassrls FROM pg_roles WHERE rolname = current_user;`) instead of writing RLS policies that would be structurally inert given the current architecture.

---

## 5. Tests added

- `testing/test_auth.py`: unpaid-order deletion block/allow, admin session-termination endpoint (success + 404-for-non-admin).
- `testing/test_auctions.py`: listing search by title, rejection of an invalid `ordering` value.
- `testing/test_file_validators.py`: `scan_for_malware` clean pass, positive match rejection, fail-closed on daemon connection failure (all mock `clamd`, no live daemon required).
- `testing/test_file_storage.py`: existing upload test updated to mock `scan_for_malware` so it doesn't require a live ClamAV daemon.

Full suite: **147/147 passing** (`cd testing && python -m pytest -q`, using `../backend/venv/Scripts/python.exe`). `python manage.py check` (from `backend/`) passes with no issues.

---

## 6. Follow-ups for whoever deploys this

1. Run a ClamAV daemon reachable at `CLAMD_HOST:CLAMD_PORT` (env-configurable) — uploads fail closed without it.
2. Investigate the 37 blank-`row_hash` `AuditLog` rows found in the dev database (§3, item 8) — find and fix whatever seed/demo path bypasses `log_action()`.
3. Schedule `verify_audit_log_hashes`, `detect_bid_anomalies`, and `verify_retention_policy` via cron / Windows Task Scheduler (no in-app scheduler exists in this project — same convention as the existing `anonymise_deleted_users` command).
4. Decide whether to act on the two review-only items in §4 before a real production deployment.
