from __future__ import annotations

from app.config import GenesisConfig
from app.persistence.store import Store
from app.services.application import GenesisApplication

def build_application(config: GenesisConfig | None = None) -> GenesisApplication:
    config = config or GenesisConfig.from_env()
    app = GenesisApplication(Store(config.database_path, busy_timeout_ms=config.busy_timeout_ms))
    app.initialize()
    return app