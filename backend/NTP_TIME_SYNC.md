# UTC Time Synchronisation (NFSR-AC-06 · FSR-AC-08 · NFSR-IN-01)

## What the application already guarantees

Every timestamp in SecureBid is generated with `django.utils.timezone.now()` —
there are zero uses of naive `datetime.now()`/`datetime.utcnow()` anywhere in
the codebase. With `USE_TZ=True` (`securebid/settings/base.py`), Django stores
every `DateTimeField` as UTC in Postgres regardless of the `TIME_ZONE`
setting, which only affects display/local-time conversion, never storage.

This means:
- `AuditLog.timestamp` and `Bid.submitted_at` are already generated from the
  same UTC clock source, and the same value used to hash a row
  (`core/audit.py`'s `log_action`) is the value stored — no skew between the
  two.
- `Listing.finalize_if_ended()`'s tie-break ordering
  (`order_by("-amount", "submitted_at", "id")`) is deterministic *as long as
  the host clock producing `submitted_at` values across concurrent requests
  is itself correct*.

**Do not change `TIME_ZONE="Asia/Singapore"` to `"UTC"` to "fix" this** — it
does not affect what's stored, only how it's displayed, and doing so would
break the existing display/email timestamp behaviour for no integrity gain.

## What still depends on OS-level NTP

The one thing application code cannot guarantee is that the *host clock*
`timezone.now()` reads from is accurate. If the EC2 instance's system clock
drifts, every timestamp generated on that host drifts with it — silently
breaking bid tie-break determinism and audit log timeline ordering across
components (e.g. if the app server and DB server clocks diverge).

### Required OS configuration

**EC2 (Ubuntu, current deployment target — see `.github/workflows/deploy.yml`):**
Use `chrony` synced to the Amazon Time Sync Service, which is reachable from
any EC2 instance without an internet route:

```bash
sudo apt-get install -y chrony
echo "server 169.254.169.123 prefer iburst minpoll 4 maxpoll 4" | sudo tee /etc/chrony/sources.d/aws.sources
sudo systemctl restart chronyd
timedatectl status   # confirm "System clock synchronized: yes"
```

Ensure the OS timezone is UTC (application code doesn't need this, but it
avoids a whole class of "was that log line local or UTC" confusion when
reading raw system/nginx logs alongside Django's):

```bash
sudo timedatectl set-timezone UTC
```

**Any other host running this app (dev VMs, CI runners, additional app
servers if this is scaled horizontally):** enable `systemd-timesyncd`
(Linux) or confirm the cloud provider's built-in NTP service is active.
Windows hosts should confirm the W32Time service is running and pointed at
a reliable NTP source.

**Database server:** if Postgres ever runs on a host separate from the app
server (currently Supabase-hosted, out of this project's OS-config scope),
confirm it is also NTP-synchronised — a drifted DB server clock affects
`NOW()`-based defaults and any DB-side triggers, independent of what the
Django app sends.

### Automated verification

The OS-level NTP client keeps the clock correct; `check_clock_drift`
(`core/management/commands/check_clock_drift.py`) is the automated check that
verifies it's actually doing so. It queries an NTP server (`NTP_SERVER`
setting, default `pool.ntp.org` — override to `169.254.169.123` in production
to match the Amazon Time Sync Service above), compares the offset against
`CLOCK_DRIFT_ALERT_THRESHOLD_SECONDS` (default 2s), and fires a security
alert (`core/alerts.py`) plus a `clock_drift_detected` audit log entry if
exceeded. Scheduled hourly via `backend/cron/securebid-cron`.

```bash
python manage.py check_clock_drift
python manage.py check_clock_drift --server 169.254.169.123
```
