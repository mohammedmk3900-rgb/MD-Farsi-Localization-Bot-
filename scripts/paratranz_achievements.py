#!/usr/bin/env python3
import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

API="https://paratranz.cn/api"
PROJECT_ID=os.getenv("PARATRANZ_PROJECT_ID","19621")
TOKEN=os.getenv("PARATRANZ_TOKEN")
WEBHOOK=os.getenv("DISCORD_ACHIEVEMENTS_WEBHOOK_URL")
STATE_FILE="data/achievements.json"

def fail(msg):
    print(f"ERROR: {msg}", file=sys.stderr); sys.exit(1)

def http(url, method="GET", payload=None):
    headers={"Accept":"application/json","User-Agent":"MD-Farsi-Localization-Achievements/1.0"}
    body=None
    if payload is not None:
        body=json.dumps(payload).encode(); headers["Content-Type"]="application/json"
    try:
        with urlopen(Request(url,data=body,headers=headers,method=method),timeout=30) as r:
            raw=r.read().decode(); return json.loads(raw) if raw else None
    except (HTTPError,URLError) as e:
        fail(f"HTTP/network error: {e}")

def main():
    if not TOKEN: fail("PARATRANZ_TOKEN is not set.")
    if not WEBHOOK: fail("DISCORD_ACHIEVEMENTS_WEBHOOK_URL is not set.")
    files=http(f"{API}/projects/{PROJECT_ID}/files", payload=None)
    # Rebuild request with auth because http() is intentionally minimal.
    req=Request(f"{API}/projects/{PROJECT_ID}/files",headers={"Accept":"application/json","Authorization":TOKEN,"User-Agent":"MD-Farsi-Localization-Achievements/1.0"})
    try:
        with urlopen(req,timeout=30) as r: files=json.loads(r.read().decode())
    except Exception as e: fail(str(e))
    if not isinstance(files,list): fail("Unexpected ParaTranz response.")
    total=sum(int(f.get("total") or 0) for f in files)
    translated=sum(int(f.get("translated") or 0) for f in files)
    pct=(translated/total*100) if total else 0
    milestones={1:"🎉 اولین ۱٪ ترجمه!",10:"🌱 ۱۰٪ ترجمه تکمیل شد!",25:"📈 ۲۵٪ ترجمه تکمیل شد!",50:"🔥 پروژه به ۵۰٪ رسید!",75:"🚀 ۷۵٪ ترجمه تکمیل شد!",100:"🏁 فارسی‌سازی کامل شد!"}
    try:
        with open(STATE_FILE,encoding="utf-8") as f: announced=set(map(int,json.load(f)))
    except (FileNotFoundError,ValueError,TypeError): announced=set()
    newly=[m for m in milestones if pct>=m and m not in announced]
    for m in newly:
        embed={"title":milestones[m],"description":f"پروژه **Millennium Dawn Farsi Localization** به **{m}%** ترجمه رسید! 🎮\n\nترجمه فعلی: **{translated:,} / {total:,}** رشته\n\nادامه می‌دیم! 💪","color":0xF1C40F}
        try:
            http(WEBHOOK+"?wait=true",method="POST",payload={"username":"MD Farsi Localization • Achievements","embeds":[embed]})
        except SystemExit: raise
        announced.add(m)
    os.makedirs("data",exist_ok=True)
    with open(STATE_FILE,"w",encoding="utf-8") as f: json.dump(sorted(announced),f,ensure_ascii=False,indent=2)
    print(f"Current progress: {pct:.2f}% | New achievements: {len(newly)}")

if __name__=="__main__": main()
