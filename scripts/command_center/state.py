#!/usr/bin/env python3
"""Safe JSON state helpers with atomic writes."""
import json, os
from pathlib import Path
def load_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError,json.JSONDecodeError,TypeError,ValueError):
        return default
def save_json(path, value):
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_suffix(p.suffix+".tmp")
    tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    os.replace(tmp,p)
