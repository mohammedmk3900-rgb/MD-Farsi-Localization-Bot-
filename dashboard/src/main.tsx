import React from "react";
import {createRoot} from "react-dom/client";
import "./styles.css";

type D={project:any;stats:any;progress:any;sections:Record<string,any>;milestones:any[];milestones_crossed:number[];records:any;history:any;automation:any;health:any;updated_at:string;source:string};
const empty:D={project:{id:19621},stats:{files:0,strings:0,translated:0,reviewed:0,words:0,translation_percent:0,review_percent:0},progress:{delta_translated:0,delta_reviewed:0,translation_percent:0,review_percent:0},sections:{},milestones:[],milestones_crossed:[],records:{},history:{count:0},automation:{interval_hours:6,engine:"GitHub Actions"},health:{status:"pending",percentage:0,passed_checks:0,total_checks:0},updated_at:"",source:"ParaTranz API"};
const nf=new Intl.NumberFormat("fa-IR");
const P=({n}:{n:number})=>Number(n||0).toFixed(2)+"%";
function App(){
 const [d,setD]=React.useState<D>(empty),[history,setHistory]=React.useState<any[]>([]);
 React.useEffect(()=>{const b=import.meta.env.BASE_URL;Promise.all([fetch(b+"data/dashboard.json").then(r=>r.json()),fetch(b+"data/history.json").then(r=>r.ok?r.json():{items:[]}).catch(()=>({items:[]}))]).then(([x,h])=>{setD(x);setHistory(h.items||[])}).catch(()=>{})},[]);
 const s=d.stats,p=d.progress,rows=Object.entries(d.sections||{}).sort((a:any,b:any)=>b[1].translation_percent-a[1].translation_percent);
 const status=d.health?.status||"pending";
 return <div className="shell">
  <header><div className="brand"><div className="logo">🇮🇷</div><div><small>MD FARSI LOCALIZATION</small><h1>COMMAND CENTER <b>V9</b></h1><p>مرکز عملیات حرفه‌ای فارسی‌سازی Millennium Dawn</p></div></div><div className={"status "+status}>● {status==="healthy"?"SYSTEM ONLINE":status==="degraded"?"SYSTEM DEGRADED":"SYSTEM CHECKING"}</div></header>
  <section className="hero panel"><div className="heroTop"><div><small>PROJECT OVERVIEW</small><h2>پیشرفت کل پروژه</h2></div><strong>{P(s.translation_percent)}</strong></div><div className="track"><i style={{width:Math.min(100,Math.max(0,s.translation_percent))+"%"}}/></div><div className="meta"><span>{nf.format(s.translated)} / {nf.format(s.strings)} رشته</span><span>{p.delta_translated>=0?"▲":"▼"} {nf.format(Math.abs(p.delta_translated))} از آخرین snapshot</span></div></section>
  <section className="metrics"><Metric icon="📝" t="ترجمه‌شده" v={nf.format(s.translated)} sub={P(s.translation_percent)}/><Metric icon="🔎" t="بازبینی‌شده" v={nf.format(s.reviewed)} sub={P(s.review_percent)}/><Metric icon="📦" t="فایل‌ها" v={nf.format(s.files)} sub={nf.format(s.words)+" کلمه"}/><Metric icon="⚡" t="تغییر اخیر" v={(p.delta_translated>=0?"+":"")+nf.format(p.delta_translated)} sub="رشته"/></section>
  <section className="cols"><section className="panel box"><Title a="PROGRESS HISTORY" t="روند پیشرفت"/><div className="chart">{history.length<2?<div className="empty">تاریخچه پس از چند همگام‌سازی شکل می‌گیرد.</div>:history.slice(-36).map((x:any)=><div className="col" key={x.timestamp}><i style={{height:Math.max(4,x.translation_percent)+"%"}}/></div>)}</div></section><section className="panel box"><Title a="SYSTEM STATUS" t="وضعیت موتور"/><div className="rows"><Row a="منبع" b="ParaTranz"/><Row a="موتور" b={d.automation.engine}/><Row a="فاصله sync" b={d.automation.interval_hours+" ساعت"}/><Row a="سلامت" b={d.health.passed_checks+"/"+d.health.total_checks}/><Row a="آخرین اجرا" b={fmt(d.updated_at)}/></div></section></section>
  <section className="panel box"><Title a="LOCALIZATION MAP" t="وضعیت بخش‌ها"/><div className="sections">{rows.map(([name,v]:any)=><div className="srow" key={name}><div><b>{name}</b><small>{nf.format(v.translated)} / {nf.format(v.strings)}</small></div><strong>{P(v.translation_percent)}</strong><div className="mini"><i style={{width:Math.min(100,v.translation_percent)+"%"}}/></div></div>)}</div></section>
  <section className="milestones">{d.milestones.map((m:any)=><div className={"mile "+(d.milestones_crossed.includes(m.threshold)?"done":"")} key={m.threshold}><span>{m.icon}</span><b>{m.threshold}%</b><small>{m.label}</small></div>)}</section>
  <footer><span>MD Farsi Localization • Command Center V9</span><span>Source: {d.source} • Project {d.project.id}</span></footer>
 </div>
}
function Metric({icon,t,v,sub}:{icon:string;t:string;v:string;sub:string}){return <article className="metric panel"><span>{icon}</span><small>{t}</small><b>{v}</b><em>{sub}</em></article>}
function Title({a,t}:{a:string;t:string}){return <div className="title"><div><small>{a}</small><h3>{t}</h3></div></div>}
function Row({a,b}:{a:string;b:string}){return <div className="row"><span>{a}</span><b>{b}</b></div>}
function fmt(v:string){if(!v)return "—";try{return new Date(v).toLocaleString("fa-IR",{dateStyle:"medium",timeStyle:"short"})}catch{return v}}
createRoot(document.getElementById("root")!).render(<App/>);
