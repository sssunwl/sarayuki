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
- v2：雪況（降雪／積雪）資料，查授權後再做 → **2026-11-09 已上線**（見下）

## 每日雪況與圖片（2026-11-09，工單 `docs/CODEX_DAILY.md`）
- `data/snow.json` 由 `_pipeline/fetch_snow.py` 抓氣象廳 AMeDAS，`snow-observation.yml` 11–5 月每天 06/12/18 JST 跑。**只原樣呈現觀測值，不准寫預報、評分、「適合去」**（気象業務法，對日本使用者發布自算預報要許可）。標題只能講過去的事實
- AMeDAS 站表 `elems[5]=='1'` 才有積雪觀測；雪季外 point JSON 根本沒有 snow 欄位，屬正常。小谷站沒有氣溫
- `resorts.json` 的 `camUrl`/`liftUrl`/`youtube`/`amedas`：網址 2026-11-09 逐一打開查證；null 的（Cortina/Arai/赤倉/Tomamu cam/八甲田 cam/安比・栂池・GALA 纜車）雪季開始再補。YouTube 直播 ID 會因重開直播而換
- 封面：`_pipeline/make_covers.py` 依 slug 決定性生成 SVG（`content/covers/`），每日排程自動補
- 雪場照片：`data/photos.json`（Wikimedia Commons，只收 CC0/PD/CC BY/BY-SA，前端必附作者+授權）。**自動挑圖會挑到巴士事故照，一律人工看過再放**；夏天照片不放，寧缺勿濫。Commons 縮圖現在走 `thumb.wikimedia.org`
- 文章：800–1400 字＋`BANNED_PHRASES`。超長舊文由每日排程 `--rewrite-next` 一天改一篇（Gemini 免費額度一次改不完）
