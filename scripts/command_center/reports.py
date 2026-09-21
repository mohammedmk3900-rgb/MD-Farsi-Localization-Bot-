#!/usr/bin/env python3
"""Build Persian daily/weekly report payloads from Command Center history."""
from datetime import datetime, timezone, timedelta
from .state import load_json
def build(period="daily"):
    snap=load_json("data/command_center.json",{})
    hist=load_json("data/discord_history.json",{}).get("snapshots",[])
    now=datetime.now(timezone.utc)
    days=1 if period=="daily" else 7
    cutoff=(now-timedelta(days=days)).timestamp()
    rows=[x for x in hist if float(x.get("epoch",0))>=cutoff]
    current=snap.get("stats",{})
    first=rows[0] if rows else current
    dt=int(current.get("translated",0))-int(first.get("translated",0))
    dr=int(current.get("reviewed",0))-int(first.get("reviewed",0))
    dp=round(float(current.get("translation_percent",0))-float(first.get("translation_percent",0)),2)
    rp=round(float(current.get("review_percent",0))-float(first.get("review_percent",0)),2)
    label="روزانه" if period=="daily" else "هفتگی"
    return {"username":"MD Farsi Localization • Command Center","embeds":[{
      "title":"📋 گزارش {} • Command Center".format(label),
      "description":"### 🇮🇷 فارسی‌سازی Millennium Dawn\n\n**بازه:** {}\n**رشد ترجمه:** {:+.2f}%  •  {:+,} رشته\n**رشد بازبینی:** {:+.2f}%  •  {:+,} رشته".format(label,dp,dt,rp,dr),
      "fields":[
        {"name":"📊 وضعیت فعلی","value":"ترجمه: **{:.2f}%**\nبازبینی: **{:.2f}%**".format(float(current.get("translation_percent",0)),float(current.get("review_percent",0))),"inline":True},
        {"name":"📝 ترجمه‌شده","value":"**{:,}** / **{:,}**".format(int(current.get("translated",0)),int(current.get("strings",0))),"inline":True},
        {"name":"🔎 بازبینی‌شده","value":"**{:,}**".format(int(current.get("reviewed",0))),"inline":True}
      ],
      "footer":{"text":"MD Farsi Localization • گزارش خودکار"},"timestamp":now.isoformat()
    }]}
