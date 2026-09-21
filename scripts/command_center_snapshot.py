#!/usr/bin/env python3
"""Single source of truth for the MD Farsi Localization Command Center V5."""
import json, os, sys, time
from datetime import datetime, timezone, timedelta
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
MILESTONES=[1,10,25,50,75,100]

def fail(msg):
    print("ERROR: "+msg,file=sys.stderr)
    sys.exit(1)

def fetch_files():
    if not TOKEN: fail("PARATRANZ_TOKEN is not set.")
    headers={"Accept":"application/json","Authorization":TOKEN,"User-Agent":"MD-Farsi-Localization-Command-Center/5.0"}
    last=""
    for attempt in range(4):
        try:
            with urlopen(Request(f"{API}/projects/{PROJECT_ID}/files",headers=headers),timeout=30) as r:
                data=json.loads(r.read().decode("utf-8"))
            if not isinstance(data,list): fail("Unexpected ParaTranz files response.")
            return data
        except HTTPError as e:
            detail=e.read().decode(errors="replace")[:800]
            last=f"ParaTranz HTTP {e.code}: {detail}"
            if e.code not in {429,500,502,503,504} or attempt>=3: break
            retry=e.headers.get("Retry-After")
            time.sleep(min(float(retry) if retry else 2**attempt,30))
        except (URLError,json.JSONDecodeError) as e:
            last=f"ParaTranz request failed: {e}"
            if attempt>=3: break
            time.sleep(min(2**attempt,10))
    fail(last or "ParaTranz request failed after retries.")

def percent(v,total): return round(v/total*100,2) if total else 0.0

def read_json(path,default):
    try: return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError,json.JSONDecodeError,TypeError,ValueError): return default

def next_sync(now):
    hour=((now.hour//6)+1)*6
    if hour>=24: target=now.replace(hour=0,minute=0,second=0,microsecond=0)+timedelta(days=1)
    else: target=now.replace(hour=hour,minute=0,second=0,microsecond=0)
    return target.isoformat()

def main():
    files=fetch_files()
    total=sum(int(x.get("total") or 0) for x in files)
    translated=sum(int(x.get("translated") or 0) for x in files)
    reviewed=sum(int(x.get("reviewed") or 0) for x in files)
    words=sum(int(x.get("words") or 0) for x in files)
    now=datetime.now(timezone.utc)
    tp=percent(translated,total); rp=percent(reviewed,total)

    old=read_json(OUT,{})
    old_stats=old.get("stats",{}) if isinstance(old,dict) else {}
    oldp=old.get("progress",{}) if isinstance(old,dict) else {}
    old_t=int(old_stats.get("translated",oldp.get("translated",translated)) or translated)
    old_r=int(old_stats.get("reviewed",oldp.get("reviewed",reviewed)) or reviewed)
    old_tp=float(oldp.get("translation_percent",old_stats.get("translation_percent",tp)) or tp)
    old_rp=float(oldp.get("review_percent",old_stats.get("review_percent",rp)) or rp)
    delta_t=translated-old_t; delta_r=reviewed-old_r
    delta_tp=round(tp-old_tp,2); delta_rp=round(rp-old_rp,2)

    history_doc=read_json(HISTORY,{})
    history=history_doc.get("snapshots",[]) if isinstance(history_doc,dict) else []
    sync_count=len(history)+1
    record=read_json("data/command_center_records.json",{})
    best_t=max(int(record.get("best_delta_translated",0)),delta_t)
    best_r=max(int(record.get("best_delta_reviewed",0)),delta_r)
    best_tp=max(float(record.get("best_delta_translation_percent",0)),delta_tp)
    best_rp=max(float(record.get("best_delta_review_percent",0)),delta_rp)

    crossed=[n for n in MILESTONES if old_tp < n <= tp]
    snap={"timestamp":now.isoformat(),"epoch":int(now.timestamp()),"files":len(files),"strings":total,
          "translated":translated,"reviewed":reviewed,"words":words,
          "translation_percent":tp,"review_percent":rp,
          "delta_translated":delta_t,"delta_reviewed":delta_r,
          "delta_translation_percent":delta_tp,"delta_review_percent":delta_rp,
          "milestones_crossed":crossed}
    if not history or history[-1].get("timestamp","")[:16]!=snap["timestamp"][:16]: history.append(snap)
    else: history[-1]=snap
    history=history[-MAX_HISTORY:]

    sections={}
    for item in files:
        name=str(item.get("name") or item.get("path") or "unknown")
        section=name.split("/",1)[0]
        b=sections.setdefault(section,{"files":0,"strings":0,"translated":0,"reviewed":0,"words":0})
        b["files"]+=1; b["strings"]+=int(item.get("total") or 0); b["translated"]+=int(item.get("translated") or 0)
        b["reviewed"]+=int(item.get("reviewed") or 0); b["words"]+=int(item.get("words") or 0)
    for b in sections.values():
        b["translation_percent"]=percent(b["translated"],b["strings"]); b["review_percent"]=percent(b["reviewed"],b["strings"])

    payload={"schema":5,"timestamp":now.isoformat(),"updated_at":now.isoformat(),
      "project":{"name":"Millennium Dawn Farsi Localization","id":int(PROJECT_ID),
                 "url":f"https://paratranz.cn/projects/{PROJECT_ID}","participants":PARTICIPANTS},
      "stats":{"files":len(files),"strings":total,"translated":translated,"reviewed":reviewed,"words":words,
               "translation_percent":tp,"review_percent":rp},
      "project_stats":{"files":len(files),"strings":total,"translated":translated,"reviewed":reviewed,"words":words},
      "progress":{"translation_percent":tp,"review_percent":rp,"translated":translated,"reviewed":reviewed,
                  "delta_translated":delta_t,"delta_reviewed":delta_r,"delta_translation_percent":delta_tp,"delta_review_percent":delta_rp},
      "history":{"count":len(history),"max":MAX_HISTORY,"latest_epoch":int(now.timestamp())},
      "records":{"best_delta_translated":best_t,"best_delta_reviewed":best_r,
                 "best_delta_translation_percent":best_tp,"best_delta_review_percent":best_rp,
                 "sync_count":sync_count},
      "sections":sections,
      "milestones":[{"threshold":n,"icon":i,"label":l} for n,i,l in
        [(1,"🎉","اولین ۱٪"),(10,"🌱","۱۰٪"),(25,"📈","۲۵٪"),(50,"🔥","۵۰٪"),(75,"🚀","۷۵٪"),(100,"🏁","۱۰۰٪")]],
      "milestones_crossed":crossed,
      "health":{"status":"pending","percentage":0,"passed_checks":0,"total_checks":0,"checks":{},"updated_at":None},
      "automation":{"interval_hours":6,"engine":"GitHub Actions","last_sync":now.isoformat(),"next_sync":next_sync(now),"mode":"scheduled","timezone":"UTC"},
      "source":"ParaTranz API"}

    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    Path("data/command_center_records.json").write_text(json.dumps({
      "best_delta_translated":best_t,"best_delta_reviewed":best_r,
      "best_delta_translation_percent":best_tp,"best_delta_review_percent":best_rp,
      "sync_count":sync_count,"updated_at":now.isoformat()
    },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    HISTORY.parent.mkdir(parents=True,exist_ok=True)
    HISTORY.write_text(json.dumps({"schema":2,"project_id":int(PROJECT_ID),"snapshots":history},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Snapshot OK: {translated:,}/{total:,} translated ({tp:.2f}%), delta={delta_t:+,}; reviewed={reviewed:,}, delta={delta_r:+,}; crossed={crossed}")

if __name__=="__main__": main()
