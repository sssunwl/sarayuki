# 派工單：Sarayuki 文章頁（接每日內容自動化）

> 規劃/審查：Claude｜實作：Codex
> **不要 commit、不要碰 `.git`、不要改 `content/`、`data/`、`_pipeline/`、`.github/`、`CLAUDE.md`、`reference/`**。

## 背景
Sarayuki 已上線（`index.html` 首頁、`resorts/index.html` 找雪場，你上一輪做的）。現在每天 GitHub Actions 會用 Gemini 查證寫一篇文章：
- 文章：`content/articles/<slug>.md`（Markdown；內文引用是 `<sup>[1](#src-1),[2](#src-2)</sup>`，文末「## 來源」清單每行是 `- <a id="src-1"></a>1. [標題](網址)（抓取：日期）`）
- 索引：`content/index.json`
```json
{"updated":"2026-09-22","articles":[
 {"slug":"first-trip","title":"第一次去日本滑雪：行程怎麼排、要準備什麼",
  "category":"beginner","resort":null,"date":"2026-09-22",
  "summary":"第一次前往日本滑雪…","sources":13}
]}
```
  - `articles` 已由新到舊排序
  - `category`：beginner＝新手入門、resort＝雪場攻略、advanced＝老手進階、travel＝行程交通
  - `resort`：對應 `data/resorts.json` 的雪場 id，或 null
現在只有 1 篇，之後每天多 1 篇。要讓網站把它們呈現出來。

## 視覺
完全沿用現有兩頁的 `:root` 變數、字體（Noto Serif TC / Noto Sans TC / IBM Plex Mono）、小標格式、4px 圓角白卡。**不要另創風格**。

## 任務一：`articles/index.html`（文章列表）
- 頁首：`← Sarayuki`、小標 `— JOURNAL / 文章`、h1「文章」、一句「每一篇都查證過，附上來源與抓取日期。」
- 分類 chip（單選）：`全部｜新手入門｜雪場攻略｜老手進階｜行程交通`，同步 URL `?c=beginner`
- 文章卡片（清單直排，桌機最寬 760px 置中）：mono 小字「日期 · 分類」、serif 標題 20px、摘要（dim、最多 2 行）、若有 `resort` 顯示小標籤「📍 雪場名」（從 `../data/resorts.json` 查 name）、右下「讀文章 →」。整張卡可點 → `view.html?slug=<slug>`
- 空狀態：「這個分類還沒有文章，每天會新增一篇。」

## 任務二：`articles/view.html`（文章頁）
- 讀 `?slug=`，驗證只允許 `^[a-z0-9]+(-[a-z0-9]+)*$`，不合法或 404 → 顯示「找不到這篇文章」＋回列表連結
- `fetch('../content/articles/<slug>.md')` 後用 **marked**（`https://cdn.jsdelivr.net/npm/marked@12/marked.min.js`）轉 HTML，再用 **DOMPurify**（`https://cdn.jsdelivr.net/npm/dompurify@3/dist/purify.min.js`）淨化後插入。DOMPurify 要允許 `sup` 與 `a[id]`（預設就允許，確認即可）
- 從 `../content/index.json` 找同 slug 的條目，在標題上方顯示 mono 小字「日期 · 分類 · N 個來源」
- 版面：單欄，內文寬 680px 置中；h1 serif 32px（手機 26px）；h2 serif 22px、上方 40px 間距、左側 3px 朱色短線；內文 17px、line-height 1.85；清單縮排適中
- 引用上標 `sup a`：朱色、mono 11px、不加底線；點了平滑捲到來源（被捲到的那一行短暫加底色 1.5 秒）
- 「## 來源」這一段：字級 13px、dim 色、連結 `target="_blank" rel="noopener"`（外部連結都要）
- 文末固定一塊灰框提醒：「票價、營業期間與交通每年變動，出發前請以官網為準。」
- 若該文 `resort` 不為 null：文末加一張雪場小卡（名稱、日文名、交通一行）＋「在地圖上看 →」連 `../resorts/?focus=<id>`（見任務三）
- `<title>` 設成「文章標題｜Sarayuki さら雪」；`<meta name="description">` 用 summary

## 任務三：把文章接進現有兩頁
1. **`resorts/index.html`**
   - 載入時同時 fetch `../content/index.json`（失敗就當沒有文章，不可讓頁面壞掉）
   - 雪場卡片：若有 `resort===該雪場 id` 的文章，在「官網 ↗」旁加一個朱色連結「攻略 →」連到 `../articles/view.html?slug=<最新那篇>`
   - 支援 URL 參數 `?focus=<id>`：載入後自動等同點了該雪場的「在地圖上看」（桌機 flyTo＋popup；手機切到地圖）。focus 不存在就忽略
2. **`index.html`（首頁）**
   - 在「— 02 / THIS SEASON」之後插入新段落 `— 03 / JOURNAL`（後面的段落編號順延：第一次滑雪 8 件事→04、老手區→05、關於→06）
   - 標題「最新文章」，列出最新 3 篇（卡片同任務一的樣式、橫排三欄，手機直排），下方「看全部文章 →」連 `articles/`
   - 0 篇時整段不顯示
   - 三個入口卡片中「第一次滑雪」維持錨點不變

## 驗收（逐條回報；沒實際跑的不要說驗證過）
1. `articles/` 顯示 1 篇 first-trip；選「雪場攻略」→ 空狀態
2. `articles/view.html?slug=first-trip` 正常渲染，上標可點並捲到來源
3. `articles/view.html?slug=../../etc` 與 `?slug=nope` 顯示找不到
4. 首頁出現「最新文章」1 張卡；段落編號 01–06 連續
5. `resorts/?focus=gala` 載入後地圖飛到 GALA 湯澤並打開 popup
6. 375px 無水平捲動（文章頁的長網址要能斷行：`overflow-wrap:anywhere`）

## 不要做的事
- 不要改 `content/`、`data/`、`_pipeline/`、`.github/`
- 不要加 npm／build；只能用上面指定的兩個 CDN 套件
- 規格沒寫的不要加；想法寫在回報最後「建議」
