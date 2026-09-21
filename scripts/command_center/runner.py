"""MD Farsi Localization Command Center V7 execution pipeline."""
from __future__ import annotations
import sys
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from command_center.config import Config
from command_center.collectors.paratranz import collect_stats
from command_center.services.snapshot import build
from command_center.services.database import record_snapshot
from command_center.services.discord import upsert,stats_embed,progress_embed,health_embed,achievement_embed
from command_center.diagnostics import collect as collect_health
from command_center.state import load_json,save_json
ACHIEVEMENT_STATE="data/achievements.json"
def _achievements()->set[int]:
 data=load_json(ACHIEVEMENT_STATE,{})
 if isinstance(data,list):return {int(x) for x in data}
 return {int(x) for x in data.get("done",[])} if isinstance(data,dict) else set()
def _save_achievements(done:set[int])->None:save_json(ACHIEVEMENT_STATE,{"schema":3,"done":sorted(done)})
def run()->None:
 config=Config();stats,files=collect_stats(config);payload,snapshot=build(config,stats,files)
 record_snapshot(payload)
 if config.stats_webhook:upsert(config.stats_webhook,"stats",stats_embed(config,payload))
 if config.progress_webhook:upsert(config.progress_webhook,"progress",progress_embed(config,payload))
 done=_achievements()
 for threshold in snapshot.milestones_crossed:
  if threshold in done or not config.achievements_webhook:continue
  upsert(config.achievements_webhook,f"achievement_{threshold}",achievement_embed(config,threshold,payload));done.add(threshold)
 _save_achievements(done)
 health=collect_health()
 payload["health"]={"status":health["status"],"percentage":health["percentage"],"passed_checks":health["passed_checks"],"total_checks":health["required_checks"],"checks":health["checks"],"updated_at":datetime.now(timezone.utc).isoformat()}
 save_json("data/command_center.json",payload);record_snapshot(payload)
 if config.health_webhook:upsert(config.health_webhook,"health",health_embed(config,health))
 print(f"Command Center V7 OK • {stats.translated:,}/{stats.strings:,} translated ({stats.translation_percent:.2f}%) • review {stats.review_percent:.2f}%")
if __name__=="__main__":
 try:run()
 except Exception as exc:print(f"ERROR: {exc}",file=sys.stderr);raise SystemExit(1)
