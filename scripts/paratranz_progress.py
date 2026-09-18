#!/usr/bin/env python3
import json, os, sys
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

API="https://paratranz.cn/api"; PROJECT_ID=os.getenv("PARATRANZ_PROJECT_ID","19621")
TOKEN=os.getenv("PARATRANZ_TOKEN"); WEBHOOK=os.getenv("DISCORD_PROGRESS_WEBHOOK_URL")
STATE="data/discord_messages.json"; VISUAL="https://raw.githubusercontent.com/mohammedmk3900-rgb/MD-Farsi-Localization-Bot-/main/assets/discord/progress.svg"

def fail(m): print(f"ERROR: {m}",file=sys.stderr); sys.exit(1)
def req(url,method="GET",payload=None):
    h={"Accept":"application/json","User-Agent":"MD-Farsi-Localization-Progress/4.0"}
    if TOKEN:h["Authorization"]=TOKEN
    body=json.dumps(payload,ensure_ascii=False).encode() if payload is not None else None
    if body:h["Content-Type"]="application/json"
    try:
        with urlopen(Request(url,data=body,headers=h,method=method),timeout=30) as r:
            raw=r.read().decode(); return json.loads(raw) if raw else None
    except HTTPError as e: raise RuntimeError(f"HTTP {e.code}: {e.read().decode(errors='replace')[:800]}")
    except (URLError,json.JSONDecodeError) as e: raise RuntimeError(str(e))
def get():
    try:
        with open("data/command_center.json",encoding="utf-8") as f:s=json.load(f)
        p=s["project"]; pr=s["progress"]
        return p["files"],p["strings"],p["translated"],p["reviewed"],pr["translation_percent"],pr["review_percent"]
    except (FileNotFoundError,KeyError,TypeError,ValueError) as e:
        fail(f"Command Center snapshot unavailable: {e}")

def mid():
    try:
        with open(STATE,encoding="utf-8") as f:return str(json.load(f).get("progress","")).strip()
    except (FileNotFoundError,ValueError,TypeError):return ""
def save(m):
    os.makedirs("data",exist_ok=True); d={"stats":"","progress":""}
    try:
        with open(STATE,encoding="utf-8") as f:d.update(json.load(f))
    except (FileNotFoundError,ValueError,TypeError):pass
    d["progress"]=str(m)
    with open(STATE,"w",encoding="utf-8") as f:json.dump(d,f,ensure_ascii=False,indent=2);f.write("\n")
def milestone(p):
    for n,title,detail in [(100,"🏁 ۱۰۰٪ — تکمیل ترجمه","ترجمه پروژه کامل شده است."),(75,"🚀 ۷۵٪ — نزدیک به پایان","بخش بزرگی از مسیر تکمیل شده است."),(50,"🔥 ۵۰٪ — نیمه راه","پروژه به نیمه مسیر ترجمه رسیده است."),(25,"📈 ۲۵٪ — یک‌چهارم مسیر","یک‌چهارم مسیر پشت سر گذاشته شده است."),(10,"🌱 ۱۰٪ — آغاز جدی","اولین نقطه عطف بزرگ ثبت شده است."),(1,"🎯 ۱٪ — اولین نقطه عطف","اولین درصد پروژه تکمیل شده است.")]:
        if p>=n:return title,detail
    return "🚀 شروع مسیر","پروژه در حال جمع‌آوری و ترجمه رشته‌هاست."
def next_sync(now):
    h=((now.hour//6)+1)*6
    target=(now.replace(hour=0,minute=0,second=0,microsecond=0).timestamp()+86400) if h>=24 else now.replace(hour=h,minute=0,second=0,microsecond=0).timestamp()
    return datetime.fromtimestamp(target,timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
def embed(x):
    files,total,tr,rv,p,r=x; now=datetime.now(timezone.utc)
    title,detail=milestone(p)
    return {"author":{"name":"MD FARSI LOCALIZATION  •  COMMAND CENTER"},"title":"📈  پیشرفت زنده  •  LIVE TRANSLATION PROGRESS","url":f"https://paratranz.cn/projects/{PROJECT_ID}",
      "description":f"### 🇮🇷 فارسی‌سازی Millennium Dawn\n**🟢 PROGRESS ENGINE  •  ONLINE  •  داده واقعی**\n\n# **{p:.2f}%**\n**{tr:,}** از **{total:,}** رشته ترجمه شده\n\n🎯 **{title}**\n{detail}",
      "color":0x2ECC71,"image":{"url":VISUAL+"?v="+str(int(now.timestamp()))},
      "fields":[
       {"name":"📝 TRANSLATED • ترجمه","value":f"**{tr:,}**\n{p:.2f}%","inline":True},
       {"name":"🔎 REVIEWED • بازبینی","value":f"**{rv:,}**\n{r:.2f}%","inline":True},
       {"name":"📄 FILES • فایل‌ها","value":f"**{files:,}**","inline":True},
       {"name":"⚡ ENGINE • موتور","value":"**ONLINE**\nParaTranz API","inline":True},
       {"name":"🔄 SYNC • همگام‌سازی","value":"**خودکار**\nهر ۶ ساعت","inline":True},
       {"name":"🎯 NEXT • باقی‌مانده","value":f"**{max(0,100-p):.2f}%**\nتا تکمیل","inline":True}],
      "footer":{"text":f"MD Farsi Localization • Sync: {now.strftime('%Y-%m-%d %H:%M UTC')} • بعدی: {next_sync(now)}"},"timestamp":now.isoformat()}
def send(e):
    if not WEBHOOK:fail("DISCORD_PROGRESS_WEBHOOK_URL is not set.")
    sep="&" if "?" in WEBHOOK else "?";r=req(WEBHOOK+sep+"wait=true",method="POST",payload={"username":"MD Farsi Localization • Command Center","embeds":[e]})
    if not r or "id" not in r:fail("Discord did not return a message ID.")
    return str(r["id"])
def edit(e,m):
    if not WEBHOOK or not m:return False
    try:req(f"{WEBHOOK}/messages/{m}",method="PATCH",payload={"embeds":[e]});return True
    except RuntimeError as ex:print(f"Recreating progress message: {ex}");return False
def main():
    x=get();e=embed(x);m=mid();m=m if edit(e,m) else send(e);save(m)
    out=os.getenv("GITHUB_OUTPUT")
    if out:
        with open(out,"a",encoding="utf-8") as f:f.write(f"message_id={m}\n")
    print(f"Progress synced: {x[4]:.2f}%")
if __name__=="__main__":main()
