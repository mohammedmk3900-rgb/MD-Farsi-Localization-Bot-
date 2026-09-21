#!/usr/bin/env python3
import json, os, sys
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

PROJECT_ID=os.getenv("PARATRANZ_PROJECT_ID","19621")
WEBHOOK=os.getenv("DISCORD_ACHIEVEMENTS_WEBHOOK_URL")
STATE="data/achievements.json"
VISUAL="https://raw.githubusercontent.com/mohammedmk3900-rgb/MD-Farsi-Localization-Bot-/main/assets/discord/achievement.svg"
MILESTONES={
    1:("🎉","اولین ۱٪","اولین نقطه عطف ترجمه ثبت شد."),
    10:("🌱","۱۰٪ — آغاز جدی","ده درصد مسیر ترجمه پشت سر گذاشته شد."),
    25:("📈","۲۵٪ — یک‌چهارم مسیر","یک‌چهارم پروژه ترجمه شده است."),
    50:("🔥","۵۰٪ — نیمه راه","پروژه به نیمه مسیر ترجمه رسید."),
    75:("🚀","۷۵٪ — نزدیک به پایان","بخش بزرگی از ترجمه تکمیل شده است."),
    100:("🏁","۱۰۰٪ — تکمیل ترجمه","ترجمه پروژه به پایان رسید."),
}

def fail(message):
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)

def stats():
    try:
        with open("data/command_center.json",encoding="utf-8") as f:
            s=json.load(f)
        p=s["stats"]
        pr=s["progress"]
        return p["strings"],p["translated"],pr["translation_percent"]
    except (FileNotFoundError,KeyError,TypeError,ValueError) as e:
        fail(f"Command Center snapshot unavailable: {e}")

def post(url,payload):
    headers={"Accept":"application/json","Content-Type":"application/json","User-Agent":"MD-Farsi-Localization-Achievements/4.1"}
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
        with open(STATE,encoding="utf-8") as f:
            return {int(x) for x in json.load(f)}
    except (FileNotFoundError,ValueError,TypeError):
        return set()

def save(done):
    os.makedirs("data",exist_ok=True)
    tmp=STATE+".tmp"
    with open(tmp,"w",encoding="utf-8") as f:
        json.dump(sorted(done),f,ensure_ascii=False,indent=2)
        f.write("\n")
    os.replace(tmp,STATE)

def main():
    if not WEBHOOK:
        fail("DISCORD_ACHIEVEMENTS_WEBHOOK_URL is not set.")
    total,translated,progress=stats()
    done=load()
    new=[n for n in MILESTONES if progress>=n and n not in done]
    for n in new:
        icon,name,detail=MILESTONES[n]
        now=datetime.now(timezone.utc)
        payload={
            "username":"MD Farsi Localization • Command Center",
            "embeds":[{
                "author":{"name":"MD FARSI LOCALIZATION • COMMAND CENTER"},
                "title":f"{icon}  دستاورد باز شد",
                "url":f"https://paratranz.cn/projects/{PROJECT_ID}",
                "image":{"url":VISUAL+"?v="+str(int(now.timestamp()))},
                "description":(
                    "### 🇮🇷 فارسی‌سازی Millennium Dawn\n\n"
                    f"## {name}\n**{detail}**\n\n"
                    f"🏆 **نقطه عطف {n}% ثبت شد**\n"
                    f"📝 **{translated:,} / {total:,}** رشته ترجمه شده"
                ),
                "color":0xF1C40F,
                "fields":[
                    {"name":"🏆 نقطه عطف","value":f"**{n}%**","inline":True},
                    {"name":"📝 ترجمه‌شده","value":f"**{translated:,}**","inline":True},
                    {"name":"📦 کل رشته‌ها","value":f"**{total:,}**","inline":True},
                ],
                "footer":{"text":"MD Farsi Localization • سیستم دستاوردها"},
                "timestamp":now.isoformat(),
            }]
        }
        post(WEBHOOK+"?wait=true",payload)
        done.add(n)
    save(done)
    print(f"Progress: {progress:.2f}% | New achievements: {len(new)}")

if __name__=="__main__":
    main()
