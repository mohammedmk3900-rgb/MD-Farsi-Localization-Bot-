from app.integrations.discord import DiscordGateway
from app.integrations.paratranz import ParaTranzIntegration
from app.services.command_center import CommandCenter
from app.services.application import GenesisApplication
from app.persistence.store import Store


class FakeParaTranz:
    def get_project(self, project_id: int):
        return {
            "words_total": 100,
            "strings_total": 20,
            "translated": 8,
            "reviewed": 5,
            "files": 2,
            "members": 3,
        }

    def get_terms(self, project_id: int):
        return [{"source": "Faction", "target": "اتحاد"}]


def test_paratranz_adapter_maps_project_stats():
    stats = ParaTranzIntegration(FakeParaTranz(), 19621).stats()
    assert stats.project_id == 19621
    assert stats.translated == 8
    assert stats.files == 2


def test_discord_gateway_registers_commands():
    gateway = DiscordGateway()
    gateway.register("status", "project.read", lambda: "ok")
    assert gateway.names() == ["status"]
    assert gateway.command("status").permission == "project.read"


def test_command_center_respects_permissions(tmp_path):
    app = GenesisApplication(Store(tmp_path / "db.sqlite"))
    center = CommandCenter(app)
    try:
        center.health("translator")
    except PermissionError:
        pass
    else:
        raise AssertionError("translator must not access health")
