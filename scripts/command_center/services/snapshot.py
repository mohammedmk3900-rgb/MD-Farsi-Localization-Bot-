"""Build the canonical Command Center V9 snapshot."""
from __future__ import annotations
from datetime import datetime,timezone
from ..config import Config
from ..models import ProjectStats,Snapshot
from ..state import load_json,save_json
from .progress import crossed,delta
SNAPSHOT_PATH="data/command_center.json"; HISTORY_PATH="data/discord_history.json"; RECORDS_PATH="data/command_center_records.json"
MILESTONES=[(1,"🎉","اولین ۱٪"),(10,"🌱","۱۰٪"),(25,"📈","۲۵٪"),(50,"🔥","۵۰٪"),(75,"🚀","۷۵٪"),(100,"🏁","۱۰۰٪")]
def build(config:Config,stats:ProjectStats,files:list[dict]):
    old=load_json(SNAPSHOT_PATH,{}) if isinstance(load_json(SNAPSHOT_PATH,{}),dict) else {}
    os=old.get("stats",{}); op=old.get("progress",{})
    previous={"translated":os.get("translated",stats.translated),"reviewed":os.get("reviewed",stats.reviewed),
              "translation_percent":op.get("translation_percent",os.get("translation_percent",stats.translation_percent)),
              "review_percent":op.get("review_percent",os.get("review_percent",stats.review_percent))}
    now=datetime.now(timezone.utc); d=delta(stats,previous); milestones=crossed(float(previous["translation_percent"]),stats.translation_percent)
    hd=load_json(HISTORY_PATH,{}); history=hd.get("snapshots",[]) if isinstance(hd,dict) else []
    rec=Snapshot(now.isoformat(),int(now.timestamp()),stats,d,milestones).to_dict()
    if history and history[-1].get("timestamp","")[:16]==rec["timestamp"][:16]: history[-1]=rec
    else: history.append(rec)
    history=history[-config.history_limit:]
    records=load_json(RECORDS_PATH,{}) if isinstance(load_json(RECORDS_PATH,{}),dict) else {}
    records={"best_delta_translated":max(int(records.get("best_delta_translated",0)),d.translated),
      "best_delta_reviewed":max(int(records.get("best_delta_reviewed",0)),d.reviewed),
      "best_delta_translation_percent":max(float(records.get("best_delta_translation_percent",0)),d.translation_percent),
      "best_delta_review_percent":max(float(records.get("best_delta_review_percent",0)),d.review_percent),
      "sync_count":int(records.get("sync_count",0))+1,"updated_at":now.isoformat()}
    sections={}
    for item in files:
        name=str(item.get("name") or item.get("path") or "unknown"); key=name.split("/",1)[0]
        x=sections.setdefault(key,{"files":0,"strings":0,"translated":0,"reviewed":0,"words":0})
        for k,src in (("files",None),("strings","total"),("translated","translated"),("reviewed","reviewed"),("words","words")): x[k]+=1 if k=="files" else int(item.get(src) or 0)
    for x in sections.values():
        total=x["strings"]; x["translation_percent"]=round(x["translated"]/total*100,2) if total else 0; x["review_percent"]=round(x["reviewed"]/total*100,2) if total else 0
    payload={"schema":9,"timestamp":now.isoformat(),"updated_at":now.isoformat(),
      "project":{"name":"Millennium Dawn Farsi Localization","id":config.project_id,"url":config.project_url,"participants":config.participants},
      "stats":{**stats.to_dict(),"translation_percent":stats.translation_percent,"review_percent":stats.review_percent},
      "progress":{"translation_percent":stats.translation_percent,"review_percent":stats.review_percent,"translated":stats.translated,"reviewed":stats.reviewed,**d.to_dict()},
      "history":{"count":len(history),"max":config.history_limit,"latest_epoch":int(now.timestamp())},"records":records,"sections":sections,
      "milestones":[{"threshold":n,"icon":i,"label":l} for n,i,l in MILESTONES],"milestones_crossed":milestones,
      "health":old.get("health",{"status":"pending","percentage":0,"passed_checks":0,"total_checks":0,"checks":{},"updated_at":None}),
      "automation":{"interval_hours":config.sync_hours,"engine":"GitHub Actions","last_sync":now.isoformat(),"mode":"scheduled","timezone":"UTC"},
      "source":"ParaTranz API"}
    save_json(SNAPSHOT_PATH,payload); save_json(RECORDS_PATH,records); save_json(HISTORY_PATH,{"schema":8,"project_id":config.project_id,"snapshots":history})
    save_json("data/dashboard_history.json",{"schema":1,"items":history})
    return payload,Snapshot(now.isoformat(),int(now.timestamp()),stats,d,milestones)
