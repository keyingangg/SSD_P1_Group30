# Data Retention & Referential Integrity Policy

_SecureBid — Sprint 3 (Suspicious activity alerting & audit integrity)_
_Requirements: NFSR-AC-07 · FSR-AC-09 · FSR-AC-10 · NFR-06 · FSR-IN-03 · FSR-IN-07_

## 1. Retention windows

| Log class    | Minimum retention | Legal basis                          |
|--------------|-------------------|--------------------------------------|
| General audit logs | **≥ 3 years** | Singapore Companies Act (§199 — accounting/records) |
| Payment logs | **≥ 5 years** | MAS guidelines (financial records)   |

These floors are declared in `backend/securebid/settings/base.py` as
`AUDIT_LOG_RETENTION_YEARS = 3` and `PAYMENT_LOG_RETENTION_YEARS = 5`.

A "payment log" is any `audit_logs` row whose `action` is in
`core.audit.PAYMENT_ACTIONS` or whose `resource_type` is in
`core.audit.PAYMENT_RESOURCE_TYPES` (`{"Order"}`). All other audit rows are
general logs.

## 2. How the floor is enforced

Retention is enforced as a **minimum floor, not an auto-purge.** Records are
never deleted:

- **Append-only trigger.** `audit_logs` carries a `BEFORE UPDATE OR DELETE`
  trigger (`prevent_audit_update_delete`, function `prevent_audit_modification`)
  that raises `audit_logs is append-only`. Defined in
  `backend/core/migrations/0002_audit_constraints.py`. The trigger fires for
  every role, including superusers.
- **Privilege revocation.** `REVOKE UPDATE, DELETE ON TABLE audit_logs FROM
  PUBLIC` removes the grant as a secondary defence.
- **Application-level guard.** `core.models.AuditLog.save()` raises on any
  attempt to modify an existing row; `default_permissions = ("add", "view")`.
- **Payment records.** `payments.Order` rows are protected from cascade
  deletion — both `winner` and `winning_bid` (and `listing`) use `PROTECT`, so a
  user or bid deletion cannot erase a payment record inside its 5-year window.

Because rows can never be updated or deleted, any record younger than its
retention window is structurally guaranteed to still exist. There is a
**deliberate decision not to auto-purge** past the window: purging would weaken
the tamper-evidence chain (per-row SHA-256 hashing, FSR-IN-07) and conflict with
the append-only guarantee.

## 3. Relationship to PDPA anonymisation

PDPA "right to erasure" is satisfied by **anonymise-in-place**, not deletion:
the PII columns are scrubbed while the row is retained. This preserves
audit-trail continuity and the retention floor simultaneously. `audit_logs.user`
is intentionally `db_constraint=False` / `on_delete=DO_NOTHING`, so audit rows
survive user-account removal.

## 4. Verification

Two management commands assert the guarantees (read-only; they never delete):

- `python manage.py verify_retention_policy` — reports audit/payment log counts
  and the age of the oldest rows against the retention floor, and confirms the
  append-only invariant (no update/delete path). Read-only.
- `python manage.py verify_integrity` — see the FK matrix below.

These pair with Sim Jun An's scheduled SHA-256 hash-verify job and can run on the
same cadence (systemd timer / cron).

## 5. Referential-integrity (on_delete) matrix

| Relationship (FK)                | on_delete   | Rationale |
|----------------------------------|-------------|-----------|
| `Bid.listing → Listing`          | **CASCADE** | Bids are meaningless without their listing. |
| `Bid.bidder → User`              | **CASCADE** | Bids belong to a user; removed with a hard user delete (normal deletion is anonymise-in-place). |
| `Order.winner → User`            | **PROTECT** | A payment record must survive a hard user delete (5-yr retention). |
| `Order.winning_bid → Bid`        | **PROTECT** | The winning bid is the basis of the charge; must not vanish. |
| `Order.listing → Listing`        | **PROTECT** | A payment record must always resolve the auction it paid for. |
| `Listing.created_by → User`      | **CASCADE** | A seller's listings are removed with a hard user delete. |
| `Listing.winner → User`          | **SET_NULL**| The listing outlives the winner reference. |
| `AuditLog.user → User`           | **DO_NOTHING** (`db_constraint=False`) | Audit rows must survive user deletion; no DB FK by design. |

`verify_integrity` asserts each row above: real FK constraints for the `bids`
and `orders` relationships, and the deliberate **absence** of a DB constraint on
`audit_logs.user_id`.
