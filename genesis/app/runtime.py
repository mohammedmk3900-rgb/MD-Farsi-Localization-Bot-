from pathlib import Path
import os
from app.persistence.store import Store
from app.services.application import GenesisApplication

def build_application() -> GenesisApplication:
    app = GenesisApplication(Store(Path(os.getenv("GENESIS_DB", "data/genesis.db"))))
    app.initialize()
    return app
