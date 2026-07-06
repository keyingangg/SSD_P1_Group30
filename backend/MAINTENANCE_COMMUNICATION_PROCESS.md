# Planned Maintenance and Communication Process (NFSR-AV-01)

This runbook defines how SecureBid schedules planned maintenance outside active auction windows and how users are informed.

## Objective

- Schedule maintenance only when no auction activity window is affected.
- Communicate maintenance clearly and early to bidders, sellers, and admins.
- Keep an audit trail of all maintenance notices and execution timestamps.

## Scheduling Rule

Planned maintenance is approved only if the requested downtime window does not overlap any listing where:

- `status` is not `draft` or `cancelled`, and
- listing auction time window intersects maintenance window (`starts_at < maintenance_end` and `ends_at > maintenance_start`).

## Pre-Maintenance Validation (Required)

Run this command before approving a window:

```bash
cd backend
python manage.py check_maintenance_window --start <ISO-8601> --end <ISO-8601>
```

Example:

```bash
python manage.py check_maintenance_window --start 2026-07-10T01:00:00+08:00 --end 2026-07-10T02:00:00+08:00
```

Expected outcomes:

- `OK: No auction window overlap detected` -> window can proceed to communication and approval.
- `BLOCKED: ... overlap ...` -> choose a different window and re-check.

## Communication Timeline

Use all times in Singapore Time (SGT) for user-facing notices.

1. `T-72h`: first notice (planned start/end, expected impact, support contact).
2. `T-24h`: reminder notice.
3. `T-1h`: final reminder.
4. `T-0`: maintenance start notice.
5. `T+completion`: maintenance complete and service restored notice.

## Communication Channels

- In-app banner (if frontend is available before downtime).
- Email notice to registered users.
- Admin operations channel (internal).
- Optional status page/update post.

## Message Template

Subject: Planned Maintenance Notice - SecureBid

Body:

- Window: `<start time>` to `<end time>` SGT
- Impact: bidding, listing updates, and checkout may be unavailable during this period.
- Reason: planned maintenance for reliability/security updates.
- Action for users: place critical bids before maintenance start.
- Support: `<support contact>`

Completion message should include:

- Actual start and end times.
- Confirmation that auction services are restored.
- Incident reference if rollback/degradation occurred.

## Execution Checklist

1. Run `check_maintenance_window` and capture output.
2. Record approved maintenance ticket ID.
3. Send notices at T-72h, T-24h, T-1h.
4. Post T-0 start notice.
5. Execute maintenance changes.
6. Validate API health and critical auction endpoints.
7. Post completion notice with actual timestamps.
8. Archive communication artifacts with ticket reference.

## Post-Maintenance Verification

- Confirm auction list/detail endpoints are responsive.
- Confirm bid submission endpoint is responsive.
- Confirm no unexpected auction status transitions occurred.
- Log final outcome in operations notes.

## Evidence for NFSR-AV-01

Store these artifacts per maintenance event:

- `check_maintenance_window` command output.
- Copies/screenshots of each notice sent.
- Start/complete timestamps.
- Any incident or rollback notes.
