from pathlib import Path
from app.runtime import build_application

def test_application_boots(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("GENESIS_DB", str(tmp_path / "genesis.db"))
    app = build_application()
    app.audit("boot", "test", {"ok": True})
    assert app.store.events()[0]["event_type"] == "boot"
