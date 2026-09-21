#!/usr/bin/env python3
"""Single source of truth for the MD Farsi Localization Command Center."""
import json, os, sys, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

API="https://paratranz.cn/api"
PROJECT_ID=os.getenv("PARATRANZ_PROJECT_ID","19621")
TOKEN=os.getenv("PARATRANZ_TOKEN")
PARTICIPANTS=int(os.getenv("PROJECT_PARTICIPANTS","8"))
OUT=Path("data/command_center.json")
HISTORY=Path("data/discord_history.json")
MAX_HISTORY=180

def fail(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)

def fetch_files():
    if not TOKEN:
        fail("PARATRANZ_TOKEN is not set.")
    headers={"Accept":"application/json","Authorization":TOKEN,"User-Agent":"MD-Farsi-Localization-Command-Center/4.0"}
    last=""
    for attempt in range(3):
        try:
            with urlopen(Request(f"{API}/projects/{PROJECT_ID}/files",headers=headers),timeout=30) as r:
                data=json.loads(r.read().decode("utf-8"))
            if not isinstance(data,list):
                fail("Unexpected ParaTranz files response.")
            return data
        except HTTPError as e:
            last=f"ParaTranz HTTP {e.code}: {e.read().decode(errors='replace')[:800]}"
        except (URLError,json.JSONDecodeError) as e:
            last=f"ParaTranz request failed: {e}"
        if attempt<2:
            time.sleep(2**(attempt+1))
    fail(last or "ParaTranz request failed after retries.")

def percent(v,total):
    return round(v/total*100,2) if total else 0.0

def previous():
    try:
        return json.loads(OUT.read_text(encoding="utf-8"))
    except (FileNotFoundError,json.JSONDecodeError,TypeError):
        return {}

def main():
    files=fetch_files()
    total=sum(int(x.get("total") or 0) for x in files)
    translated=sum(int(x.get("translated") or 0) for x in files)
    reviewed=sum(int(x.get("reviewed") or 0) for x in files)
    words=sum(int(x.get("words") or 0) for x in files)
    now=datetime.now(timezone.utc)
    tp=percent(translated,total); rp=percent(reviewed,total)

    old=previous()
    oldp=old.get("progress",{}) if isinstance(old,dict) else {}
    delta_translated=translated-int(oldp.get("translated") or translated)
    delta_reviewed=reviewed-int(oldp.get("reviewed") or reviewed)

    history=[]
    try:
        h=json.loads(HISTORY.read_text(encoding="utf-8"))
        history=h.get("snapshots",[]) if isinstance(h,dict) else []
    except (FileNotFoundError,json.JSONDecodeError,TypeError):
        history=[]
    snap={"timestamp":now.isoformat(),"epoch":int(now.timestamp()),"files":len(files),"strings":total,
          "translated":translated,"reviewed":reviewed,"words":words,
          "translation_percent":tp,"review_percent":rp,
          "delta_translated":delta_translated,"delta_reviewed":delta_reviewed}
    if not history or history[-1].get("timestamp","")[:16]!=snap["timestamp"][:16]:
        history.append(snap)
    else:
        history[-1]=snap
    history=history[-MAX_HISTORY:]

    sections={}
    for item in files:
        name=str(item.get("name") or item.get("path") or "unknown")
        section=name.split("/",1)[0]
        bucket=sections.setdefault(section,{"files":0,"strings":0,"translated":0,"reviewed":0,"words":0})
        bucket["files"]+=1
        bucket["strings"]+=int(item.get("total") or 0)
        bucket["translated"]+=int(item.get("translated") or 0)
        bucket["reviewed"]+=int(item.get("reviewed") or 0)
        bucket["words"]+=int(item.get("words") or 0)
    for v in sections.values():
        v["translation_percent"]=percent(v["translated"],v["strings"])
        v["review_percent"]=percent(v["reviewed"],v["strings"])

    payload={"schema":3,"timestamp":now.isoformat(),"updated_at":now.isoformat(),
      "project":{"name":"Millennium Dawn Farsi Localization","id":int(PROJECT_ID),
                 "url":f"https://paratranz.cn/projects/{PROJECT_ID}","participants":PARTICIPANTS},
      "stats":{"files":len(files),"strings":total,"translated":translated,"reviewed":reviewed,"words":words,
               "translation_percent":tp,"review_percent":rp},
      "project_stats":{"files":len(files),"strings":total,"translated":translated,"reviewed":reviewed,"words":words},
      "progress":{"translation_percent":tp,"review_percent":rp,"translated":translated,"reviewed":reviewed,
                  "delta_translated":delta_translated,"delta_reviewed":delta_reviewed},
      "sections":sections,
      "milestones":[{"threshold":1,"icon":"🎉","label":"اولین ۱٪"},{"threshold":10,"icon":"🌱","label":"۱۰٪"},
                    {"threshold":25,"icon":"📈","label":"۲۵٪"},{"threshold":50,"icon":"🔥","label":"۵۰٪"},
                    {"threshold":75,"icon":"🚀","label":"۷۵٪"},{"threshold":100,"icon":"🏁","label":"۱۰۰٪"}],
      "health":{"paratranz":"online","snapshot":"healthy","history":"healthy","visuals":"pending","discord":"pending"},
      "automation":{"interval_hours":6,"engine":"GitHub Actions","last_sync":now.isoformat(),"next_sync":None},
      "source":"ParaTranz API"}

    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    HISTORY.parent.mkdir(parents=True,exist_ok=True)
    HISTORY.write_text(json.dumps({"schema":1,"project_id":int(PROJECT_ID),"snapshots":history},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Snapshot OK: {translated:,}/{total:,} translated ({tp:.2f}%), {reviewed:,} reviewed ({rp:.2f}%), history={len(history)}")

if __name__=="__main__":
    main()
