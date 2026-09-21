"""Read-only JSON API for Command Center state and history."""
from __future__ import annotations
import json
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs,urlparse
from .services.database import recent
STATE=Path("data/command_center.json")
class Handler(BaseHTTPRequestHandler):
 def _send(self,status:int,payload:object)->None:
  body=json.dumps(payload,ensure_ascii=False).encode();self.send_response(status);self.send_header("Content-Type","application/json; charset=utf-8");self.send_header("Cache-Control","no-store");self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body)
 def do_GET(self)->None:
  p=urlparse(self.path)
  if p.path=="/api/v1/command-center":
   if not STATE.exists():self._send(503,{"error":"state_unavailable"});return
   try:self._send(200,json.loads(STATE.read_text(encoding="utf-8")))
   except (OSError,json.JSONDecodeError):self._send(500,{"error":"invalid_state"})
   return
  if p.path=="/api/v1/history":
   try:self._send(200,{"items":recent(int(parse_qs(p.query).get("limit",["30"])[0]))})
   except (ValueError,OSError,json.JSONDecodeError):self._send(400,{"error":"invalid_history_request"})
   return
  self._send(404,{"error":"not_found"})
 def log_message(self,*_args)->None:return
def serve(host:str="127.0.0.1",port:int=8787)->None:ThreadingHTTPServer((host,port),Handler).serve_forever()
if __name__=="__main__":serve()
