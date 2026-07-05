# Codex 工作規則

使用者不想自行處理 Git 指令或網站部署流程。凡是協助更新如意精舍網站時，Codex 應主動代為處理以下步驟，除非遇到登入、權限、衝突或其他必須由使用者確認的狀況。

## 如意精舍網站更新流程

網站 repo 位置：

`C:\Users\user\Documents\GitHub\ruyi99`

每次開始修改網站前：

1. 進入網站 repo。
2. 執行 `git status` 檢查工作區。
3. 若工作區乾淨，執行 `git pull` 取得最新版。
4. 若工作區不乾淨，先判斷是否為本次工作相關變更；不要覆蓋或丟棄使用者既有變更。

修改完成後：

1. 用本機預覽確認頁面可讀取。
2. 執行 `git status` 檢查變更。
3. `git add` 本次相關檔案。
4. 建立清楚的 commit message。
5. 執行 `git push` 推送到 GitHub。
6. 回報 commit hash、修改檔案與預覽/正式網址。

## 特別注意

- 不要要求使用者自行執行 `git pull`、`git commit`、`git push`，除非真的需要使用者登入或處理權限。
- 不要執行 `python build.py`，除非確認 `/tmp/ruyi99-crawl/site.json` 或相應原始資料檔已存在；目前網站可直接編輯產出的靜態 HTML。
- 對《大智度論》講義導讀頁，優先放在 `study-group/perfection-of-wisdom/` 底下的卷次資料夾，例如 `juan054/index.html`。
