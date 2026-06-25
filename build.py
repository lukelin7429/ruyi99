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
    '<a class="brand" href="%s"><img class="brand-logo" src="%s" alt="如意精舍" width="42" height="42"><span>如意精舍'%(u("/"),u("/assets/img/ruyi-logo.png"))+
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
    icons=('<link rel="icon" href="%s" sizes="any">'
           '<link rel="icon" type="image/png" href="%s" sizes="32x32">'
           '<link rel="apple-touch-icon" href="%s">'
           %(u("/assets/favicon.ico"),u("/assets/favicon-32.png"),u("/assets/apple-touch-icon.png")))
    return (
    '<!DOCTYPE html><html lang="zh-Hant"><head><meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width,initial-scale=1">'
    '<title>%s · 如意精舍</title>'
    '<meta name="description" content="%s">%s'
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600;700&display=swap" rel="stylesheet">'
    '<link rel="stylesheet" href="%s">'
    '</head><body>%s%s%s%s'
    '<script src="%s"></script></body></html>'
    %(esc(title),esc(desc or title),icons,u("/assets/css/site.css"),topbar(active_top),body,footer(),LIGHTBOX,u("/assets/js/site.js")))

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

# 專欄 helpers ---------------------------------------------------------------
BYLINES=("文/林吉祥","文/謝呂賢","文/孫一成")
def article_full_title(child_o):
    """The real article title = first text block on the article page."""
    d=content.get(out2path.get(child_o),{})
    for b in d.get("blocks",[]):
        if b["t"] in ("h","p","li"):
            t=b.get("text","").strip()
            if t and "返回" not in t: return t
    return name_of(child_o)

def article_excerpt(child_o):
    d=content.get(out2path.get(child_o),{}); full=article_full_title(child_o)
    for b in d.get("blocks",[]):
        if b["t"] in ("h","p","li"):
            t=b.get("text","").strip()
            if not t or t==full or t.startswith(full): continue
            if t.startswith("文/") or t.replace(" ","") in BYLINES: continue
            if len(t)>14 and "返回" not in t:
                return (t[:64]+"…") if len(t)>64 else t
    return ""

ORBS='<div class="band-orbs"><span></span><span></span><span></span><span></span><span></span></div>'
def band(crumb, eyebrow, title, sub="", byline="", slim=False):
    return ('<section class="band%s">%s<div class="band-inner">%s'
            '<div class="eyebrow">%s</div><h1>%s</h1>%s%s</div></section>'
            %(" slim" if slim else "", ORBS, crumb, esc(eyebrow), esc(title),
              '<p class="sub">%s</p>'%esc(sub) if sub else '',
              '<p class="byline">%s</p>'%esc(byline) if byline else ''))

def stagger(i):  # inline reveal delay for staggered entrance
    return ' style="transition-delay:%dms"'%min(i*55,520)

def article_card(child_o, i=0):
    ttl=article_full_title(child_o); ex=article_excerpt(child_o)
    idx='<div class="idx">第 %02d 篇</div>'%(i+1)
    return ('<a class="acard rvl"%s href="%s">%s<h3>%s</h3>%s'
            '<span class="more">閱讀全文 <span class="arw">→</span></span></a>'
            %(stagger(i),u(child_o),idx,esc(ttl),('<p>%s</p>'%esc(ex)) if ex else ''))

def author_teaser(author_o):
    arts=children.get(author_o,[])
    if not arts: return ""
    # author page lists newest first; take first article's title
    return article_full_title(_column_order(author_o)[0]) if arts else ""

AUTHOR_PALETTES=[("#7c2942","#b5446a","#f6ebee"),   # 梅 plum
                 ("#2f5d52","#43806f","#e8f1ee"),   # 松 pine
                 ("#9a6a1e","#c29a45","#f7efe0")]    # 金 gold
def author_panel(author_o, i=0):
    nm=name_of(author_o)
    arts=_column_order(author_o); n=len(arts)
    c1,c2,cs=AUTHOR_PALETTES[i%len(AUTHOR_PALETTES)]
    recent=""
    for k in arts[:3]:
        t=article_full_title(k); t=(t[:24]+"…") if len(t)>24 else t
        recent+=('<a class="ap-item" href="%s"><span class="ap-dot"></span>'
                 '<span>%s</span></a>'%(u(k),esc(t)))
    delay=min(i*70,520)
    return ('<div class="apanel rvl" style="transition-delay:%dms;--ac:%s;--ac2:%s;--acs:%s">'
            '<div class="ap-top"><div class="ap-id"><div class="ap-name">%s</div>'
            '<div class="ap-role">專欄作者</div></div>'
            '<div class="ap-count"><b>%d</b><span>篇文章</span></div></div>'
            '<div class="ap-body"><div class="ap-label">近期文章</div>%s</div>'
            '<a class="ap-cta" href="%s">查看全部文章 <span class="arw">→</span></a></div>'
            %(delay,c1,c2,cs,esc(nm),n,recent,u(author_o)))

def _column_order(o):
    """Order child articles by the author's manual TOC sequence, then leftovers."""
    kids=children.get(o,[])
    title2child={}
    for k in kids: title2child.setdefault(article_full_title(k),k)
    ordered=[]; used=set()
    for b in content[out2path[o]]["blocks"]:
        if b["t"] in ("h","p","li"):
            t=b.get("text","").strip()
            if t in title2child and title2child[t] not in used:
                ck=title2child[t]; ordered.append(ck); used.add(ck)
    for k in sorted(kids,key=natkey):
        if k not in used: ordered.append(k)
    return ordered

def build_column(o):
    """專欄 listing pages: themed band header + dynamic clickable cards."""
    nm=name_of(o)
    kids=children.get(o,[])
    authors=[k for k in kids if children.get(k)]
    if authors:  # /column/ overview → author cards
        hdr=band(crumb_html(o),"如意專欄 · COLUMN",nm,
                 "古典智慧對照現代生活，三位作者以佛法觀照當代議題、書寫心得。")
        # order authors by article count desc (most prolific first), capped to palette
        auth=sorted(authors,key=lambda k:-len(children.get(k,[])))
        cards='<div class="apanels rvl">'+''.join(
            author_panel(k,i) for i,k in enumerate(auth))+'</div>'
    else:        # author page → article cards in TOC order
        arts=_column_order(o)
        hdr=band(crumb_html(o),"專欄作者 · ESSAYS",nm,
                 "%s 的佛法心得文章，共 %d 篇。"%(nm,len(arts)))
        cards='<div class="acards rvl">'+''.join(
            article_card(k,i) for i,k in enumerate(arts))+'</div>'
    body=hdr+'<main class="tintbg"><div class="wrap">'+cards+'</div></main>'
    return page(nm,"/column/",body,nm+" · 如意精舍")

def build_column_article(o):
    """Single 專欄 article: themed slim band, full title, byline, clean body."""
    d=content[out2path[o]]; full=article_full_title(o); byline=""
    author=name_of("/"+"/".join(o.strip("/").split("/")[:2])+"/")  # /column/<author>
    body_blocks=[]
    for b in d["blocks"]:
        if b["t"] in ("h","p","li"):
            t=b.get("text","").strip()
            if t==full or t.startswith(full): continue
            if t.startswith("文/") or t.replace(" ","") in BYLINES:
                byline=byline or t; continue
        body_blocks.append(b)
    hdr=band(crumb_html(o),"如意專欄",full,byline=byline or ("文／"+author),slim=True)
    inner=render_blocks(body_blocks,full)
    return page(full,"/column/",hdr+'<main><div class="wrap">'+inner+'</div></main>',full+" · 如意精舍")

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

# ---------------- 影音 (videos) ----------------
VIDEO_PALETTES=[("#7c2942","#b5446a","#f6ebee"),    # 梅 plum — 佛法常識
                ("#274a78","#3f6aa5","#e8eef6")]    # 琉璃 lapis — 淨土
def video_thumb_mini(ytid):
    return ('<button class="vt" data-yt="%s" aria-label="播放影片" '
            'style="background-image:url(https://i.ytimg.com/vi/%s/hqdefault.jpg)">'
            '<span class="pl"><i></i></span></button>'%(ytid,ytid))

def video_panel(cat_o, desc, i=0):
    d=content[out2path[cat_o]]; nm=d["name"]
    yts=[b["id"] for b in d["blocks"] if b["t"]=="yt"]; n=len(yts)
    c1,c2,cs=VIDEO_PALETTES[i%len(VIDEO_PALETTES)]
    thumbs=''.join(video_thumb_mini(v) for v in yts[:3])
    delay=min(i*70,520)
    return ('<div class="apanel vpanel rvl" style="transition-delay:%dms;--ac:%s;--ac2:%s;--acs:%s">'
            '<div class="ap-top"><div class="ap-id"><div class="ap-name">%s</div>'
            '<div class="ap-role">影音分類</div></div>'
            '<div class="ap-count"><b>%d</b><span>部影片</span></div></div>'
            '<div class="ap-body">%s<div class="vp-thumbs">%s</div></div>'
            '<a class="ap-cta" href="%s">觀看全部影片 <span class="arw">→</span></a></div>'
            %(delay,c1,c2,cs,esc(nm),n,
              '<p class="vp-desc">%s</p>'%esc(desc) if desc else '',thumbs,u(cat_o)))

def build_videos(o):
    """影音 index: themed band + colorful video-category panels."""
    nm=name_of(o); d=content[out2path[o]]
    paras=[b["text"] for b in d["blocks"] if b["t"] in ("h","p","li") and len(b.get("text",""))>40]
    hdr=band(crumb_html(o),"佛法影音 · VIDEOS",nm,
             "深入淺出的佛學常識與淨土法門講座，撥開迷霧、安頓身心。")
    kids=children.get(o,[])
    panels=''.join(video_panel(k,paras[i] if i<len(paras) else "",i) for i,k in enumerate(kids))
    body=hdr+'<main class="tintbg"><div class="wrap"><div class="apanels rvl">'+panels+'</div></div></main>'
    return page(nm,"/videos/",body,nm+" · 如意精舍")

def build_video_category(o):
    """影音 分類頁: themed band + full video wall (titles + inline lightbox)."""
    d=content[out2path[o]]; nm=d["name"]
    cnt=sum(1 for b in d["blocks"] if b["t"]=="yt")
    hdr=band(crumb_html(o),"影音分類",nm,"共 %d 部影片，點選縮圖即可當頁觀看。"%cnt)
    rest=[b for b in d["blocks"] if not (b["t"] in ("h","p","li") and b.get("text","").strip()==nm)]
    inner=render_blocks(rest,nm)
    return page(nm,"/videos/",hdr+'<main class="tintbg"><div class="wrap">'+inner+'</div></main>',nm+" · 如意精舍")

# ---------------- 法會資訊 (news) ----------------
# 2026 法會時間表 — 上半年為現行站確認資料；下半年念佛法會＝每月第二個週日（10/11 經 Luke 確認）
NEWS_PHOTOS=[("assets/img/news-chanting.jpg","晨間誦經共修"),
             ("assets/img/news-altar.jpg","大殿三寶佛與供果"),
             ("assets/img/news-talk.png","法師開示講法"),
             ("assets/img/news-bathing.jpg","浴佛法會")]
NEWS_EVENTS=[  # (solar, lunar/週次, 名稱, 備註, 類型)
 ("1/10","農曆十一月廿二","回娘家","","home"),
 ("1/11","農曆十一月廿三","念佛法會","","nianfo"),
 ("2/1","農曆十二月十四","念佛法會","","nianfo"),
 ("3/1","農曆正月十三","念佛法會","","nianfo"),
 ("4/12","農曆二月廿五","念佛法會","","nianfo"),
 ("5/10","農曆三月廿四","浴佛節","釋迦牟尼佛聖誕","yufo"),
 ("6/7","農曆四月廿二","念佛法會","","nianfo"),
 ("6/28","農曆五月十四","念佛法會","","nianfo"),
 ("7/8 ～ 7/12","農曆五月廿四～廿八","兒童學佛營","暑期成長活動","camp"),
 ("8/9","週日","念佛法會","","nianfo"),
 ("9/13","週日","念佛法會","","nianfo"),
 ("10/11","週日","念佛法會","","nianfo"),
 ("11/8","週日","念佛法會","","nianfo"),
 ("12/13","週日","念佛法會","","nianfo"),
]
EV_ACCENT={"nianfo":("#7c2942","#b5446a"),"yufo":("#9a6a1e","#c29a45"),
           "camp":("#2f5d52","#43806f"),"home":("#274a78","#3f6aa5")}
def build_news(o):
    nm=name_of(o)
    hdr=band(crumb_html(o),"法會資訊 · DHARMA EVENTS",nm,
             "念佛、浴佛與兒童學佛營——歡迎隨喜參加，共沐法喜。")
    # carousel
    slides=""
    for i,(src,cap) in enumerate(NEWS_PHOTOS):
        slides+=('<div class="slide%s" style="background-image:url(%s)">'
                 '<div class="cap">%s</div></div>'%(" on" if i==0 else "",u("/"+src),esc(cap)))
    dots=''.join('<button class="dot%s" data-i="%d" aria-label="第%d張"></button>'
                 %(" on" if i==0 else "",i,i+1) for i in range(len(NEWS_PHOTOS)))
    carousel=('<div class="carousel rvl" id="newsCar"><div class="slides">%s</div>'
              '<button class="car-nav prev" data-d="-1" aria-label="上一張">‹</button>'
              '<button class="car-nav next" data-d="1" aria-label="下一張">›</button>'
              '<div class="dots">%s</div></div>'%(slides,dots))
    # schedule
    cards=""
    for solar,sub,name,note,typ in NEWS_EVENTS:
        c1,c2=EV_ACCENT.get(typ,EV_ACCENT["nianfo"])
        mo=solar.split("/")[0] if "/" in solar else solar
        cards+=('<div class="scard rvl" style="--ac:%s;--ac2:%s">'
                '<div class="sdate"><span class="dy">%s</span></div>'
                '<div class="sbody"><div class="sname">%s</div>'
                '<div class="ssub">%s</div>%s</div></div>'
                %(c1,c2,esc(solar),esc(name),esc(sub),
                  '<div class="snote">%s</div>'%esc(note) if note else ''))
    sched=('<div class="section-title rvl"><h2>2026 年法會時間表</h2><div class="rule"></div></div>'
           '<p class="sched-note rvl">念佛法會於每月第二個週日舉行（20:30 前後，詳情請洽精舍）。</p>'
           '<div class="sched rvl">%s</div>'%cards)
    body=hdr+'<main class="tintbg"><div class="wrap">'+carousel+sched+'</div></main>'
    return page(nm,"/news/",body,nm+" · 如意精舍")

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
        if o=="/column/" or (o.startswith("/column/") and children.get(o)):
            write(o,build_column(o))
        elif o.startswith("/column/"):
            write(o,build_column_article(o))
        elif o=="/news/":
            write(o,build_news(o))
        elif o=="/videos/":
            write(o,build_videos(o))
        elif o.startswith("/videos/") and not children.get(o):
            write(o,build_video_category(o))
        else:
            write(o,build_page(o))
        n+=1
    # CNAME + nojekyll
    open(os.path.join(ROOT,".nojekyll"),"w").write("")
    print("built %d pages"%n)
