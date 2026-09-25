from pathlib import Path

from app.engine import GoWorkerClient, RustEngineClient


def test_go_client_builds_from_environment(monkeypatch):
    monkeypatch.setenv("GENESIS_GO_URL", "http://127.0.0.1:8090")
    client = GoWorkerClient.from_env()
    assert client is not None
    assert client.base_url == "http://127.0.0.1:8090"


def test_rust_client_builds_from_environment(monkeypatch):
    monkeypatch.setenv("GENESIS_RUST_ENGINE", str(Path("/tmp/genesis-engine")))
    client = RustEngineClient.from_env()
    assert client is not None
    assert client.executable.endswith("genesis-engine")
