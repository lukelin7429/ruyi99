#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把「大智度論 · 逐字精讀」網頁與小考題庫回寫成 Markdown，存進 Obsidian vault。

用途：網站是呈現層，Obsidian 是總資料庫。每次發布精讀頁或更新小考之後執行本腳本，
      vault 就會有一份與線上完全一致的純文字鏡射，不需要人工抄寫，因此不會漂移。
      與 sync_precepts_to_obsidian.py 同一套做法，只是來源目錄與輸出檔名不同。

用法：
    python3 scripts/sync_dzdl_to_obsidian.py            # 同步全部講次＋小考
    python3 scripts/sync_dzdl_to_obsidian.py 061-01     # 只同步指定講次
"""
import html
import os
import re
import sys
from datetime import date

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEEP = os.path.join(REPO, "study-group", "perfection-of-wisdom", "deep")
QUIZ = os.path.join(REPO, "study-group", "perfection-of-wisdom", "quiz", "quiz-data.js")
VAULT = os.path.expanduser(
    "~/Library/Mobile Documents/iCloud~md~obsidian/Documents/第二大腦"
    "/知識庫/佛法/大智度論/逐字精讀（網站鏡射）"
)
SITE = "https://ruyi99.org"
BASE = "/study-group/perfection-of-wisdom/deep/"


def unwrap(s):
    """行內標籤轉 Markdown。"""
    s = re.sub(r"(?is)<br\s*/?>", "　", s)
    s = re.sub(r"(?is)<(strong|b)>(.*?)</\1>", lambda m: "**" + m.group(2).strip() + "**", s)
    s = re.sub(r"(?is)<em>(.*?)</em>", r"*\1*", s)
    s = re.sub(r"(?is)<a [^>]*href=\"([^\"]+)\"[^>]*>(.*?)</a>", r"[\2](\1)", s)
    s = re.sub(r"(?s)<[^>]+>", "", s)
    s = html.unescape(s)
    return re.sub(r"[ \t]+", " ", s).strip()


DIV_CLASSES = ("quote-box", "sutra", "flow", "map-grid", "matrix", "speakers", "recap-box",
               "tree", "prog", "srcnote", "nextprev", "warn")
TAGS = ("h2", "h3", "p", "table", "ol", "ul")


def div_inner(s, open_end):
    """從 <div ...> 的結尾位置起，用深度計數找出對應的 </div>，回傳 (inner, end)。

    不能用 <div...>(.*?)</div> 這種非貪婪比對——巢狀的 div（例如 .flow > .flow-row > .box）
    會在第一個 </div> 就收尾，整塊內容被吃掉。
    """
    depth, i = 1, open_end
    while depth:
        m = re.compile(r"(?i)<(/?)div\b[^>]*>").search(s, i)
        if not m:
            return s[open_end:], len(s)
        depth += -1 if m.group(1) else 1
        i = m.end()
        if not depth:
            return s[open_end:m.start()], i
    return s[open_end:], len(s)


def cards(inner, cls, bullet="- "):
    out, i = [], 0
    pat = re.compile(r"(?is)<div class=\"%s\"[^>]*>" % cls)
    while True:
        m = pat.search(inner, i)
        if not m:
            break
        cin, i = div_inner(inner, m.end())
        out.append(bullet + unwrap(cin))
    return out


def blocks(frag):
    """把 guide-main 的內容依序轉成 Markdown 區塊。"""
    out, pos = [], 0
    nxt = re.compile(
        r"(?is)<(?:(h2|h3|p|table|ol|ul)\b[^>]*>|div class=\"(%s)\"[^>]*>)" % "|".join(DIV_CLASSES)
    )
    while True:
        m = nxt.search(frag, pos)
        if not m:
            break
        tag, dcls = m.group(1), m.group(2)
        if tag:
            close = re.compile(r"(?is)</%s>" % tag).search(frag, m.end())
            if not close:
                break
            inner, pos = frag[m.end():close.start()], close.end()
        else:
            inner, pos = div_inner(frag, m.end())

        if tag in ("h2", "h3"):
            out.append(("### " if tag == "h2" else "#### ") + unwrap(inner))
        elif tag == "p":
            t = unwrap(inner)
            if t:
                out.append(t)
        elif tag == "table":
            rows = re.findall(r"(?is)<tr[^>]*>(.*?)</tr>", inner)
            md = []
            for i, r in enumerate(rows):
                cells = [unwrap(c) for c in re.findall(r"(?is)<t[hd][^>]*>(.*?)</t[hd]>", r)]
                md.append("| " + " | ".join(cells) + " |")
                if i == 0:
                    md.append("|" + "---|" * len(cells))
            out.append("\n".join(md))
        elif tag in ("ol", "ul"):
            items = re.findall(r"(?is)<li[^>]*>(.*?)</li>", inner)
            mark = (lambda i: "%d. " % (i + 1)) if tag == "ol" else (lambda i: "- ")
            out.append("\n".join(mark(i) + unwrap(x) for i, x in enumerate(items)))
        elif dcls == "quote-box":
            out.append("> " + unwrap(inner).replace("　", "\n> "))
        elif dcls == "sutra":
            # 經論引文：<span class="who">說者</span> 內文
            who = re.search(r"(?is)<span class=\"who\">(.*?)</span>", inner)
            body = unwrap(re.sub(r"(?is)<span class=\"who\">.*?</span>", "", inner))
            head = ("**〔%s〕**\n> " % unwrap(who.group(1))) if who else ""
            out.append("> " + head + body.replace("　", "\n> "))
        elif dcls == "prog":
            done = len(re.findall(r'class="done"', inner))
            total = len(re.findall(r"<i", inner))
            out.append("**進度**：%d／%d 講" % (done, total))
        elif dcls == "flow":
            rows, i = [], 0
            while True:
                mm = re.compile(r"(?is)<div class=\"flow-row\"[^>]*>").search(inner, i)
                if not mm:
                    break
                rin, i = div_inner(inner, mm.end())
                boxes = []
                j = 0
                while True:
                    bm = re.compile(r"(?is)<div class=\"box\"[^>]*>").search(rin, j)
                    if not bm:
                        break
                    bin_, j = div_inner(rin, bm.end())
                    sm = re.search(r"(?is)<small>(.*?)</small>", bin_)
                    head = unwrap(re.sub(r"(?is)<small>.*?</small>", "", bin_))
                    boxes.append(head + ("（%s）" % unwrap(sm.group(1)) if sm else ""))
                if boxes:
                    rows.append("　→　".join(boxes))
            if rows:
                out.append("\n\n↓\n\n".join(rows))
        elif dcls == "map-grid":
            out += ["\n".join(cards(inner, "map-card"))] if cards(inner, "map-card") else []
        elif dcls == "matrix":
            out += ["\n".join(cards(inner, "cell"))] if cards(inner, "cell") else []
        elif dcls == "speakers":
            items, i = [], 0
            pat = re.compile(r"(?is)<div class=\"spk\"[^>]*>")
            while True:
                mm = pat.search(inner, i)
                if not mm:
                    break
                cin, i = div_inner(inner, mm.end())
                b = re.search(r"(?is)<b>(.*?)</b>", cin)
                em = re.search(r"(?is)<em>(.*?)</em>", cin)
                pp = re.search(r"(?is)<p>(.*?)</p>", cin)
                items.append("- **%s**%s：%s" % (
                    unwrap(b.group(1)) if b else "",
                    "（%s）" % unwrap(em.group(1)) if em else "",
                    unwrap(pp.group(1)) if pp else ""))
            if items:
                out.append("\n".join(items))
        elif dcls == "recap-box":
            items = re.findall(r"(?is)<li[^>]*>(.*?)</li>", inner)
            lead = unwrap(re.sub(r"(?is)<ol.*?</ol>", "", inner))
            body = "\n".join("%d. %s" % (i + 1, unwrap(x)) for i, x in enumerate(items))
            out.append((lead + "\n\n" if lead else "") + body)
        elif dcls == "tree":
            # 依 <ul> 巢狀深度縮排，否則整棵樹會被壓平成一層
            depth, lines = 0, []
            for m2 in re.finditer(r"(?is)<(/?)(ul|li)\b[^>]*>", inner):
                if m2.group(2) == "ul":
                    depth += -1 if m2.group(1) else 1
                elif m2.group(2) == "li" and not m2.group(1):
                    nxt2 = re.compile(r"(?is)<ul|</li>").search(inner, m2.end())
                    txt2 = unwrap(inner[m2.end():nxt2.start() if nxt2 else len(inner)])
                    if txt2:
                        lines.append("  " * max(depth - 1, 0) + "- " + txt2)
            if lines:
                out.append("\n".join(lines))
        elif dcls == "srcnote":
            out.append("> [!info]\n> " + unwrap(inner))
        elif dcls == "warn":
            out.append("> [!warning]\n> " + unwrap(inner))
        elif dcls == "nextprev":
            links = re.findall(r"(?is)<a [^>]*href=\"([^\"]+)\"[^>]*>(.*?)</a>", inner)
            out.append(" ｜ ".join("[%s](%s%s)" % (unwrap(t), SITE, u) for u, t in links))
    return [b for b in out if b]


def sync_page(slug):
    path = os.path.join(DEEP, slug, "index.html") if slug != "index" else os.path.join(DEEP, "index.html")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        s = f.read()
    h1 = unwrap(re.search(r"(?is)<h1>(.*?)</h1>", s).group(1))
    sub = unwrap(re.search(r"(?is)<p class=\"sub\">(.*?)</p>", s).group(1))
    eyebrow = unwrap(re.search(r"(?is)<div class=\"eyebrow\">(.*?)</div>", s).group(1))
    i = s.find('<div class="guide-main">')
    body = s[i + len('<div class="guide-main">'):s.find("</main>")]
    url = SITE + BASE + ("" if slug == "index" else slug + "/")
    name = "卷61 逐字精讀總覽（網站鏡射）" if slug == "index" else \
           "卷%s 第%s講 %s（精讀·網站鏡射）" % (slug[:3], slug[4:].lstrip("0"), h1)

    md = [
        "---",
        f'title: "{name}"',
        f'source: "{url}"',
        'author: "釋厚觀主編《大智度論講義》（第09期）為底本"',
        f"created: {date.today().isoformat()}",
        f'description: "{sub[:150]}"',
        "tags:",
        '  - "佛法"',
        '  - "大智度論"',
        '  - "般若"',
        '  - "隨喜迴向品"',
        '  - "備課"',
        '  - "網站鏡射"',
        "---",
        "",
        "> [!abstract] 自動產生，請勿在此編輯",
        "> 本檔由 `scripts/sync_dzdl_to_obsidian.py` 從網站頁面自動轉出，每次網站更新後重新產生，改這裡不會生效。",
        f"> 線上版本：{url}",
        "> 備課原料：[[大智度論——卷61]]　／　地圖：[[大智度論——卷61——結構大綱]]",
        "",
        f"# {h1}",
        "",
        f"*{eyebrow}*",
        "",
        sub,
        "",
        "---",
        "",
    ]
    md += [b + "\n" for b in blocks(body)]
    os.makedirs(VAULT, exist_ok=True)
    out = os.path.join(VAULT, name + ".md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(md).rstrip() + "\n")
    return out


def sync_quiz():
    if not os.path.exists(QUIZ):
        return None
    with open(QUIZ, encoding="utf-8") as f:
        js = f.read()
    url = SITE + "/study-group/perfection-of-wisdom/quiz/"
    md = [
        "---",
        'title: "大智度論 小考題庫（網站鏡射）"',
        f'source: "{url}"',
        f"created: {date.today().isoformat()}",
        'description: "逐字精讀小考全部回合的題目、正解與解析"',
        "tags:",
        '  - "佛法"',
        '  - "大智度論"',
        '  - "小考"',
        '  - "網站鏡射"',
        "---",
        "",
        "> [!abstract] 自動產生，請勿在此編輯",
        "> 由 `scripts/sync_dzdl_to_obsidian.py` 從 `quiz-data.js` 轉出。",
        f"> 線上作答：{url}",
        "",
        "# 大智度論　逐字精讀小考題庫",
        "",
    ]
    rounds = re.findall(
        r"(?s)\{\s*id:\s*\"[^\"]*\",\s*title:\s*\"([^\"]*)\",\s*range:\s*\"([^\"]*)\",\s*theme:\s*\"([^\"]*)\",\s*questions:\s*\[(.*?)\]\s*\}",
        js,
    )
    for title, rng, theme, qs in rounds:
        md += [f"## {title}　{theme}", f"**範圍**：{rng}", ""]
        for n, q in enumerate(re.findall(r"(?s)\{\s*type:(.*?)\}\s*(?:,|$)", qs), 1):
            typ = re.search(r'^\s*"(\w+)"', q).group(1)
            stem = re.search(r'q:\s*"((?:[^"\\]|\\.)*)"', q).group(1)
            exp = re.search(r'explain:\s*"((?:[^"\\]|\\.)*)"', q)
            src = re.search(r'source:\s*"((?:[^"\\]|\\.)*)"', q)
            md.append(f"**{n}.（{'單選' if typ == 'choice' else '是非'}）** {stem}")
            if typ == "choice":
                opts = re.findall(r'"((?:[^"\\]|\\.)*)"', re.search(r"options:\s*\[(.*?)\]", q).group(1))
                ans = int(re.search(r"answer:\s*(\d+)", q).group(1))
                for k, o in enumerate(opts):
                    md.append(f"- {'**(正解) ' if k == ans else ''}{chr(65+k)}. {o}{'**' if k == ans else ''}")
            else:
                ans = re.search(r"answer:\s*(true|false)", q).group(1)
                md.append(f"- **正解：{'○ 對' if ans == 'true' else '✗ 錯'}**")
            if exp:
                md.append(f"> 解析：{exp.group(1)}" + (f"（{src.group(1)}）" if src else ""))
            md.append("")
    os.makedirs(VAULT, exist_ok=True)
    out = os.path.join(VAULT, "小考題庫.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(md).rstrip() + "\n")
    return out


if __name__ == "__main__":
    slugs = sys.argv[1:] or ["index"] + sorted(
        d for d in os.listdir(DEEP) if re.fullmatch(r"\d{3}-\d{2}", d)
    )
    for s in slugs:
        r = sync_page(s)
        print(("✓ " + r) if r else f"✗ 找不到 deep/{s}/")
    q = sync_quiz()
    print(("✓ " + q) if q else "✗ 找不到 quiz-data.js")
