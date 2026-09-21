#!/usr/bin/env python3
"""Runtime health checks for the Command Center."""
import json, os
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
def check_json(path, required=()):
    try:
        d=json.loads(Path(path).read_text(encoding="utf-8"))
        missing=[k for k in required if k not in d]
        return (not missing, "ok" if not missing else "missing:"+",".join(missing))
    except FileNotFoundError: return False,"missing"
    except (json.JSONDecodeError,TypeError,ValueError): return False,"invalid-json"
def check_svg(path):
    try:
        head=Path(path).read_text(encoding="utf-8")[:500]
        return ("<svg" in head, "ok" if "<svg" in head else "invalid-svg")
    except FileNotFoundError: return False,"missing"
def check_webhook(url):
    if not url: return False,"not-configured"
    try:
        with urlopen(Request(url,headers={"User-Agent":"MD-Farsi-Localization-Health/5.0"}),timeout=15) as r:
            return (200 <= r.status < 300, f"http-{r.status}")
    except HTTPError as e: return False,f"http-{e.code}"
    except (URLError,TimeoutError): return False,"unreachable"
def collect():
    checks={}
    checks["token"]=bool(os.getenv("PARATRANZ_TOKEN"))
    checks["snapshot"]=check_json("data/command_center.json",("schema","stats","progress","automation"))[0]
    checks["history"]=check_json("data/discord_history.json",("schema","snapshots"))[0]
    checks["stats_visual"]=check_svg("assets/discord/stats.svg")[0]
    checks["progress_visual"]=check_svg("assets/discord/progress.svg")[0]
    checks["history_visual"]=check_svg("assets/discord/progress-history.svg")[0]
    checks["stats_webhook"]=check_webhook(os.getenv("DISCORD_WEBHOOK_URL"))[0]
    checks["progress_webhook"]=check_webhook(os.getenv("DISCORD_PROGRESS_WEBHOOK_URL"))[0]
    checks["achievements_webhook"]=check_webhook(os.getenv("DISCORD_ACHIEVEMENTS_WEBHOOK_URL"))[0]
    required=list(checks)
    passed=sum(bool(checks[k]) for k in required)
    percentage=round(passed/len(required)*100,1) if required else 0.0
    status="healthy" if percentage==100 else ("degraded" if percentage>=70 else "critical")
    return {"status":status,"percentage":percentage,"checks":checks,"required_checks":len(required),"passed_checks":passed}
