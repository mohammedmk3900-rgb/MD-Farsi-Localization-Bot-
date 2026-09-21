#!/usr/bin/env python3
import json, os, sys
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

API="https://paratranz.cn/api"; PROJECT_ID=os.getenv("PARATRANZ_PROJECT_ID","19621")
TOKEN=os.getenv("PARATRANZ_TOKEN"); WEBHOOK=os.getenv("DISCORD_ACHIEVEMENTS_WEBHOOK_URL")
STATE="data/achievements.json"; VISUAL="https://raw.githubusercontent.com/mohammedmk3900-rgb/MD-Farsi-Localization-Bot-/main/assets/discord/achievement.svg"
MILESTONES={1:("🎉","اولین ۱٪","اولین نقطه عطف ترجمه ثبت شد!"),10:("🌱","۱۰٪ — آغاز جدی","ده درصد مسیر ترجمه پشت سر گذاشته شد."),25:("📈","۲۵٪ — یک‌چهارم مسیر","یک‌چهارم پروژه ترجمه شده است."),50:("🔥","۵۰٪ — نیمه راه","پروژه به نیمه مسیر ترجمه رسید."),75:("🚀","۷۵٪ — نزدیک به پایان","بخش بزرگی از ترجمه تکمیل شده است."),100:("🏁","۱۰۰٪ — تکمیل ترجمه","ترجمه پروژه به پایان رسید.")}

def fail(m):print(f"ERROR: {m}",file=sys.stderr);sys.exit(1)
def stats():
    try:
        with open("data/command_center.json",encoding="utf-8") as f:s=json.load(f)
        p=s["project"]; pr=s["progress"]
        return p["strings"],p["translated"],pr["translation_percent"]
    except (FileNotFoundError,KeyError,TypeError,ValueError) as e:
        fail(f"Command Center snapshot unavailable: {e}")

def post(url,payload):
    headers={"Accept":"application/json","Content-Type":"application/json","User-Agent":"MD-Farsi-Localization-Achievements/4.0"}
    try:
        with urlopen(Request(url,data=json.dumps(payload,ensure_ascii=False).encode(),headers=headers,method="POST"),timeout=30) as r:
            raw=r.read().decode()
            return json.loads(raw) if raw else None
    except HTTPError as e:
        raise RuntimeError(f"Discord HTTP {e.code}: {e.read().decode(errors='replace')[:800]}")
    except (URLError,json.JSONDecodeError) as e:
        raise RuntimeError(f"Discord request failed: {e}")

def load():
    try:
        with open(STATE,encoding="utf-8") as f:return {int(x) for x in json.load(f)}
    except (FileNotFoundError,ValueError,TypeError):return set()
def save(s):
    os.makedirs("data",exist_ok=True)
    tmp=STATE+".tmp"
    with open(tmp,"w",encoding="utf-8") as f:
        json.dump(sorted(s),f,ensure_ascii=False,indent=2); f.write("\n")
    os.replace(tmp, STATE)
def main():
    if not WEBHOOK:fail("DISCORD_ACHIEVEMENTS_WEBHOOK_URL is not set.")
    total,tr,p=stats();done=load();new=[n for n in MILESTONES if p>=n and n not in done]
    for n in new:
        icon,name,detail=MILESTONES[n];now=datetime.now(timezone.utc)
        payload={"username":"MD Farsi Localization • Command Center","embeds":[{"author":{"name":"MD FARSI LOCALIZATION • ACHIEVEMENTS"},"title":f"{icon}  دستاورد باز شد  •  ACHIEVEMENT UNLOCKED","url":f"https://paratranz.cn/projects/{PROJECT_ID}","image":{"url":VISUAL+"?v="+str(int(now.timestamp()))},"description":f"### 🇮🇷 فارسی‌سازی Millennium Dawn\n\n## {name}\n**{detail}**\n\n🏆 **نقطه عطف {n}% ثبت شد**\n📝 **{tr:,} / {total:,}** رشته ترجمه شده\n\n✨ یک مرحله دیگر از مسیر فارسی‌سازی ثبت شد.","color":0xF1C40F,"fields":[{"name":"🏆 MILESTONE • نقطه عطف","value":f"**{n}%**","inline":True},{"name":"📝 TRANSLATED • ترجمه","value":f"**{tr:,}**","inline":True},{"name":"📦 TOTAL • کل","value":f"**{total:,}**","inline":True}],"footer":{"text":"MD Farsi Localization • Achievement System • سیستم دستاوردها"},"timestamp":now.isoformat()}]}
        post(WEBHOOK+"?wait=true",payload);done.add(n)
    save(done);print(f"Progress: {p:.2f}% | New achievements: {len(new)}")
if __name__=="__main__":main()
