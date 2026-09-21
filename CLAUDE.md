# Sarayuki さら雪

日本雪場的中立指南（2026-09-22 開）。DiveInOut 的滑雪版姊妹概念，但品牌獨立。
「さら雪」＝剛下、還沒人碰過的新雪。

## 定位（已定案）
- **地區**：先做日本（北海道／東北／長野／新潟）。韓國、中國崇禮以後再說
- **讀者**：新手與老手都要。新手要「看得懂、敢出發」，老手要「粉雪、樹林、非壓雪」的真資訊
- **中立**：不收錢排名、不收業配換排序。日後若有聯盟連結，必須跟內容分開並標示
- **語言**：書面繁中，雪場名附日文原名

## 技術
- 純靜態、零相依、無 build（跟 DiveInOut 同做法）：`index.html`、`resorts/index.html`
- 資料唯一來源：`data/resorts.json`（欄位說明寫在檔內 `schema`）
- 地圖：Leaflet 1.9.4 + markercluster（unpkg CDN），底圖 Esri World_Light_Gray（**CARTO 已全面要求 API key，不要用**）
- 部署：GitHub Pages（repo sssunwl/sarayuki）；之後掛 `sarayuki.sssuni.com`
- 實作派給 Codex，Claude 寫規格＋在瀏覽器實測審查

## 資料紀律
- 雪季月份、交通時間、纜車票價每年都會變 → `verify:true` 並在頁面標「出發前以官網為準」
- 纜車票價 v0 不放（每年漲、容易過時），只放官網連結
- 官網網址要實際打開確認過才放；不確定就 `url:null`
- 非壓雪／backcountry 內容一定附安全提醒（嚮導、雪崩裝備、遵守雪場公告）

## 路線
- v0（核心，12 月雪季前上線）：首頁（三入口＋第一次滑雪 8 件事）＋雪場地圖篩選頁
- v1：比照 SakiDiveDB 做每日內容豐富化（Gemini 查證寫稿，附來源），雪場深度攻略
- v2：雪況（降雪／積雪）資料，查授權後再做
