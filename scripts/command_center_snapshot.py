#!/usr/bin/env python3
"""Single-source-of-truth collector for MD Farsi Localization Command Center V3."""
import json, os, sys
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

API="https://paratranz.cn/api"
PROJECT_ID=os.getenv("PARATRANZ_PROJECT_ID","19621")
TOKEN=os.getenv("PARATRANZ_TOKEN")
OUT="data/command_center.json"
HISTORY="data/discord_history.json"
MAX_HISTORY=180

def fail(msg):
    print(f"ERROR: {msg}", file=sys.stderr); sys.exit(1)

def api_files():
    if not TOKEN: fail("PARATRANZ_TOKEN is not set.")
    request=Request(f"{API}/projects/{PROJECT_ID}/files",headers={
        "Accept":"application/json","Authorization":TOKEN,
        "User-Agent":"MD-Farsi-Localization-Command-Center/3.0"})
    try:
        with urlopen(request,timeout=30) as response:
            data=json.loads(response.read().decode())
    except HTTPError as e:
        fail(f"ParaTranz HTTP {e.code}: {e.read().decode(errors='replace')[:800]}")
    except (URLError,json.JSONDecodeError) as e:
        fail(f"ParaTranz request failed: {e}")
    if not isinstance(data,list): fail("Unexpected ParaTranz files response.")
    return data

def main():
    files=api_files()
    total=sum(int(x.get("total") or 0) for x in files)
    translated=sum(int(x.get("translated") or 0) for x in files)
    reviewed=sum(int(x.get("reviewed") or 0) for x in files)
    words=sum(int(x.get("words") or 0) for x in files)
    now=datetime.now(timezone.utc)
    translation=translated/total*100 if total else 0
    review=reviewed/total*100 if total else 0

    snapshot={
        "schema":3,"timestamp":now.isoformat(),"epoch":int(now.timestamp()),
        "project":{"id":int(PROJECT_ID),"files":len(files),"strings":total,
                   "translated":translated,"reviewed":reviewed,"words":words},
        "progress":{"translation_percent":round(translation,4),
                    "review_percent":round(review,4),
                    "remaining_percent":round(max(0,100-translation),4)},
        "health":{"paratranz":"online","data_integrity":"healthy","collector":"healthy"},
        "automation":{"interval_hours":6,"last_sync":now.isoformat()}
    }
    os.makedirs("data",exist_ok=True)
    with open(OUT,"w",encoding="utf-8") as f:
        json.dump(snapshot,f,ensure_ascii=False,indent=2); f.write("\n")

    points=[]
    try:
        with open(HISTORY,encoding="utf-8") as f:
            old=json.load(f)
            if isinstance(old,dict) and isinstance(old.get("snapshots"),list):
                points=old["snapshots"]
    except (FileNotFoundError,ValueError,TypeError):
        pass

    point={**snapshot["project"],**snapshot["progress"],
           "timestamp":snapshot["timestamp"],"epoch":snapshot["epoch"]}
    if not points or points[-1].get("timestamp","")[:16] != point["timestamp"][:16]:
        points.append(point)
    else:
        points[-1]=point

    with open(HISTORY,"w",encoding="utf-8") as f:
        json.dump({"schema":3,"project_id":int(PROJECT_ID),
                   "snapshots":points[-MAX_HISTORY:]},f,ensure_ascii=False,indent=2)
        f.write("\n")
    print(json.dumps(snapshot,ensure_ascii=False))

if __name__=="__main__":
    main()
