#!/usr/bin/env python3
"""Compute and publish a persistent Persian Command Center health message."""
import json, os, sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0,"scripts")
from command_center.diagnostics import collect
from command_center.http_client import request_json
from command_center.state import load_json, save_json

WEBHOOK=os.getenv("DISCORD_HEALTH_WEBHOOK_URL")
STATE="data/discord_messages.json"

def main():
    health=collect()
    snap=load_json("data/command_center.json",{})
    snap["health"]={
        "status":health["status"],
        "percentage":health["percentage"],
        "passed_checks":health["passed_checks"],
        "total_checks":health["required_checks"],
        "checks":health["checks"],
        "updated_at":datetime.now(timezone.utc).isoformat()
    }
    Path("data").mkdir(exist_ok=True)
    Path("data/command_center.json").write_text(json.dumps(snap,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if not WEBHOOK:
        print("Health computed; DISCORD_HEALTH_WEBHOOK_URL not configured, skipping Discord.")
        return
    state=load_json(STATE,{"stats":"","progress":"","health":""})
    mid=str(state.get("health",""))
    icons={"healthy":"🟢","degraded":"🟡","critical":"🔴"}
    icon=icons[health["status"]]
    fields=[]
    for key,value in health["checks"].items():
        fields.append({"name":key.replace("_"," ").title(),"value":"✅ OK" if value else "❌ FAIL","inline":True})
    embed={
      "author":{"name":"MD FARSI LOCALIZATION • COMMAND CENTER"},
      "title":"🛰️ سلامت سیستم • SYSTEM HEALTH",
      "description":"### 🇮🇷 وضعیت عملیاتی\n\n{} **{}** — **{:.1f}%**\n**{}/{}** بررسی موفق".format(icon,health["status"].upper(),health["percentage"],health["passed_checks"],health["required_checks"]),
      "color":0x2ECC71 if health["status"]=="healthy" else (0xF1C40F if health["status"]=="degraded" else 0xE74C3C),
      "fields":fields,
      "footer":{"text":"MD Farsi Localization • Health Engine • بدون نمایش Secret"},
      "timestamp":datetime.now(timezone.utc).isoformat()
    }
    try:
        if mid:
            request_json(f"{WEBHOOK}/messages/{mid}",method="PATCH",payload={"embeds":[embed]})
        else:
            r=request_json(WEBHOOK+"?wait=true",method="POST",payload={"username":"MD Farsi Localization • Command Center","embeds":[embed]})
            mid=str(r["id"])
    except RuntimeError as exc:
        if mid and "HTTP 404" in str(exc):
            r=request_json(WEBHOOK+"?wait=true",method="POST",payload={"username":"MD Farsi Localization • Command Center","embeds":[embed]})
            mid=str(r["id"])
        else:
            raise
    state["health"]=mid
    save_json(STATE,state)
    print("Health:",health["status"],health["percentage"],"%")

if __name__=="__main__": main()
