#!/usr/bin/env python3
"""Generate data-driven SVG visuals for Discord."""
import html, json, os
HISTORY="data/discord_history.json"; OUT="assets/discord"

def load():
    try:
        with open(HISTORY,encoding="utf-8") as f:return json.load(f).get("snapshots",[])
    except (FileNotFoundError,ValueError,TypeError):return []
def latest(p):
    return p[-1] if p else {"files":0,"strings":0,"translated":0,"reviewed":0,"translation_percent":0,"review_percent":0}
def grid():
    return '<g stroke="#fff" stroke-opacity=".055">'+''.join(f'<path d="M0 {y}h1600"/>' for y in (100,200,300,400))+''.join(f'<path d="M{x} 0v520"/>' for x in (160,320,480,640,800,960,1120,1280,1440))+"</g>"
def defs():
    return '<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#070b17"/><stop offset=".55" stop-color="#111d3d"/><stop offset="1" stop-color="#263b78"/></linearGradient><linearGradient id="cyan"><stop stop-color="#6d7cff"/><stop offset="1" stop-color="#31d7ff"/></linearGradient><linearGradient id="green"><stop stop-color="#35e58a"/><stop offset="1" stop-color="#7affc0"/></linearGradient><radialGradient id="glow"><stop stop-color="#6d7cff" stop-opacity=".42"/><stop offset="1" stop-color="#6d7cff" stop-opacity="0"/></radialGradient></defs>'
def stats_svg(s):
    t=s["translation_percent"]; r=s["review_percent"]; tw=max(0,min(650,t/100*650))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="520" viewBox="0 0 1600 520">{defs()}<rect width="1600" height="520" rx="28" fill="url(#bg)"/><circle cx="1300" cy="250" r="330" fill="url(#glow)"/>{grid()}
<text x="76" y="82" fill="#91a0ff" font-family="Arial" font-size="18" font-weight="700" letter-spacing="4">MD FARSI LOCALIZATION • COMMAND CENTER</text>
<text x="76" y="164" fill="#fff" font-family="Arial" font-size="62" font-weight="800">PROJECT STATISTICS</text>
<text x="78" y="207" fill="#b8c1df" font-family="Arial" font-size="24">آمار زنده پروژه فارسی‌سازی Millennium Dawn</text>
<g transform="translate(76 255)"><rect width="860" height="72" rx="20" fill="#fff" fill-opacity=".055" stroke="#fff" stroke-opacity=".1"/><text x="24" y="31" fill="#aeb8dc" font-family="Arial" font-size="15" font-weight="700">TRANSLATION • ترجمه</text><text x="24" y="58" fill="#fff" font-family="Arial" font-size="24" font-weight="800">{t:.2f}%</text><rect x="170" y="24" width="650" height="24" rx="12" fill="#000" fill-opacity=".25"/><rect x="170" y="24" width="{tw:.1f}" height="24" rx="12" fill="url(#cyan)"/></g>
<g transform="translate(76 345)"><rect width="410" height="82" rx="18" fill="#fff" fill-opacity=".055"/><text x="22" y="30" fill="#8f9cff" font-family="Arial" font-size="14" font-weight="700">STRINGS</text><text x="22" y="61" fill="#fff" font-family="Arial" font-size="24" font-weight="800">{s["translated"]:,} / {s["strings"]:,}</text></g>
<g transform="translate(510 345)"><rect width="410" height="82" rx="18" fill="#fff" fill-opacity=".055"/><text x="22" y="30" fill="#8f9cff" font-family="Arial" font-size="14" font-weight="700">REVIEW • بازبینی</text><text x="22" y="61" fill="#fff" font-family="Arial" font-size="24" font-weight="800">{r:.2f}%</text></g>
<g transform="translate(1040 86)"><circle cx="220" cy="170" r="140" fill="none" stroke="#fff" stroke-opacity=".08" stroke-width="24"/><circle cx="220" cy="170" r="140" fill="none" stroke="url(#cyan)" stroke-width="24" stroke-dasharray="{max(0,min(880,t/100*880)):.1f} 880" stroke-linecap="round" transform="rotate(-90 220 170)"/><text x="220" y="164" text-anchor="middle" fill="#fff" font-family="Arial" font-size="43" font-weight="800">{t:.2f}%</text><text x="220" y="197" text-anchor="middle" fill="#aeb8dc" font-family="Arial" font-size="18">ترجمه</text></g>
<text x="76" y="484" fill="#6f7ca5" font-family="Arial" font-size="15" letter-spacing="3">LIVE DATA • PARATRANZ API • AUTOMATED SYNC</text></svg>'''
def chart_path(values,x0=1080,y0=120,width=400,height=190):
    if not values:return ""
    step=width/max(len(values)-1,1); out=[]
    for i,v in enumerate(values):
        x=x0+i*step; y=y0+height-(v/100)*height; out.append(("M" if i==0 else "L")+f"{x:.1f},{y:.1f}")
    return " ".join(out)
def progress_svg(s,points):
    t=s["translation_percent"]; vals=[float(x.get("translation_percent",0)) for x in points[-30:]]; path=chart_path(vals)
    last_y=310-(vals[-1]/100*190) if vals else 310
    width=max(0,min(814,t/100*814))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="520" viewBox="0 0 1600 520">{defs()}<rect width="1600" height="520" rx="28" fill="url(#bg)"/><circle cx="1250" cy="250" r="340" fill="url(#glow)"/>{grid()}
<text x="76" y="82" fill="#91a0ff" font-family="Arial" font-size="18" font-weight="700" letter-spacing="4">LIVE PROGRESS • پیشرفت زنده</text><text x="76" y="170" fill="#fff" font-family="Arial" font-size="72" font-weight="800">{t:.2f}%</text><text x="78" y="212" fill="#b8c1df" font-family="Arial" font-size="25">از مسیر فارسی‌سازی تکمیل شده</text>
<rect x="76" y="260" width="850" height="70" rx="35" fill="#000" fill-opacity=".25" stroke="#fff" stroke-opacity=".1"/><rect x="94" y="278" width="{width:.1f}" height="34" rx="17" fill="url(#green)"/>
<text x="76" y="390" fill="#fff" font-family="Arial" font-size="25" font-weight="700">{s["translated"]:,} ترجمه‌شده</text><text x="76" y="425" fill="#b8c1df" font-family="Arial" font-size="20">از {s["strings"]:,} رشته</text>
<g><text x="1080" y="82" fill="#aeb8dc" font-family="Arial" font-size="16" font-weight="700">HISTORY • ۳۰ نقطه اخیر</text><rect x="1050" y="105" width="460" height="235" rx="22" fill="#000" fill-opacity=".18" stroke="#fff" stroke-opacity=".08"/><path d="{path}" fill="none" stroke="url(#green)" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/><circle cx="1480" cy="{last_y:.1f}" r="7" fill="#fff"/></g>
<text x="76" y="485" fill="#6f7ca5" font-family="Arial" font-size="15" letter-spacing="3">PROGRESS ENGINE • HISTORY TRACKING • PARATRANZ</text></svg>'''
def main():
    points=load(); s=latest(points); os.makedirs(OUT,exist_ok=True)
    with open(os.path.join(OUT,"stats.svg"),"w",encoding="utf-8") as f:f.write(stats_svg(s))
    with open(os.path.join(OUT,"progress.svg"),"w",encoding="utf-8") as f:f.write(progress_svg(s,points))
    with open(os.path.join(OUT,"progress-history.svg"),"w",encoding="utf-8") as f:f.write(progress_svg(s,points))
    print(f"Generated visuals from {len(points)} real snapshots.")
if __name__=="__main__":main()
