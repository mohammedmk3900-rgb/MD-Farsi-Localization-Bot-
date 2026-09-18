#!/usr/bin/env python3
"""Single-source-of-truth collector for MD Farsi Localization Command Center V3."""
import json, os, sys
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen\nimport time

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
    last_error = None
    for attempt in range(3):
        request=Request(f"{API}/projects/{PROJECT_ID}/files",headers={
            "Accept":"application/json","Authorization":TOKEN,
            "User-Agent":"MD-Farsi-Localization-Command-Center/3.1"})
        try:
            with urlopen(request,timeout=30) as response:
                data=json.loads(response.read().decode())
            if not isinstance(data,list): fail("Unexpected ParaTranz files response.")
            return data
        except HTTPError as e:
            last_error = f"ParaTranz HTTP {e.code}: {e.read().decode(errors='replace')[:800]}"
        except (URLError,json.JSONDecodeError) as e:
            last_error = f"ParaTranz request failed: {e}"
        if attempt < 2: time.sleep(2 ** (attempt + 1))
    fail(last_error or "ParaTranz request failed after retries.")

