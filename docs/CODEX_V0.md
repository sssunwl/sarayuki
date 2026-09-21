# 派工單：Sarayuki さら雪 v0（首頁＋雪場地圖）

> 規劃/審查：Claude｜實作：Codex
> **不要 git init、不要 commit、不要碰 `.git`；不要改 `data/resorts.json`、`CLAUDE.md`、`reference/`**。做完我會自己開瀏覽器審查。

## 背景
Sarayuki（さら雪＝剛下、沒人碰過的新雪）是日本雪場的中立指南，給華語滑雪客看：新手要「看得懂、敢出發」，老手要粉雪、樹林、非壓雪的真資訊。**不收錢排名**。
純靜態網站（GitHub Pages，網址將是 `https://sssunwl.github.io/sarayuki/`），無 build、無框架、無 npm，所有路徑都用相對路徑。

## 要產出的檔案
1. `index.html` — 首頁
2. `resorts/index.html` — 雪場地圖＋篩選頁
3. `.nojekyll`（空檔）

## 最重要的參考
`reference/diveinout-spots.html` 是姊妹站 DiveInOut 已上線、已審查過的潛點地圖頁（篩選邏輯、URL 同步、markercluster、手機清單/地圖切換、sticky 規則都驗證過）。
**`resorts/index.html` 請以它為骨架改寫**：互動與版面架構沿用，換成下面的資料欄位、篩選項目與視覺風格。它踩過的坑不要再踩：
- 手機（< 960px）只有「清單｜地圖＋計數＋篩選↑」那一條 sticky（≤ 64px），篩選區不 sticky
- 「這個月」chip 放在月份列最前面
- 一般滾輪不縮放地圖，⌘/Ctrl＋滾輪或捏合才縮放

## 視覺風格：日式滑雪雜誌（跟 DiveInOut 的深海暗色**相反**，走淺色紙感）
```
:root{
  --paper:#f6f5f1;   /* 頁面底，雪白偏暖的紙色 */
  --ink:#16202a;     /* 主文字，墨色 */
  --dim:#5b6673;     /* 次要文字（對 --paper 對比 ≥ 4.5:1） */
  --line:rgba(22,32,42,.12);
  --card:#ffffff;
  --shu:#d9412b;     /* 朱色，唯一強調色：選中狀態、地圖標記、peak 月份 */
  --ice:#7fa7c2;     /* 冰藍，輔助色：開放月份、群聚 */
}
```
- 字體（Google Fonts）：標題 `Noto Serif TC` 900；內文 `Noto Sans TC` 400/700；英文小標與數字 `IBM Plex Mono`
- 中文標題 line-height ≥ 1.05、letter-spacing ≥ -0.01em（方塊字不能黏在一起）
- 雜誌感元素：
  - 首頁 hero 左側大字 `SARAYUKI`（Plex Mono 或 serif 皆可，字距放寬），右側直書 `さら雪`（`writing-mode:vertical-rl`，Noto Serif TC，朱色）
  - 小標格式：`— 01 / FIND A RESORT` 這種 mono 小字＋細線
  - 卡片：白底、1px `--line` 邊框、圓角 4px（雜誌感用小圓角，不要 12px 的 app 感）、hover 時上移 2px＋陰影
  - 大量留白；不要漸層背景、不要毛玻璃、不要 emoji 當裝飾（篩選 chip 的圖示除外）
- 內文對比 ≥ 4.5:1

## 資料（`fetch` 相對路徑：首頁 `data/resorts.json`、雪場頁 `../data/resorts.json`）
`resorts[]` 每筆欄位：
| 欄位 | 型別 | 說明 |
|---|---|---|
| id, name, nameJa, place | string | name＝中文＋英文名；nameJa＝日文原名（卡片上小字顯示） |
| lat, lng | number | |
| area | `hokkaido`\|`tohoku`\|`nagano`\|`niigata` | 顯示：北海道、東北、長野、新潟 |
| months | int[] | 開放月份（概略），範圍只會出現 11、12、1–5 |
| peak | int[] | 雪況最佳月份 |
| levelFit | array of `beginner`\|`intermediate`\|`advanced` | 適合的程度 |
| tags | array | 見下表 |
| hub | string | 出發點（例：新千歲機場、東京、長野） |
| access | string | 交通說明全文 |
| accessMin | number | 從 hub 出發大約幾分鐘 |
| see | string | 亮點 |
| note | string | 注意（可能是空字串，空的就不顯示） |
| url | string\|null | 官網；null 就不顯示連結 |
| verify | boolean | true＝季節/交通需出發前確認 |

tags 顯示對照（chip 用）：
powder＝❄️ 粉雪、tree＝🌲 樹林滑、onsen＝♨️ 溫泉、night＝🌙 夜滑、family＝👨‍👩‍👧 親子、international＝🌐 外語友善、skiinout＝🏨 住宿直通雪場、backcountry＝⛰ 非壓雪區、daytrip＝🚄 城市一日來回、snowmonster＝🌨 樹冰、longseason＝📅 滑到春天

levelFit 顯示：beginner＝第一次 OK、intermediate＝會轉彎、advanced＝老手

## 頁面一：`resorts/index.html`（雪場地圖）
- 頁首：`← Sarayuki`、小標 `— RESORTS / 雪場`、h1「找雪場」、說明「選月份、程度、想要的，找出適合你的雪場。」
- **篩選**（組內 OR、組間 AND，同 DiveInOut）：
  1. 月份（單選）：`這個月｜全部｜11月｜12月｜1月｜2月｜3月｜4月｜5月`。選 N → 留 `months` 含 N。「這個月」若不在 11–5 月（例如 9 月），按下時選「12月」並在旁邊小字提示「雪季從 12 月開始」
  2. 我的程度（單選）：`全部｜第一次滑｜會轉彎｜老手` → `levelFit` 含 beginner / intermediate / advanced
  3. 想要（多選 chip）：11 個 tags，`tags` 有交集即符合
  4. 地區（select）：全部＋4 區
- URL 參數：`m`、`lv`、`t`、`a`（多選逗號），`history.replaceState`，載入時還原
- 排序：地區順序（北海道→東北→長野→新潟），同區依 accessMin 由小到大
- 計數「符合 X / 22 個雪場」、清除篩選、空狀態（「這個組合目前沒有雪場。試試放寬月份或程度？」）
- **雪場卡片**：
```
┌───────────────────────────────────────┐
│ 二世古 Grand Hirafu                     │ ← serif 18px 900
│ ニセコグラン・ヒラフ · 北海道・倶知安町     │ ← dim 12px
│ [第一次 OK] [會轉彎] [老手]               │ ← levelFit 小標籤（有的才顯示）
│ ❄️ 🌲 🌙 🌐 🏨 ⛰                         │ ← tags 圖示，title 屬性寫中文
│ 11 12  1  2  3  4  5                    │ ← 7 格月份條
│ 🚃 新千歲機場巴士約 2.5–3 小時            │
│ 世界級 JAPOW。四個雪場共用…（最多 2 行）   │
│ ⚠️ 出發前以官網為準   官網 ↗   在地圖上看 → │
└───────────────────────────────────────┘
```
  - 月份條 7 格（11、12、1、2、3、4、5），格高 6px、間距 2px：`peak` 內＝朱色 `--shu`；`months` 內但非 peak＝冰藍 `--ice`；其他＝`--line`。目前選中的月份那格加 1px `--ink` 外框。格下 mono 10px 標月份。圖例一行小字：「朱＝雪況最好 · 藍＝開放」
  - 官網連結 `target="_blank" rel="noopener"`；url 為 null 不顯示
  - `verify` 為 true 顯示「⚠️ 出發前以官網為準」
- **地圖**：
  - 底圖 Esri 淺灰：`https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}`，attribution `Tiles © Esri`，maxZoom 16。**不要**加 CSS filter
  - 初始 `fitBounds` 全部雪場，padding 40
  - 單點標記：直徑 14px 朱色圓、2px 白邊、淡陰影；群聚：白底、1.5px `--ice` 邊、墨色 mono 數字，32/38/44px
  - Popup：白底、4px 圓角、墨色字，內容＝名稱、日文名、程度標籤、交通、亮點、注意、官網
- 頁尾：「季節、交通與票價每年變動，出發前請以各雪場官網為準。Sarayuki 不收費排名。」＋資料更新日（`updated`）

## 頁面二：`index.html`（首頁）
由上到下：
1. **Hero**（高度約 85vh）：左邊大字 `SARAYUKI`，下面一行「日本雪場，從剛下的那一層開始。」再一行 dim 小字「新手看得懂，老手不無聊。中立，不收錢排名。」；右邊直書朱色 `さら雪`（大，約 18vw 高度上限 520px）。手機版直書縮小放右上角，不可擠壓標題
2. **三個入口**（小標 `— 01 / START`）三張並排卡片（手機直排）：
   - 「第一次滑雪」→ 錨點 `#first`
   - 「找雪場」→ `resorts/`
   - 「老手的粉雪」→ `resorts/?lv=advanced&t=powder,tree`
   每張：大號 mono 編號、serif 標題、一句說明、箭頭
3. **這個月去哪**（小標 `— 02 / THIS SEASON`）：`11月`…`5月` 七個 chip，點了 → `resorts/?m=N`。當月若在雪季內就高亮當月；不在雪季（6–10 月）顯示一行「雪季從 12 月開始，先看看 12 月能去哪 →」連 `resorts/?m=12`
4. **第一次滑雪 8 件事**（`id="first"`，小標 `— 03 / FIRST TIME`），手風琴，一次只開一個，內容照抄下方文字：
   1. **雙板還是單板？** 雙板入門比較快；單板前兩天摔最多，但上手後很好玩。拿不定主意就先選雙板。
   2. **第一天一定要上課** 請教練教半天，比自己摔一整天有效。很多雪場有英文課，部分雪場也有中文教練。
   3. **裝備用租的就好** 雪板、雪鞋、雪杖、安全帽，雪場或周邊店家都租得到。自己準備雪衣雪褲、防水手套、雪鏡、脖圍就夠了。
   4. **穿法像洋蔥** 排汗內層＋保暖中層＋防水外層。不要穿棉質內衣，一流汗就濕冷。
   5. **選山腳有緩坡的雪場** 新手需要寬、緩、有魔毯（輸送帶）的練習區。在「找雪場」選「第一次滑」就能篩出來。
   6. **票買半天就好** 第一次先買半日票或一日票，在初級滑道練到能控制速度、會停，再往上走。
   7. **雪道上的規矩** 下方（前方）的人有優先權；要停就停在滑道邊，不要停在中間或死角；跌倒後盡快起身移到旁邊。
   8. **什麼時候去** 12 月初雪量常不穩；1–2 月雪最好也最冷；3 月比較暖，適合新手；4 月之後是春雪，只剩部分高海拔雪場。
5. **老手區**（小標 `— 04 / BEYOND THE PISTE`）：一段文字「粉雪、樹林、非壓雪區——日本最迷人的地方，也是最危險的地方。」＋按鈕「看老手雪場 →」連 `resorts/?lv=advanced&t=powder,tree,backcountry`＋一行安全提醒「非壓雪區務必遵守雪場公告，建議請嚮導並攜帶雪崩三件套（探測器、探桿、雪鏟）。」
6. **關於**（小標 `— 05 / ABOUT`）：「Sarayuki 是給華語滑雪客的日本雪場中立指南。我們不收錢排名，資料標明出處與覆核日期。」＋「收錄 N 個雪場」（N 由資料長度動態）
7. 頁尾：`© Sarayuki さら雪` ＋「季節與交通資訊每年變動，出發前請以官網為準」

## 驗收清單（請逐條回報；沒實際跑過的不要說驗證過）
1. 雪場頁選「1月＋第一次滑」→ 17 個
2. 只選「想要：🚄 城市一日來回」→ 3 個：札幌手稻、輕井澤王子、GALA 湯澤
3. `resorts/?lv=advanced&t=tree` → 5 個：二世古、留壽都、喜樂樂、白馬 Cortina、斑尾高原
4. 選「5月」→ 1 個：神樂；選「11月」→ 1 個：輕井澤王子
5. `resorts/?lv=beginner&t=onsen` → 3 個：藏王溫泉、野澤溫泉、妙高 赤倉溫泉
6. 375px 寬兩頁都無水平捲動
7. 首頁「收錄 N 個雪場」顯示 22

## 不要做的事
- 不要 git init／commit
- 不要改 `data/resorts.json`（資料有問題寫在回報裡）
- 不要新增 npm、build、框架
- 規格沒寫的東西不要加；有想法寫在回報最後「建議」
