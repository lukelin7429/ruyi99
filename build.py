#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""如意精舍 ruyi99.org static site generator.
Reads /tmp/ruyi99-crawl/site.json (content + slug map + tree), emits HTML."""
import json, os, re, html, glob

ROOT=os.path.dirname(os.path.abspath(__file__))
SITE=json.load(open("/tmp/ruyi99-crawl/site.json"))
try:
    VTITLES=json.load(open("/tmp/ruyi99-crawl/vtitles.json"))  # {ytid:title} optional
except Exception:
    VTITLES={}
content=SITE["content"]; omap=SITE["omap"]; children=SITE["children"]
out2path={}
for p,o in omap.items():
    if o=="/":
        if p=="/home": out2path[o]=p
        out2path.setdefault(o,p)
    else:
        out2path[o]=p

NAV=[("首頁","/"),("法師簡介","/bhikkhuni/"),("讀書會","/study-group/"),
     ("法會資訊","/news/"),("影音","/videos/"),("專欄","/column/"),("夏令營","/camps/")]
NAVNAME={o:n for n,o in NAV}
SITE_NAME="如意精舍"
ADDR="南投縣信義鄉自強村陽和巷80號"; TEL="049-2791267"
EMAIL_MASTER="a0909359364@gmail.com"; EMAIL_LUKE="luke@ruyi99.org"
EMAIL_EN="ruyi@ruyimeditation.org"; EN_SITE="https://ruyimeditation.org"
YT_CHANNEL="https://www.youtube.com/@ruyi99"

BASE=os.environ.get("BASE","/ruyi99")  # project-pages base; set BASE="" for apex ruyi99.org
def u(path):  # prefix an absolute site path with BASE
    if path.startswith("http"): return path
    if not path.startswith("/"): path="/"+path
    return BASE+path

def esc(s): return html.escape(s,quote=True)

def natkey(o):
    last=o.strip("/").split("/")[-1]
    nums=re.findall(r'\d+',last)
    return (int(nums[0]) if nums else 0, last)

def name_of(o):
    if o in NAVNAME: return NAVNAME[o]
    p=out2path.get(o)
    if p and p in content: return content[p]["name"] or o
    return o.strip("/").split("/")[-1]

def crumb_html(o):
    if o=="/": return ""
    parts=[]; segs=o.strip("/").split("/")
    acc="/"; parts.append('<a href="%s">首頁</a>'%u("/"))
    for i,s in enumerate(segs):
        acc="/"+"/".join(segs[:i+1])+"/"
        nm=esc(name_of(acc))
        if i==len(segs)-1:
            parts.append('<span>›</span>'+nm)
        else:
            parts.append('<span>›</span><a href="%s">%s</a>'%(u(acc),nm))
    return '<div class="crumb">'+''.join(parts)+'</div>'

def topbar(active_top):
    links=[]
    for n,o in NAV:
        cls=' class="active"' if o==active_top else ''
        links.append('<a href="%s"%s>%s</a>'%(u(o),cls,esc(n)))
    return (
    '<header class="topbar"><div class="topbar-inner">'
    '<a class="brand" href="%s"><span class="seal">如</span><span>如意精舍'%u("/")+
    '<small>RU-YI MEDITATION</small></span></a>'
    '<button class="hamb" aria-label="選單">☰</button>'
    '<nav class="nav">'+''.join(links)+'</nav>'
    '</div></header>')

def footer():
    return (
    '<footer class="foot"><div class="wrap">'
    '<div><div class="fbrand">如意精舍</div>'
    '<p>南投縣信義鄉風櫃斗山上，海拔約 800 公尺。<br>兩位法師於 2017 年回鄉弘法，'
    '以弘揚正知正見的佛法為理念，帶領大眾聞思修。</p></div>'
    '<div><h4>聯絡</h4><p>%s<br>電話：%s<br>'
    '<a href="mailto:%s">%s</a><br><a href="mailto:%s">%s</a></p></div>'
    '<div><h4>連結</h4><p>'
    '<a href="%s" target="_blank" rel="noopener">YouTube 頻道 @ruyi99</a><br>'
    '<a href="%s" target="_blank" rel="noopener">English site · ruyimeditation.org</a></p></div>'
    '</div><div class="wrap bot">© 如意精舍 Ru-Yi Meditation Center · 南投信義．風櫃斗</div>'
    '</footer>'
    %(ADDR,TEL,EMAIL_MASTER,EMAIL_MASTER,EMAIL_LUKE,EMAIL_LUKE,YT_CHANNEL,EN_SITE))

LIGHTBOX='<div class="lb" id="lb"><button class="lb-close" id="lb-close">×</button><div class="lb-box" id="lb-box"></div></div>'

def page(title, active_top, body, desc=""):
    return (
    '<!DOCTYPE html><html lang="zh-Hant"><head><meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width,initial-scale=1">'
    '<title>%s · 如意精舍</title>'
    '<meta name="description" content="%s">'
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600;700&display=swap" rel="stylesheet">'
    '<link rel="stylesheet" href="%s">'
    '</head><body>%s%s%s%s'
    '<script src="%s"></script></body></html>'
    %(esc(title),esc(desc or title),u("/assets/css/site.css"),topbar(active_top),body,footer(),LIGHTBOX,u("/assets/js/site.js")))

def yt_thumb(ytid,cap=""):
    t=VTITLES.get(ytid,cap)
    capdiv='<div class="cap">%s</div>'%esc(t) if t else ''
    return ('<button class="vthumb rvl" data-yt="%s">'
            '<div class="thumbimg" style="background-image:url(https://i.ytimg.com/vi/%s/hqdefault.jpg)">'
            '<span class="play"><i></i></span></div>%s</button>'%(ytid,ytid,capdiv))

def render_blocks(blocks, pagename=""):
    """Render ordered content blocks, grouping youtube runs into grids."""
    out=[]; prose=[]; vids=[]
    def flush_prose():
        if prose:
            out.append('<div class="prose rvl">'+''.join(prose)+'</div>'); prose.clear()
    def flush_vids():
        if not vids: return
        if len(vids)==1:
            out.append('<div class="video-solo rvl"><iframe loading="lazy" '
                'src="https://www.youtube-nocookie.com/embed/%s?rel=0" '
                'allow="encrypted-media;fullscreen" allowfullscreen></iframe></div>'%vids[0])
        else:
            out.append('<div class="video-grid">'+''.join(yt_thumb(v) for v in vids)+'</div>')
        vids.clear()
    for b in blocks:
        if b["t"]=="yt":
            flush_prose(); vids.append(b["id"]); continue
        flush_vids()
        if b["t"]=="h":
            lvl=b["level"]
            tag="h2" if lvl<=2 else ("h3" if lvl==3 else "h4")
            txt=b["text"]
            # demote long heading-styled paragraphs to body for readability
            if lvl>=3 and len(txt)>34:
                prose.append('<p>%s</p>'%esc(txt))
            else:
                prose.append('<%s>%s</%s>'%(tag,esc(txt),tag))
        elif b["t"]=="li":
            prose.append('<p>• %s</p>'%esc(b["text"]))
        elif b["t"]=="p":
            prose.append('<p>%s</p>'%esc(b["text"]))
        elif b["t"]=="img":
            flush_prose()
            out.append('<figure class="rvl"><img loading="lazy" src="%s" alt=""></figure>'%u("/"+b["src"]))
    flush_prose(); flush_vids()
    return ''.join(out)

def child_section(o):
    kids=sorted(children.get(o,[]),key=natkey)
    if not kids: return ""
    # decide style
    def chapterlike(k):
        nm=name_of(k); return bool(re.search(r'\d',nm)) and len(nm)<=16
    dense = len(kids)>=10 and sum(chapterlike(k) for k in kids)>=len(kids)*0.6
    items=[]
    if dense:
        for k in kids:
            nm=name_of(k); p=out2path.get(k); has_v=p and content.get(p,{}).get("n_yt",0)>0
            num=(re.findall(r'\d+',k.strip("/").split("/")[-1]) or [""])[0]
            badge='<span class="vid">▶ 影片</span>' if has_v else ''
            items.append('<a href="%s"><span class="n">%s</span><span>%s</span>%s</a>'
                         %(u(k),num,esc(nm),badge))
        return '<div class="chaplist rvl">'+''.join(items)+'</div>'
    else:
        for k in kids:
            nm=name_of(k); p=out2path.get(k); d=content.get(p,{})
            kc=children.get(k,[])
            if kc:
                meta='共 %d 篇'%len(kc)
            elif d.get("n_yt",0)>0:
                meta='%d 部影片'%d["n_yt"]
            else:
                meta='閱讀 →'
            items.append('<a class="card" href="%s"><div class="k">Ru-Yi</div>'
                         '<h3>%s</h3><div class="meta">%s</div></a>'%(u(k),esc(nm),meta))
        return '<div class="cards rvl">'+''.join(items)+'</div>'

# ---------------- HOME (bespoke) ----------------
HERO_ART=('<svg class="hero-art" viewBox="0 0 1200 600" preserveAspectRatio="xMidYMax slice" '
 'xmlns="http://www.w3.org/2000/svg" aria-hidden="true">'
 '<defs><linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">'
 '<stop offset="0" stop-color="#2b2030"/><stop offset="0.5" stop-color="#6e2840"/>'
 '<stop offset="1" stop-color="#9c3a55"/></linearGradient>'
 '<linearGradient id="m1" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#4a2236"/><stop offset="1" stop-color="#3a1a2b"/></linearGradient>'
 '<linearGradient id="m2" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#5e2940"/><stop offset="1" stop-color="#4a2034"/></linearGradient></defs>'
 '<rect width="1200" height="600" fill="url(#sky)"/>'
 '<circle cx="980" cy="130" r="66" fill="#f0d9a6" opacity="0.85"/>'
 '<circle cx="958" cy="118" r="66" fill="#9c3a55" opacity="0.55"/>'
 '<g opacity="0.5" fill="#fff">'
 '<path d="M0 250 Q300 215 620 245 T1200 235" stroke="#fff" stroke-width="0" fill="none"/>'
 '<rect x="0" y="300" width="1200" height="40" fill="#fff" opacity="0.05"/></g>'
 '<path d="M0 430 L180 320 L340 410 L520 300 L700 400 L880 330 L1050 420 L1200 350 L1200 600 L0 600Z" fill="url(#m2)"/>'
 '<path d="M0 520 L200 430 L420 510 L640 420 L860 500 L1080 440 L1200 500 L1200 600 L0 600Z" fill="url(#m1)"/>'
 '<g stroke="#7c2942" stroke-width="5" fill="none" opacity="0.9" stroke-linecap="round">'
 '<path d="M70 600 C120 500 150 470 130 410"/><path d="M130 470 C150 450 180 455 195 440"/>'
 '<path d="M126 430 C146 414 176 420 188 405"/></g>'
 '<g fill="#f4e3e8">'
 + ''.join('<g transform="translate(%d,%d) scale(%.2f)">'
   '<circle cx="0" cy="-6" r="5"/><circle cx="5.7" cy="-1.8" r="5"/><circle cx="3.5" cy="4.8" r="5"/>'
   '<circle cx="-3.5" cy="4.8" r="5"/><circle cx="-5.7" cy="-1.8" r="5"/>'
   '<circle cx="0" cy="0" r="2.4" fill="#c98a2e"/></g>'%(x,y,s)
   for x,y,s in [(196,440,1.5),(190,402,1.2),(150,410,1.0),(128,408,0.9),(210,455,1.0)])
 +'</g></svg>')

def build_home():
    d=content["/home"]
    imgs=[b["src"] for b in d["blocks"] if b["t"]=="img"]
    intro=[b["text"] for b in d["blocks"] if b["t"] in ("h","p") and len(b.get("text",""))>30][:4]
    vids=[b["id"] for b in d["blocks"] if b["t"]=="yt"]
    _=u  # base-aware url helper
    body=['<section class="hero"><div class="hero-photo hero-designed">%s<div class="hero-text rvl">'
          '<div class="eyebrow">南投 · 信義 · 風櫃斗</div>'
          '<h1>如意精舍</h1>'
          '<p>海拔約 800 公尺的山上道場，以弘揚正知正見的佛法為理念，'
          '帶領大眾聞思修、深植菩提種子。</p></div></div></section>'%HERO_ART]
    body.append('<main><div class="prose rvl">'+''.join('<p>%s</p>'%esc(t) for t in intro)+'</div>')
    # section cards
    secs=[("法師簡介","/bhikkhuni/","認識回鄉弘法的兩位法師"),
          ("讀書會","/study-group/","線上研讀經論，聞思修並進"),
          ("法會資訊","/news/","念佛、浴佛與每月定期法會"),
          ("影音","/videos/","佛法常識與淨土講座影音"),
          ("專欄","/column/","三位作者的佛法心得文章"),
          ("夏令營","/camps/","兒童心靈環保成長營歷年紀錄")]
    cards=''.join('<a class="card" href="%s"><div class="k">Ru-Yi</div><h3>%s</h3>'
                  '<p>%s</p><div class="meta">前往 →</div></a>'%(u(o),esc(n),esc(desc))
                  for n,o,desc in secs)
    body.append('<div class="section-title rvl"><h2>度眾事業</h2><div class="rule"></div></div>')
    body.append('<div class="cards rvl">'+cards+'</div>')
    if vids:
        body.append('<div class="section-title rvl"><h2>精選影音</h2><div class="rule"></div></div>')
        body.append('<div class="video-grid">'+''.join(yt_thumb(v) for v in vids)+'</div>')
    # 精舍剪影 gallery (real photos only — drop small icons/logos)
    gal=[i for i in imgs if os.path.exists(os.path.join(ROOT,i))
         and os.path.getsize(os.path.join(ROOT,i))>=80*1024]
    if gal:
        body.append('<div class="section-title rvl"><h2>精舍剪影</h2><div class="rule"></div></div>')
        body.append('<div class="gallery rvl">'+''.join(
            '<figure><img loading="lazy" src="%s" alt="如意精舍"></figure>'%u("/"+g) for g in gal)+'</div>')
    body.append('</main>')
    return page("如意精舍 · 南投信義風櫃斗山上的佛教道場","/",''.join(body),
                "如意精舍位於南投縣信義鄉風櫃斗，海拔約800公尺。兩位法師2017年回鄉弘法，弘揚正知正見的佛法。")

# ---------------- generic interior page ----------------
def build_page(o):
    p=out2path[o]; d=content[p]; nm=d["name"]
    top="/"+o.strip("/").split("/")[0]+"/"
    active=top if top in NAVNAME else "/"
    blocks=d["blocks"]
    has_children=bool(children.get(o))
    body=['<div class="pagehead"><div class="wrap">%s<h1>%s</h1></div></div><main><div class="wrap">'
          %(crumb_html(o),esc(nm))]
    inner=render_blocks(blocks,nm)
    if inner: body.append(inner)
    if has_children:
        if inner:
            body.append('<div class="section-title rvl"><h2>篇章</h2><div class="rule"></div></div>')
        body.append(child_section(o))
    body.append('</div></main>')
    return page(nm,active,''.join(body),nm+" · 如意精舍")

def write(o,htmltext):
    rel=o.strip("/")
    d=os.path.join(ROOT,rel) if rel else ROOT
    os.makedirs(d,exist_ok=True)
    open(os.path.join(d,"index.html"),"w").write(htmltext)

if __name__=="__main__":
    n=0
    write("/",build_home()); n+=1
    for o in sorted(out2path):
        if o=="/": continue
        write(o,build_page(o)); n+=1
    # CNAME + nojekyll
    open(os.path.join(ROOT,".nojekyll"),"w").write("")
    print("built %d pages"%n)
