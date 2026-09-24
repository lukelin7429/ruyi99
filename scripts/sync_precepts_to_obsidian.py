#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把「梵網經菩薩戒 · 逐條精讀」網頁與小考題庫回寫成 Markdown，存進 Obsidian vault。

用途：網站是呈現層，Obsidian 是總資料庫。每次發布精讀頁或更新小考之後執行本腳本，
      vault 就會有一份與線上完全一致的純文字鏡射，不需要人工抄寫，因此不會漂移。

用法：
    python3 scripts/sync_precepts_to_obsidian.py          # 同步全部
    python3 scripts/sync_precepts_to_obsidian.py 01 02    # 只同步指定戒條
"""
import html
import os
import re
import sys
from datetime import date

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VAULT = os.path.expanduser(
    "~/Library/Mobile Documents/iCloud~md~obsidian/Documents/第二大腦"
    "/知識庫/佛法/梵網經菩薩戒/演培法師講記"
)
SITE = "https://ruyi99.org"


def unwrap(s):
    """行內標籤轉 Markdown。"""
    s = re.sub(r"(?is)<br\s*/?>", "　", s)
    s = re.sub(r"(?is)<(strong|b)>(.*?)</\1>", lambda m: "**" + m.group(2).strip() + "**", s)
    s = re.sub(r"(?is)<em>(.*?)</em>", r"*\1*", s)
    s = re.sub(r"(?is)<a [^>]*href=\"([^\"]+)\"[^>]*>(.*?)</a>", r"[\2](\1)", s)
    s = re.sub(r"(?s)<[^>]+>", "", s)
    s = html.unescape(s)
    return re.sub(r"[ \t]+", " ", s).strip()


DIV_CLASSES = ("quote-box", "flow", "map-grid", "matrix", "warn", "term-list", "nextprev")
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
            out.append("> " + unwrap(inner))
        elif dcls == "flow":
            rows = []
            i = 0
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
        elif dcls in ("map-grid", "matrix"):
            cls = "map-card" if dcls == "map-grid" else "cell"
            items, i = [], 0
            while True:
                cm = re.compile(r"(?is)<div class=\"%s\"[^>]*>" % cls).search(inner, i)
                if not cm:
                    break
                cin, i = div_inner(inner, cm.end())
                items.append("- " + unwrap(cin))
            if items:
                out.append("\n".join(items))
        elif dcls == "warn":
            out.append("> [!warning]\n> " + unwrap(inner))
        elif dcls == "term-list":
            out.append("、".join(unwrap(t) for t in re.findall(r"(?is)<span>(.*?)</span>", inner)))
        elif dcls == "nextprev":
            links = re.findall(r"(?is)<a [^>]*href=\"([^\"]+)\"[^>]*>(.*?)</a>", inner)
            out.append(" ｜ ".join("[%s](%s%s)" % (unwrap(t), SITE, u) for u, t in links))
    return [b for b in out if b]


def sync_guide(num):
    path = os.path.join(REPO, "study-group", "precepts", "deep", num, "index.html")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        s = f.read()
    h1 = unwrap(re.search(r"(?is)<h1>(.*?)</h1>", s).group(1))
    sub = unwrap(re.search(r"(?is)<p class=\"sub\">(.*?)</p>", s).group(1))
    i = s.find('<div class="guide-main">')
    body = s[i + len('<div class="guide-main">'):s.find("</main>")]
    url = f"{SITE}/study-group/precepts/deep/{num}/"

    md = [
        "---",
        f'title: "輕戒{num} {h1}｜精讀（網站鏡射）"',
        f'source: "{url}"',
        'author: "演培法師（講記底本）"',
        f"created: {date.today().isoformat()}",
        f'description: "{sub[:120]}"',
        "tags:",
        '  - "佛法"',
        '  - "菩薩戒"',
        '  - "梵網經"',
        '  - "演培法師"',
        '  - "備課"',
        '  - "網站鏡射"',
        "---",
        "",
        "> [!abstract] 自動產生，請勿在此編輯",
        f"> 本檔由 `scripts/sync_precepts_to_obsidian.py` 從網站頁面自動轉出，每次網站更新後重新產生，改這裡不會生效。",
        f"> 線上版本：{url}",
        f"> 逐字轉錄原料：[[輕戒{num} {h1}]]",
        "",
        f"# 輕戒{num}　{h1}",
        "",
        sub,
        "",
        "---",
        "",
    ]
    md += [b + "\n" for b in blocks(body)]
    out = os.path.join(VAULT, f"輕戒{num} {h1}（精讀）.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(md).rstrip() + "\n")
    return out


def sync_quiz():
    path = os.path.join(REPO, "study-group", "precepts", "quiz", "quiz-data.js")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        js = f.read()
    url = f"{SITE}/study-group/precepts/quiz/"
    md = [
        "---",
        'title: "梵網經菩薩戒 小考題庫（網站鏡射）"',
        f'source: "{url}"',
        f"created: {date.today().isoformat()}",
        'description: "讀書會小考全部回合的題目、正解與解析"',
        "tags:",
        '  - "佛法"',
        '  - "菩薩戒"',
        '  - "梵網經"',
        '  - "小考"',
        '  - "網站鏡射"',
        "---",
        "",
        "> [!abstract] 自動產生，請勿在此編輯",
        "> 由 `scripts/sync_precepts_to_obsidian.py` 從 `quiz-data.js` 轉出。",
        f"> 線上作答：{url}",
        "",
        "# 梵網經菩薩戒　小考題庫",
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
    out = os.path.join(VAULT, "小考題庫.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(md).rstrip() + "\n")
    return out


if __name__ == "__main__":
    os.makedirs(VAULT, exist_ok=True)
    nums = sys.argv[1:] or sorted(
        d for d in os.listdir(os.path.join(REPO, "study-group", "precepts", "deep"))
        if d.isdigit()
    )
    for n in nums:
        r = sync_guide(n)
        print(("✓ " + r) if r else f"✗ 找不到 deep/{n}/")
    q = sync_quiz()
    print(("✓ " + q) if q else "✗ 找不到 quiz-data.js")
