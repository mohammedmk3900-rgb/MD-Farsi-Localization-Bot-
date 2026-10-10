from __future__ import annotations

import os
import time

from app.runtime import build_application
from app.services.scheduling import ScheduledSyncRunner


def main() -> None:
    poll_seconds = max(5, int(os.getenv("GENESIS_SCHEDULER_POLL_SECONDS", "30")))
    interval_seconds = max(60, int(os.getenv("GENESIS_PARATRANZ_SYNC_INTERVAL_SECONDS", "3600")))
    application = build_application()
    runner = ScheduledSyncRunner(application, interval_seconds=interval_seconds)
    runner.register()
    print(f"V11 Genesis scheduler active; poll={poll_seconds}s sync_interval={interval_seconds}s")
    while True:
        try:
            runner.run_once()
        except Exception as exc:
            # Durable failure state and retry time are already recorded by the runner.
            print(f"Scheduled ParaTranz sync failed: {type(exc).__name__}: {exc}")
        time.sleep(poll_seconds)


if __name__ == "__main__":
    main()
