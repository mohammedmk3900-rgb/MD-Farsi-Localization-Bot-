from pathlib import Path


def test_settings_default_database_is_platform_local():
    from app.config import PLATFORM_DIR, Settings

    settings = Settings()
    assert Path(settings.database_path).parent == PLATFORM_DIR / "data"


def test_run_api_has_a_valid_settings_export():
    import run_api

    assert run_api.settings.api_port > 0


def test_discord_role_permissions_are_unioned():
    from app.bot.main import permissions_for_role_names

    permissions = permissions_for_role_names({"translator", "reviewer"})
    assert "translation.check" in permissions
    assert "translation.review" in permissions
    assert "tasks.self" in permissions
    assert "tasks.review" in permissions
    assert permissions_for_role_names(set(), is_owner=True) == {"*"}
