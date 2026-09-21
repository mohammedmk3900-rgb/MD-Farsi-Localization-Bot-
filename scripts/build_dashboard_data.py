"""Build the secret-free public dashboard data contract."""
import json
from pathlib import Path
SOURCE=Path("data/command_center.json"); OUTPUT=Path("dashboard/public/data/dashboard.json"); HISTORY=Path("data/discord_history.json"); HOUT=Path("dashboard/public/data/history.json")
def main():
    source=json.loads(SOURCE.read_text(encoding="utf-8"))
    required=("project","stats","progress","sections","milestones","automation","health","updated_at")
    missing=[k for k in required if k not in source]
    if missing: raise SystemExit("Snapshot missing: "+", ".join(missing))
    public={k:source.get(k) for k in ("project","stats","progress","sections","milestones","milestones_crossed","records","history","automation","health","updated_at","source")}
    public["schema"]=9
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(public,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if HISTORY.exists():
        h=json.loads(HISTORY.read_text(encoding="utf-8"))
        HOUT.write_text(json.dumps({"schema":1,"items":h.get("snapshots",[])},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    else: HOUT.write_text('{"schema":1,"items":[]}\n',encoding="utf-8")
if __name__=="__main__": main()
