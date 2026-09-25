from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    paratranz_project_id: int = 19621
    paratranz_token: str = ""
    discord_bot_token: str = ""
    discord_guild_id: str = ""

    channel_stats: str = ""
    channel_progress: str = ""
    channel_achievements: str = ""
    channel_health: str = ""
    channel_reports: str = ""
    channel_glossary: str = ""

    database_path: str = "data/platform.db"
    recent_messages_per_channel: int = 50
    api_token: str = ""
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    cors_origins: str = ""
