"""Runtime configuration for the MD Farsi Localization Command Center V8."""
from __future__ import annotations
import os
from dataclasses import dataclass

def _int(name: str, default: int, minimum: int = 0) -> int:
    try: return max(minimum, int(os.getenv(name, str(default))))
    except ValueError: return default

@dataclass(frozen=True)
class Config:
    project_id:int; participants:int; paratranz_token:str; stats_webhook:str; progress_webhook:str
    achievements_webhook:str; health_webhook:str; reports_webhook:str; history_limit:int; sync_hours:int
    @classmethod
    def from_env(cls):
        return cls(_int("PARATRANZ_PROJECT_ID",19621,1),_int("PROJECT_PARTICIPANTS",8),
          os.getenv("PARATRANZ_TOKEN","").strip(),os.getenv("DISCORD_WEBHOOK_URL","").strip(),
          os.getenv("DISCORD_PROGRESS_WEBHOOK_URL","").strip(),os.getenv("DISCORD_ACHIEVEMENTS_WEBHOOK_URL","").strip(),
          os.getenv("DISCORD_HEALTH_WEBHOOK_URL","").strip(),os.getenv("DISCORD_REPORTS_WEBHOOK_URL","").strip(),
          _int("COMMAND_CENTER_HISTORY_LIMIT",180,1),_int("COMMAND_CENTER_SYNC_HOURS",6,1))
    @property
    def project_url(self): return f"https://paratranz.cn/projects/{self.project_id}"
    @property
    def api_url(self): return f"https://paratranz.cn/api/projects/{self.project_id}/files"
    @property
    def terms_url(self): return f"https://paratranz.cn/api/projects/{self.project_id}/terms"
