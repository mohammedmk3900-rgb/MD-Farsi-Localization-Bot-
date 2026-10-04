from __future__ import annotations

import argparse
import logging
import os

from app.services.scheduler import build_scheduler


def main() -> int:
    parser = argparse.ArgumentParser(description="MD Farsi autonomous operations scheduler")
    parser.add_argument("--once", action="store_true", help="Run all due jobs once and exit")
    parser.add_argument("--poll-seconds", type=int, default=int(os.getenv("SCHEDULER_POLL_SECONDS", "30")))
    parser.add_argument("--lease-seconds", type=int, default=int(os.getenv("SCHEDULER_LEASE_SECONDS", "900")))
    args = parser.parse_args()

    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    scheduler = build_scheduler(args.poll_seconds, args.lease_seconds)
    if args.once:
        results = scheduler.run_once()
        return 1 if any(item["status"] == "failed" for item in results) else 0

    scheduler.run_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
