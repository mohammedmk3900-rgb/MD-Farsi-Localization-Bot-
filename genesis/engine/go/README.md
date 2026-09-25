# Genesis Go Worker

Go is the concurrent service lane of Genesis.

Reserved for long-lived background workers and network-facing jobs. Python remains authoritative for Genesis business rules and SQLite state transitions.

Planned workers include ParaTranz synchronization, Discord notification delivery, and scheduled background jobs.

The first implementation intentionally exposes only a health endpoint until a real worker workload is attached.
