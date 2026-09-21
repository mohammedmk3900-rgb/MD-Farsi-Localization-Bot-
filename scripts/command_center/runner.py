"""Single production entry point for Command Center V8."""
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

def run():
    c=Config.from_env(); stats,files=collect_stats(c); payload,snapshot=build(c,stats,files)
    done=load_json("data/achievements.json",{}); done={int(x) for x in done.get("done",[])} if isinstance(done,dict) else set()
    if c.stats_webhook: upsert(c.stats_webhook,"stats",stats_embed(c,payload))
    if c.progress_webhook: upsert(c.progress_webhook,"progress",progress_embed(c,payload))
    for n in snapshot.milestones_crossed:
        if n not in done and c.achievements_webhook:
            upsert(c.achievements_webhook,"achievement_"+str(n),achievement_embed(c,n,payload)); done.add(n)
    save_json("data/achievements.json",{"schema":1,"done":sorted(done)})
    health=collect_health()
    payload["health"]={"status":health["status"],"percentage":health["percentage"],"passed_checks":health["passed_checks"],"total_checks":health["required_checks"],"checks":health["checks"],"updated_at":datetime.now(timezone.utc).isoformat()}
    save_json("data/command_center.json",payload); record_snapshot(payload)
    if c.health_webhook: upsert(c.health_webhook,"health",health_embed(c,health))
    print(f"Command Center V9 OK • {stats.translated:,}/{stats.strings:,} translated ({stats.translation_percent:.2f}%)")
    return payload

if __name__=="__main__":
    try: run()
    except Exception as exc: print("ERROR: "+str(exc),file=sys.stderr); raise SystemExit(1)
