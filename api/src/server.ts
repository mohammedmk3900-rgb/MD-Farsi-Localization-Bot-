import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import type { ServerResponse } from "node:http";

const port = Number(process.env.PORT ?? 8787);
const root = resolve(process.env.MD_FARSI_DATA_ROOT ?? process.cwd());

async function jsonFile(name: string): Promise<string> {
  return readFile(resolve(root, name), "utf8");
}

function send(res: ServerResponse, status: number, body: string): void {
  res.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "no-store",
    "Access-Control-Allow-Origin": "*",
  });
  res.end(body);
}

const server = createServer(async (req, res) => {
  try {
    const path = new URL(req.url ?? "/", "http://localhost").pathname;
    if (path === "/health") {
      send(res, 200, JSON.stringify({ status: "ok", service: "md-farsi-command-center-api", version: 9 }));
      return;
    }
    if (path === "/api/v1/command-center") {
      send(res, 200, await jsonFile("dashboard/public/data/dashboard.json"));
      return;
    }
    if (path === "/api/v1/history") {
      send(res, 200, await jsonFile("dashboard/public/data/history.json"));
      return;
    }
    send(res, 404, JSON.stringify({ error: "not_found" }));
  } catch (error) {
    const message = error instanceof Error ? error.message : "internal_error";
    send(res, 500, JSON.stringify({ error: "data_unavailable", detail: message }));
  }
});

server.listen(port, "0.0.0.0", () => {
  console.log(`MD Farsi Command Center API V9 listening on :${port}`);
});
