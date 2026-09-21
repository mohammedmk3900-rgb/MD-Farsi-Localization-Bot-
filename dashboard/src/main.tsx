import React from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

type Data = {
  stats: {
    files: number;
    strings: number;
    translated: number;
    reviewed: number;
    words: number;
    translation_percent: number;
    review_percent: number;
  };
  progress: { delta_translated: number };
  health: { status: string; percentage: number };
  updated_at?: string | null;
};

const empty: Data = {
  stats: { files: 0, strings: 0, translated: 0, reviewed: 0, words: 0, translation_percent: 0, review_percent: 0 },
  progress: { delta_translated: 0 },
  health: { status: "pending", percentage: 0 },
};

function App() {
  const [d, setD] = React.useState<Data>(empty);

  React.useEffect(() => {
    fetch(`${import.meta.env.BASE_URL}data/dashboard.json`)
      .then((r) => {
        if (!r.ok) throw new Error("dashboard data unavailable");
        return r.json();
      })
      .then(setD)
      .catch(() => setD(empty));
  }, []);

  const s = d.stats;
  const progress = Math.min(100, Math.max(0, s.translation_percent || 0));
  const status = d.health.status || "pending";

  return (
    <main>
      <header>
        <div>
          <small>MD FARSI LOCALIZATION</small>
          <h1>Command Center</h1>
          <p>مرکز عملیات فارسی‌سازی Millennium Dawn</p>
        </div>
        <b className={status}>● {status.toUpperCase()}</b>
      </header>

      <section className="hero">
        <span>پیشرفت ترجمه</span>
        <strong>{progress.toFixed(2)}%</strong>
        <div className="bar"><i style={{ width: `${progress}%` }} /></div>
        <em>{s.translated.toLocaleString()} از {s.strings.toLocaleString()} رشته</em>
      </section>

      <section className="grid">
        <Card t="📦 فایل‌ها" v={s.files} />
        <Card t="📝 کلمات" v={s.words} />
        <Card t="🔎 بازبینی" v={s.review_percent.toFixed(2) + "%"} />
        <Card t="📈 تغییر اخیر" v={d.progress.delta_translated} />
      </section>

      <footer>
        ParaTranz → Command Center • Single Source of Truth
        {d.updated_at ? ` • آخرین همگام‌سازی: ${d.updated_at}` : ""}
      </footer>
    </main>
  );
}

function Card({ t, v }: { t: string; v: number | string }) {
  return <article><span>{t}</span><strong>{typeof v === "number" ? v.toLocaleString() : v}</strong></article>;
}

createRoot(document.getElementById("root")!).render(<App />);
