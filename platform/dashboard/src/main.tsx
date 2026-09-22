import React,{useEffect,useState} from "react";
import {createRoot} from "react-dom/client";
import "./style.css";

type Dashboard={schema:number;project:any;health:any;discord:any};
const API=import.meta.env.VITE_API_BASE||"";

function App(){
 const [data,setData]=useState<Dashboard|null>(null);
 const [error,setError]=useState("");
 useEffect(()=>{fetch(API+"/api/v1/dashboard").then(r=>r.ok?r.json():Promise.reject()).then(setData).catch(()=>setError("اتصال به Platform Core برقرار نشد."));},[]);
 if(error)return <main><h1>MD Farsi Command Center</h1><p>{error}</p></main>;
 if(!data)return <main><h1>در حال اتصال به Core…</h1></main>;
 const p=data.project||{};
 return <main>
  <header><div><span>MD NEWS</span><h1>مرکز فرمان پروژه فارسی‌سازی</h1></div><div className="status">{data.health?.status||"unknown"}</div></header>
  <section className="grid">
   <article><b>ترجمه</b><strong>{Number(p.translation_percent||0).toFixed(2)}%</strong><small>{p.translated||0} / {p.strings_total||0} رشته</small></article>
   <article><b>بازبینی</b><strong>{Number(p.review_percent||0).toFixed(2)}%</strong><small>{p.reviewed||0} بررسی</small></article>
   <article><b>واژه‌ها</b><strong>{p.words_total||0}</strong><small>{p.files||0} فایل</small></article>
   <article><b>Discord</b><strong>{data.discord?.channels||0}</strong><small>کانال عملیاتی</small></article>
  </section>
  <section className="panel"><h2>معماری</h2><p>ParaTranz → Platform Core → MD news → Discord / Dashboard</p><p>بدون Webhook به‌عنوان منبع منطق کسب‌وکار.</p></section>
 </main>
}
createRoot(document.getElementById("root")!).render(<App/>);