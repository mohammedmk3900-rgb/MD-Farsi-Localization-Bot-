#!/usr/bin/env python3
"""Sync an external glossary website into the Discord Persian glossary channel."""
from __future__ import annotations
import csv, hashlib, html, io, json, os, re, sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

SOURCE_URL=os.getenv("GLOSSARY_SOURCE_URL","").strip()
WEBHOOK=os.getenv("DISCORD_GLOSSARY_WEBHOOK_URL","").strip()
STATE="data/glossary.json"
MESSAGE_STATE="data/discord_messages.json"
MAX_ENTRIES=int(os.getenv("GLOSSARY_MAX_ENTRIES","1000"))

def fail(m): print("ERROR: "+m,file=sys.stderr); sys.exit(1)
def fetch(url):
    req=Request(url,headers={"Accept":"application/json,text/csv,text/html,text/plain;q=0.9,*/*;q=0.8","User-Agent":"MD-Farsi-Localization-Glossary/1.0"})
    try:
        with urlopen(req,timeout=30) as r: return r.read(),r.headers.get("Content-Type","")
    except (HTTPError,URLError) as e: raise RuntimeError(f"Glossary source request failed: {e}") from e

class TableParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.rows=[]; self.row=[]; self.cell=[]; self.in_cell=False
    def handle_starttag(self,tag,attrs):
        if tag=="tr": self.row=[]
        elif tag in {"td","th"}: self.cell=[]; self.in_cell=True
    def handle_data(self,data):
        if self.in_cell: self.cell.append(data)
    def handle_endtag(self,tag):
        if tag in {"td","th"} and self.in_cell:
            self.row.append(" ".join("".join(self.cell).split())); self.cell=[]; self.in_cell=False
        elif tag=="tr" and self.row: self.rows.append(self.row); self.row=[]

def clean(v): return re.sub(r"\s+"," ",html.unescape(str(v or ""))).strip()
def pair(a,b):
    a,b=clean(a),clean(b)
    return {"source":a,"target":b} if a and b and a.casefold()!=b.casefold() else None

def parse_json(text):
    data=json.loads(text); out=[]
    if isinstance(data,dict):
        for k,v in data.items():
            if isinstance(v,str):
                p=pair(k,v)
            elif isinstance(v,dict):
                p=pair(v.get("source") or v.get("english") or v.get("en") or v.get("term"),
                       v.get("target") or v.get("persian") or v.get("fa") or v.get("farsi") or v.get("translation"))
            else: p=None
            if p: out.append(p)
    elif isinstance(data,list):
        for item in data:
            if isinstance(item,dict):
                p=pair(item.get("source") or item.get("english") or item.get("en") or item.get("term"),
                       item.get("target") or item.get("persian") or item.get("fa") or item.get("farsi") or item.get("translation"))
            elif isinstance(item,(list,tuple)) and len(item)>=2: p=pair(item[0],item[1])
            else: p=None
            if p: out.append(p)
    return out

def parse_delimited(text,delimiter):
    rows=list(csv.reader(io.StringIO(text),delimiter=delimiter))
    if not rows: return []
    h=[clean(x).lower() for x in rows[0]]
    src=next((i for i,x in enumerate(h) if x in {"source","english","en","term","key"}),0)
    dst=next((i for i,x in enumerate(h) if x in {"target","persian","fa","farsi","translation"}),1 if len(h)>1 else 0)
    header=any(x in {"source","english","en","term","target","persian","fa","farsi","translation"} for x in h)
    out=[]
    for row in rows[1 if header else 0:]:
        if len(row)>max(src,dst):
            p=pair(row[src],row[dst])
            if p: out.append(p)
    return out

def parse_html(text):
    p=TableParser(); p.feed(text)
    if not p.rows: return []
    h=[clean(x).lower() for x in p.rows[0]]
    src=next((i for i,x in enumerate(h) if x in {"source","english","en","term","key"}),0)
    dst=next((i for i,x in enumerate(h) if x in {"target","persian","fa","farsi","translation"}),1)
    out=[]
    for row in p.rows[1:]:
        if len(row)>max(src,dst):
            x=pair(row[src],row[dst])
            if x: out.append(x)
    return out

def parse_text(text):
    out=[]
    for line in text.splitlines():
        line=clean(line)
        if not line or line.startswith("#"): continue
        parts=re.split(r"\s*(?:=>|→|->|\|)\s*",line,maxsplit=1)
        if len(parts)==2:
            p=pair(parts[0],parts[1])
            if p: out.append(p)
    return out

def parse(body,ctype):
    text=body.decode("utf-8-sig",errors="replace"); ctype=ctype.lower()
    if "json" in ctype or text.lstrip().startswith(("{","[")):
        try: x=parse_json(text)
        except json.JSONDecodeError: x=[]
        if x: return x
    if "html" in ctype or "<table" in text.lower():
        x=parse_html(text)
        if x: return x
    if "\t" in text[:2000]:
        x=parse_delimited(text,"\t")
        if x: return x
    if "," in text[:2000]:
        x=parse_delimited(text,",")
        if x: return x
    return parse_text(text)

def normalize(entries):
    unique={}
    for x in entries: unique[x["source"].casefold()]=x
    out=sorted(unique.values(),key=lambda x:x["source"].casefold())
    if not out: raise RuntimeError("No glossary entries were found in the source.")
    return out[:MAX_ENTRIES]

def load(path,default):
    try:
        with open(path,encoding="utf-8") as f: return json.load(f)
    except (FileNotFoundError,json.JSONDecodeError,TypeError,ValueError): return default

def save(path,data):
    os.makedirs(os.path.dirname(path) or ".",exist_ok=True); tmp=path+".tmp"
    with open(tmp,"w",encoding="utf-8") as f: json.dump(data,f,ensure_ascii=False,indent=2); f.write("\n")
    os.replace(tmp,path)

def discord(method,url,payload):
    r=Request(url,data=json.dumps(payload,ensure_ascii=False).encode(),headers={"Accept":"application/json","Content-Type":"application/json","User-Agent":"MD-Farsi-Localization-Glossary/1.0"},method=method)
    with urlopen(r,timeout=30) as x:
        raw=x.read().decode(); return json.loads(raw) if raw else {}

def build_embed(entries):
    now=datetime.now(timezone.utc)
    shown=entries[:25]
    lines=[f"**{x['source']}** → {x['target']}" for x in shown]
    if len(entries)>25: lines.append(f"… و **{len(entries)-25:,}** مدخل دیگر")
    digest=hashlib.sha256(json.dumps(entries,ensure_ascii=False,sort_keys=True).encode()).hexdigest()[:12]
    return {"author":{"name":"MD FARSI LOCALIZATION • COMMAND CENTER"},"title":"📚 واژه‌نامه ترجمه • GLOSSARY",
      "description":"واژه‌نامه پروژه به‌صورت خودکار از منبع تعیین‌شده همگام می‌شود.\n\n"+"\n".join(lines),
      "fields":[{"name":"📚 تعداد مدخل","value":f"**{len(entries):,}**","inline":True},
                {"name":"🔐 نسخه","value":digest,"inline":True},
                {"name":"🔄 وضعیت","value":"به‌روزرسانی خودکار","inline":True}],
      "footer":{"text":f"آخرین Sync: {now.strftime('%Y-%m-%d %H:%M UTC')} • منبع خارجی"},
      "timestamp":now.isoformat()}

def main():
    if not SOURCE_URL: fail("GLOSSARY_SOURCE_URL is not set.")
    if not WEBHOOK: fail("DISCORD_GLOSSARY_WEBHOOK_URL is not set.")
    body,ctype=fetch(SOURCE_URL); entries=normalize(parse(body,ctype))
    old=load(STATE,{}); old_entries=old.get("entries",[]) if isinstance(old,dict) else []
    if entries==old_entries:
        print(f"Glossary unchanged: {len(entries):,} entries"); return
    save(STATE,{"schema":1,"source_url":SOURCE_URL,"updated_at":datetime.now(timezone.utc).isoformat(),"entries":entries})
    mid=str(load(MESSAGE_STATE,{}).get("glossary","")).strip()
    embed=build_embed(entries)
    if mid:
        try:
            discord("PATCH",f"{WEBHOOK}/messages/{mid}",{"embeds":[embed]})
            print(f"Glossary updated: {len(entries):,} entries"); return
        except HTTPError: pass
    result=discord("POST",WEBHOOK+"?wait=true",{"username":"MD Farsi Localization • Command Center","embeds":[embed]})
    if not result.get("id"): fail("Discord did not return a glossary message ID.")
    state=load(MESSAGE_STATE,{})
    if not isinstance(state,dict): state={}
    state["glossary"]=str(result["id"]); save(MESSAGE_STATE,state)
    print(f"Glossary message created: {len(entries):,} entries")

if __name__=="__main__":
    try: main()
    except (RuntimeError,HTTPError,URLError) as e: fail(str(e))
