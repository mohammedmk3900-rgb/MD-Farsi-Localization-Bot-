#!/usr/bin/env python3
"""Persist real ParaTranz snapshots for the Discord Command Center."""
import json, os, sys
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

API="https://paratranz.cn/api"; PROJECT_ID=os.getenv("PARATRANZ_PROJECT_ID","19621")
TOKEN=os.getenv("PARATRANZ_TOKEN"); STATE="data/discord_history.json"; MAX_POINTS=180

def fail(m):print(f"ERROR: {m}",file=sys.stderr);sys.exit(1)
def get_files():
    if not TOKEN:fail("PARATRANZ_TOKEN is not set.")
    h={"Accept":"application/json","Authorization":TOKEN,"User-Agent":"MD-Farsi-Localization-History/4.0"}
    try:
        with urlopen(Request(f"{API}/projects/{PROJECT_ID}/files",headers=h),timeout=30) as r:data=json.loads(r.read().decode())
    except HTTPError as e:fail(f"HTTP {e.code}: {e.read().decode(errors='replace')[:800]}")
    except (URLError,json.JSONDecodeError) as e:fail(f"ParaTranz request failed: {e}")
    if not isinstance(data,list):fail("Unexpected ParaTranz files response.")
    return data
def load():
    try:
        with open(STATE,encoding="utf-8") as f:
            d=json.load(f);return d.get("snapshots",[]) if isinstance(d,dict) else []
    except (FileNotFoundError,ValueError,TypeError):return []
def main():
    fs=get_files(); total=sum(int(x.get("total") or 0) for x in fs); tr=sum(int(x.get("translated") or 0) for x in fs)
    rv=sum(int(x.get("reviewed") or 0) for x in fs); words=sum(int(x.get("words") or 0) for x in fs); now=datetime.now(timezone.utc)
    snap={"timestamp":now.isoformat(),"epoch":int(now.timestamp()),"files":len(fs),"strings":total,"translated":tr,"reviewed":rv,"words":words,
          "translation_percent":round(tr/total*100 if total else 0,4),"review_percent":round(rv/total*100 if total else 0,4)}
    points=load()
    if not points or points[-1].get("timestamp","")[:16]!=snap["timestamp"][:16]:points.append(snap)
    else:points[-1]=snap
    points=points[-MAX_POINTS:]
    os.makedirs("data",exist_ok=True)
    with open(STATE,"w",encoding="utf-8") as f:json.dump({"schema":1,"project_id":int(PROJECT_ID),"snapshots":points},f,ensure_ascii=False,indent=2);f.write("\n")
    print(f"History: {len(points)} points | {snap['translation_percent']:.2f}% translation | {snap['review_percent']:.2f}% review")
if __name__=="__main__":main()
