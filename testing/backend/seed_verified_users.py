#!/usr/bin/env python3
"""Create or update verified test users for NFSR load testing.

This script is idempotent:
- Creates missing users.
- Updates existing users to be active, verified, and non-staff.
- Exports a users CSV usable by test_system_load.py / load_test_nfsr_av_02.py.

Example:
  python testing/backend/seed_verified_users.py \
    --count 200 \
    --email-prefix nfsr_user \
    --domain example.test \
    --password StrongPass123! \
    --output-csv testing/backend/users.csv
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed verified users for load tests")
    parser.add_argument("--count", type=int, default=200, help="Number of users to seed")
    parser.add_argument("--email-prefix", default="nfsr_user", help="Email local-part prefix")
    parser.add_argument("--domain", default="example.test", help="Email domain")
    parser.add_argument("--password", default="StrongPass123!", help="Password for all seeded users")
    parser.add_argument(
        "--output-csv",
        default="testing/backend/users.csv",
        help="CSV output path (email,password)",
    )
    parser.add_argument(
        "--settings-module",
        default="securebid.settings.development",
        help="Django settings module",
    )
    return parser.parse_args()


def bootstrap_django(settings_module: str) -> Path:
    script_path = Path(__file__).resolve()
    repo_root = script_path.parents[2]
    backend_dir = repo_root / "backend"

    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module)

    import django  # pylint: disable=import-outside-toplevel

    django.setup()
    return repo_root


def seed_users(args: argparse.Namespace) -> tuple[int, int, list[tuple[str, str]]]:
    from django.contrib.auth import get_user_model  # pylint: disable=import-outside-toplevel

    User = get_user_model()
    created = 0
    updated = 0
    creds: list[tuple[str, str]] = []

    for i in range(1, args.count + 1):
        email = f"{args.email_prefix}{i:03d}@{args.domain}"
        display_name = f"NFSR User {i:03d}"

        user = User.objects.filter(email=email).first()
        if user is None:
            User.objects.create_user(
                email=email,
                display_name=display_name,
                password=args.password,
                is_active=True,
                is_email_verified=True,
                is_staff=False,
                is_superuser=False,
            )
            created += 1
        else:
            user.display_name = display_name
            user.is_active = True
            user.is_email_verified = True
            user.is_staff = False
            user.is_superuser = False
            user.set_password(args.password)
            user.save(update_fields=[
                "display_name",
                "is_active",
                "is_email_verified",
                "is_staff",
                "is_superuser",
                "password",
            ])
            updated += 1

        creds.append((email, args.password))

    return created, updated, creds


def write_csv(repo_root: Path, output_csv: str, creds: list[tuple[str, str]]) -> Path:
    output_path = Path(output_csv)
    if not output_path.is_absolute():
        output_path = repo_root / output_path

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["email", "password"])
        writer.writerows(creds)

    return output_path


def main() -> int:
    args = parse_args()

    if args.count < 1:
        print("ERROR: --count must be >= 1", file=sys.stderr)
        return 2

    repo_root = bootstrap_django(args.settings_module)
    created, updated, creds = seed_users(args)
    csv_path = write_csv(repo_root, args.output_csv, creds)

    print(f"Seed complete. Created: {created}, Updated: {updated}, Total: {len(creds)}")
    print(f"CSV written: {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
