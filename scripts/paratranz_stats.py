#!/usr/bin/env python3
import json, os, sys
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

API="https://paratranz.cn/api"
PROJECT_ID=os.getenv("PARATRANZ_PROJECT_ID","19621")
TOKEN=os.getenv("PARATRANZ_TOKEN")
WEBHOOK=os.getenv("DISCORD_WEBHOOK_URL")
STATE="data/discord_messages.json"
VISUAL="https://raw.githubusercontent.com/mohammedmk3900-rgb/MD-Farsi-Localization-Bot-/main/assets/discord/stats.svg"
PARTICIPANTS=int(os.getenv("PROJECT_PARTICIPANTS","8"))

def fail(msg): print(f"ERROR: {msg}",file=sys.stderr); sys.exit(1)
def req(url,method="GET",payload=None):
    h={"Accept":"application/json","User-Agent":"MD-Farsi-Localization-Stats/4.0"}
    if TOKEN:h["Authorization"]=TOKEN
    body=json.dumps(payload,ensure_ascii=False).encode() if payload is not None else None
    if body:h["Content-Type"]="application/json"
    try:
        with urlopen(Request(url,data=body,headers=h,method=method),timeout=30) as r:
            raw=r.read().decode(); return json.loads(raw) if raw else None
    except HTTPError as e: raise RuntimeError(f"HTTP {e.code}: {e.read().decode(errors='replace')[:800]}")
    except (URLError,json.JSONDecodeError) as e: raise RuntimeError(str(e))

def get_stats():
    if not TOKEN: fail("PARATRANZ_TOKEN is not set.")
    fs=req(f"{API}/projects/{PROJECT_ID}/files")
    if not isinstance(fs,list): fail("ParaTranz returned an unexpected files response.")
    total=sum(int(x.get("total") or 0) for x in fs); translated=sum(int(x.get("translated") or 0) for x in fs)
    reviewed=sum(int(x.get("reviewed") or 0) for x in fs); words=sum(int(x.get("words") or 0) for x in fs)
    return {"files":len(fs),"strings":total,"translated":translated,"reviewed":reviewed,"words":words,
            "translation_percent":translated/total*100 if total else 0,"review_percent":reviewed/total*100 if total else 0,"participants":PARTICIPANTS}

def load_id():
    try:
        with open(STATE,encoding="utf-8") as f:return str(json.load(f).get("stats","")).strip()
    except (FileNotFoundError,ValueError,TypeError):return ""
def save_id(mid):
    os.makedirs("data",exist_ok=True); state={"stats":"","progress":""}
    try:
        with open(STATE,encoding="utf-8") as f: state.update(json.load(f))
    except (FileNotFoundError,ValueError,TypeError): pass
    state["stats"]=str(mid)
    with open(STATE,"w",encoding="utf-8") as f: json.dump(state,f,ensure_ascii=False,indent=2); f.write("\n")

def next_sync(now):
    h=((now.hour//6)+1)*6
    target=(now.replace(hour=0,minute=0,second=0,microsecond=0).timestamp()+86400) if h>=24 else now.replace(hour=h,minute=0,second=0,microsecond=0).timestamp()
    return datetime.fromtimestamp(target,timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

def build_embed(s):
    now=datetime.now(timezone.utc); visual=VISUAL+"?v="+str(int(now.timestamp()))
    remaining=max(0,100-s["translation_percent"])
    return {"author":{"name":"MD FARSI LOCALIZATION  •  COMMAND CENTER"},
      "title":"📊  آمار پروژه  •  PROJECT STATISTICS","url":f"https://paratranz.cn/projects/{PROJECT_ID}",
      "description":f"### 🇮🇷 فارسی‌سازی Millennium Dawn\n**🟢 LIVE  •  داده واقعی  •  همگام‌سازی خودکار**\n\n🌐 **پیشرفت ترجمه:** **{s['translation_percent']:.2f}%**\n🔎 **پیشرفت بازبینی:** **{s['review_percent']:.2f}%**\n\nآخرین وضعیت مستقیماً از ParaTranz دریافت شده است.",
      "color":0x5865F2,"image":{"url":visual},
      "fields":[
       {"name":"📦 PROJECT • پروژه","value":f"**{s['files']:,}** فایل\n**{s['words']:,}** کلمه","inline":True},
       {"name":"📝 STRINGS • رشته‌ها","value":f"**{s['strings']:,}** کل\n**{s['translated']:,}** ترجمه‌شده","inline":True},
       {"name":"🔎 REVIEW • بازبینی","value":f"**{s['reviewed']:,}** بازبینی‌شده\n**{s['review_percent']:.2f}%**","inline":True},
       {"name":"👥 CONTRIBUTORS • مشارکت","value":f"**{s['participants']:,}** مشارکت‌کننده","inline":True},
       {"name":"📈 REMAINING • باقی‌مانده","value":f"**{remaining:.2f}%**\nتا تکمیل ترجمه","inline":True},
       {"name":"⚡ AUTOMATION • خودکارسازی","value":"**ONLINE**\nهر ۶ ساعت","inline":True}],
      "footer":{"text":f"MD Farsi Localization • آخرین Sync: {now.strftime('%Y-%m-%d %H:%M UTC')} • بعدی: {next_sync(now)}"},
      "timestamp":now.isoformat()}

def send(e):
    if not WEBHOOK:fail("DISCORD_WEBHOOK_URL is not set.")
    sep="&" if "?" in WEBHOOK else "?"; r=req(WEBHOOK+sep+"wait=true",method="POST",payload={"username":"MD Farsi Localization • Command Center","embeds":[e]})
    if not r or "id" not in r:fail("Discord did not return a message ID.")
    return str(r["id"])
def edit(e,mid):
    if not WEBHOOK or not mid:return False
    try:req(f"{WEBHOOK}/messages/{mid}",method="PATCH",payload={"embeds":[e]});return True
    except RuntimeError as ex:print(f"Recreating stats message: {ex}");return False

def main():
    try:
        s=get_stats(); e=build_embed(s); m=load_id(); m=m if edit(e,m) else send(e); save_id(m)
        out=os.getenv("GITHUB_OUTPUT")
        if out:
            with open(out,"a",encoding="utf-8") as f:f.write(f"message_id={m}\n")
        print(f"Stats synced: {s['translation_percent']:.2f}% translation / {s['review_percent']:.2f}% review")
    except RuntimeError as ex:fail(str(ex))
if __name__=="__main__":main()
