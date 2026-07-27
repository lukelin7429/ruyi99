#!/usr/bin/env python3
"""新增一筆讀書會錄音：自動插入子頁 audlist 按鈕、同步子頁與總覽頁的集數統計。

用法：
    python3 scripts/add_study_group_recording.py <category> <R2 audio URL>

例：
    python3 scripts/add_study_group_recording.py perfection-of-wisdom \
        "https://pub-5ad2341e8b004b218d2fb35c9dc311b8.r2.dev/perfection-of-wisdom/20260727%E5%A4%A7%E6%99%BA%E5%BA%A6%E8%AB%96356.m4a"

只處理已經migrate到 R2 直連（data-audio-src）的分類子頁。若該分類子頁還在用
Google Drive 內嵌（data-drive，見 data/audio.json + build.py 的 render_audio），
本工具會拒絕執行——那條路線走 ruyi99-study-group-audio-sync 排程流程，不要用這支手動改。

集數一律用「實際算出來的按鈕數」寫回子頁與總覽頁，不用人工加一，
避免像 2026-07-27 那次漏改總覽頁卡片數字、外層跟內頁對不上的狀況再發生。
"""
import re
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FILENAME_RE = re.compile(r"^(\d{8})(.+?)(\d{3})\.(m4a|aac|mp3)$")


def parse_url(url):
    path = urllib.parse.urlparse(url).path
    filename = urllib.parse.unquote(Path(path).name)
    m = FILENAME_RE.match(filename)
    if not m:
        sys.exit(f"無法解析檔名格式：{filename}（預期 YYYYMMDD<標題>NNN.副檔名）")
    date8, _title, num, _ext = m.groups()
    date = f"{date8[0:4]}/{date8[4:6]}/{date8[6:8]}"
    return num, date


def update_detail_page(category, url, num, date):
    page_path = ROOT / "study-group" / category / "index.html"
    if not page_path.exists():
        sys.exit(f"找不到子頁：{page_path}")
    html = page_path.read_text(encoding="utf-8")

    audlist_start = html.find('<div class="audlist')
    if audlist_start == -1:
        sys.exit("子頁裡找不到 <div class=\"audlist ...\">，可能這個分類還沒用錄音清單版型。")

    if 'data-drive="' in html[audlist_start:audlist_start + 2000] and 'data-audio-src="' not in html[audlist_start:audlist_start + 2000]:
        sys.exit(
            "這個分類的錄音清單還是用 data-drive（Google Drive 內嵌），不是 R2 直連。\n"
            "這支工具只處理 data-audio-src。Drive 那條路線請走 ruyi99-study-group-audio-sync 排程，不要手動改。"
        )

    button_re = re.compile(
        r'<button class="aud-item" data-audio-src="([^"]+)">'
        r'<span class="aud-play"><i></i></span>'
        r'<span class="aud-num">第\s*(\d+)\s*集</span>'
        r'<span class="aud-date">([^<]*)</span>'
        r'<span class="aud-go">收聽</span></button>'
    )
    buttons = list(button_re.finditer(html))
    if not buttons:
        sys.exit("audlist 裡沒找到任何 aud-item 按鈕，格式可能跟預期不同，改用手動編輯。")

    existing_nums = {int(m.group(2)) for m in buttons}
    new_num = int(num)
    if new_num in existing_nums:
        sys.exit(f"第 {new_num} 集已經存在於子頁裡，沒有新增（避免重複）。")

    new_button = (
        '<button class="aud-item" data-audio-src="%s">'
        '<span class="aud-play"><i></i></span>'
        '<span class="aud-num">第 %s 集</span>'
        '<span class="aud-date">%s</span>'
        '<span class="aud-go">收聽</span></button>' % (url, num, date)
    )

    # 依集數由大到小排序插入，維持現有「最新在最上面」的順序
    insert_before = None
    for m in buttons:
        if int(m.group(2)) < new_num:
            insert_before = m
            break

    if insert_before is not None:
        # 找到第一個比新集數小的按鈕，插在它前面（涵蓋最常見的「新增最新一集」情況）
        anchor = insert_before.start()
    else:
        # 新集數比現有全部都小（回補很舊的一集）：插在最後一顆按鈕後面
        anchor = buttons[-1].end()

    html = html[:anchor] + new_button + html[anchor:]

    total = len(existing_nums) + 1
    count_re = re.compile(r"(收聽錄音（共\s*)(\d+)(\s*集）)")
    if not count_re.search(html):
        sys.exit("找不到「共 N 集」統計文字，格式可能跟預期不同。")
    html = count_re.sub(lambda m: f"{m.group(1)}{total}{m.group(3)}", html)

    page_path.write_text(html, encoding="utf-8")
    return total


def update_overview_card(category, total):
    overview_path = ROOT / "study-group" / "index.html"
    html = overview_path.read_text(encoding="utf-8")

    card_re = re.compile(
        r'(<a class="sgcard rvl"[^>]*href="/study-group/%s/"[^>]*>.*?</a>)' % re.escape(category),
        re.DOTALL,
    )
    m = card_re.search(html)
    if not m:
        sys.exit(f"總覽頁找不到 /study-group/{category}/ 對應的卡片，可能是合併卡片（combine），要手動改。")

    card_html = m.group(1)
    n_re = re.compile(r'(<span class="sgcard-n">)(\d+)([^<]*</span>)')
    if not n_re.search(card_html):
        sys.exit("卡片裡找不到 sgcard-n 統計文字，格式可能跟預期不同。")
    new_card_html = n_re.sub(lambda mm: f"{mm.group(1)}{total}{mm.group(3)}", card_html)

    html = html[: m.start()] + new_card_html + html[m.end():]
    overview_path.write_text(html, encoding="utf-8")


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    category, url = sys.argv[1], sys.argv[2]
    num, date = parse_url(url)
    total = update_detail_page(category, url, num, date)
    update_overview_card(category, total)
    print(f"OK：{category} 新增第 {num} 集（{date}），子頁與總覽頁集數同步更新為 {total}。")
    print("接下來請自行檢查 git diff、commit、push。")


if __name__ == "__main__":
    main()
