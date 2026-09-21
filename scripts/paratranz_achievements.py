#!/usr/bin/env python3
"""Milestone notifications: only notify when a threshold is crossed."""
import json, os, sys
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

PROJECT_ID=os.getenv("PARATRANZ_PROJECT_ID","19621")
WEBHOOK=os.getenv("DISCORD_ACHIEVEMENTS_WEBHOOK_URL")
STATE="data/achievements.json"
MILESTONES={1:("🎉","اولین ۱٪","اولین نقطه عطف ترجمه ثبت شد."),10:("🌱","۱۰٪ — آغاز جدی","ده درصد مسیر ترجمه پشت سر گذاشته شد."),25:("📈","۲۵٪ — یک‌چهارم مسیر","یک‌چهارم پروژه ترجمه شده است."),50:("🔥","۵۰٪ — نیمه راه","پروژه به نیمه مسیر ترجمه رسید."),75:("🚀","۷۵٪ — نزدیک به پایان","بخش بزرگی از ترجمه تکمیل شده است."),100:("🏁","۱۰۰٪ — تکمیل ترجمه","ترجمه پروژه به پایان رسید.")}

def fail(m): print("ERROR: "+m,file=sys.stderr); sys.exit(1)
def stats():
    try:
        s=json.load(open("data/command_center.json",encoding="utf-8"))
        p=s["stats"]; pr=s["progress"]
        old=float(s.get("previous_progress_percent",0) or 0)
        return p["strings"],p["translated"],pr["translation_percent"],old
    except (FileNotFoundError,KeyError,TypeError,ValueError) as e: fail(f"Command Center snapshot unavailable: {e}")
def load():
    try:
        d=json.load(open(STATE,encoding="utf-8"))
        if isinstance(d,list): return set(map(int,d))
        return set(map(int,d.get("done",[])))
    except (FileNotFoundError,ValueError,TypeError): return set()
def save(done):
    os.makedirs("data",exist_ok=True); tmp=STATE+".tmp"
    with open(tmp,"w",encoding="utf-8") as f: json.dump({"schema":2,"done":sorted(done)},f,ensure_ascii=False,indent=2); f.write("\n")
    os.replace(tmp,STATE)
def post(payload):
    with urlopen(Request(WEBHOOK+"?wait=true",data=json.dumps(payload,ensure_ascii=False).encode(),headers={"Accept":"application/json","Content-Type":"application/json","User-Agent":"MD-Farsi-Localization-Achievements/5.0"},method="POST"),timeout=30) as r:
        return json.loads(r.read().decode()) if r.readable() else None
def main():
    if not WEBHOOK: fail("DISCORD_ACHIEVEMENTS_WEBHOOK_URL is not set.")
    total,translated,progress,old=stats(); done=load()
    new=[n for n in MILESTONES if old < n <= progress and n not in done]
    for n in new:
        icon,name,detail=MILESTONES[n]; now=datetime.now(timezone.utc)
        payload={"username":"MD Farsi Localization • Command Center","embeds":[{
          "author":{"name":"MD FARSI LOCALIZATION • COMMAND CENTER"},"title":f"{icon}  دستاورد باز شد","url":f"https://paratranz.cn/projects/{PROJECT_ID}",
          "description":f"### 🇮🇷 فارسی‌سازی Millennium Dawn\n\n## {name}\n**{detail}**\n\n🏆 **نقطه عطف {n}% ثبت شد**\n📝 **{translated:,} / {total:,}** رشته ترجمه شده",
          "color":0xF1C40F,"timestamp":now.isoformat()
        }]}
        post(payload); done.add(n)
    save(done); print(f"Progress: {progress:.2f}% | New achievements: {len(new)}")
if __name__=="__main__": main()
