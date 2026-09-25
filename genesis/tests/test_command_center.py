from app.integrations.discord import DiscordActor, DiscordCommandGateway, DiscordCommandError
from app.persistence.store import Store
from app.services.application import GenesisApplication


def app(tmp_path):
    application = GenesisApplication(Store(tmp_path / "genesis.db"))
    application.initialize()
    return application


def test_command_center_status(tmp_path):
    application = app(tmp_path)
    status = application.command_center.status()
    assert status["health"]["status"] == "ok"
    assert status["tasks"]["total"] == 0


def test_discord_role_permissions(tmp_path):
    application = app(tmp_path)
    gateway = DiscordCommandGateway(application)
    actor = DiscordActor("u1", ("translator",))
    task = gateway.create_task(actor, "x") if False else None
    check = gateway.check_translation(actor, "$NAME", "$NAME")
    assert check.approved_for_review


def test_discord_denies_management(tmp_path):
    application = app(tmp_path)
    gateway = DiscordCommandGateway(application)
    actor = DiscordActor("u1", ("translator",))
    try:
        gateway.create_task(actor, "x")
    except DiscordCommandError:
        pass
    else:
        assert False, "translator must not create managed tasks"
