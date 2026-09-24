from __future__ import annotations

import argparse
import json

from app.services.jobs import audit, glossary_sync, health, report, sync


def main() -> int:
    parser = argparse.ArgumentParser(description="MD Farsi Localization Platform jobs")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("sync")
    report_parser = sub.add_parser("report")
    report_parser.add_argument("--period", choices=("daily", "weekly"), default="daily")
    sub.add_parser("glossary-sync")
    sub.add_parser("health")
    sub.add_parser("audit")

    args = parser.parse_args()
    if args.command == "sync":
        result = sync()
    elif args.command == "report":
        result = report(args.period)
    elif args.command == "glossary-sync":
        result = glossary_sync()
    elif args.command == "health":
        result = health()
    else:
        result = audit()

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
