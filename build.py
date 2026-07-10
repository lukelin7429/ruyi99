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
try:
    STUDY_GROUPS=json.load(open(os.path.join(ROOT,"data","study_group.json")))
except Exception:
    STUDY_GROUPS=[]
try:
    AUDIO=json.load(open(os.path.join(ROOT,"data","audio.json")))
except Exception:
    AUDIO={}
try:
    INTROS=json.load(open(os.path.join(ROOT,"data","intros.json")))
except Exception:
    INTROS={}
try:
    ES_LESSONS=json.load(open(os.path.join(ROOT,"data","english_school.json")))
except Exception:
    ES_LESSONS=[]

def _apply_es_zh(lessons):
    """疊加中文翻譯(獨立檔 english_school_zh.json)，使英文資料即使被重產也不會洗掉中譯。"""
    try:
        ZH=json.load(open(os.path.join(ROOT,"data","english_school_zh.json")))
    except Exception:
        return
    for L in lessons:
        z=ZH.get(L.get("id"))
        if not z: continue
        oz=z.get("objectives_zh",[])
        for o,t in zip(L.get("objectives",[]),oz):
            if t and not o.get("zh_html"): o["zh_html"]=t
        flat=[e for p in L.get("patterns",[]) for e in p.get("examples",[])]
        for e,t in zip(flat,z.get("examples_zh",[])):
            if t and not e.get("zh"): e["zh"]=t
        if z.get("grammar_zh") and L.get("grammar") and not L["grammar"].get("zh_html"):
            L["grammar"]["zh_html"]=z["grammar_zh"]
        sp=z.get("story_paras_zh") or []
        if sp and L.get("story") and not L["story"].get("paras_zh") \
           and len(sp)==len(L["story"].get("paras",[])):
            L["story"]["paras_zh"]=sp
        if L.get("principle"):
            if z.get("principle_lede_zh") and not L["principle"].get("lede_zh"):
                L["principle"]["lede_zh"]=z["principle_lede_zh"]
            if z.get("principle_html_zh") and not L["principle"].get("zh_html"):
                L["principle"]["zh_html"]=z["principle_html_zh"]
        for ti,t in zip((L.get("practice") or {}).get("tiers",[]),z.get("practice_reqs_zh",[])):
            if t and not ti.get("req_zh"): ti["req_zh"]=t
_apply_es_zh(ES_LESSONS)
try:
    DAILY_QUOTES=json.load(open(os.path.join(ROOT,"data","daily_quotes.json")))
except Exception:
    DAILY_QUOTES=[]

# 合併卡片（如「般若經講記」＝心經＋金剛經）：把多個來源系列收進一張卡、一頁。
EXTRA_NAMES={}   # out -> 顯示名稱覆寫（讓麵包屑顯示合併後的書名）
COMBINED=[c for grp in STUDY_GROUPS for c in grp.get("cards",[]) if c.get("combine")]
REDIRECTS={}     # 舊系列首頁 -> 合併頁，避免重複內容
for _c in COMBINED:
    EXTRA_NAMES[_c["out"]]=_c["name"]
    for _src in _c["combine"]:
        EXTRA_NAMES[_src]=_c["name"]
        REDIRECTS[_src]=_c["out"]

# 手工頁面：內容由協作者直接手寫在 built HTML 裡，不屬於任何 build_*() 資料模型，
# 上面的主迴圈（跑 out2path）本來就碰不到、不會覆蓋。這裡只是把它們「登記」進
# sitemap.xml／search.json（這兩個檔案每次重建是整包重寫，不是累加），讓頁面能被
# 收錄、被全站搜尋找到。新增一卷就加一行 out path，不需要重新產生內容。
HANDMADE_PAGES=[
    "/study-group/shurangama/juan01/",
    # 補登：這幾頁先前是靠手動 patch 進 sitemap.xml/search.json 才被收錄，
    # 一旦有人在快取沒還原全的狀況下跑全站重建，就會被整包重寫時悄悄漏掉。
    "/column/Lucien/buddhist-leadership/",
    "/column/Lucien/buddhist-leadership/page-2/",
    "/column/Lucien/buddhist-leadership/page-3/",
    "/column/Lucien/life-in-breath/",
    "/study-group/perfection-of-wisdom/life-topics/",
]

out2path={}
for p,o in omap.items():
    if o=="/":
        if p=="/home": out2path[o]=p
        out2path.setdefault(o,p)
    else:
        out2path[o]=p

NAV=[("首頁","/"),("法師簡介","/bhikkhuni/"),("讀書會","/study-group/"),
     ("法會資訊","/news/"),("影音","/videos/"),("專欄","/column/"),("學習園地","/learn/")]
NAVNAME={o:n for n,o in NAV}
SITE_NAME="如意精舍"
SITE_URL="https://ruyi99.org"
ADDR="南投縣信義鄉自強村陽和巷80號"; TEL="049-2791267"
EMAIL_MASTER="a0909359364@gmail.com"; EMAIL_LUKE="luke@ruyi99.org"
EMAIL_EN="ruyi@ruyimeditation.org"; EN_SITE="https://ruyimeditation.org"
YT_CHANNEL="https://www.youtube.com/@ruyi99"

# Base path for absolute site URLs. This repo is served on the apex domain
# ruyi99.org (see CNAME), where the correct base is "" — NOT "/ruyi99".
# Auto-detect: if a CNAME exists, force BASE="" so a rebuild can never
# silently re-break the live site by prefixing assets with /ruyi99 (which 404s
# on the apex and leaves every page unstyled). Override only via env if needed.
if "BASE" in os.environ:
    BASE=os.environ["BASE"]
elif os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)),"CNAME")):
    BASE=""            # apex custom domain — no path prefix
else:
    BASE="/ruyi99"     # fallback for project-pages (username.github.io/ruyi99/)
def u(path):  # prefix an absolute site path with BASE
    if path.startswith("http"): return path
    if not path.startswith("/"): path="/"+path
    return BASE+path

def esc(s): return html.escape(s,quote=True)

# ---- 全站搜尋索引：write() 逐頁累積，build 結束後寫出 search.json ----
SEARCH_INDEX=[]
_TAG_RE=re.compile(r"<[^>]+>")
_SCRIPT_RE=re.compile(r"<(script|style|svg)\b.*?</\1>",re.S|re.I)
_WS_RE=re.compile(r"\s+")
def _index_page(o,htmltext):
    mt=re.search(r"<title>(.*?)</title>",htmltext,re.S)
    title=mt.group(1) if mt else o
    for suf in (" · 如意精舍",):
        if title.endswith(suf): title=title[:-len(suf)]
    md=re.search(r'<meta name="description" content="([^"]*)"',htmltext)
    desc=html.unescape(md.group(1)) if md else ""
    # 取 topbar 之後、footer 之前的主體文字，去掉 nav/footer 雜訊
    body=htmltext
    i=body.find("</header>"); body=body[i+9:] if i!=-1 else body
    j=body.find('<footer'); body=body[:j] if j!=-1 else body
    body=_SCRIPT_RE.sub(" ",body)
    body=html.unescape(_TAG_RE.sub(" ",body))
    body=_WS_RE.sub(" ",(desc+" "+body)).strip()
    SEARCH_INDEX.append({"title":title.strip(),"url":u(o if o!="/" else "/"),
                         "body":body[:300].rstrip()})

def natkey(o):
    last=o.strip("/").split("/")[-1]
    nums=re.findall(r'\d+',last)
    return (int(nums[0]) if nums else 0, last)

def name_of(o):
    if o in EXTRA_NAMES: return EXTRA_NAMES[o]
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
    mob_links = ''.join(links).replace('<a ', '<a ').replace('class="active"','class="active"')
    return (
    '<header class="topbar"><div class="topbar-inner">'
    '<a class="brand" href="%s"><img class="brand-logo" src="%s" alt="如意精舍" width="42" height="42"><span>如意精舍'%(u("/"),u("/assets/img/ruyi-logo.png"))+
    '<small>RU-YI MEDITATION</small></span></a>'
    '<nav class="nav">'+''.join(links)+'</nav>'
    '<div class="topbar-actions">'
    '<button type="button" class="nav-search-btn" id="siteSearchBtn" aria-label="搜尋本站" title="搜尋（按 /）">'
    '<svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"></circle><line x1="21" y1="21" x2="16.5" y2="16.5"></line></svg>'
    '<span class="nav-search-label">搜尋</span></button>'
    '<button class="hamb" id="ruyi99Hamb" aria-label="選單" aria-expanded="false">'
    '<span></span><span></span><span></span>'
    '</button>'
    '</div>'
    '</div></header>'
    '<div class="mob-drawer" id="ruyi99Drawer" aria-hidden="true">'
    '<nav>'+mob_links+'</nav>'
    '</div>'
    '<script>'
    '(function(){'
    'var btn=document.getElementById("ruyi99Hamb");'
    'var dr=document.getElementById("ruyi99Drawer");'
    'if(!btn||!dr)return;'
    'function open(){dr.classList.add("is-open");dr.setAttribute("aria-hidden","false");btn.classList.add("is-open");btn.setAttribute("aria-expanded","true");document.body.classList.add("mob-nav-open");}'
    'function close(){dr.classList.remove("is-open");dr.setAttribute("aria-hidden","true");btn.classList.remove("is-open");btn.setAttribute("aria-expanded","false");document.body.classList.remove("mob-nav-open");}'
    'btn.addEventListener("click",function(e){e.stopPropagation();dr.classList.contains("is-open")?close():open();});'
    'document.addEventListener("click",function(e){if(dr.classList.contains("is-open")&&!dr.contains(e.target)&&!btn.contains(e.target))close();});'
    '})();'
    '</script>'
    )

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
    og=('<meta property="og:type" content="website">'
        '<meta property="og:site_name" content="如意精舍">'
        '<meta property="og:title" content="%s · 如意精舍">'
        '<meta property="og:description" content="%s">'
        '<meta property="og:image" content="%s/assets/img/hero-fengguidou.jpg">'
        '<meta property="og:locale" content="zh_TW">'
        '<meta name="twitter:card" content="summary_large_image">'
        '<!--CANON-->'%(esc(title),esc(desc or title),SITE_URL))
    return (
    '<!DOCTYPE html><html lang="zh-Hant"><head><meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width,initial-scale=1">'
    '<title>%s · 如意精舍</title>'
    '<meta name="description" content="%s">%s%s'
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600;700&display=swap" rel="stylesheet">'
    '<link rel="stylesheet" href="%s">'
    '<link rel="stylesheet" href="%s">'
    '</head><body>%s%s%s%s'
    '<script>window.RS_INDEX="%s"</script>'
    '<script src="%s"></script>'
    '<script src="%s"></script></body></html>'
    %(esc(title),esc(desc or title),og,icons,u("/assets/css/site.css"),u("/assets/css/search.css"),
      topbar(active_top),body,footer(),LIGHTBOX,
      u("/search.json"),u("/assets/js/site.js"),u("/assets/js/search.js")))

def yt_thumb(ytid,cap="",force=False):
    t=cap if force else VTITLES.get(ytid,cap)
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
            fp=os.path.join(ROOT,b["src"].lstrip("/"))
            try:
                if os.path.exists(fp) and os.path.getsize(fp)<30*1024:
                    continue  # 跳過裝飾用小圖(如意精舍紅印等)，不當內容圖渲染
            except Exception: pass
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

def photo_carousel(items):
    """items: list of (rel_src, caption). Full image shown (contain) over a blurred
    backdrop so subjects (e.g. Buddha images) are never cropped."""
    slides=""
    for i,(src,cap) in enumerate(items):
        url=u("/"+src)
        slides+=('<div class="slide%s"><div class="slide-bg" style="background-image:url(%s)"></div>'
                 '<div class="slide-fg" style="background-image:url(%s)"></div>%s</div>'
                 %(" on" if i==0 else "",url,url,
                   '<div class="cap">%s</div>'%esc(cap) if cap else ''))
    dots=''.join('<button class="dot%s" data-i="%d" aria-label="第%d張"></button>'
                 %(" on" if i==0 else "",i,i+1) for i in range(len(items)))
    return ('<div class="carousel rvl"><div class="slides">%s</div>'
            '<button class="car-nav prev" data-d="-1" aria-label="上一張">‹</button>'
            '<button class="car-nav next" data-d="1" aria-label="下一張">›</button>'
            '<div class="dots">%s</div></div>'%(slides,dots))

def feat_video(ytid):
    t=VTITLES.get(ytid,"")
    return ('<button class="featvid rvl" data-yt="%s">'
            '<div class="fv-thumb" style="background-image:url(https://i.ytimg.com/vi/%s/hqdefault.jpg)">'
            '<span class="fv-play"><i></i></span></div>'
            '<div class="fv-cap">%s</div></button>'%(ytid,ytid,esc(t)))

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

HOME_EXTRA_PHOTOS=["assets/img/home-courtyard-service.jpg","assets/img/home-kids-camp.jpg",
                   "assets/img/home-mountain-trail.jpg","assets/img/home-group-photo.jpg",
                   "assets/img/home-misty-mountain.jpg"]
def build_home():
    d=content["/home"]
    imgs=[b["src"] for b in d["blocks"] if b["t"]=="img"]+HOME_EXTRA_PHOTOS
    intro=[b["text"] for b in d["blocks"] if b["t"] in ("h","p") and len(b.get("text",""))>30][:4]
    vids=[b["id"] for b in d["blocks"] if b["t"]=="yt"]
    _=u  # base-aware url helper
    body=['<section class="hero"><div class="hero-photo hero-banner" style="background-image:url(%s)">'
          '<div class="hero-text rvl">'
          '<div class="eyebrow">南投 · 信義 · 風櫃斗</div>'
          '<h1>如意精舍</h1>'
          '<p>海拔約 800 公尺的山上道場，以弘揚正知正見的佛法為理念，'
          '帶領大眾聞思修、深植菩提種子。</p></div></div></section>'
          %u("/assets/img/hero-fengguidou.jpg")]
    # 今日一句經典法語（每天依日期自動輪替，純前端、無需重建）
    if DAILY_QUOTES:
        q0=DAILY_QUOTES[0]
        body.append('<section class="daily-wrap"><div class="wrap"><div class="daily rvl">'
            '<div class="daily-k">今日一句 · 經典法語</div>'
            '<span class="daily-mark">”</span>'
            '<blockquote class="daily-q" id="daily-q">%s</blockquote>'
            '<p class="daily-plain" id="daily-plain">%s</p>'
            '<cite class="daily-src" id="daily-src">——《%s》</cite>'
            '<script type="application/json" id="daily-data">%s</script>'
            '</div></div></section>'
            %(esc(q0["q"]),esc(q0["plain"]),esc(q0["src"]),
              json.dumps(DAILY_QUOTES,ensure_ascii=False).replace("</","<\\/")))
    # 首頁醒目卡片：週四英語課（讓家長一眼就找到上課資訊）
    body.append('<section class="home-feat-wrap"><a class="home-feat rvl" href="%s">'
        '<div class="hf-ic">🍃</div><div class="hf-body">'
        '<div class="hf-k">學習園地 · 給孩子的課程</div>'
        '<h3>週四英語課 · 如意英文學校</h3>'
        '<p>每週四，把英文學習和佛法、一顆柔軟慈悲的心結合在一起。免費課程，'
        '歡迎國小到青少年的孩子一起來學、來玩——線上還有 24 週的複習：'
        '單字發音、句型、故事與自我檢測小考。課程由 Teacher Dom 老師設計。</p>'
        '<span class="hf-go">認識課程・看 24 週複習 <span class="arw">→</span></span>'
        '</div></a></section>'%u("/english-school/"))
    body.append('<main><div class="prose rvl">'+''.join('<p>%s</p>'%esc(t) for t in intro)+'</div>')
    # 度眾事業 — 6 張平衡(3欄)、有圖示與配色、有動感的卡片
    IC={
     "masters":'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="7" r="3.4"/><path d="M5 20c0-3.6 3.1-6 7-6s7 2.4 7 6"/></svg>',
     "book":'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5.5C10.3 4.4 8 4 5.5 4.2 4.7 4.3 4 5 4 5.8V18c0 .9.8 1.5 1.6 1.4C8 19.2 10.4 19.6 12 20.7"/><path d="M12 5.5C13.7 4.4 16 4 18.5 4.2c.8.1 1.5.8 1.5 1.6V18c0 .9-.8 1.5-1.6 1.4C16 19.2 13.6 19.6 12 20.7"/><path d="M12 5.5v15.2"/></svg>',
     "cal":'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><rect x="3.5" y="5" width="17" height="15" rx="2.5"/><path d="M3.5 9.5h17M8 3.5v3M16 3.5v3"/></svg>',
     "play":'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="8.5"/><path d="M10.3 9.2l4.6 2.8-4.6 2.8z" fill="currentColor" stroke="none"/></svg>',
     "pen":'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M15.5 5.5l3 3M4 20l1-4 11-11 3 3-11 11-4 1z"/></svg>',
     "sun":'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 3v2.5M12 18.5V21M4.2 4.2l1.8 1.8M18 18l1.8 1.8M3 12h2.5M18.5 12H21M4.2 19.8L6 18M18 6l1.8-1.8"/></svg>',
    }
    secs=[("法師簡介","/bhikkhuni/","認識回鄉弘法的兩位法師","masters","#7c2942","#b5446a"),
          ("讀書會","/study-group/","線上研讀經論，聞思修並進","book","#2f5d52","#43806f"),
          ("法會資訊","/news/","念佛、浴佛與每月定期法會","cal","#274a78","#3f6aa5"),
          ("影音","/videos/","佛法常識與淨土講座影音","play","#9a6a1e","#c29a45"),
          ("專欄","/column/","三位作者的佛法心得文章","pen","#5a3d7a","#7d5aa6"),
          ("學習園地","/learn/","週四英語課（融入佛法）與兒童夏令營，孩子的學習園地","sun","#2f7d77","#3f9d95")]
    cards=''.join('<a class="hcard rvl" style="--ac:%s;--ac2:%s;transition-delay:%dms" href="%s">'
                  '<div class="hcard-ic">%s</div><h3>%s</h3><p>%s</p>'
                  '<span class="hcard-go">前往 <span class="arw">→</span></span></a>'
                  %(c1,c2,min(i*70,360),u(o),IC[ic],esc(n),esc(desc))
                  for i,(n,o,desc,ic,c1,c2) in enumerate(secs))
    body.append('<div class="section-title rvl"><h2>度眾事業</h2><div class="rule"></div></div>')
    body.append('<div class="hcards rvl">'+cards+'</div>')
    # 精選影音 — 3 支放大卡片（夏令營＋佛法影音＋淨土）
    FEATURED=["xtWmje_dBEQ","ft00NuF51Fg","TRRzNYXtHCk"]
    body.append('<div class="section-title rvl"><h2>精選影音</h2><div class="rule"></div></div>')
    body.append('<div class="feat-grid">'+''.join(feat_video(v) for v in FEATURED)+'</div>')
    # 精舍剪影 — 放大輪播（real photos only）
    gal=[i for i in imgs if os.path.exists(os.path.join(ROOT,i))
         and os.path.getsize(os.path.join(ROOT,i))>=80*1024]
    if gal:
        body.append('<div class="section-title rvl"><h2>精舍剪影</h2><div class="rule"></div></div>')
        body.append(photo_carousel([(g,"") for g in gal]))
    body.append('</main>')
    ld={"@context":"https://schema.org","@type":["BuddhistTemple","Organization"],
        "name":"如意精舍","alternateName":"Ru-Yi Meditation Center","url":SITE_URL,
        "logo":SITE_URL+"/assets/img/ruyi-logo.png","image":SITE_URL+"/assets/img/hero-fengguidou.jpg",
        "telephone":"+886-49-2791267","email":EMAIL_LUKE,
        "address":{"@type":"PostalAddress","streetAddress":"自強村陽和巷80號",
                   "addressLocality":"信義鄉","addressRegion":"南投縣","postalCode":"556","addressCountry":"TW"},
        "foundingDate":"2017","sameAs":[YT_CHANNEL,EN_SITE]}
    body.append('<script type="application/ld+json">%s</script>'%json.dumps(ld,ensure_ascii=False))
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

def build_video_wall(o, active_top, eyebrow):
    """themed band + full video wall (titles + inline lightbox). 影音分類 / 夏令營年度共用。"""
    d=content[out2path[o]]; nm=d["name"]
    cnt=sum(1 for b in d["blocks"] if b["t"]=="yt")
    hdr=band(crumb_html(o),eyebrow,nm,"共 %d 部影片，點選縮圖即可當頁觀看。"%cnt)
    rest=[b for b in d["blocks"] if not (b["t"] in ("h","p","li") and b.get("text","").strip()==nm)]
    inner=render_blocks(rest,nm)
    return page(nm,active_top,hdr+'<main class="tintbg"><div class="wrap">'+inner+'</div></main>',nm+" · 如意精舍")

# ---------------- 夏令營 (camps) ----------------
def _camp_year(o):
    m=re.search(r'(\d{4})',o); return int(m.group(1)) if m else 0
def build_camps(o):
    """夏令營 index: image-led year cards, newest first."""
    nm=name_of(o)
    hdr=band(crumb_html(o),"夏令營 · SUMMER CAMP",nm,
             "兒童與青少年心靈環保成長營，歷年活動影音紀錄。")
    kids=sorted(children.get(o,[]),key=_camp_year,reverse=True)
    # 2026 為手動生成頁（不在爬蟲內），置頂呈現：青少年營＋兒童營各一張
    cards=('<a class="campcard rvl" href="%s">'
           '<div class="cc-img"><div class="bg" style="background-image:url(/assets/img/camp-2026-teen.jpg);background-position:center 42%%"></div>'
           '<span class="cc-badge">最新一屆</span><span class="cc-year">2026</span></div>'
           '<div class="cc-body"><div class="cc-title">青少年學佛營</div>'
           '<div class="cc-meta">7/4–7/7 · 課程表 <span class="arw">→</span></div></div></a>'
           %u("/camps/2026/"))
    cards+=('<a class="campcard rvl" style="transition-delay:70ms" href="%s">'
            '<div class="cc-img"><div class="bg" style="background-image:url(/assets/img/camp-2026-kids.jpg)"></div>'
            '<span class="cc-badge">最新一屆</span><span class="cc-year">2026</span></div>'
            '<div class="cc-body"><div class="cc-title">兒童學佛營</div>'
            '<div class="cc-meta">7/8–7/12 · 課程表 <span class="arw">→</span></div></div></a>'
            %u("/camps/2026-kids/"))
    for i,k in enumerate(kids):
        d=content[out2path[k]]; nmk=d["name"]
        yts=[b["id"] for b in d["blocks"] if b["t"]=="yt"]; n=len(yts)
        thumb=yts[0] if yts else ""
        badge=''
        cards+=('<a class="campcard rvl" style="transition-delay:%dms" href="%s">'
                '<div class="cc-img"><div class="bg" style="background-image:url(https://i.ytimg.com/vi/%s/hqdefault.jpg)"></div>'
                '%s<span class="cc-year">%d</span><span class="cc-play"><i></i></span></div>'
                '<div class="cc-body"><div class="cc-title">%s</div>'
                '<div class="cc-meta">%d 部影片 <span class="arw">→</span></div></div></a>'
                %(min(i*70,520),u(k),thumb,badge,_camp_year(k),esc(nmk),n))
    body=hdr+'<main class="tintbg"><div class="wrap"><div class="campgrid rvl">'+cards+'</div></div></main>'
    return page(nm,"/learn/",body,nm+" · 如意精舍")

# ---------------- 2026 青少年學佛營（手動生成，不在爬蟲內） ----------------
EXTRA_NAMES["/camps/2026/"]="2026 夏令營"

# 四天主題（日期, 主題, 第N天, 一句話, 主色, 副色）
CAMP26_THEMES=[
 ("7/4","願力種子","第 1 天","做包子、開營、迎新之夜——種下這趟旅程的願","#2f5d52","#43806f"),
 ("7/5","覺察紀錄","第 2 天","影像教學、大自然行禪、月光禪修——學習向內觀照","#274a78","#3f6aa5"),
 ("7/6","共創表達","第 3 天","拍微電影、佛法漫畫、星空影展——把善念說出來","#9a6a1e","#c29a45"),
 ("7/7","傳承結業","第 4 天","領袖培力、感恩信、結業——把這份光帶回家","#7c2942","#b5446a"),
]
# 每日課程表：(主色,副色,主題,日期, [ (時間, 課名, 說明/老師, 標記, 是否亮點) ])
CAMP26_SCHEDULE=[
 ("#2f5d52","#43806f","願力種子","7/4（六）",[
   ("10:00 前","報到安單","學員陸續上山、安頓","",False),
   ("上午","開營典禮","相見歡・破冰","",False),
   ("13:30","生活禪・做包子","揉麵、造型、等發酵","",True),
   ("15:00","佛學第一堂・願力種子","饅頭出爐 · 竣翔老師","",False),
   ("17:00","晚課梵唱／料理晚餐","A 組料理・B 組梵唱","",False),
   ("19:00","每日歌詠（三寶歌）","家維老師","",False),
   ("19:40","迎新之夜","小隊主持・表演帶動","",True),
   ("21:00","山上日記","寫下今天最有感覺的一件事","",True),
 ]),
 ("#274a78","#3f6aa5","覺察紀錄","7/5（日）",[
   ("06:00","晨間瑜珈・靜坐／早課梵唱／早餐","一天的開始","",False),
   ("08:30","佛學第四堂・生命願景","暐哲老師","",False),
   ("10:20","影像（一）・教與拍","鏡頭語言＋手機拍攝，畫出分鏡腳本","吉祥老師",True),
   ("11:40","無聲用餐體驗","專注感受食物・餐後分享 · 維哲老師","",True),
   ("13:30","音樂（一）","聲音覺察・基礎梵唱 · 竣翔老師","",False),
   ("15:00","大自然行禪＋森林靜心尋寶","行禪山林・五感任務・靜坐 · 維哲老師","",True),
   ("19:40","月光禪修","戶外月光打坐・觀星・呼吸引導 · 家維老師","",True),
   ("21:00","山上日記","","",True),
 ]),
 ("#9a6a1e","#c29a45","共創表達","7/6（一）",[
   ("06:00","晨間瑜珈・靜坐／早課梵唱／早餐","","",False),
   ("08:30","佛學第三堂・領袖智慧","呂賢老師","",False),
   ("10:20","60 秒佛法微電影拍攝","影像（二）升級版・實拍＋初剪","吉祥老師",True),
   ("13:30","音樂（二）","和諧共鳴・音樂會準備 · 芷睿老師","",False),
   ("15:00","佛學第二堂・情緒智慧","認識情緒・第二支箭・受念處","吉祥老師",False),
   ("16:30","佛法漫畫創作","把佛法故事畫成漫畫・分組發表 · 芷睿老師","",True),
   ("19:00","我的煩惱解決室","匿名寫煩惱・佛法智慧找解方 · 呂賢老師","",True),
   ("19:40","星空影展・音聲供養","佛學第五堂 傳承與感恩 · 竣翔老師","微電影放映",True),
   ("21:00","山上日記","","",True),
 ]),
 ("#7c2942","#b5446a","傳承結業","7/7（二）",[
   ("06:00","晨間瑜珈・靜坐／早課梵唱／早餐","","",False),
   ("08:30","佛學第六堂・我為何吃素","家維老師","",False),
   ("10:20","領袖培力・團康實戰","暐哲老師","",False),
   ("11:40","心靈交流・感恩信寫作","寫給最想感謝的人・結業後寄出","",True),
   ("下午","結業・賦歸","帶著願力與覺察回家","",False),
 ]),
]
# 活動影片（營隊進行中陸續上線；(YouTube ID, 標題) — 播放清單 PLQbEm5zT7U80）
CAMP26_VIDS=[
 ("exaNyUKRaN4","開營典禮"),
 ("5hpBeq17UXg","相見歡・破冰"),
 ("a0ngRAcoTww","生活禪・做包子"),
 ("XdUb_B1WcI0","佛學第一堂・願力種子"),
 ("4tLKW_IKhNo","料理晚餐"),
 ("b5_JI1q8Q28","三寶歌教學"),
 ("cBcW9-hn4ig","晨間瑜珈"),
 ("6cEJ9CdUWn4","早課"),
 ("e6eU2H4gc4k","佛學第四堂・生命願景"),
 ("eSi21KPWtGo","大自然行禪"),
 ("p7FZZTPi4MU","晨間瑜珈・第三天"),
 ("4tPWiJKzoL8","佛學第三堂・領袖智慧"),
 ("b2CecQpxiH8","拍片教學"),
 ("LzGeo_8X9SQ","佛曲教唱"),
]
CAMP26_PLAYLIST="https://www.youtube.com/playlist?list=PLQbEm5zT7U80"
# 學生「60 秒佛法微電影」創作成果（與上面的活動側拍紀錄區隔開）
CAMP26_FILMS=[
 ("T8VLudxG-9U","喜捨班・微電影"),
 ("yH1ZacXsCQE","精進班・微電影"),
 ("h19ayYFdsDQ","慈悲班・微電影"),
 ("4bO27OXFTDY","慈悲班・幕後花絮"),
]

CAMP26_CSS=("<style>"
 ".c26-meta{display:flex;flex-wrap:wrap;gap:10px;margin-top:18px}"
 ".c26-meta span{background:rgba(255,255,255,.16);border:1px solid rgba(255,255,255,.30);"
 "color:#fff;padding:7px 15px;border-radius:999px;font-size:14.5px;font-weight:600}"
 ".c26-meta b{font-weight:800}"
 ".c26-sib{background:rgba(255,255,255,.94);color:#3a2e1c!important;padding:7px 15px;"
 "border-radius:999px;font-size:14.5px;font-weight:800;text-decoration:none;"
 "transition:transform .2s,box-shadow .2s;box-shadow:0 3px 12px rgba(0,0,0,.18)}"
 ".c26-sib:hover{transform:translateY(-2px);box-shadow:0 6px 18px rgba(0,0,0,.26)}"
 ".c26-themes{display:grid;gap:18px;grid-template-columns:repeat(4,1fr);margin:8px 0 8px}"
 "@media(max-width:820px){.c26-themes{grid-template-columns:repeat(2,1fr)}}"
 "@media(max-width:520px){.c26-themes{grid-template-columns:1fr}}"
 ".c26-th{position:relative;overflow:hidden;border-radius:16px;padding:20px;color:#fff;"
 "background:linear-gradient(150deg,var(--a),var(--b));box-shadow:var(--shadow);"
 "transition:transform .26s cubic-bezier(.2,.7,.2,1),box-shadow .26s}"
 ".c26-th:hover{transform:translateY(-8px);box-shadow:var(--shadow-hover)}"
 ".c26-th .day{font-family:var(--serif);font-size:13px;letter-spacing:.16em;opacity:.92}"
 ".c26-th h3{margin:4px 0 8px;font-size:22px;font-weight:800;letter-spacing:.04em}"
 ".c26-th .dt{font-size:15px;font-weight:700;opacity:.95;margin-bottom:8px}"
 ".c26-th p{margin:0;font-size:14.5px;line-height:1.65;color:rgba(255,255,255,.92)}"
 ".c26-dayhead{max-width:var(--maxw);margin:46px auto 14px;display:flex;align-items:center;gap:14px}"
 ".c26-dayhead .pill{background:linear-gradient(150deg,var(--a),var(--b));color:#fff;"
 "padding:6px 16px;border-radius:999px;font-weight:800;font-size:15px;letter-spacing:.04em}"
 ".c26-dayhead h2{font-size:23px;margin:0;letter-spacing:.05em}"
 ".c26-dayhead .dt{color:var(--sub);font-size:15px;font-weight:600}"
 ".c26-dayhead .rule{flex:1;height:1px;background:var(--line)}"
 ".c26-jx .sdate{position:relative}"
 ".c26-jx .sname::after{content:'吉祥老師';margin-left:8px;font-size:12px;font-weight:800;"
 "color:#fff;background:var(--plum);padding:2px 8px;border-radius:999px;vertical-align:middle}"
 ".c26-vidnote{background:var(--plum-soft);border:1px dashed var(--plum);border-radius:16px;"
 "padding:26px;text-align:center;color:var(--plum-deep);font-size:16px;line-height:1.7}"
 ".c26-vidnote .ic{font-size:32px;display:block;margin-bottom:8px}"
 ".c26-teach{display:flex;align-items:center;gap:18px;flex-wrap:wrap;justify-content:center;"
 "margin:40px auto 8px;max-width:760px;background:#fbf8f2;border:1px solid var(--line);"
 "border-radius:16px;padding:20px 24px}"
 ".c26-teach .ic{font-size:30px}"
 ".c26-teach .tx{flex:1;min-width:220px}"
 ".c26-teach .tx b{display:block;font-size:16.5px;color:var(--ink)}"
 ".c26-teach .tx span{font-size:14px;color:var(--sub)}"
 ".c26-teach a.btn{background:var(--plum);color:#fff;padding:11px 20px;border-radius:999px;"
 "font-weight:700;font-size:15px;white-space:nowrap}"
 ".c26-teach a.btn:hover{background:var(--plum-deep);color:#fff}"
 ".c26-filmwrap{background:linear-gradient(180deg,rgba(124,41,66,.06),rgba(124,41,66,.01));"
 "border:1.5px solid var(--plum-soft,#eddce3);border-radius:20px;padding:26px 22px 8px;margin:6px 0 12px}"
 ".c26-filmnote{margin:0 0 18px;font-size:15px;color:var(--sub);line-height:1.7}"
 "</style>")

def build_camp_2026(o="/camps/2026/"):
    hero=band(crumb_html(o),"SUMMER CAMP 2026","2026 青少年學佛營",
        "四天三夜，在風櫃斗的山上，用影像、音樂、行禪與佛法，"
        "陪伴青少年認識自己、學習覺察與感恩。全程免費、遠離 3C、親近大自然。")
    # hero meta chips（注入 band 後）
    meta=('<div class="c26-meta">'
          '<span>🗓️ <b>7/4 – 7/7</b>（四天三夜）</span>'
          '<span>🎒 對象 <b>青少年</b></span>'
          '<span>📍 <b>如意精舍</b>（南投信義・風櫃斗）</span>'
          '<span>💛 <b>全程免費</b></span>'
          '<a class="c26-sib" href="%s">🧒 另有兒童營 7/8–7/12 →</a></div>'%u("/camps/2026-kids/"))
    hero=hero.replace("</div></section>",meta+"</div></section>",1)
    parts=[hero,'<main class="tintbg"><div class="wrap">']
    # 影片紀錄（放最前面，方便家長第一眼找到）
    parts.append('<div class="section-title rvl"><h2>活動影片紀錄</h2><div class="rule"></div></div>')
    if CAMP26_VIDS:
        parts.append('<div class="video-grid">'+''.join(yt_thumb(v[0],v[1],force=True) for v in CAMP26_VIDS)+'</div>')
        parts.append('<div class="rvl" style="text-align:center;margin:20px 0 4px">'
                     '<a href="%s" target="_blank" rel="noopener" '
                     'style="display:inline-flex;align-items:center;gap:8px;font-weight:700;'
                     'color:var(--sub,#5c5348);text-decoration:none;border:1.5px solid var(--line,#e7ddc9);'
                     'padding:10px 20px;border-radius:99px">'
                     '▶ 在 YouTube 看完整播放清單（陸續更新）→</a></div>'%CAMP26_PLAYLIST)
    else:
        parts.append('<div class="c26-vidnote rvl"><span class="ic">🎬</span>'
                     '活動影片將於營隊結束後陸續上線，敬請期待。<br>'
                     '<span style="font-size:14px;color:var(--sub)">'
                     '歷年夏令營影音紀錄請見 <a href="%s">夏令營總覽</a>。</span></div>'%u("/camps/"))
    # 學生微電影作品（與上面的活動側拍紀錄區隔開）
    if CAMP26_FILMS:
        parts.append('<div class="section-title rvl"><h2>🎬 學生微電影作品</h2><div class="rule"></div></div>')
        parts.append('<div class="c26-filmwrap rvl">'
                     '<p class="c26-filmnote">7/6 共創表達日，喜捨班、精進班、慈悲班三隊各自實拍剪輯一部「60 秒佛法微電影」，'
                     '當晚在星空下首映——這是孩子們親手完成的創作，與上方的活動紀錄側拍不同。</p>'
                     '<div class="video-grid">'+''.join(yt_thumb(v[0],v[1],force=True) for v in CAMP26_FILMS)+'</div>'
                     '</div>')
    # 四天主題
    parts.append('<div class="section-title rvl"><h2>四天，四個主題</h2><div class="rule"></div></div>')
    th='<div class="c26-themes rvl">'
    for dt,name,day,line,a,b in CAMP26_THEMES:
        th+=('<div class="c26-th rvl" style="--a:%s;--b:%s">'
             '<div class="day">%s</div><h3>%s</h3><div class="dt">%s</div><p>%s</p></div>'
             %(a,b,esc(day),esc(name),esc(dt),esc(line)))
    th+='</div>'; parts.append(th)
    # 每日課程表
    parts.append('<div class="section-title rvl"><h2>每日課程表</h2><div class="rule"></div></div>')
    parts.append('<p class="sched-note rvl">完整四天流程；標示 ★ 為動手體驗活動。實際內容以營隊現場為準。</p>')
    for a,b,theme,dt,rows in CAMP26_SCHEDULE:
        parts.append('<div class="c26-dayhead rvl" style="--a:%s;--b:%s">'
                     '<span class="pill">%s</span><h2>%s</h2><span class="dt">%s</span>'
                     '<span class="rule"></span></div>'%(a,b,esc(dt),esc(theme),""))
        cards='<div class="sched rvl">'
        for time,cname,desc,note,star in rows:
            jx=' c26-jx' if note=="吉祥老師" else ''
            shown_note=note if note and note!="吉祥老師" else ''
            star_mark='★ ' if star else ''
            cards+=('<div class="scard rvl%s" style="--ac:%s;--ac2:%s">'
                    '<div class="sdate"><span class="dy">%s</span></div>'
                    '<div class="sbody"><div class="sname">%s%s</div>'
                    '%s%s</div></div>'
                    %(jx,a,b,esc(time),star_mark,esc(cname),
                      '<div class="ssub">%s</div>'%esc(desc) if desc else '',
                      '<div class="snote">%s</div>'%esc(shown_note) if shown_note else ''))
        cards+='</div>'; parts.append(cards)
    # 教師專區（低調連結、非卡片）
    parts.append('<div class="c26-teach rvl"><div class="ic">🔑</div>'
                 '<div class="tx"><b>教師教學專區</b>'
                 '<span>8 位老師的授課教材，提供備課使用的教學指引（逐分鐘流程、講師口白、學習單）。</span></div>'
                 '<a class="btn" href="%s">進入教師專區 →</a></div>'%u("/camps/2026/teaching/"))
    parts.append('<div class="c26-teach rvl"><div class="ic">📋</div>'
                 '<div class="tx"><b>主持人手冊</b>'
                 '<span>總隊輔・隊輔現場用——4 天逐分鐘流程稿、開場口白、19 個團康活動操作卡。</span></div>'
                 '<a class="btn" href="%s">進入主持人手冊 →</a></div>'%u("/camps/2026/host-guide/"))
    parts.append('</div></main>')
    return page("2026 青少年學佛營","/learn/",CAMP26_CSS+''.join(parts),
                "2026 如意精舍青少年學佛營（7/4–7/7）課程表與活動紀錄 · 如意精舍")

# ---------------- 2026 兒童學佛營（手動生成，不在爬蟲內） ----------------
EXTRA_NAMES["/camps/"]="夏令營"
EXTRA_NAMES["/camps/2026-kids/"]="2026 兒童營"
EXTRA_NAMES["/camps/2026-kids/teaching/"]="教師專區"
EXTRA_NAMES["/camps/2026-kids/teaching/brave-no-game/"]="勇敢說不互動遊戲"

# 五天主題（日期, 主題, 第N天, 一句話, 主色, 副色）
KIDS26_THEMES=[
 ("7/8","歡喜啟程","第 1 天","報到、開營、認識三寶、英文與戲劇——歡喜相見，種下這趟旅程的開始","#b5591e","#d98b3f"),
 ("7/9","親近山林","第 2 天","整個上午的大自然探索、石頭彩拚、影片欣賞——走進山林，感受生命","#2f6d4f","#4f9670"),
 ("7/10","品德創意","第 3 天","立體畫、歌唱、闖關、戲劇演出——在創作與遊戲中學品德","#276b78","#3f96a5"),
 ("7/11","智慧感恩","第 4 天","弟子規、十大弟子、了凡四訓、甜點 DIY、結營晚會——聆聽智慧，滿懷感恩","#6a3a6e","#9a5a9e"),
 ("7/12","圓滿賦歸","第 5 天","與人為善、經絡拍打、親子同心、結營典禮——帶著善念與笑容回家","#a83a55","#cf6480"),
]
# 每日課程表：(主色,副色,主題,日期, [ (時間, 課名, 說明/老師, 標記, 是否亮點) ])
KIDS26_SCHEDULE=[
 ("#b5591e","#d98b3f","歡喜啟程","7/8（三）",[
   ("10:00 前","報到安單","學員陸續上山、安頓","",False),
   ("10:20","開營典禮","歡喜相見・迎接新朋友","",False),
   ("11:30","午餐／午休","","",False),
   ("13:30","相見歡","小隊分組・破冰遊戲 · 隊輔","",True),
   ("14:40","認識三寶","佛・法・僧的故事 · 尉家維老師","",False),
   ("15:50","英文 English","Dom Jones 老師","",True),
   ("17:00","晚課／晚餐","","",False),
   ("18:40","戲劇編排","分組排練・晚間活動","",True),
   ("20:30","盥洗・安板","","",False),
 ]),
 ("#2f6d4f","#4f9670","親近山林","7/9（四）",[
   ("06:00","起床・盥洗","","",False),
   ("06:30","早課／晨操／早餐","一天的開始","",False),
   ("08:00","大自然探索","整個上午的山林體驗 · 邱志中老師","",True),
   ("11:30","午餐／午休","","",False),
   ("13:30","石頭彩拚","撿石頭・彩繪創作 · 邱志中老師","",True),
   ("14:40","生命在呼吸間","謝呂賢老師","",False),
   ("15:50","腦力激盪","團隊動腦遊戲 · 隊輔","",True),
   ("17:00","晚課／晚餐","","",False),
   ("18:40","影片欣賞","尉峻翔老師","",True),
   ("20:30","盥洗・安板","","",False),
 ]),
 ("#276b78","#3f96a5","品德創意","7/10（五）",[
   ("06:00","起床・盥洗","","",False),
   ("06:30","早課／晨操／早餐","","",False),
   ("08:00","勇敢說不","保護自己 · 謝呂賢老師","",False),
   ("09:10","手繪錯覺立體畫","郭曉君老師","",True),
   ("10:20","品德與人生","劉翠玲老師","",False),
   ("11:30","午餐／午休","","",False),
   ("13:30","歌唱","尉芷睿老師","",True),
   ("14:40","三世因果","蔡暐哲老師","",False),
   ("15:50","闖關體驗","分站遊戲 · 隊輔","",True),
   ("17:00","晚課／晚餐","","",False),
   ("18:40","戲劇演出","分組成果發表","",True),
   ("20:30","盥洗・安板","","",False),
 ]),
 ("#6a3a6e","#9a5a9e","智慧感恩","7/11（六）",[
   ("06:00","起床・盥洗","","",False),
   ("06:30","早課／晨操／早餐","","",False),
   ("08:00","心靈的力量","蔡謙睿老師","",False),
   ("09:10","創意畫","林秀珠老師","",True),
   ("10:20","弟子規","劉昭崇老師","",False),
   ("11:30","午餐／午休","","",False),
   ("13:30","十大弟子","詹璦瑛老師","",False),
   ("14:40","了凡四訓","詹銅城老師","",False),
   ("15:50","甜蜜的祝福","夏威夷豆棗糕 DIY · 李莉莉老師","",True),
   ("17:00","晚課／晚餐","","",False),
   ("18:40","結營晚會","才藝表演・溫馨迴響","",True),
   ("20:30","盥洗・安板","","",False),
 ]),
 ("#a83a55","#cf6480","圓滿賦歸","7/12（日）",[
   ("06:00","起床・盥洗","","",False),
   ("06:30","早課／晨操／早餐","","",False),
   ("08:00","與人為善","尉家維老師","",False),
   ("09:10","經絡拍打","健康養生小體驗 · 張玉妮老師","",True),
   ("10:20","親子同心","家長入營・親子活動 · 隊輔","",True),
   ("11:10","結營典禮","賦歸・帶著善念回家","",False),
 ]),
]
# 活動影片（營隊結束後填入 YouTube ID 即自動長出可點縮圖；現為空＝顯示「待上線」）
KIDS26_VIDS=[
 ("dSIR-IVoT7A","開營前活動"),
 ("jZdGZISonZg","開營典禮"),
 ("-8UZ9gvvau0","相見歡"),
 ("KtCXndwWf9o","認識三寶"),
 ("FHQVkDrRSLw","戲劇編排"),
 ("tF8vhLjRJns","早課"),
 ("Ql322XmGp4M","歡樂歌唱"),
 ("j1p98R6393c","大自然探索"),
 ("nxJQzkgrS0Y","晚課"),
 ("AFoa-wso88s","早操"),
 ("5mU6liC3si4","生命在呼吸間"),
 ("Pab8_dq9zh4","腦力激盪"),
 ("t7PGGStXOFI","三世因果"),
 ("dj1HfNwIil8","學佛行儀"),
 ("PBZPDNgHh4w","勇敢說不"),
]
KIDS26_PLAYLIST="https://www.youtube.com/playlist?list=PLVFEzL1YVNqA"

def build_camp_kids_2026(o="/camps/2026-kids/"):
    hero=band(crumb_html(o),"SUMMER CAMP 2026","2026 兒童學佛營",
        "五天四夜，在風櫃斗的山上，用大自然、藝術、戲劇與佛法故事，"
        "陪伴國小學童親近自然、學習品德與感恩。全程免費、遠離 3C、親近大自然。")
    meta=('<div class="c26-meta">'
          '<span>🗓️ <b>7/8 – 7/12</b>（五天四夜）</span>'
          '<span>🎒 對象 <b>國小學童</b></span>'
          '<span>📍 <b>如意精舍</b>（南投信義・風櫃斗）</span>'
          '<span>💛 <b>全程免費</b></span>'
          '<a class="c26-sib" href="%s">🧑‍🎓 另有青少年營 7/4–7/7 →</a></div>'%u("/camps/2026/"))
    hero=hero.replace("</div></section>",meta+"</div></section>",1)
    parts=[hero,'<main class="tintbg"><div class="wrap">']
    # 影片紀錄（放最前面，方便家長第一眼找到）
    parts.append('<div class="section-title rvl"><h2>活動影片紀錄</h2><div class="rule"></div></div>')
    if KIDS26_VIDS:
        parts.append('<div class="video-grid">'+''.join(yt_thumb(v[0],v[1],force=True) for v in KIDS26_VIDS)+'</div>')
        parts.append('<div class="rvl" style="text-align:center;margin:20px 0 4px">'
                     '<a href="%s" target="_blank" rel="noopener" '
                     'style="display:inline-flex;align-items:center;gap:8px;font-weight:700;'
                     'color:var(--sub,#5c5348);text-decoration:none;border:1.5px solid var(--line,#e7ddc9);'
                     'padding:10px 20px;border-radius:99px">'
                     '▶ 在 YouTube 看完整播放清單（陸續更新）→</a></div>'%KIDS26_PLAYLIST)
    else:
        parts.append('<div class="c26-vidnote rvl"><span class="ic">🎬</span>'
                     '活動影片將於營隊結束後陸續上線，敬請期待。<br>'
                     '<span style="font-size:14px;color:var(--sub)">'
                     '歷年夏令營影音紀錄請見 <a href="%s">夏令營總覽</a>。</span></div>'%u("/camps/"))
    # 五天主題
    parts.append('<div class="section-title rvl"><h2>五天，五個主題</h2><div class="rule"></div></div>')
    th='<div class="c26-themes rvl">'
    for dt,name,day,line,a,b in KIDS26_THEMES:
        th+=('<div class="c26-th rvl" style="--a:%s;--b:%s">'
             '<div class="day">%s</div><h3>%s</h3><div class="dt">%s</div><p>%s</p></div>'
             %(a,b,esc(day),esc(name),esc(dt),esc(line)))
    th+='</div>'; parts.append(th)
    # 每日課程表
    parts.append('<div class="section-title rvl"><h2>每日課程表</h2><div class="rule"></div></div>')
    parts.append('<p class="sched-note rvl">完整五天流程；標示 ★ 為動手體驗與活動課程。實際內容以營隊現場為準。</p>')
    for a,b,theme,dt,rows in KIDS26_SCHEDULE:
        parts.append('<div class="c26-dayhead rvl" style="--a:%s;--b:%s">'
                     '<span class="pill">%s</span><h2>%s</h2><span class="dt">%s</span>'
                     '<span class="rule"></span></div>'%(a,b,esc(dt),esc(theme),""))
        cards='<div class="sched rvl">'
        for time,cname,desc,note,star in rows:
            star_mark='★ ' if star else ''
            cards+=('<div class="scard rvl" style="--ac:%s;--ac2:%s">'
                    '<div class="sdate"><span class="dy">%s</span></div>'
                    '<div class="sbody"><div class="sname">%s%s</div>'
                    '%s</div></div>'
                    %(a,b,esc(time),star_mark,esc(cname),
                      '<div class="ssub">%s</div>'%esc(desc) if desc else ''))
        cards+='</div>'; parts.append(cards)
    parts.append('<div class="c26-teach rvl"><div class="ic">KEY</div>'
                 '<div class="tx"><b>教師專區</b>'
                 '<span>提供本營授課老師備課、帶活動與補充教材使用。</span></div>'
                 '<a class="btn" href="%s">進入教師專區 →</a></div>'%u("/camps/2026-kids/teaching/"))
    parts.append('</div></main>')
    return page("2026 兒童學佛營","/learn/",CAMP26_CSS+''.join(parts),
                "2026 如意精舍兒童學佛營（7/8–7/12）課程表與活動紀錄 · 如意精舍")

KIDS26_TEACH_CSS=("<style>"
".teacher-hub{display:grid;gap:22px;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));margin:18px 0 38px}"
".teacher-tile{display:flex;flex-direction:column;gap:14px;background:#fff;border:1px solid var(--line);border-radius:18px;padding:26px;box-shadow:var(--shadow);text-decoration:none;color:var(--ink);transition:transform .22s,box-shadow .22s,border-color .22s}"
".teacher-tile:hover{transform:translateY(-6px);box-shadow:var(--shadow-hover);border-color:transparent;color:var(--ink)}"
".teacher-tile .tag{width:max-content;background:var(--plum-soft);color:var(--plum-deep);border-radius:999px;padding:5px 12px;font-size:13px;font-weight:800;letter-spacing:.08em}"
".teacher-tile h2{margin:0;font-size:24px;letter-spacing:.04em}"
".teacher-tile p{margin:0;color:var(--sub);line-height:1.75}"
".teacher-tile .go{margin-top:auto;color:var(--plum);font-weight:800}"
".teacher-note{background:#fbf8f2;border:1px solid var(--line);border-radius:16px;padding:20px;color:var(--sub);line-height:1.8}"
"</style>")

def build_kids26_teaching(o="/camps/2026-kids/teaching/"):
    hero=band(crumb_html(o),"TEACHER AREA","教師專區",
              "兒童學佛營授課老師備課使用。此區會持續補充教案、學習單與課堂活動。",slim=True)
    body=(hero+'<main class="tintbg"><div class="wrap">'
          '<div class="teacher-hub rvl">'
          '<a class="teacher-tile" href="%s"><span class="tag">互動遊戲</span>'
          '<h2>勇敢說不</h2><p>依照「不要就是不藥」簡報設計，帶孩子練習看穿偽裝、STOP 四步驟、拒毒六招與求助。</p>'
          '<span class="go">開始遊戲 →</span></a>'
          '<a class="teacher-tile" href="%s" target="_blank" rel="noopener"><span class="tag">上課簡報</span>'
          '<h2>勇敢說不</h2><p>7/10（五）08:00 · 謝呂賢老師。115 更新版反毒課程：識毒、拒毒、求助，36 頁投影片含逐頁講師口白。</p>'
          '<span class="go">開始上課簡報 →</span></a>'
          '<a class="teacher-tile" href="%s" target="_blank" rel="noopener"><span class="tag">上課簡報</span>'
          '<h2>生命在呼吸間</h2><p>7/9（四）14:40 · 謝呂賢老師。從一口氣認識無常、無我與菩薩的願，21 頁投影片含逐頁講師口白。</p>'
          '<span class="go">開始上課簡報 →</span></a>'
          '<a class="teacher-tile" href="%s" target="_blank" rel="noopener"><span class="tag">上課簡報</span>'
          '<h2>三世因果</h2><p>7/10（五）14:40 · 蔡暐哲老師。因緣果的種子比喻、善因小劇場與種子分類活動，14 頁投影片含逐頁講師口白。</p>'
          '<span class="go">開始上課簡報 →</span></a>'
          '</div><div class="teacher-note rvl">教師專區未來可再加入講義、學習單、影片連結與課程備忘。'
          '目前放置「互動遊戲」與三份上課簡報入口，避免一般家長或學員直接進入備課資料。</div>'
          '</div></main>'%(u("/camps/2026-kids/teaching/brave-no-game/"),
                            u("/camps/2026-kids/teaching/brave-no-slides.html"),
                            u("/camps/2026-kids/teaching/life-in-breath-slides.html"),
                            u("/camps/2026-kids/teaching/cause-and-effect-slides.html")))
    return page("2026 兒童營教師專區","/learn/",KIDS26_TEACH_CSS+body,
                "2026 如意精舍兒童學佛營教師專區")

KIDS26_GAME_CSS=("<style>"
".game-shell{max-width:1120px;margin:0 auto 44px}"
".game-panel{background:#fff;border:1px solid var(--line);border-radius:18px;box-shadow:var(--shadow);padding:24px;margin:20px 0}"
".game-top{display:flex;gap:16px;align-items:center;justify-content:space-between;flex-wrap:wrap}"
".score{display:flex;gap:10px;flex-wrap:wrap}.score span{background:#fbf8f2;border:1px solid var(--line);border-radius:999px;padding:7px 13px;font-size:14px;font-weight:800;color:var(--ink-soft)}"
".meter{height:12px;background:#eee6d8;border-radius:999px;overflow:hidden;margin-top:14px}.meter i{display:block;height:100%;width:0;background:linear-gradient(90deg,#2f6d4f,#d98b3f);transition:width .28s}"
".mission-grid{display:grid;gap:14px;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));margin-top:18px}"
".mission{border:1px solid var(--line);background:#fbf8f2;border-radius:14px;padding:18px;text-align:left;cursor:pointer;color:var(--ink);transition:transform .18s,border-color .18s,background .18s}"
".mission:hover{transform:translateY(-3px);border-color:#d9b879}.mission.done{background:#edf6ef;border-color:#9cc7a8}.mission h3{margin:0 0 8px;font-size:18px}.mission p{margin:0;color:var(--sub);font-size:14px;line-height:1.6}"
".stage{display:none}.stage.active{display:block}.stage h2{margin:0 0 10px;font-size:28px}.stage-lead{color:var(--sub);line-height:1.75;margin:0 0 18px}"
".choices{display:grid;gap:12px}.choice{border:1.5px solid var(--line);background:#fff;border-radius:14px;padding:15px 16px;text-align:left;cursor:pointer;font-size:16px;color:var(--ink);line-height:1.6;transition:background .18s,border-color .18s,transform .18s}.choice:hover{transform:translateY(-2px);border-color:#d9b879}.choice.good{background:#eef8f0;border-color:#7fbd8b}.choice.bad{background:#fff0ed;border-color:#dd9286}"
".feedback{min-height:58px;margin-top:16px;padding:14px 16px;border-radius:14px;background:#fbf8f2;color:var(--ink-soft);line-height:1.7;border:1px solid var(--line)}"
".navrow{display:flex;gap:10px;flex-wrap:wrap;margin-top:18px}.game-btn{border:0;background:var(--plum);color:#fff;border-radius:999px;padding:10px 18px;font-weight:800;cursor:pointer}.game-btn.secondary{background:#efe6d7;color:#4d4035}.game-btn:disabled{opacity:.45;cursor:not-allowed}"
".cards{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));margin-top:16px}.flip{min-height:118px;border:1px solid var(--line);border-radius:14px;background:#fff;padding:18px;display:flex;align-items:center;justify-content:center;text-align:center;font-weight:800;cursor:pointer;color:var(--ink);transition:transform .2s,background .2s}.flip.revealed{background:#edf6ef;color:#24523e}.flip:hover{transform:translateY(-3px)}"
".script-box{background:#2f5d52;color:#fff;border-radius:16px;padding:20px;margin-top:16px}.script-box b{display:block;font-size:20px;margin-bottom:8px}.script-box p{margin:0;color:rgba(255,255,255,.9);line-height:1.8}"
".finish{display:grid;gap:16px;grid-template-columns:1.1fr .9fr;align-items:center}.finish-card{background:#fbf8f2;border:1px solid var(--line);border-radius:16px;padding:20px}.finish-card h3{margin:0 0 10px}.finish-card ul{margin:0;padding-left:20px;color:var(--sub);line-height:1.8}"
"@media(max-width:760px){.finish{grid-template-columns:1fr}.stage h2{font-size:24px}.game-panel{padding:18px}}"
"</style>")

KIDS26_GAME_JS=r"""<script>
(function(){
var score=0, completed={}, current="";
var missions={
 disguise:{title:"看穿偽裝", lead:"毒品不一定長得像毒品。請判斷哪些物品需要提高警覺，重點是來源可不可信。",
  questions:[
   ["朋友拿出包裝可愛的咖啡包，說「很好喝，不要問那麼多」。你要怎麼做？",["我不喝不明來源的東西，先問老師。","看起來像飲料，喝一點沒關係。","幫朋友保管，等一下再說。"],0,"包裝可愛不代表安全。不明來源不吃、不喝、不吸。"],
   ["有人說電子煙不是毒品，只是放鬆一下。你要怎麼判斷？",["可能混入危險成分，離開並告訴大人。","只吸一口就知道了。","如果很多人試過就安全。"],0,"電子煙、煙彈可能被混入毒品。不是可信任大人提供的，就不要碰。"],
   ["陌生人給糖果，包裝漂亮，還說免費。",["免費不代表安全，我不要。","免費很划算，可以收下。","先拿著，不吃就好。"],0,"免費也是常見話術。拒絕、離開、求助，是保護自己。"]
  ]},
 stop:{title:"STOP 四步驟", lead:"遇到不舒服的邀請，先不要急著回應。把 STOP 四步驟排進心裡。",
  cards:[["S","Stop：先停下來"],["T","Think：想一想危險"],["O","Out：離開現場"],["P","Protect：找大人保護"]]},
 refuse:{title:"拒毒六招", lead:"拒絕不是沒禮貌，是保護自己。請幫主角選一句能說出口的安全回答。",
  questions:[
   ["同學說：「大家都有試，你不敢喔？」",["對，我就是很惜命。","好啦，只試一次。","你不要告訴老師就好。"],0,"這是自我解嘲，幽默但立場清楚。"],
   ["朋友說：「這不是毒品啦，吸一口很放鬆。」",["是朋友就不要害我，我先走。","你先吸，我再看看。","幫我藏一下。"],0,"友誼勸說加走為上策：真正的朋友不會逼你做危險的事。"],
   ["有人一直催你喝不明飲料。",["我不喝不明來源的東西，我要去找老師。","喝完再問是什麼。","如果好喝就再拿一包。"],0,"堅持拒絕並求助，最安全。"]
  ]},
 help:{title:"求助練習", lead:"孩子不需要自己當偵探。發現危險時，先保護自己，再找可信任的大人。",
  questions:[
   ["你看到有人拿不明煙彈要大家試。",["離開現場，告訴老師、家長或隊輔。","留下來拍照傳給同學。","幫忙拿去別的地方藏。"],0,"不要拍照炫耀、不要幫忙保管。先離開，再求助。"],
   ["朋友疑似被誘惑，但他叫你不要說。",["找可信任的大人一起幫忙。","答應保密，免得朋友生氣。","自己去質問對方。"],0,"保護朋友不是保密危險，而是找大人一起處理。"],
   ["如果現場已經有立即危險。",["先離開，必要時撥打 110。","再觀察一下就好。","自己把東西搶過來。"],0,"緊急危險要找警察與大人，不要自己硬撐。"]
  ]}
};
function qs(s){return document.querySelector(s)}
function qsa(s){return Array.from(document.querySelectorAll(s))}
function update(){
 qs("#gameScore").textContent=score;
 var done=Object.keys(completed).length;
 qs("#gameDone").textContent=done+"/4";
 qs("#gameMeter").style.width=(done*25)+"%";
 qsa(".mission").forEach(function(b){b.classList.toggle("done",!!completed[b.dataset.mission])});
 qs("#finishBtn").disabled=done<4;
}
function openMission(id){
 current=id; var m=missions[id], html='<div class="stage active"><h2>'+m.title+'</h2><p class="stage-lead">'+m.lead+'</p>';
 if(m.cards){
  html+='<div class="cards">'+m.cards.map(function(c){return '<button class="flip" data-back="'+c[1]+'">'+c[0]+'</button>'}).join("")+'</div>';
  html+='<div class="feedback">請依序點開 STOP，帶孩子全班念一次。</div>';
 }else{
  html+='<div id="questionBox"></div><div class="feedback" id="feedback">請選一個最安全的做法。</div>';
 }
 html+='<div class="navrow"><button class="game-btn secondary" id="backHome">回任務選單</button><button class="game-btn" id="completeMission">完成這一關</button></div></div>';
 qs("#stageArea").innerHTML=html;
 if(m.cards){
  qsa(".flip").forEach(function(btn){btn.addEventListener("click",function(){btn.textContent=btn.dataset.back;btn.classList.add("revealed")})});
 }else{renderQuestion(0)}
 qs("#backHome").onclick=function(){qs("#stageArea").innerHTML=""};
 qs("#completeMission").onclick=function(){if(!completed[current]){completed[current]=true;score+=10}qs("#stageArea").innerHTML='<div class="feedback">這一關完成。請回任務選單選下一關。</div>';update()};
}
function renderQuestion(i){
 var m=missions[current], q=m.questions[i], box=qs("#questionBox");
 box.innerHTML='<div class="script-box"><b>情境 '+(i+1)+'</b><p>'+q[0]+'</p></div><div class="choices">'+q[1].map(function(t,idx){return '<button class="choice" data-i="'+idx+'">'+t+'</button>'}).join("")+'</div>';
 qsa(".choice").forEach(function(btn){btn.onclick=function(){
  var good=Number(btn.dataset.i)===q[2]; btn.classList.add(good?"good":"bad");
  qs("#feedback").textContent=(good?"答對了。":"這個選擇不夠安全。")+" "+q[3];
  if(good) score+=3;
  setTimeout(function(){ if(i<m.questions.length-1) renderQuestion(i+1); else qs("#feedback").textContent+=" 這組情境完成，可以按「完成這一關」。"; update();},900);
 }});
}
qsa(".mission").forEach(function(btn){btn.onclick=function(){openMission(btn.dataset.mission)}});
qs("#finishBtn").onclick=function(){
 qs("#stageArea").innerHTML='<div class="finish"><div class="game-panel"><h2>闖關完成</h2><p class="stage-lead">請全班一起念：我不碰不明來源的東西；真正的朋友不會害我；遇到危險，我會離開並找大人。</p><div class="script-box"><b>勇敢不是逞強</b><p>勇敢是懂得保護自己，也懂得求助。</p></div></div><div class="finish-card"><h3>老師收束提問</h3><ul><li>今天最常見的誘惑話術是哪一句？</li><li>你最容易說出口的拒絕句是哪一句？</li><li>請寫下三位可信任的大人。</li></ul></div></div>';
};
qs("#resetBtn").onclick=function(){score=0;completed={};qs("#stageArea").innerHTML="";update()};
update();
})();
</script>"""

def build_kids26_brave_no_game(o="/camps/2026-kids/teaching/brave-no-game/"):
    hero=band(crumb_html(o),"INTERACTIVE GAME","勇敢說不互動遊戲",
              "依照反毒課程「不要就是不藥」設計，讓孩子在情境中練習識毒、拒毒、求助。",slim=True)
    body=(hero+'<main class="tintbg"><div class="wrap"><div class="game-shell">'
          '<div class="game-panel game-top rvl"><div><h2 style="margin:0 0 6px">任務總覽</h2>'
          '<p class="stage-lead" style="margin:0">老師可投影使用，分組作答，也可讓全班一起喊出拒絕句。</p></div>'
          '<div class="score"><span>分數 <b id="gameScore">0</b></span><span>完成 <b id="gameDone">0/4</b></span></div>'
          '<div class="meter" style="flex-basis:100%%"><i id="gameMeter"></i></div></div>'
          '<div class="mission-grid rvl">'
          '<button class="mission" data-mission="disguise"><h3>1. 看穿偽裝</h3><p>糖果、咖啡包、電子煙，不看外表，看來源。</p></button>'
          '<button class="mission" data-mission="stop"><h3>2. STOP 四步驟</h3><p>先停、想危險、離開、找大人保護。</p></button>'
          '<button class="mission" data-mission="refuse"><h3>3. 拒毒六招</h3><p>把「我不要」練到真的說得出口。</p></button>'
          '<button class="mission" data-mission="help"><h3>4. 求助練習</h3><p>孩子不用當偵探，安全求助最重要。</p></button>'
          '</div><div id="stageArea"></div>'
          '<div class="navrow rvl"><button class="game-btn" id="finishBtn" disabled>完成總結</button>'
          '<button class="game-btn secondary" id="resetBtn">重新開始</button>'
          '<a class="game-btn secondary" href="%s" style="text-decoration:none">回教師專區</a></div>'
          '</div></div></main>'%u("/camps/2026-kids/teaching/"))
    return page("勇敢說不互動遊戲","/learn/",KIDS26_GAME_CSS+body+KIDS26_GAME_JS,
                "2026 兒童學佛營教師用互動遊戲：勇敢說不，不要就是不藥")

# ---------------- 法會資訊 (news) ----------------
# 2026 法會時間表 — 上半年為現行站確認資料；下半年念佛法會＝每月第二個週日（10/11 經 Luke 確認）
NEWS_PHOTOS=[("assets/img/news-chanting.jpg",""),
             ("assets/img/news-altar.jpg",""),
             ("assets/img/news-talk.png",""),
             ("assets/img/news-bathing.jpg",""),
             ("assets/img/news-recitation-outdoor.jpg",""),
             ("assets/img/news-flower-offering.jpg",""),
             ("assets/img/news-altar-service.jpg","")]
NEWS_EVENTS=[  # (solar, 農曆, 名稱, 備註, 類型) — 依現行站時間表（Luke 截圖核對）
 ("1/10","農曆十一月廿二","回娘家","","home"),
 ("1/11","農曆十一月廿三","念佛法會","","nianfo"),
 ("2/1","農曆十二月十四","念佛法會","","nianfo"),
 ("3/1","農曆正月十三","念佛法會","","nianfo"),
 ("4/12","農曆二月廿五","念佛法會","","nianfo"),
 ("5/10","農曆三月廿四","浴佛節","釋迦牟尼佛聖誕","yufo"),
 ("6/7","農曆四月廿二","念佛法會","","nianfo"),
 ("6/28","農曆五月十四","念佛法會","","nianfo"),
 ("7/4 ～ 7/7","農曆五月廿一～廿三","青少年學佛營","","camp"),
 ("7/8 ～ 7/12","農曆五月廿四～廿八","兒童學佛營","暑期成長活動","camp"),
 ("8/2","農曆六月二十","念佛法會","","nianfo"),
 ("8/23","農曆七月初四","念佛法會","","nianfo"),
 ("9/6","農曆七月廿五","盂蘭盆法會","","ullambana"),
 ("10/11","農曆九月初一","念佛法會","","nianfo"),
 ("11/8","農曆九月三十","念佛法會","","nianfo"),
 ("12/6","農曆十月廿八","念佛法會","","nianfo"),
 ("1/10","農曆十二月初三","念佛法會","2027 年","nianfo"),
]
EV_ACCENT={"nianfo":("#7c2942","#b5446a"),"yufo":("#9a6a1e","#c29a45"),
           "camp":("#2f5d52","#43806f"),"home":("#274a78","#3f6aa5"),
           "ullambana":("#5a3d7a","#7d5aa6")}
def build_news(o):
    nm=name_of(o)
    hdr=band(crumb_html(o),"法會資訊 · DHARMA EVENTS",nm,
             "念佛、浴佛與兒童學佛營——歡迎隨喜參加，共沐法喜。")
    # carousel (no-crop)
    carousel=('<div class="section-title rvl"><h2>精舍剪影</h2><div class="rule"></div></div>'
              +photo_carousel([(src,cap) for src,cap in NEWS_PHOTOS]))
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
    sched=('<div class="section-title rvl"><h2>法會時間表</h2><div class="rule"></div></div>'
           '<p class="sched-note rvl">歡迎隨喜參加，共沐法喜；實際時間以精舍最新公告為準。</p>'
           '<div class="sched rvl">%s</div>'%cards)
    body=hdr+'<main class="tintbg"><div class="wrap">'+sched+carousel+'</div></main>'
    return page(nm,"/news/",body,nm+" · 如意精舍")

# ---------------- 讀書會 (study-group) ----------------
SG_ACCENT={"戒律":("#7c2942","#b5446a"),"佛法基礎":("#2f5d52","#43806f"),
           "淨土":("#274a78","#3f6aa5"),"唯識":("#9a6a1e","#c29a45"),
           "般若":("#5a3d7a","#7d5aa6")}
def build_study_group(o):
    nm=name_of(o)
    hdr=band(crumb_html(o),"讀書會 · STUDY GROUP",nm,
             "多聞薰習、深入經藏。利用現代科技，為居家修行者提供一個研讀佛法的清淨空間。")
    # intro 三欄
    intro=('<div class="sg-intro rvl">'
           '<div class="sgi"><h3>核心宗旨</h3>'
           '<p>打破空間的藩籬。無論身在何處，只要有網路，就能與同修一起深入義理，'
           '將佛法智慧真正內化為生活的力量。</p></div>'
           '<div class="sgi"><h3>特色</h3><ul>'
           '<li>系統導讀 · 深度剖析經論</li><li>雲端共修 · 打破時空限制</li>'
           '<li>互動討論 · 集思廣益共學</li></ul></div>'
           '<div class="sgi"><h3>共修時間</h3>'
           '<p class="sg-time">週一、二、三　20:30 – 21:30</p>'
           '<p>加入資格：不分背景，對研讀佛法、探索智慧有興趣之人皆可參加，'
           '歡迎每一顆精進求法的心。</p></div></div>')
    # 法門分類卡片
    secs=""
    for grp in STUDY_GROUPS:
        cat=grp["cat"]; c1,c2=SG_ACCENT.get(cat,("#7c2942","#b5446a"))
        cards=""
        for j,card in enumerate(grp["cards"]):
            out=card["out"]
            # 講次數：優先採用錄音集數（去重），其次才是子頁數，再次才是影片數。
            # 梵網經菩薩戒等只有 1 篇戒本子頁、卻有多集錄音導讀，
            # 若只數子頁會誤顯示「1 篇講次」。合併卡片則加總各來源系列。
            if card.get("combine"):
                n=sum(series_count(co) for co in card["combine"])
            else:
                n=series_count(out)
            meta=('%d 篇講次 ' % n) if n else ''
            cards+=('<a class="sgcard rvl" style="transition-delay:%dms" href="%s">'
                    '<div class="sgcard-head"><span>%s</span></div>'
                    '<div class="sgcard-body"><p>%s</p>'
                    '<div class="sgcard-foot"><span class="sgcard-n">%s</span>'
                    '<span class="sgcard-more">深入研讀 <span class="arw">→</span></span></div>'
                    '</div></a>'%(min(j*60,360),u(out),esc(card["name"]),esc(card["desc"]),meta))
        secs+=('<section class="sgcat rvl" style="--ac:%s;--ac2:%s">'
               '<div class="sgcat-head"><span class="sgcat-zh">%s</span>'
               '<span class="sgcat-line"></span><span class="sgcat-en">法門</span></div>'
               '<div class="sgcards">%s</div></section>'%(c1,c2,esc(cat),cards))
    body=hdr+'<main class="tintbg"><div class="wrap">'+intro+secs+'</div></main>'
    return page(nm,"/study-group/",body,nm+" · 如意精舍")

def render_audio(o):
    """錄音共修：Drive 音檔列表，點擊當頁內嵌播放（不彈出 Drive）。"""
    a=AUDIO.get(o)
    if not a: return ""
    items=""; seen=set()
    for it in a["items"]:
        if it.get("num") in seen: continue   # 去除重複集數
        seen.add(it.get("num"))
        label="第 %s 集" % it["num"] if it.get("num") else "錄音"
        date=it.get("date","")
        items+=('<button class="aud-item" data-drive="%s">'
                '<span class="aud-play"><i></i></span>'
                '<span class="aud-num">%s</span>'
                '<span class="aud-date">%s</span>'
                '<span class="aud-go">收聽</span></button>'%(it["id"],esc(label),esc(date)))
    return ('<div class="section-title rvl"><h2>%s</h2><div class="rule"></div></div>'
            '<p class="aud-note rvl">點選任一集即可在本頁收聽錄音（共 %d 集）。</p>'
            '<div class="audlist rvl">%s</div>'%(esc(a.get("title","錄音共修")),len(seen),items))

def render_intro(o):
    """經典介紹（內容佚失時的詳細導讀）。"""
    it=INTROS.get(o)
    if not it: return ""
    parts=['<div class="intro rvl">']
    if it.get("byline"):
        parts.append('<div class="intro-byline">%s</div>'%esc(it["byline"]))
    if it.get("lead"):
        parts.append('<p class="intro-lead">%s</p>'%esc(it["lead"]))
    for sec in it.get("sections",[]):
        parts.append('<h2 class="intro-h">%s</h2>'%esc(sec["h"]))
        for p in sec.get("p",[]):
            parts.append('<p>%s</p>'%esc(p))
    if it.get("link"):
        parts.append('<a class="intro-cta" href="%s" target="_blank" rel="noopener">'
                     '%s <span class="arw">→</span></a>'%(esc(it["link"]["url"]),esc(it["link"]["text"])))
    if it.get("note"):
        parts.append('<p class="intro-note">%s</p>'%esc(it["note"]))
    parts.append('</div>')
    return ''.join(parts)

def build_study_series(o):
    """經典頁：去除作者手打的文字目錄，只留章節影音導覽。"""
    nm=name_of(o); cnt=len(children.get(o,[]))
    hdr=band(crumb_html(o),"讀書會 · 經典導讀",nm,
             "共 %d 個講次，點選即可當頁觀看影音。"%cnt)
    body=hdr+'<main class="tintbg"><div class="wrap">'+child_section(o)+render_audio(o)+'</div></main>'
    return page(nm,"/study-group/",body,nm+" · 如意精舍")

def yt_count(out):
    p=out2path.get(out)
    if not p or p not in content: return 0
    return sum(1 for b in content[p]["blocks"] if b["t"]=="yt")

def series_count(out):
    """單一系列的講次數：錄音 → 子頁 → 影片，依序採計。"""
    au=AUDIO.get(out,{}).get("items",[])
    nau=len({i.get("num") for i in au if i.get("num")})
    return nau if nau else (len(children.get(out,[])) or yt_count(out))

def redirect_html(to,title):
    url=u(to)
    return ('<!DOCTYPE html><html lang="zh-Hant"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta http-equiv="refresh" content="0; url=%s">'
            '<link rel="canonical" href="%s%s"><title>%s · 如意精舍</title>'
            '<script>location.replace("%s")</script></head>'
            '<body style="font-family:sans-serif;padding:2rem;text-align:center">'
            '正在前往 <a href="%s">%s</a>…</body></html>'
            %(url,SITE_URL,to,esc(title),url,url,esc(title)))

def build_prajna(card):
    """合併頁：先介紹《心經》《金剛經》兩部經，再列出般若經講記的講課內容。"""
    o=card["out"]; nm=card["name"]
    video_o,chap_o=card["combine"][0],card["combine"][1]   # 心經(影音)、金剛經(章節)
    total=series_count(video_o)+series_count(chap_o)
    hdr=band(crumb_html(o),"讀書會 · 經典導讀",nm,
             "印順導師《般若經講記》收錄《心經》與《金剛經》兩部講記，"
             "共 %d 個講次。先認識這兩部經，再依序研讀。"%total)
    intro_cards="".join('<div class="sgi rvl"><h3>%s</h3><p>%s</p></div>'
                        %(esc(it["name"]),esc(it["text"])) for it in card.get("intros",[]))
    intro=('<div class="section-title rvl"><h2>關於這兩部經</h2><div class="rule"></div></div>'
           '<div class="sg-intro rvl">'+intro_cards+'</div>')
    # 心經 · 講課內容（影音格狀清單，點縮圖當頁播放）
    pairs=_yt_series_pairs(content[out2path[video_o]]["blocks"])
    vid_grid="".join(yt_thumb(yid,_session_label(cap,i+1),force=True)
                     for i,(yid,cap) in enumerate(pairs))
    sec_video=('<div class="section-title rvl"><h2>心經 · 講課內容</h2><div class="rule"></div></div>'
               '<div class="video-grid">'+vid_grid+'</div>')
    # 金剛經 · 講課內容（章節清單）
    sec_chap=('<div class="section-title rvl"><h2>金剛經 · 講課內容</h2><div class="rule"></div></div>'
              +child_section(chap_o))
    body=hdr+'<main class="tintbg"><div class="wrap">'+intro+sec_video+sec_chap+'</div></main>'
    return page(nm,"/study-group/",body,nm+" · 如意精舍")

def _yt_series_pairs(blocks):
    """配對每支 YouTube 與其後方的日期說明 <p>（如「20230816 讀書會錄音檔」）。"""
    pairs=[]
    for i,b in enumerate(blocks):
        if b["t"]=="yt":
            cap=blocks[i+1]["text"] if i+1<len(blocks) and blocks[i+1]["t"]=="p" else ""
            pairs.append((b["id"],cap))
    return pairs

def _session_label(cap,idx):
    m=re.search(r'(\d{4})(\d{2})(\d{2})',cap or "")
    lab="第 %02d 集"%idx
    if m: lab+=" · %s/%s/%s"%(m.group(1),m.group(2),m.group(3))
    return lab

def build_study_video_series(o):
    """影音講次系列（YouTube）：與其他經典系列一致的講次格狀清單，點選當頁播放。
    八識規矩頌、心經等以一支支 YouTube 加日期說明呈現，原本被當成散落的單頁影片，
    這裡統一成「共 N 個講次」的影音導覽，與錄音／子頁系列外觀一致。"""
    d=content[out2path[o]]; nm=d["name"]
    pairs=_yt_series_pairs(d["blocks"])
    hdr=band(crumb_html(o),"讀書會 · 經典導讀",nm,
             "共 %d 個講次，點選即可當頁觀看影音。"%len(pairs))
    thumbs="".join(yt_thumb(yid,_session_label(cap,i+1),force=True)
                   for i,(yid,cap) in enumerate(pairs))
    body=hdr+('<main class="tintbg"><div class="wrap">'
              '<div class="video-grid">'+thumbs+'</div></div></main>')
    return page(nm,"/study-group/",body,nm+" · 如意精舍")

def build_study_chapter(o):
    """講次頁：band header＋影片／錄音（去除與標題重複的文字）。"""
    d=content[out2path[o]]; nm=d["name"]
    hdr=band(crumb_html(o),"讀書會 · 經典",nm,slim=True)
    # 去除與標題重複的文字，以及裝飾用圖片(如意精舍紅印)
    rest=[b for b in d["blocks"] if b["t"]!="img"
          and not (b["t"] in ("h","p","li") and b.get("text","").strip()==nm)]
    inner=render_intro(o)+render_blocks(rest,nm)+render_audio(o)
    return page(nm,"/study-group/",hdr+'<main class="tintbg"><div class="wrap">'+inner+'</div></main>',nm+" · 如意精舍")

# ---------------- 法師簡介 (bhikkhuni) ----------------
def build_bhikkhuni(o):
    d=content[out2path[o]]; nm=d["name"]; blocks=d["blocks"]
    portraits=[]; bio=[]; gallery=[]; seen_h2=False; i=0
    while i < len(blocks):
        b=blocks[i]
        if b["t"]=="h" and b.get("level")==2:
            seen_h2=True; i+=1; continue
        if (not seen_h2 and b["t"]=="img" and i+1<len(blocks)
                and blocks[i+1]["t"]=="p" and len(blocks[i+1].get("text",""))<=8):
            portraits.append((b["src"],blocks[i+1]["text"])); i+=2; continue
        if seen_h2:
            if b["t"]=="img": gallery.append(b["src"])
            elif b["t"] in ("h","p","li") and b.get("text","")!=nm: bio.append(b["text"])
        i+=1
    EN={"陽慧法師":"Ven. Master Yang-hui","達慧法師":"Ven. Master Da-hui"}
    CROP={"陽慧法師":"assets/img/master1.jpg","達慧法師":"assets/img/master2.jpg"}  # 半身置中裁切
    LOTUS=('<svg viewBox="0 0 48 32" fill="currentColor" aria-hidden="true">'
           '<path d="M24 3 C20 11 20 20 24 27 C28 20 28 11 24 3Z"/>'
           '<path d="M24 27 C18 23 14 15 13 8 C19 11 23 19 24 27Z"/>'
           '<path d="M24 27 C30 23 34 15 35 8 C29 11 25 19 24 27Z"/>'
           '<path d="M24 28 C16 27 8 23 4 17 C12 16 20 20 24 28Z"/>'
           '<path d="M24 28 C32 27 40 23 44 17 C36 16 28 20 24 28Z"/></svg>')
    pcards=""
    for i,(src,name) in enumerate(portraits):
        en=EN.get(name,""); src=CROP.get(name,src)
        pcards+=('<div class="master rvl" style="transition-delay:%dms">'
                 '<div class="m-photo"><div class="bg" style="background-image:url(%s)"></div></div>'
                 '<div class="m-plate"><span class="m-lotus">%s</span>'
                 '<div class="m-name">%s</div>'
                 '%s'
                 '<div class="m-rule"></div>'
                 '<div class="m-role">如意精舍 · 共同創辦</div></div></div>'
                 %(min(i*90,300),u("/"+src),LOTUS,esc(name),
                   '<div class="m-en">%s</div>'%esc(en) if en else '',))
    hdr=band(crumb_html(o),"法師簡介 · THE MASTERS",nm,
             "兩位法師生長於信義鄉風櫃斗，出家後回鄉弘法、深耕菩提。")
    body=hdr+'<main class="tintbg"><div class="wrap">'
    body+='<div class="masters rvl">'+pcards+'</div>'
    if bio:
        body+=('<div class="section-title rvl"><h2>兩位法師的故事</h2><div class="rule"></div></div>'
               '<div class="prose rvl">'+''.join('<p>%s</p>'%esc(t) for t in bio)+'</div>')
    if gallery:
        body+=('<div class="m-gallery rvl">'
               +''.join('<figure><img loading="lazy" src="%s" alt="如意精舍"></figure>'%u("/"+g)
                        for g in gallery)+'</div>')
    body+='</div></main>'
    return page(nm,"/bhikkhuni/",body,nm+" · 如意精舍")

# ================= 學習園地 / 如意英文學校 (English School) =================
# 24 課英語課（融入佛法）線上複習庫。內容由 data/english_school.json 提供，
# 設計為如意精舍自家的童趣版（plum/gold 底 + 每週糖果色），與英文站各自獨立。
ES_THEME={1:'saffron',2:'pink',3:'jade',4:'sky',5:'coral',6:'violet',7:'gold',8:'saffron',
 9:'pink',10:'jade',11:'sky',12:'coral',13:'pink',14:'jade',15:'coral',16:'violet',17:'gold',
 18:'saffron',19:'sky',20:'jade',21:'pink',22:'coral',23:'violet',24:'gold'}
ES_EMOJI={1:'🙏',2:'🧘',3:'🌱',4:'💗',5:'💎',6:'🛤️',7:'🎯',8:'🔥',9:'☸️',10:'🌊',11:'🌬️',12:'🕊️',
 13:'💛',14:'🤝',15:'❤️',16:'🤲',17:'🍃',18:'🎉',19:'👨‍👩‍👧',20:'🌳',21:'✨',22:'🪷',23:'🧘‍♀️',24:'👑'}
ES_QLABEL={'eng':('💬','英文目標'),'spirit':('🪷','佛學／心靈目標')}
# friendly breadcrumb names for the manually-written learning pages
EXTRA_NAMES["/english-school/"]="如意英文學校"
for _esd in ES_LESSONS:
    EXTRA_NAMES["/english-school/%s/"%_esd["id"]]="第 %d 週"%_esd["week"]

ES_CSS = """<style>
.es{max-width:900px;margin:0 auto;
 --ac:#e0892a;--ac2:#b86a12;--soft:#fdf2e2;--line2:#f1ddc0;}
.es.t-saffron{--ac:#ef7d2e;--ac2:#b85a12;--soft:#fff0e0;--line2:#ffe2c6;}
.es.t-pink{--ac:#e85684;--ac2:#b83560;--soft:#ffe7ef;--line2:#ffd2e0;}
.es.t-jade{--ac:#2aa996;--ac2:#1c8273;--soft:#ddf4ef;--line2:#c2ece4;}
.es.t-sky{--ac:#3f9be0;--ac2:#1f72b8;--soft:#e4f1fc;--line2:#cce6fa;}
.es.t-coral{--ac:#ef6253;--ac2:#c43c30;--soft:#ffe8e4;--line2:#ffd4cd;}
.es.t-violet{--ac:#8d63e6;--ac2:#6a3fc0;--soft:#efe7fc;--line2:#e0d2fa;}
.es.t-gold{--ac:#d4961e;--ac2:#a76f0c;--soft:#fbf1d6;--line2:#f1e2b2;}
.es .es-intro{display:grid;gap:16px;margin:30px 0 6px}
@media(min-width:820px){.es .es-intro{grid-template-columns:1.3fr 1fr}}
.es .es-note{background:#fff;border:2px solid var(--line);border-radius:18px;padding:22px 24px;
 box-shadow:var(--shadow);font-size:16px;line-height:1.8;color:var(--ink-soft)}
.es .es-note .ic{font-size:30px;display:block;margin-bottom:6px}
.es .es-note b{color:var(--ac2)}
.es .es-teacher{background:linear-gradient(160deg,#fbf1d8,#f7e7cf);border:2px solid #ecd6a6;
 border-radius:18px;padding:22px 24px;position:relative;overflow:hidden}
.es .es-teacher::after{content:"💛";position:absolute;right:-12px;bottom:-16px;font-size:120px;opacity:.12;transform:rotate(-12deg)}
.es .es-teacher .who{display:flex;align-items:center;gap:13px;margin-bottom:10px}
.es .es-teacher .av{width:54px;height:54px;border-radius:50%;background:linear-gradient(135deg,#f1c75a,#e08a2e);
 display:flex;align-items:center;justify-content:center;font-size:28px;flex-shrink:0;box-shadow:0 8px 18px -8px rgba(224,138,46,.7)}
.es .es-teacher .who b{font-family:var(--serif);font-size:22px;color:#9a5a12;display:block;line-height:1.1}
.es .es-teacher .who span{font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:#b8862f;font-weight:700}
.es .es-teacher p{font-size:15px;line-height:1.8;color:#6b4f23;position:relative;z-index:1;margin:0}
.es .es-qhead{display:flex;align-items:center;gap:13px;margin:40px 0 14px;flex-wrap:wrap}
.es .es-qbadge{font-family:var(--serif);font-weight:700;color:#fff;font-size:14px;letter-spacing:.04em;
 padding:7px 16px;border-radius:30px}
.es .es-qhead h2{font-size:23px;margin:0;letter-spacing:.04em;color:var(--ink)}
.es .es-qhead .qs{flex-basis:100%;font-size:14px;color:var(--sub);margin-top:-4px}
.es .es-grid{display:grid;gap:15px;grid-template-columns:1fr}
@media(min-width:560px){.es .es-grid{grid-template-columns:1fr 1fr}}
@media(min-width:840px){.es .es-grid{grid-template-columns:1fr 1fr 1fr}}
.es .es-card{position:relative;display:flex;flex-direction:column;background:#fff;border:2px solid var(--line2);
 border-radius:20px;padding:20px;box-shadow:var(--shadow);overflow:hidden;
 transition:transform .25s,box-shadow .25s,border-color .25s}
.es .es-card::before{content:"";position:absolute;inset:0 0 auto 0;height:7px;background:var(--cc)}
.es a.es-card:hover{transform:translateY(-6px);box-shadow:var(--shadow-hover);border-color:var(--cc)}
.es .es-card .top{display:flex;align-items:center;gap:12px;margin:4px 0 12px}
.es .es-card .emo{width:50px;height:50px;border-radius:15px;background:var(--ccs);display:flex;
 align-items:center;justify-content:center;font-size:26px;flex-shrink:0;transition:transform .25s}
.es a.es-card:hover .emo{transform:scale(1.12) rotate(-7deg)}
.es .es-card .wk{font-family:var(--serif);font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--ccd);font-weight:700}
.es .es-card .wn{font-family:var(--serif);font-size:23px;font-weight:700;color:var(--ink);line-height:1}
.es .es-card h3{font-size:17px;line-height:1.35;color:var(--ink);margin:0 0 auto;font-weight:700}
.es .es-card .go{font-family:var(--serif);font-size:14px;color:var(--ccd);font-weight:700;margin-top:14px}
.es .es-card .live{position:absolute;top:13px;right:13px;font-family:var(--serif);font-size:11px;font-weight:700;
 letter-spacing:.05em;color:#fff;background:#2bae6a;padding:4px 10px;border-radius:20px}
/* lesson body */
.es-les{max-width:820px}
.es-les .sec{margin:0 0 46px}
.es-les .sh{display:flex;align-items:center;gap:13px;margin:0 0 18px;flex-wrap:wrap}
.es-les .sh h2{font-size:23px;margin:0;color:var(--ink);position:relative;padding-bottom:8px;letter-spacing:.02em}
.es-les .sh h2::after{content:"";position:absolute;left:0;bottom:0;width:42px;height:5px;border-radius:5px;background:var(--ac)}
.es-les .sh .tag{font-size:12px;letter-spacing:.04em;color:var(--ac2);font-weight:700;background:var(--soft);padding:5px 12px;border-radius:20px}
.es-les .lede{font-size:17px;color:var(--ink-soft);line-height:1.8;margin:0 0 18px}
.es-les .note{font-size:14px;color:var(--sub);margin:0 0 16px}
.es-les .obj2{display:grid;gap:15px}
@media(min-width:660px){.es-les .obj2{grid-template-columns:1fr 1fr}}
.es-les .obj{background:#fff;border:2px solid var(--line);border-radius:16px;padding:20px 22px;box-shadow:var(--shadow)}
.es-les .obj.eng{border-top:6px solid #d4961e}.es-les .obj.spirit{border-top:6px solid var(--mist)}
.es-les .obj h3{font-size:17px;margin:0 0 3px}.es-les .obj .ozh{font-size:12px;color:var(--sub);font-weight:700;letter-spacing:.04em;margin-bottom:9px}
.es-les .obj p{font-size:15px;color:var(--ink-soft);line-height:1.7;margin:0}
.es-les .vt{width:100%;border-collapse:separate;border-spacing:0 10px}
.es-les .vt tr{background:#fff;box-shadow:var(--shadow)}
.es-les .vt td{padding:13px 15px;border-top:2px solid var(--line2);border-bottom:2px solid var(--line2)}
.es-les .vt td:first-child{border-left:6px solid var(--ac);border-radius:14px 0 0 14px}
.es-les .vt td:last-child{border-right:2px solid var(--line2);border-radius:0 14px 14px 0;text-align:right}
.es-les .vw{font-family:var(--serif);font-size:21px;font-weight:700;color:var(--ink)}
.es-les .vp{font-size:12px;color:var(--sub);font-weight:600;margin-left:4px}
.es-les .vz{font-size:15px;color:var(--ink-soft)}
.es-say{background:var(--soft);border:2px solid var(--line2);color:var(--ac2);border-radius:50%;
 width:40px;height:40px;cursor:pointer;font-size:16px;display:inline-flex;align-items:center;justify-content:center;
 transition:transform .15s,background .15s;vertical-align:middle}
.es-say:hover,.es-say.on{background:var(--ac);border-color:var(--ac);color:#fff;transform:scale(1.1)}
.es-les .pat{background:#fff;border:2px solid var(--line2);border-radius:16px;padding:18px 20px;margin-bottom:16px;box-shadow:var(--shadow)}
.es-les .pl{display:inline-block;font-family:var(--serif);font-size:12px;letter-spacing:.04em;text-transform:uppercase;
 color:#fff;background:var(--ac);padding:4px 12px;border-radius:20px;margin-bottom:11px;font-weight:700}
.es-les .pf{font-family:var(--serif);font-size:22px;font-weight:700;color:var(--ink);background:var(--soft);
 border-radius:11px;padding:11px 16px;margin-bottom:12px}
.es-les .ex{font-size:16px;color:var(--ink-soft);margin:0 0 8px;line-height:1.6}
.es-les .ex strong{color:var(--ink)}
.es-sayl{background:none;border:none;color:var(--ac);cursor:pointer;font-size:15px;padding:0 2px;vertical-align:middle;transition:transform .15s}
.es-sayl:hover,.es-sayl.on{transform:scale(1.25)}
.es-les .gram{background:var(--soft);border:2px solid var(--line2);border-radius:16px;padding:18px 22px}
.es-les .gram h4{font-size:16px;color:var(--ac2);margin:0 0 7px}.es-les .gram p{font-size:15px;color:var(--ink-soft);line-height:1.75;margin:0}
.es-les .gram .ok{color:var(--mist);font-weight:700}
.es-les figure.fig{margin:0 0 18px;border-radius:16px;overflow:hidden;border:3px solid #fff;box-shadow:var(--shadow-lg)}
.es-les figure.fig img{width:100%;display:block}
.es-les figure.fig figcaption{font-size:13px;color:var(--sub);padding:10px 15px;background:var(--soft)}
.es-les .story p{font-size:16px;color:var(--ink-soft);line-height:1.85;margin:0 0 14px}
.es-les .story strong{color:var(--ink)}.es-les .zh-gloss{color:var(--sub);font-size:14px}
.es-les .zh-trans{font-size:15px;color:var(--sub);line-height:1.85;margin:-4px 0 14px;
  padding:8px 12px;background:var(--bg-soft);border-left:3px solid var(--gold);border-radius:0 8px 8px 0}
.es-les .zh-trans::before{content:"中譯　";font-size:12px;color:var(--gold);font-weight:700}
.es-les .ex-zh{display:block;font-size:14.5px;color:var(--sub);margin-top:2px;padding-left:2px}
.es-les .tr-zh{font-size:14px;color:var(--sub);line-height:1.8;margin:6px 0 0;
  padding-top:6px;border-top:1px dashed var(--line)}
.es-les .qcheck{background:var(--soft);border:2px dashed var(--ac);border-radius:16px;padding:17px 21px;margin-top:16px}
.es-les .qcheck h4{font-size:15px;color:var(--ac2);margin:0 0 9px}
.es-les .qcheck ul{margin:0;padding-left:20px}.es-les .qcheck li{font-size:15px;color:var(--ink-soft);margin-bottom:6px;line-height:1.6}
.es-les .vid{border-radius:16px;overflow:hidden;border:3px solid #fff;box-shadow:var(--shadow-lg);background:#000;margin:0 0 16px}
.es-les .vid video{width:100%;display:block}
.es-les .pbox{background:linear-gradient(160deg,#fbf1d8,#f6e6cd);border:2px solid #ecd6a6;border-radius:16px;padding:20px 24px}
.es-les .pbox h4{font-size:17px;color:#9a5a12;margin:0 0 7px}.es-les .pbox p{font-size:15px;color:#6b4f23;line-height:1.75;margin:0}
.es-les .tiers{display:grid;gap:15px}@media(min-width:740px){.es-les .tiers{grid-template-columns:repeat(3,1fr)}}
.es-les .tier{background:#fff;border:2px solid var(--line);border-radius:16px;padding:20px;box-shadow:var(--shadow);display:flex;flex-direction:column}
.es-les .tier.t1{border-top:6px solid #2bae6a}.es-les .tier.t2{border-top:6px solid #d4961e}.es-les .tier.t3{border-top:6px solid #8d63e6}
.es-les .tier .tb{align-self:flex-start;font-family:var(--serif);font-size:12px;letter-spacing:.04em;text-transform:uppercase;
 color:#fff;padding:5px 13px;border-radius:20px;margin-bottom:11px;font-weight:700}
.es-les .tier.t1 .tb{background:#2bae6a}.es-les .tier.t2 .tb{background:#d4961e}.es-les .tier.t3 .tb{background:#8d63e6}
.es-les .tier h3{font-size:17px;margin:0 0 3px}.es-les .tier .ta{font-size:13px;color:var(--sub);font-weight:700;margin-bottom:10px}
.es-les .tier .tr{font-size:14px;color:var(--ink-soft);line-height:1.6;margin-bottom:11px}
.es-les .tier .te{font-size:14px;color:var(--ink-soft);background:var(--bg-mist);border-radius:11px;padding:11px 13px;line-height:1.6}
.es-les .tier .te b{display:block;color:var(--ac2);font-size:11px;letter-spacing:.06em;text-transform:uppercase;margin-bottom:4px}
.es-quiz{background:var(--soft);border:2px solid var(--line2);border-radius:20px;padding:24px 22px}
.es-quiz .q{padding:18px 0;border-bottom:2px dashed var(--line2)}.es-quiz .q:last-child{border-bottom:none}
.es-quiz .qn{display:inline-block;font-family:var(--serif);font-size:13px;color:#fff;background:var(--ac);text-transform:uppercase;letter-spacing:.04em;padding:4px 12px;border-radius:20px;margin-bottom:10px}
.es-quiz .qx{font-size:18px;color:var(--ink);font-weight:700;margin:0 0 13px;line-height:1.5}
.es-opt{display:block;width:100%;text-align:left;background:#fff;border:2px solid var(--line2);border-radius:13px;
 padding:12px 17px;margin-bottom:9px;font-size:17px;color:var(--ink);cursor:pointer;font-family:inherit;font-weight:600;transition:transform .12s,border-color .12s,background .12s}
.es-opt:hover:not(:disabled){border-color:var(--ac);transform:translateX(4px)}
.es-opt:disabled{cursor:default}
.es-opt.correct{background:#eafaf0;border-color:#2bae6a;color:#1c7a4a}
.es-opt.wrong{background:#ffeeec;border-color:#ef6253;color:#b23b2f}
.es-opt.correct::after{content:"  🎉"}.es-opt.wrong::after{content:"  💡"}
.es-expl{display:none;margin-top:11px;padding:13px 17px;background:#fff;border-left:5px solid var(--ac);border-radius:0 11px 11px 0;font-size:15px;color:var(--ink-soft);line-height:1.7}
.es-expl.show{display:block}.es-expl strong{color:var(--ink)}
.es-lnav{display:flex;justify-content:space-between;gap:13px;margin-top:42px;flex-wrap:wrap}
.es-lnav a{font-family:var(--serif);font-weight:700;color:var(--ac2);background:var(--soft);border:2px solid var(--line2);border-radius:30px;padding:10px 18px;transition:transform .15s}
.es-lnav a:hover{transform:translateY(-2px);color:var(--ac2)}
.es-thanks{text-align:center;margin:48px 0 6px;padding:26px;background:linear-gradient(135deg,#fbf1d8,#f7e7ef 60%,#e4f3ee);border-radius:20px;border:2px solid #efd9b8}
.es-thanks b{font-family:var(--serif);font-size:21px;color:#9a5a12;display:block;margin-bottom:5px}
.es-thanks p{font-size:15px;color:#6b5230;margin:0}
/* two-card learn hub */
.es-learn{display:grid;gap:18px;margin:34px 0}
@media(min-width:760px){.es-learn{grid-template-columns:1fr 1fr}}
.es-lc{display:flex;flex-direction:column;background:#fff;border:2px solid var(--line);border-radius:20px;
 padding:26px 26px 24px;box-shadow:var(--shadow);overflow:hidden;position:relative;transition:transform .25s,box-shadow .25s}
.es-lc::before{content:"";position:absolute;inset:0 0 auto 0;height:8px;background:var(--cc)}
.es-lc:hover{transform:translateY(-6px);box-shadow:var(--shadow-hover)}
.es-lc .ic{width:62px;height:62px;border-radius:18px;background:var(--ccs);display:flex;align-items:center;justify-content:center;font-size:32px;margin-bottom:14px}
.es-lc h3{font-size:21px;margin:0 0 4px;color:var(--ink)}
.es-lc .en{font-family:var(--serif);font-size:14px;letter-spacing:.06em;color:var(--ccd);font-weight:700;margin-bottom:10px}
.es-lc p{font-size:15px;color:var(--ink-soft);line-height:1.75;margin:0 0 auto}
.es-lc .go{font-family:var(--serif);font-weight:700;color:var(--ccd);margin-top:16px}
</style>"""

ES_SCRIPT = """<script>
(function(){
 function pick(){var v=speechSynthesis.getVoices()||[];return v.filter(function(x){return/en[-_]US/i.test(x.lang)})[0]||v.filter(function(x){return/^en/i.test(x.lang)})[0]||null;}
 var bs=document.querySelectorAll('.es-say,.es-sayl');
 if(bs.length&&'speechSynthesis'in window){try{speechSynthesis.onvoiceschanged=function(){};}catch(e){}
  bs.forEach(function(b){b.addEventListener('click',function(e){e.preventDefault();e.stopPropagation();
   var t=b.getAttribute('data-say');if(!t)return;speechSynthesis.cancel();
   var u=new SpeechSynthesisUtterance(t);u.lang='en-US';u.rate=.86;var vc=pick();if(vc)u.voice=vc;
   document.querySelectorAll('.es-say.on,.es-sayl.on').forEach(function(o){o.classList.remove('on');});
   b.classList.add('on');u.onend=function(){b.classList.remove('on');};u.onerror=function(){b.classList.remove('on');};
   speechSynthesis.speak(u);});});}
 document.querySelectorAll('.es-quiz .q').forEach(function(q){
  var ci=parseInt(q.dataset.correct,10),opts=q.querySelectorAll('.es-opt'),ex=q.querySelector('.es-expl');
  opts.forEach(function(btn,idx){btn.addEventListener('click',function(){
   if(q.dataset.done)return;q.dataset.done='1';opts.forEach(function(b){b.disabled=true;});
   if(idx===ci){btn.classList.add('correct');}else{btn.classList.add('wrong');opts[ci].classList.add('correct');}
   if(ex)ex.classList.add('show');});});});
})();
</script>"""

def es_say(t,inline=False):
    return '<button class="es-say%s" data-say="%s" aria-label="聽發音">🔊</button>'%(
        'l' if False else '',esc(t)) if not inline else \
        '<button class="es-sayl" data-say="%s" aria-label="聽發音">🔊</button>'%esc(t)

def build_learn(o):
    hero=band(crumb_html(o),"RU-YI LEARNING","學習園地",
        "如意精舍為孩子預備的兩種學習機會：每週四的英語課（融入佛法），以及寒暑假的兒童夏令營。"
        "歡迎家長帶著孩子一起來學習、成長。")
    es=u("/english-school/"); cp=u("/camps/")
    cards=('<div class="es-learn">'
      '<a class="es-lc" style="--cc:#ef7d2e;--ccs:#fff0e0;--ccd:#b85a12" href="%s">'
      '<div class="ic">🍃</div><h3>如意英文學校</h3><div class="en">RU-YI ENGLISH SCHOOL</div>'
      '<p>每週四的英語課，把英文學習與一顆柔軟慈悲的心結合在一起。24 週課程線上複習：'
      '單字發音、句型、故事、佛法小品與自我檢測小考。課程由 Teacher Dom 老師設計。</p>'
      '<div class="go">看 24 週課程 →</div></a>'
      '<a class="es-lc" style="--cc:#3f9d95;--ccs:#dff4ef;--ccd:#1c8273" href="%s">'
      '<div class="ic">☀️</div><h3>兒童夏令營</h3><div class="en">SUMMER CAMP</div>'
      '<p>寒暑假的兒童與青少年心靈環保成長營，在遊戲與團體生活中認識自己、學習感恩與專注。'
      '歷年活動影音紀錄都在這裡。</p><div class="go">看歷年夏令營 →</div></a>'
      '</div>')%(es,cp)
    body=hero+'<main class="tintbg"><div class="wrap"><div class="es">'+cards+'</div></div></main>'
    return page("學習園地","/learn/",ES_CSS+body,"學習園地 · 週四英語課與兒童夏令營 · 如意精舍")

def _es_qcards(ls):
    out=''
    for d in ls:
        wk=d['week'];th=ES_THEME[wk];em=ES_EMOJI[wk]
        cc={'saffron':('#ef7d2e','#fff0e0','#b85a12'),'pink':('#e85684','#ffe7ef','#b83560'),
            'jade':('#2aa996','#ddf4ef','#1c8273'),'sky':('#3f9be0','#e4f1fc','#1f72b8'),
            'coral':('#ef6253','#ffe8e4','#c43c30'),'violet':('#8d63e6','#efe7fc','#6a3fc0'),
            'gold':('#d4961e','#fbf1d6','#a76f0c')}[th]
        live='<span class="live">★ Live</span>' if wk==1 else ''
        out+=('<a class="es-card" style="--cc:%s;--ccs:%s;--ccd:%s" href="%s">%s'
              '<div class="top"><span class="emo">%s</span><div><div class="wk">Week</div><div class="wn">%d</div></div></div>'
              '<h3>%s</h3><div class="go">開始上課 →</div></a>'
              %(cc[0],cc[1],cc[2],u("/english-school/%s/"%d['id']),live,em,wk,esc(d['title_en'])))
    return out

def build_english_school(o):
    hero=band(crumb_html(o),"RU-YI ENGLISH SCHOOL","如意英文學校",
        "週四的英語課，把英文學習和一顆慈悲安定的心結合在一起。每一週都有可以聽、可以說的單字，"
        "句型、故事、佛法小品與自我檢測小考。免費提供給上課的孩子與所有想學習的人。",
        byline="課程設計 · Teacher Dom 老師")
    q1=[d for d in ES_LESSONS if d['quarter']==1]; q2=[d for d in ES_LESSONS if d['quarter']==2]
    intro=('<div class="es-intro">'
      '<div class="es-note"><span class="ic">📚</span><b>給上課的同學：</b>用這些頁面複習我們在課堂上學過的內容——'
      '點 🔊 聽每個單字的發音、再讀一次故事、做小考檢測自己。一起快樂學英文！</div>'
      '<div class="es-teacher"><div class="who"><div class="av">🌟</div>'
      '<div><span>Our Teacher</span><b>Teacher Dom</b></div></div>'
      '<p>這趟英文旅程的每一週，都是 <b>Teacher Dom 老師</b>用心設計的——把英文和一顆慈悲安定的心'
      '一起教給孩子。謝謝老師！💛</p></div></div>')
    body=[hero,'<main class="tintbg"><div class="wrap"><div class="es">',intro]
    body.append('<div class="es-qhead"><span class="es-qbadge" style="background:linear-gradient(135deg,#ef9a43,#ee6f3d)">Quarter 1 · 第 1–3 個月</span>'
                '<h2>基礎、精進與恆心 🌱</h2><div class="qs">建立心的力量與單字基礎——專注、清楚、正精進。</div></div>')
    body.append('<div class="es-grid">'+_es_qcards(q1)+'</div>')
    body.append('<div class="es-qhead"><span class="es-qbadge" style="background:linear-gradient(135deg,#ee7eb3,#8d63e6)">Quarter 2 · 第 4–7 個月</span>'
                '<h2>品格、慈悲與善語 💞</h2><div class="qs">用心說話、慈悲生活——慈、悲、喜、捨。</div></div>')
    body.append('<div class="es-grid">'+_es_qcards(q2)+'</div>')
    body.append('<div class="es-thanks"><b>✏️ 課程由 Teacher Dom 老師用心設計</b>'
                '<p>24 週的英文與佛心——為如意英文學校的孩子們而做。</p></div>')
    body.append('</div></div></main>')
    return page("如意英文學校","/learn/",ES_CSS+''.join(body),
                "如意英文學校 · 週四英語課（融入佛法）24 週線上複習 · 如意精舍")

def _es_pills(d):
    return ''.join('<span class="les-pill"></span>' for _ in [])  # pills shown in band sub instead

def build_es_lesson(d, prev_d, next_d):
    wk=d['week'];th=ES_THEME[wk];em=ES_EMOJI[wk]
    o="/english-school/%s/"%d['id']
    sub=' · '.join([p['label']+'：'+p['text'] for p in d['pills']])
    hero=band(crumb_html(o),"%s  Week %d"%(("Quarter 1" if d['quarter']==1 else "Quarter 2"),wk),
              d['title_en'], d['title_zh'], byline=sub)
    B=['<main class="tintbg"><div class="wrap"><div class="es-les es t-%s">'%th]
    # overview / objectives
    objs=''
    for ob in d['objectives']:
        em2,zh=ES_QLABEL.get(ob['kind'],('•',ob['zh']))
        zt='<p class="zh-trans">%s</p>'%ob['zh_html'] if ob.get('zh_html') else ''
        objs+='<div class="obj %s"><h3>%s %s</h3><div class="ozh">%s</div><p>%s</p>%s</div>'%(
            ob['kind'], em2,esc(ob['h3']),esc(ob['zh'] or zh),ob['html'],zt)
    B.append('<section class="sec"><div class="sh"><h2>本週重點</h2><span class="tag">Overview</span></div>'
             '<div class="obj2">%s</div></section>'%objs)
    # vocab
    rows=''
    for v in d['vocab']:
        rows+=('<tr><td><span class="vw">%s</span><span class="vp">%s</span></td>'
               '<td class="vz">%s</td><td><button class="es-say" data-say="%s" aria-label="聽發音">🔊</button></td></tr>'
               %(esc(v['word']),esc(v['pos']),esc(v['zh']),esc(v['say'])))
    B.append('<section class="sec"><div class="sh"><h2>單字 Vocabulary</h2><span class="tag">點 🔊 聽發音</span></div>'
             '<p class="note">聽、跟著念、大聲說三次。</p><table class="vt">%s</table></section>'%rows)
    # patterns
    pats=''
    for p in d['patterns']:
        exs=''
        for ex in p['examples']:
            ez='<span class="ex-zh">%s</span>'%esc(ex['zh']) if ex.get('zh') else ''
            exs+='<p class="ex">%s <button class="es-sayl" data-say="%s" aria-label="聽發音">🔊</button>%s</p>'%(ex['html'],esc(ex['say']),ez)
        pats+='<div class="pat"><span class="pl">%s</span><div class="pf">%s</div>%s</div>'%(
            esc(p['label']),esc(p['formula']),exs)
    if d.get('grammar'):
        gz='<p class="zh-trans">%s</p>'%d['grammar']['zh_html'] if d['grammar'].get('zh_html') else ''
        pats+='<div class="gram"><h4>✏️ %s</h4><p>%s</p>%s</div>'%(esc(d['grammar']['h4']),d['grammar']['html'],gz)
    B.append('<section class="sec"><div class="sh"><h2>句型 Sentence Patterns</h2><span class="tag">Key Patterns</span></div>%s</section>'%pats)
    # story
    st=d['story']
    sh=''
    if st.get('img'):
        sh+='<figure class="fig"><img loading="lazy" src="%s" alt=""><figcaption>%s</figcaption></figure>'%(
            u("/english-school/assets/"+st['img']),esc(st.get('figcaption') or ''))
    pz=st.get('paras_zh') or []
    sp=''
    for i,pp in enumerate(st['paras']):
        sp+='<p>%s</p>'%pp
        if i<len(pz) and pz[i]: sp+='<p class="zh-trans">%s</p>'%pz[i]
    sh+='<div class="story">'+sp+'</div>'
    if st.get('qcheck'):
        sh+='<div class="qcheck"><h4>🤔 %s</h4><ul>%s</ul></div>'%(
            esc(st['qcheck']['h4']),''.join('<li>%s</li>'%it for it in st['qcheck']['items']))
    B.append('<section class="sec"><div class="sh"><h2>故事 The Story</h2><span class="tag">Story</span></div>%s</section>'%sh)
    # principle
    pr=d['principle']
    ph=''
    if pr.get('lede'):
        ph+='<p class="lede">%s</p>'%pr['lede']
        if pr.get('lede_zh'): ph+='<p class="zh-trans">%s</p>'%pr['lede_zh']
    if pr.get('video'):
        ph+=('<div class="vid"><video controls preload="metadata"><source src="%s" type="video/mp4">'
             '您的瀏覽器不支援影片播放。</video></div>'%u("/english-school/assets/"+pr['video']))
    if pr.get('h4'):
        pzt='<p class="zh-trans">%s</p>'%pr['zh_html'] if pr.get('zh_html') else ''
        ph+='<div class="pbox"><h4>🌟 %s</h4><p>%s</p>%s</div>'%(esc(pr['h4']),pr['html'],pzt)
    if ph:
        B.append('<section class="sec"><div class="sh"><h2>佛法小品 The Principle</h2><span class="tag">Principle</span></div>%s</section>'%ph)
    # practice
    pc=d['practice']
    if pc['tiers']:
        tiers=''
        for t in pc['tiers']:
            rz='<div class="tr-zh">%s</div>'%t['req_zh'] if t.get('req_zh') else ''
            tiers+=('<div class="tier %s"><span class="tb">%s</span><h3>%s</h3><div class="ta">%s</div>'
                    '<div class="tr">%s</div>%s<div class="te">%s</div></div>'%(
                        t['tier'],esc(t['badge']),esc(t['h3']),esc(t['age']),t['req'],rz,t['ex']))
        B.append('<section class="sec"><div class="sh"><h2>練習 Practice</h2><span class="tag">Homework</span></div>'
                 '<p class="note">%s</p><div class="tiers">%s</div></section>'%(pc.get('note') or '',tiers))
    # quiz
    qs=''
    for q in d['quiz']:
        opts=''.join('<button class="es-opt">%s</button>'%esc(op) for op in q['options'])
        qs+=('<div class="q" data-correct="%d"><span class="qn">%s</span><div class="qx">%s</div>%s'
             '<div class="es-expl">%s</div></div>'%(q['correct'],esc(q['num']),esc(q['text']),opts,q['expl']))
    B.append('<section class="sec"><div class="sh"><h2>小考 Mini Quiz</h2><span class="tag">Check Yourself</span></div>'
             '<p class="note">選出最適合的答案，點選後會看到解析。</p><div class="es-quiz">%s</div></section>'%qs)
    # lesson nav
    nav='<div class="es-lnav"><a href="%s">← 所有課程</a>'%u("/english-school/")
    if next_d: nav+='<a href="%s">Week %d：%s →</a>'%(u("/english-school/%s/"%next_d['id']),next_d['week'],esc(next_d['title_en']))
    nav+='</div>'
    B.append(nav)
    B.append('</div></div></main>')
    return page(d['title_en'],"/learn/",ES_CSS+hero+''.join(B)+ES_SCRIPT,
                "如意英文學校 第 %d 週 · %s · 如意精舍"%(wk,d['title_en']))


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
    canon=SITE_URL+(o if o!="/" else "/")
    seo=('<link rel="canonical" href="%s"><meta property="og:url" content="%s">'%(canon,canon))
    htmltext=htmltext.replace("<!--CANON-->",seo)
    rel=o.strip("/")
    d=os.path.join(ROOT,rel) if rel else ROOT
    os.makedirs(d,exist_ok=True)
    open(os.path.join(d,"index.html"),"w").write(htmltext)
    if 'http-equiv="refresh"' not in htmltext:   # 不收錄轉址頁
        _index_page(o,htmltext)

if __name__=="__main__":
    n=0
    write("/",build_home()); n+=1
    for o in sorted(out2path):
        if o=="/": continue
        if o in REDIRECTS:   # 舊系列首頁 → 合併頁
            write(o,redirect_html(REDIRECTS[o],EXTRA_NAMES.get(o,""))); n+=1; continue
        if o=="/column/" or (o.startswith("/column/") and children.get(o)):
            write(o,build_column(o))
        elif o.startswith("/column/"):
            write(o,build_column_article(o))
        elif o=="/study-group/":
            write(o,build_study_group(o))
        elif o.startswith("/study-group/") and children.get(o):
            write(o,build_study_series(o))
        elif (o.startswith("/study-group/") and o.strip("/").count("/")==1
              and yt_count(o)>=2 and not AUDIO.get(o)):
            # 僅頂層的影音講次系列（八識規矩頌、心經）：整頁就是一支支 YouTube；
            # 不可套用到底下含文字內容的單篇講次頁（如 Buddhism101/B01 提問），
            # 否則會吃掉內文。
            write(o,build_study_video_series(o))
        elif o.startswith("/study-group/"):
            write(o,build_study_chapter(o))
        elif o=="/bhikkhuni/":
            write(o,build_bhikkhuni(o))
        elif o=="/news/":
            write(o,build_news(o))
        elif o=="/videos/":
            write(o,build_videos(o))
        elif o.startswith("/videos/") and not children.get(o):
            write(o,build_video_wall(o,"/videos/","影音分類"))
        elif o=="/camps/":
            write(o,build_camps(o))
        elif o.startswith("/camps/") and not children.get(o):
            write(o,build_video_wall(o,"/learn/","夏令營 · 活動紀錄"))
        else:
            write(o,build_page(o))
        n+=1
    # 合併頁（不在 omap 內，手動產生）
    for c in COMBINED:
        write(c["out"],build_prajna(c)); n+=1
    # 2026 青少年學佛營 + 兒童學佛營（不在 omap 內，手動產生）
    write("/camps/2026/",build_camp_2026("/camps/2026/")); n+=1
    write("/camps/2026-kids/",build_camp_kids_2026("/camps/2026-kids/")); n+=1
    write("/camps/2026-kids/teaching/",build_kids26_teaching("/camps/2026-kids/teaching/")); n+=1
    write("/camps/2026-kids/teaching/brave-no-game/",build_kids26_brave_no_game("/camps/2026-kids/teaching/brave-no-game/")); n+=1
    # 學習園地 + 如意英文學校（不在 omap 內，手動產生）
    write("/learn/",build_learn("/learn/")); n+=1
    write("/english-school/",build_english_school("/english-school/")); n+=1
    for i,_d in enumerate(ES_LESSONS):
        _prev=ES_LESSONS[i-1] if i>0 else None
        _next=ES_LESSONS[i+1] if i<len(ES_LESSONS)-1 else None
        write("/english-school/%s/"%_d["id"],build_es_lesson(_d,_prev,_next)); n+=1
    # 手工頁登記：讀取既有 built HTML 納入全站搜尋索引，不重新產生／不覆寫內容
    for _o in HANDMADE_PAGES:
        _p=os.path.join(ROOT,_o.strip("/"),"index.html")
        if os.path.exists(_p):
            _index_page(_o,open(_p).read())
        else:
            print("WARNING: handmade page missing on disk, skipped:",_o)
    # CNAME + nojekyll
    open(os.path.join(ROOT,".nojekyll"),"w").write("")
    # sitemap.xml (all pages) + robots.txt — for Google 收錄
    # 收錄合併頁、排除已轉址的舊系列首頁
    urls=["/"]+sorted([o for o in out2path if o!="/" and o not in REDIRECTS]
                      +[c["out"] for c in COMBINED]
                      +["/learn/","/english-school/","/camps/2026/","/camps/2026-kids/",
                        "/camps/2026-kids/teaching/","/camps/2026-kids/teaching/brave-no-game/"]
                      +["/english-school/%s/"%d["id"] for d in ES_LESSONS]
                      +HANDMADE_PAGES)
    sm=['<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for o in urls:
        pr="1.0" if o=="/" else ("0.8" if o.count("/")<=2 else "0.6")
        sm.append("<url><loc>%s%s</loc><priority>%s</priority></url>"%(SITE_URL,o if o!="/" else "/",pr))
    sm.append("</urlset>")
    open(os.path.join(ROOT,"sitemap.xml"),"w").write("\n".join(sm))
    open(os.path.join(ROOT,"robots.txt"),"w").write(
        "User-agent: *\nAllow: /\nSitemap: %s/sitemap.xml\n"%SITE_URL)
    # 全站搜尋索引
    seen=set(); idx=[]
    for e in SEARCH_INDEX:
        if e["url"] in seen or "backup" in e["url"]: continue
        seen.add(e["url"]); idx.append(e)
    idx.sort(key=lambda e:e["url"])
    json.dump(idx,open(os.path.join(ROOT,"search.json"),"w"),
              ensure_ascii=False,separators=(",",":"))
    print("built %d pages + sitemap(%d urls) + robots + search(%d)"%(n,len(urls),len(idx)))
