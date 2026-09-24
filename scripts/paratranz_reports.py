#!/usr/bin/env python3
"""Send optional daily/weekly Persian reports without affecting the 6-hour sync."""
import os,sys
sys.path.insert(0,"scripts")
from command_center.http_client import request_json
from command_center.reports import build

def main():
    webhook=os.getenv("DISCORD_REPORTS_WEBHOOK_URL")
    if not webhook:
        print("DISCORD_REPORTS_WEBHOOK_URL not configured; report skipped.")
        return
    period=os.getenv("REPORT_PERIOD","daily")
    request_json(webhook+"?wait=true",method="POST",payload=build(period))
    print("Report sent:",period)

if __name__=="__main__": main()
