# PDPA Compliance — SecureBid Platform

**Requirements covered:** NFSR-C-08 · NFSR-C-03 · FSR-C-04 · FSR-C-09 · NFR-04 · SFR-05c

---

## 1. PII Collected and Legal Basis

| Field | Location | Purpose | Basis |
|-------|----------|---------|-------|
| `email` | `users.email` | Account authentication and email verification | Contract / legitimate interest |
| `display_name` | `users.display_name` | User-facing identity label | Contract |
| Delivery address | `orders.delivery_address_snapshot` | One-time fulfilment snapshot captured at checkout only | Contract |

**What is NOT collected:**
- Government-issued ID numbers (NFSR-C-08)
- Financial account numbers, card numbers, or CVV (NFSR-C-03 / FSR-C-09)
- Full card data of any kind — handled exclusively by Stripe Elements client-side

---

## 2. Payment Data Flow (Stripe)

```
Browser (Stripe.js / Elements)
    │  card number, expiry, CVV entered client-side
    │  never transmitted to SecureBid backend
    ▼
Stripe API ──► returns { client_secret, payment_intent_id }
    │
    ▼
SecureBid backend stores ONLY:
    • stripe_payment_intent_id  (opaque reference string, not card data)
    • stripe_idempotency_key    (UUID for duplicate-charge prevention)
    • fulfillment_status        (pending_payment / paid / shipped / …)
```

**Verification (NFSR-C-03 / FSR-C-04):**
- Raw card numbers, CVV, and expiry dates are **never** transmitted to or stored on the application backend.
- The backend calls `stripe.PaymentIntent.create()` with an amount and currency only; no card data is passed.
- Webhook events are verified with HMAC-SHA256 (`STRIPE_WEBHOOK_SECRET`) before processing.
- `stripe_payment_intent_id` is a Stripe-side opaque reference; it contains no cardholder data.

**Payment data retention (NFR-04):**
- Payment intent details are not retained beyond what Stripe stores on their platform.
- The `Order` record stores only the intent ID and fulfilment status.
- Once an order reaches `delivered` status, no further Stripe API calls are made and no additional data is stored.

---

## 3. Data Flows

### 3.1 Registration
```
User supplies: email, display_name, password
→ Password hashed with Argon2id (never stored in plaintext)
→ EmailVerificationToken created (one-time, expires in 24 h)
→ Verification email sent (email address used once for delivery)
```

### 3.2 Login
```
User supplies: email, password (+ optional TOTP)
→ AuditLog records: user_id, action, IP address, user_agent, device_fingerprint (SHA-256 hash of IP+UA), timestamp
→ Session created (30-minute inactivity timeout, HttpOnly + SameSite=Strict cookies)
→ UserSessionRecord stores IP+UA for new-device notification only
```

### 3.3 Checkout
```
User supplies: delivery address (entered in checkout form)
→ Stored as orders.delivery_address_snapshot (text snapshot)
→ Stripe Elements: card data collected client-side, tokenised by Stripe, never reaches backend
→ AuditLog records: action=CHECKOUT_INITIATED, order_id, amount (no card data)
```

### 3.4 Account Deletion
```
User (or admin) requests deletion
→ Sessions invalidated immediately (all devices)
→ AuditLog entry written: action=account_deleted, user_id, timestamp
→ anonymise_user_data() called immediately:
    • users.email          → deleted-{uuid}@anon.invalid
    • users.display_name   → "Deleted User"
    • users.password       → unusable (argon2 placeholder)
    • users.is_active      → False
    • users.deleted_at     → timestamp
    • users.is_anonymised  → True
    • orders.delivery_address_snapshot → "[REDACTED]"
    • audit_logs.ip_address, user_agent, device_fingerprint → scrubbed
    • Auth tokens, MFA device, session records → hard-deleted
→ Bid and Order records preserved with anonymised bidder identity (auction integrity)
```

---

## 4. PII Anonymisation Job (NFSR-C-08 · SFR-05c)

Anonymisation is applied **immediately** on account deletion. The management command acts as a scheduled safety net.

### Management Command

```bash
# Run daily via cron or task scheduler
python manage.py anonymise_deleted_users

# Check what would be anonymised (no changes made)
python manage.py anonymise_deleted_users --dry-run

# Force-run for accounts deleted at any time (not just 30-day window)
python manage.py anonymise_deleted_users --days 0
```

### Recommended Cron (Linux/Docker)
```cron
0 2 * * * cd /app && python manage.py anonymise_deleted_users >> /var/log/anonymise.log 2>&1
```

### What is anonymised

| Record | Fields scrubbed | Fields preserved |
|--------|----------------|-----------------|
| `users` | email, display_name, password, is_active | id (UUID), created_at, deleted_at |
| `orders` | delivery_address_snapshot → `[REDACTED]` | id, stripe_payment_intent_id, fulfillment_status, winning_bid_id, timestamps |
| `audit_logs` | ip_address → null, user_agent → "", device_fingerprint → "" | action, timestamp, resource_type/id, before_data, after_data, role |
| `email_verification_tokens` | Entire record deleted | — |
| `password_reset_tokens` | Entire record deleted | — |
| `staff_invite_tokens` | Entire record deleted | — |
| `user_session_records` | Entire record deleted | — |
| `otp_totp_totpdevice` | Entire record deleted | — |
| `account_lockout_profiles` | Entire record deleted | — |

### What is preserved (auction integrity)

| Record | Rationale |
|--------|-----------|
| `bids` | Bid history required for auction integrity and dispute resolution; `anonymous_identifier` (e.g. "Bidder #4729") used for public display |
| `orders` | Payment record required for fulfilment, chargebacks, and regulatory audit |
| `audit_logs` | Security event trail required for forensics; PII fields scrubbed |
| `listings` | Item records; `winner` FK already SET_NULL on user deletion |

---

## 5. Audit Log PII Handling

Audit logs are append-only by design (integrity). On account deletion, PII fields are scrubbed via direct `QuerySet.update()` (bypasses the append-only guard), and `row_hash` is overwritten to `[PII_ANONYMISED]` to signal redaction. Action, timestamps, resource IDs, and non-PII metadata are retained for security audit purposes.

---

## 6. Data Minimisation (NFSR-C-08 · FSR-C-09)

- No government-issued IDs, passport numbers, or NRIC collected at any point.
- No financial account numbers stored; Stripe holds tokenised card data under their own PCI DSS compliance.
- Delivery address is captured only at checkout (not at registration) and only once per order.
- Device fingerprint in audit logs is a one-way SHA-256 hash of IP + User-Agent; not reversible to the original IP alone without the User-Agent.
- Bid records display only `anonymous_identifier` publicly; `bidder_id` is internal and FK-linked to the now-anonymised user row after deletion.

---

## 7. Relevant Code Locations

| Component | File |
|-----------|------|
| Anonymisation service | `accounts/anonymisation.py` |
| Management command | `accounts/management/commands/anonymise_deleted_users.py` |
| Self-deletion view | `accounts/views.py` → `DeleteAccountView` |
| Admin deletion view | `accounts/views.py` → `AdminUserDetailView.delete()` |
| Stripe client (no card data) | `payments/stripe_client.py` |
| Payment intent creation | `payments/views.py` → `CreatePaymentIntentView` |
| Audit log model | `core/models.py` → `AuditLog` |
| User model (soft-delete fields) | `accounts/models.py` → `User.is_anonymised`, `User.anonymised_at` |
