# 如意精舍 ruyi99.org

南投縣信義鄉風櫃斗山上佛教道場「如意精舍」的中文官方網站。
依現行 Google Sites（ruyi99.org）整站架構**忠實複製**並以高質感重建，全站 **388 頁**（首頁／法師簡介／讀書會／法會資訊／影音／專欄／夏令營），含 540＋ 部 YouTube 講經與活動影片。

## 設計
- 中文字體 `PingFang TC`；墨梅山寺配色（墨＋梅＋金）。
- 影片一律**當頁燈箱內嵌播放**，不彈出 YouTube。
- 捲動揭示動效、響應式（手機漢堡選單）。

## 建置
本站由 `build.py` 從結構化內容（爬自現行站）生成靜態 HTML。

```bash
# GitHub 專案頁（lukelin7429.github.io/ruyi99/）—— 預設
python3 build.py

# 正式網域 ruyi99.org（apex，根路徑為 /）—— 點網域後改用這個重建
BASE="" python3 build.py
```

> ⚠️ 上線到 `ruyi99.org` 時：用 `BASE="" python3 build.py` 重建，並新增 `CNAME` 檔（內容 `ruyi99.org`）。在 Luke 確認指向前**不要**動 DNS／CNAME。

## 內容來源
原始爬檔與架構盤點存於 Obsidian vault `_組織事務/如意精舍/`。
