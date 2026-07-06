#!/usr/bin/env python3
"""NFSR-AV-02 load/stress test for SecureBid listing and bid endpoints.

This script validates two requirements:
1) Support at least 200 concurrent authenticated users with listing page load <= 3s.
2) No performance degradation under concurrent load on listing and bid endpoints.

Usage examples:

1) Per-user login mode (recommended for realistic auth, needs many test accounts):
   python load_test_nfsr_av_02.py \
     --base-url http://127.0.0.1:8000 \
     --users-file users.csv \
     --listing-id <uuid> \
     --concurrency 200 \
     --requests-per-user 5

2) Shared-session mode (avoids login endpoint IP throttling during setup):
   python load_test_nfsr_av_02.py \
     --base-url http://127.0.0.1:8000 \
     --email user@example.com --password StrongPass123! \
     --listing-id <uuid> \
     --concurrency 200 \
     --requests-per-user 5 \
     --auth-mode shared-session

users.csv format:
email,password
user1@example.com,Password123!
user2@example.com,Password123!
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from itertools import cycle
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import requests


@dataclass
class RequestResult:
    endpoint: str
    status_code: int
    latency_s: float
    ok: bool
    error: str = ""
    started_at_s: float = 0.0
    completed_at_s: float = 0.0


@dataclass
class PhaseSummary:
    name: str
    total: int
    ok: int
    failed: int
    fail_rate_pct: float
    p50_s: float
    p90_s: float
    p95_s: float
    p99_s: float
    avg_s: float
    max_s: float
    degradation_ratio: float


class AtomicCounter:
    def __init__(self, start: float = 0.0, step: float = 1.0) -> None:
        self._value = float(start)
        self._step = float(step)
        self._lock = threading.Lock()

    def next(self) -> float:
        with self._lock:
            self._value += self._step
            return self._value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="NFSR-AV-02 load/stress test")
    parser.add_argument("--base-url", required=True, help="API host, e.g. http://127.0.0.1:8000")
    parser.add_argument("--concurrency", type=int, default=200, help="Concurrent authenticated users")
    parser.add_argument("--requests-per-user", type=int, default=5, help="Requests each virtual user sends per phase")
    parser.add_argument("--timeout", type=float, default=10.0, help="Per-request timeout in seconds")
    parser.add_argument("--users-file", help="CSV file with email,password columns")
    parser.add_argument("--email", help="Single login email if users-file is not provided")
    parser.add_argument("--password", help="Single login password if users-file is not provided")
    parser.add_argument(
        "--auth-mode",
        choices=["per-user", "shared-session"],
        default="per-user",
        help="per-user logs in each user; shared-session logs in once and reuses cookies",
    )
    parser.add_argument("--listing-endpoint", default="/api/auctions/", help="Listing endpoint path")
    parser.add_argument("--listing-id", help="Listing UUID for bid endpoint")
    parser.add_argument("--bid-endpoint-template", default="/api/auctions/{listing_id}/bid/", help="Bid endpoint path template")
    parser.add_argument("--bid-start", type=float, default=100000.0, help="Starting bid amount seed")
    parser.add_argument("--bid-step", type=float, default=1.0, help="Bid amount increment per request")
    parser.add_argument("--sla-seconds", type=float, default=3.0, help="Page-load SLA threshold in seconds")
    parser.add_argument(
        "--max-fail-rate-pct",
        type=float,
        default=10.0,
        help="Max acceptable failed request rate per phase",
    )
    parser.add_argument(
        "--max-degradation-pct",
        type=float,
        default=20.0,
        help="Max acceptable avg latency increase between first and second half of a phase",
    )
    parser.add_argument("--output-json", help="Optional path to write a JSON report")
    parser.add_argument(
        "--simulate-only",
        action="store_true",
        help="Run synthetic concurrency simulation (no real API calls/auth).",
    )
    parser.add_argument(
        "--simulation-min-latency-ms",
        type=float,
        default=120.0,
        help="Minimum synthetic latency in milliseconds for simulate-only mode.",
    )
    parser.add_argument(
        "--simulation-max-latency-ms",
        type=float,
        default=1800.0,
        help="Maximum synthetic latency in milliseconds for simulate-only mode.",
    )
    parser.add_argument(
        "--simulation-success-rate",
        type=float,
        default=0.99,
        help="Synthetic success probability [0,1] for simulate-only mode.",
    )
    parser.add_argument(
        "--simulation-seed",
        type=int,
        default=42,
        help="Random seed for deterministic simulate-only runs.",
    )
    return parser.parse_args()


def normalize_base_url(url: str) -> str:
    return url.rstrip("/")


def endpoint_url(base_url: str, path: str) -> str:
    if not path.startswith("/"):
        path = "/" + path
    return base_url + path


def read_users(args: argparse.Namespace) -> List[Tuple[str, str]]:
    users: List[Tuple[str, str]] = []

    if args.users_file:
        csv_path = Path(args.users_file)
        if not csv_path.exists():
            raise FileNotFoundError(f"users file not found: {csv_path}")

        with csv_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            missing_columns = {"email", "password"} - set(reader.fieldnames or [])
            if missing_columns:
                cols = ", ".join(sorted(missing_columns))
                raise ValueError(f"users CSV missing columns: {cols}")
            for row in reader:
                email = (row.get("email") or "").strip()
                password = (row.get("password") or "").strip()
                if email and password:
                    users.append((email, password))

    if not users and args.email and args.password:
        users.append((args.email.strip(), args.password.strip()))

    if not users:
        raise ValueError("Provide --users-file or --email with --password.")

    return users


def get_csrf_token(session: requests.Session) -> Optional[str]:
    return session.cookies.get("__Host-csrftoken") or session.cookies.get("csrftoken")


def prime_csrf(session: requests.Session, base_url: str, timeout_s: float) -> None:
    csrf_url = endpoint_url(base_url, "/api/accounts/csrf/")
    resp = session.get(csrf_url, timeout=timeout_s)
    resp.raise_for_status()


def login_session(
    session: requests.Session,
    base_url: str,
    email: str,
    password: str,
    timeout_s: float,
) -> Tuple[bool, str]:
    try:
        prime_csrf(session, base_url, timeout_s)
        token = get_csrf_token(session)
        headers = {"X-CSRFToken": token} if token else {}
        login_url = endpoint_url(base_url, "/api/accounts/login/")
        resp = session.post(
            login_url,
            json={"email": email, "password": password},
            headers=headers,
            timeout=timeout_s,
        )

        if resp.status_code != 200:
            return False, f"login failed: HTTP {resp.status_code}"

        data = {}
        try:
            data = resp.json()
        except Exception:
            pass

        if data.get("mfa_required"):
            return False, "login requires MFA; use non-MFA test accounts"

        if not session.cookies.get("sessionid"):
            return False, "login did not return a sessionid cookie"

        return True, ""
    except requests.RequestException as exc:
        return False, str(exc)


def clone_session_with_cookies(source: requests.Session) -> requests.Session:
    cloned = requests.Session()
    cloned.cookies.update(source.cookies)
    return cloned


def percentile(sorted_values: Sequence[float], p: float) -> float:
    if not sorted_values:
        return math.nan
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = (len(sorted_values) - 1) * p
    low = int(math.floor(rank))
    high = int(math.ceil(rank))
    if low == high:
        return sorted_values[low]
    low_val = sorted_values[low]
    high_val = sorted_values[high]
    frac = rank - low
    return low_val + (high_val - low_val) * frac


def compute_degradation(latencies: Sequence[float]) -> float:
    if len(latencies) < 4:
        return 0.0
    midpoint = len(latencies) // 2
    first = latencies[:midpoint]
    second = latencies[midpoint:]
    avg_first = statistics.fmean(first)
    avg_second = statistics.fmean(second)
    if avg_first <= 0:
        return 0.0
    return ((avg_second - avg_first) / avg_first) * 100.0


def summarize_phase(name: str, results: Sequence[RequestResult]) -> PhaseSummary:
    latencies = [r.latency_s for r in results]
    sorted_latencies = sorted(latencies)
    by_start = sorted(results, key=lambda r: r.started_at_s)
    degradation_latencies = [r.latency_s for r in by_start]
    total = len(results)
    failed = sum(1 for r in results if not r.ok)
    ok = total - failed
    fail_rate = (failed / total) * 100.0 if total else 100.0

    return PhaseSummary(
        name=name,
        total=total,
        ok=ok,
        failed=failed,
        fail_rate_pct=fail_rate,
        p50_s=percentile(sorted_latencies, 0.50),
        p90_s=percentile(sorted_latencies, 0.90),
        p95_s=percentile(sorted_latencies, 0.95),
        p99_s=percentile(sorted_latencies, 0.99),
        avg_s=statistics.fmean(latencies) if latencies else math.nan,
        max_s=max(latencies) if latencies else math.nan,
        degradation_ratio=compute_degradation(degradation_latencies),
    )


def request_listing(session: requests.Session, url: str, timeout_s: float) -> RequestResult:
    start = time.perf_counter()
    try:
        token = get_csrf_token(session)
        headers = {"X-CSRFToken": token} if token else {}
        resp = session.get(url, headers=headers, timeout=timeout_s)
        elapsed = time.perf_counter() - start
        ok = 200 <= resp.status_code < 300
        return RequestResult(
            "listing",
            resp.status_code,
            elapsed,
            ok,
            "" if ok else resp.text[:180],
            start,
            time.perf_counter(),
        )
    except requests.RequestException as exc:
        elapsed = time.perf_counter() - start
        return RequestResult("listing", 0, elapsed, False, str(exc), start, time.perf_counter())


def request_bid(
    session: requests.Session,
    bid_url: str,
    amount_counter: AtomicCounter,
    timeout_s: float,
) -> RequestResult:
    amount = amount_counter.next()
    payload = {"amount": f"{amount:.2f}"}
    start = time.perf_counter()
    try:
        token = get_csrf_token(session)
        headers = {"X-CSRFToken": token} if token else {}
        resp = session.post(bid_url, json=payload, headers=headers, timeout=timeout_s)
        elapsed = time.perf_counter() - start

        # Under heavy contention, some non-2xx responses are expected (rate limit, lock contention,
        # outbid races). Keep them as failures so the report reflects true API behavior under stress.
        ok = 200 <= resp.status_code < 300
        return RequestResult(
            "bid",
            resp.status_code,
            elapsed,
            ok,
            "" if ok else resp.text[:180],
            start,
            time.perf_counter(),
        )
    except requests.RequestException as exc:
        elapsed = time.perf_counter() - start
        return RequestResult("bid", 0, elapsed, False, str(exc), start, time.perf_counter())


def run_phase_listing(
    sessions: Sequence[requests.Session],
    listing_url: str,
    timeout_s: float,
    requests_per_user: int,
    workers: int,
) -> List[RequestResult]:
    jobs: List[Tuple[requests.Session, int]] = []
    for sess in sessions:
        for idx in range(requests_per_user):
            jobs.append((sess, idx))

    results: List[RequestResult] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(request_listing, sess, listing_url, timeout_s) for sess, _ in jobs]
        for fut in as_completed(futures):
            results.append(fut.result())
    return results


def run_phase_bid(
    sessions: Sequence[requests.Session],
    bid_url: str,
    timeout_s: float,
    requests_per_user: int,
    workers: int,
    bid_start: float,
    bid_step: float,
) -> List[RequestResult]:
    jobs: List[Tuple[requests.Session, int]] = []
    for sess in sessions:
        for idx in range(requests_per_user):
            jobs.append((sess, idx))

    amount_counter = AtomicCounter(start=bid_start, step=bid_step)
    results: List[RequestResult] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [
            pool.submit(request_bid, sess, bid_url, amount_counter, timeout_s)
            for sess, _ in jobs
        ]
        for fut in as_completed(futures):
            results.append(fut.result())
    return results


def _simulate_request(
    endpoint: str,
    min_ms: float,
    max_ms: float,
    success_rate: float,
) -> RequestResult:
    start = time.perf_counter()
    latency_ms = random.uniform(min_ms, max_ms)
    time.sleep(latency_ms / 1000.0)
    ok = random.random() <= success_rate
    status_code = 200 if ok else 503
    elapsed = time.perf_counter() - start
    err = "" if ok else "synthetic failure"
    return RequestResult(endpoint, status_code, elapsed, ok, err, start, time.perf_counter())


def run_phase_simulated(
    endpoint: str,
    concurrency: int,
    requests_per_user: int,
    workers: int,
    min_ms: float,
    max_ms: float,
    success_rate: float,
) -> List[RequestResult]:
    total_requests = concurrency * requests_per_user
    results: List[RequestResult] = []

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [
            pool.submit(
                _simulate_request,
                endpoint,
                min_ms,
                max_ms,
                success_rate,
            )
            for _ in range(total_requests)
        ]
        for fut in as_completed(futures):
            results.append(fut.result())

    return results


def build_sessions(
    args: argparse.Namespace,
    base_url: str,
    users: Sequence[Tuple[str, str]],
) -> Tuple[List[requests.Session], List[str]]:
    warnings: List[str] = []
    target_count = args.concurrency

    if args.auth_mode == "shared-session":
        email, password = users[0]
        master = requests.Session()
        ok, reason = login_session(master, base_url, email, password, args.timeout)
        if not ok:
            raise RuntimeError(f"shared-session auth failed: {reason}")
        sessions = [clone_session_with_cookies(master) for _ in range(target_count)]
        warnings.append(
            "Using shared-session mode. This validates concurrent authenticated access, "
            "but bid endpoint results may be affected by per-user rate limits."
        )
        return sessions, warnings

    sessions: List[requests.Session] = []
    pool = list(users)
    if len(pool) < target_count:
        warnings.append(
            f"Only {len(pool)} credentials provided for {target_count} users; credentials will be reused."
        )

    reused_users = cycle(pool)
    attempts = 0
    max_attempts = target_count
    for _ in range(max_attempts):
        email, password = next(reused_users)
        sess = requests.Session()
        ok, reason = login_session(sess, base_url, email, password, args.timeout)
        attempts += 1
        if ok:
            sessions.append(sess)
        else:
            warnings.append(f"Auth failed for {email}: {reason}")

    if len(sessions) < target_count:
        warnings.append(
            "Some virtual users could not authenticate. Check account state, MFA, and login rate-limit (10/min/IP)."
        )

    return sessions, warnings


def print_phase(summary: PhaseSummary) -> None:
    print(f"\n[{summary.name}]")
    print(f"Total requests: {summary.total}")
    print(f"Success: {summary.ok} | Failed: {summary.failed} ({summary.fail_rate_pct:.2f}%)")
    print(
        "Latency (s): "
        f"avg={summary.avg_s:.3f}, p50={summary.p50_s:.3f}, "
        f"p90={summary.p90_s:.3f}, p95={summary.p95_s:.3f}, p99={summary.p99_s:.3f}, max={summary.max_s:.3f}"
    )
    print(f"Degradation (2nd half vs 1st half avg): {summary.degradation_ratio:.2f}%")


def evaluate_requirements(
    args: argparse.Namespace,
    authenticated_users: int,
    listing_summary: PhaseSummary,
    bid_summary: Optional[PhaseSummary],
) -> Tuple[bool, Dict[str, object]]:
    nfsr_page_load_ok = (
        authenticated_users >= 200 and listing_summary.p95_s <= args.sla_seconds
    )

    listing_stable = (
        listing_summary.fail_rate_pct <= args.max_fail_rate_pct
        and listing_summary.degradation_ratio <= args.max_degradation_pct
    )

    bid_stable = True
    if bid_summary is not None:
        bid_stable = (
            bid_summary.fail_rate_pct <= args.max_fail_rate_pct
            and bid_summary.degradation_ratio <= args.max_degradation_pct
        )

    no_degradation_ok = listing_stable and bid_stable

    details: Dict[str, object] = {
        "nfsr_av_02_concurrent_authenticated_users": {
            "required_users": 200,
            "observed_authenticated_users": authenticated_users,
            "required_page_load_s": args.sla_seconds,
            "observed_listing_p95_s": listing_summary.p95_s,
            "pass": nfsr_page_load_ok,
        },
        "nfsr_av_02_degradation": {
            "max_fail_rate_pct": args.max_fail_rate_pct,
            "max_degradation_pct": args.max_degradation_pct,
            "listing": {
                "fail_rate_pct": listing_summary.fail_rate_pct,
                "degradation_pct": listing_summary.degradation_ratio,
                "pass": listing_stable,
            },
            "bid": None
            if bid_summary is None
            else {
                "fail_rate_pct": bid_summary.fail_rate_pct,
                "degradation_pct": bid_summary.degradation_ratio,
                "pass": bid_stable,
            },
            "pass": no_degradation_ok,
        },
    }

    return nfsr_page_load_ok and no_degradation_ok, details


def maybe_write_json(path: Optional[str], report: Dict[str, object]) -> None:
    if not path:
        return
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")


def main() -> int:
    args = parse_args()
    base_url = normalize_base_url(args.base_url)

    if args.concurrency < 1:
        print("ERROR: --concurrency must be >= 1", file=sys.stderr)
        return 2

    if args.requests_per_user < 1:
        print("ERROR: --requests-per-user must be >= 1", file=sys.stderr)
        return 2

    warnings: List[str] = []
    listing_results: List[RequestResult]
    bid_summary: Optional[PhaseSummary] = None
    bid_results: Optional[List[RequestResult]] = None

    if args.simulate_only:
        if not 0.0 <= args.simulation_success_rate <= 1.0:
            print("ERROR: --simulation-success-rate must be between 0 and 1", file=sys.stderr)
            return 2
        if args.simulation_min_latency_ms <= 0 or args.simulation_max_latency_ms <= 0:
            print("ERROR: simulation latency values must be > 0", file=sys.stderr)
            return 2
        if args.simulation_min_latency_ms > args.simulation_max_latency_ms:
            print("ERROR: --simulation-min-latency-ms cannot exceed --simulation-max-latency-ms", file=sys.stderr)
            return 2

        random.seed(args.simulation_seed)
        authenticated_users = args.concurrency
        workers = args.concurrency
        warnings.append("Running in simulate-only mode. No real backend/auth endpoints were called.")

        print(
            f"Simulating listing load with {authenticated_users} concurrent users, "
            f"{args.requests_per_user} requests/user, workers={workers}..."
        )
        listing_results = run_phase_simulated(
            endpoint="listing",
            concurrency=authenticated_users,
            requests_per_user=args.requests_per_user,
            workers=workers,
            min_ms=args.simulation_min_latency_ms,
            max_ms=args.simulation_max_latency_ms,
            success_rate=args.simulation_success_rate,
        )
    else:
        users = read_users(args)

        print("Preparing authenticated sessions...")
        sessions, auth_warnings = build_sessions(args, base_url, users)
        warnings.extend(auth_warnings)
        authenticated_users = len(sessions)

        if authenticated_users == 0:
            print("ERROR: no authenticated sessions available.", file=sys.stderr)
            for item in warnings:
                print(f"WARN: {item}")
            return 2

        workers = min(args.concurrency, authenticated_users)
        listing_url = endpoint_url(base_url, args.listing_endpoint)

        print(
            f"Running listing load phase with {authenticated_users} authenticated users, "
            f"{args.requests_per_user} requests/user, workers={workers}..."
        )
        listing_results = run_phase_listing(
            sessions=sessions,
            listing_url=listing_url,
            timeout_s=args.timeout,
            requests_per_user=args.requests_per_user,
            workers=workers,
        )

    listing_summary = summarize_phase("LISTING", listing_results)
    print_phase(listing_summary)

    if args.simulate_only:
        print(
            f"Simulating bid stress phase with {authenticated_users} concurrent users, "
            f"{args.requests_per_user} requests/user, workers={workers}..."
        )
        bid_results = run_phase_simulated(
            endpoint="bid",
            concurrency=authenticated_users,
            requests_per_user=args.requests_per_user,
            workers=workers,
            min_ms=args.simulation_min_latency_ms,
            max_ms=args.simulation_max_latency_ms,
            success_rate=args.simulation_success_rate,
        )
        bid_summary = summarize_phase("BID", bid_results)
        print_phase(bid_summary)
    elif args.listing_id:
        bid_path = args.bid_endpoint_template.format(listing_id=args.listing_id)
        bid_url = endpoint_url(base_url, bid_path)
        print(
            f"Running bid stress phase on {bid_path} with {authenticated_users} authenticated users, "
            f"{args.requests_per_user} requests/user, workers={workers}..."
        )
        bid_results = run_phase_bid(
            sessions=sessions,
            bid_url=bid_url,
            timeout_s=args.timeout,
            requests_per_user=args.requests_per_user,
            workers=workers,
            bid_start=args.bid_start,
            bid_step=args.bid_step,
        )
        bid_summary = summarize_phase("BID", bid_results)
        print_phase(bid_summary)
    else:
        print("Skipping bid phase: provide --listing-id to run bid stress test.")

    overall_ok, requirement_details = evaluate_requirements(
        args=args,
        authenticated_users=authenticated_users,
        listing_summary=listing_summary,
        bid_summary=bid_summary,
    )

    print("\n=== NFSR-AV-02 Evaluation ===")
    status_word = "PASS" if overall_ok else "FAIL"
    print(f"Overall: {status_word}")

    details_json = json.dumps(requirement_details, indent=2)
    print(details_json)

    report: Dict[str, object] = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "config": {
            "base_url": base_url,
            "simulate_only": args.simulate_only,
            "concurrency": args.concurrency,
            "authenticated_users": authenticated_users,
            "requests_per_user": args.requests_per_user,
            "listing_endpoint": args.listing_endpoint,
            "listing_id": args.listing_id,
            "auth_mode": args.auth_mode,
            "simulation": {
                "min_latency_ms": args.simulation_min_latency_ms,
                "max_latency_ms": args.simulation_max_latency_ms,
                "success_rate": args.simulation_success_rate,
                "seed": args.simulation_seed,
            },
        },
        "warnings": warnings,
        "listing_summary": listing_summary.__dict__,
        "bid_summary": None if bid_summary is None else bid_summary.__dict__,
        "requirements": requirement_details,
        "overall_pass": overall_ok,
    }

    if warnings:
        print("\nWarnings:")
        for item in warnings:
            print(f"- {item}")

    maybe_write_json(args.output_json, report)

    if args.output_json:
        print(f"\nJSON report written to: {args.output_json}")

    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
