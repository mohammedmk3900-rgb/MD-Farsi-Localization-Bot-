import React from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

type Dashboard = {
  schema?: number;
  project: any;
  health: any;
  discord: any;
};

const empty: Dashboard = {
  project: null,
  health: { status: "pending" },
  discord: null,
};

const nf = new Intl.NumberFormat("fa-IR");
const API = String(import.meta.env.VITE_PLATFORM_API_URL || "").replace(/\/$/, "");

async function getJson(path: string) {
  const url = API ? API + path : path;
  const response = await fetch(url, { headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error(String(response.status));
  return response.json();
}

function App() {
  const [dashboard, setDashboard] = React.useState<Dashboard>(empty);
  const [history, setHistory] = React.useState<any[]>([]);
  const [error, setError] = React.useState("");

  const load = React.useCallback(async () => {
    try {
      const [d, h] = await Promise.all([
        getJson("/api/v1/dashboard"),
        getJson("/api/v1/history?limit=36"),
      ]);
      setDashboard(d);
      setHistory(h.items || []);
      setError("");
    } catch {
      setError("اتصال به Platform Core برقرار نشد.");
    }
  }, []);

  React.useEffect(() => {
    load();
    const timer = window.setInterval(load, 60_000);
    return () => window.clearInterval(timer);
  }, [load]);

  const p = dashboard.project || {};
  const translation = Number(p.translation_percent || 0);
  const review = Number(p.review_percent || 0);
  const status = dashboard.health?.status || "pending";

  return (
    <div className="shell" dir="rtl">
      <header>
        <div className="brand">
          <div className="logo">🇮🇷</div>
          <div>
            <small>MD FARSI LOCALIZATION</small>
            <h1>COMMAND CENTER <b>PLATFORM</b></h1>
            <p>مرکز عملیات حرفه‌ای فارسی‌سازی Millennium Dawn</p>
          </div>
        </div>
        <div className={"status " + status}>
          ● {status === "healthy" ? "SYSTEM ONLINE" : status === "degraded" ? "SYSTEM DEGRADED" : "SYSTEM CHECKING"}
        </div>
      </header>

      {error && <div className="panel error">{error}</div>}

      <section className="hero panel">
        <div className="heroTop">
          <div><small>LIVE PLATFORM CORE</small><h2>پیشرفت کل پروژه</h2></div>
          <strong>{translation.toFixed(2)}%</strong>
        </div>
        <div className="track"><i style={{ width: Math.min(100, Math.max(0, translation)) + "%" }} /></div>
        <div className="meta">
          <span>{nf.format(p.translated || 0)} / {nf.format(p.strings_total || 0)} رشته</span>
          <span>{nf.format(p.reviewed || 0)} بازبینی</span>
        </div>
      </section>

      <section className="metrics">
        <Metric icon="📝" title="ترجمه‌شده" value={nf.format(p.translated || 0)} sub={translation.toFixed(2) + "%"} />
        <Metric icon="🔎" title="بازبینی‌شده" value={nf.format(p.reviewed || 0)} sub={review.toFixed(2) + "%"} />
        <Metric icon="📦" title="فایل‌ها" value={nf.format(p.files || 0)} sub={nf.format(p.words_total || 0) + " کلمه"} />
        <Metric icon="🧩" title="Discord" value={nf.format(dashboard.discord?.channels || 0)} sub="کانال" />
      </section>

      <section className="cols">
        <section className="panel box">
          <Title label="PROGRESS HISTORY" title="روند پیشرفت" />
          <div className="chart">
            {history.length < 2
              ? <div className="empty">تاریخچه پس از چند همگام‌سازی شکل می‌گیرد.</div>
              : history.slice().reverse().map((x: any, i: number) => {
                  const value = Number(x.payload?.project?.translation_percent || 0);
                  return <div className="col" key={i}><i style={{ height: Math.max(4, value) + "%" }} /></div>;
                })}
          </div>
        </section>
        <section className="panel box">
          <Title label="PLATFORM STATUS" title="وضعیت موتور" />
          <div className="rows">
            <Row a="منبع ترجمه" b="ParaTranz" />
            <Row a="واژه‌نامه" b="ParaTranz Terms" />
            <Row a="تاریخچه" b="SQLite Event Store" />
            <Row a="Discord" b={dashboard.discord ? "Connected" : "Not connected"} />
            <Row a="Health" b={status} />
          </div>
        </section>
      </section>

      <footer>
        <span>MD Farsi Localization • Platform Command Center</span>
        <span>Source: Platform Core • Project {p.project_id || 19621}</span>
      </footer>
    </div>
  );
}

function Metric({ icon, title, value, sub }: { icon: string; title: string; value: string; sub: string }) {
  return <article className="metric panel"><span>{icon}</span><small>{title}</small><b>{value}</b><em>{sub}</em></article>;
}
function Title({ label, title }: { label: string; title: string }) {
  return <div className="title"><div><small>{label}</small><h3>{title}</h3></div></div>;
}
function Row({ a, b }: { a: string; b: string }) {
  return <div className="row"><span>{a}</span><b>{b}</b></div>;
}

createRoot(document.getElementById("root")!).render(<App />);
