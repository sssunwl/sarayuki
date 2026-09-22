# CODEX 派工：雪夜視覺系統套用到其餘頁面

2026-09-23 開單。首頁 `index.html` 已改版完成並上線，**它就是這份設計系統的參考實作**。
這張單的工作：把同一套視覺與互動套到 `resorts/index.html`、`articles/index.html`、`articles/view.html`。

## 鐵則

1. **不要改首頁 `index.html`**。它是真相來源，有問題先回報不要自己改。
2. **不要動功能邏輯**：篩選、地圖、markercluster、URL 參數（`?m=` `?lv=` `?t=` `?focus=` `?slug=`）、
   marked/DOMPurify 渲染、上標引用，全部維持現有行為。這是換皮不是重寫。
3. **純靜態、零相依、無 build**。除了現有的 Leaflet / marked / DOMPurify CDN，不准加任何套件、框架、打包工具。
4. **不要改 `data/resorts.json`、`content/*`**。
5. 舊配色（`--paper:#f6f5f1`、`--shu:#d9412b` 朱紅、`--ice:#7fa7c2`）**全部移除**，不准殘留。
6. 中文大標排版底線：`line-height` ≥ 1.05、`letter-spacing` ≥ -0.01em。不要照抄英文站的緊行距負字距。
7. 每頁都要 `prefers-reduced-motion: reduce` 的降級（關動畫、`.reveal` 直接顯示）。
8. 手機 375px 寬不得橫向捲動（`document.documentElement.scrollWidth > innerWidth` 必須是 false）。

## 設計 token（照抄首頁 `:root`）

```css
--night:#0a1628;   /* 夜空、頁尾、深色區 */
--deep:#12284a;
--dusk:#2b4a7a;
--snow:#f5f8fc;    /* 頁面底色 */
--frost:#e7eff8;   /* 次級底色、chip 未選取 */
--card:#ffffff;
--ink:#0f1e33;     /* 主文字 */
--dim:#5a6a80;     /* 次要文字 */
--line:rgba(15,30,51,.1);
--ice:#3d9bff;     /* 亮冰藍：強調、進度 */
--glacier:#1f6fd1; /* 主要互動色：連結、選取中的 chip、eyebrow */
--aqua:#8fd3ff;    /* 深色區上的強調 */
--glow:#ffb8a8;    /* 晨光粉：只用在警告／少量點綴，不要當主色 */
--ease:cubic-bezier(.2,.8,.2,1);
```

字體（換掉 IBM Plex Mono，全站統一）：

```html
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@200;300;500;700&family=Noto+Sans+TC:wght@400;500;700&family=Noto+Serif+TC:wght@700;900&display=swap" rel="stylesheet">
```

- 標題 `h1,h2,h3`：Noto Serif TC 900
- 內文：Noto Sans TC
- **數字、英文標籤、eyebrow、按鈕英文字**：Outfit（原本 IBM Plex Mono 的位置全部換成它）
- eyebrow 樣式：`font:700 12px/1 Outfit; letter-spacing:.26em; color:var(--glacier)`，前面掛首頁那個雪花 SVG mask（`--flake`，直接從首頁 CSS 複製）

## 共用元件（從首頁複製，不要重新發明）

- **固定導覽列 `.nav`**：三頁都要加，取代現在各頁的「← 返回」。左邊 `SARAYUKI さら雪` 連回 `../`，右邊「找雪場／文章／第一次滑雪」。
  深色頁首上是透明白字，捲動過首屏後切 `.solid`（毛玻璃白底深字）。非首頁沒有深色首屏 → **直接預設 `.solid`**。
- **圓角卡**：`border-radius:22px`、`background:var(--card)`、`box-shadow:0 1px 0 var(--line),0 18px 40px -26px rgba(15,30,51,.35)`，
  hover `translateY(-6px)` 加深陰影。方框直角卡全部淘汰。
- **chip / 篩選鈕**：未選 `background:var(--frost)` 無框；選取中 `background:var(--glacier);color:#fff`；hover 淺冰藍。圓角 99px，最小高度 34px。
- **按鈕 `.btn` / `.btn-primary` / `.btn-ghost`**：照抄首頁。
- **`.reveal` 捲動浮現**：照抄首頁的 IntersectionObserver（threshold .15）。動態插入的卡片要記得補 observe。
- **飄雪 canvas `snowfall()`**：照抄首頁的函式。**只用在深色區塊**，不要蓋在地圖或長篇內文上。

## 各頁工作

### 1. `resorts/index.html`（找雪場）

- 頁首（篩選列上方那塊）改成**深色雪夜 header**：用首頁 hero 的漸層縮短版（高度約 300px，不要整頁），
  加一層飄雪 canvas（`data-density=".6"`）、一層山脊 SVG 收邊到白色篩選列。標題「找雪場」白字。
- 篩選列 `.filters` 維持 sticky，底色改 `rgba(245,248,252,.88)` + `backdrop-filter:blur(14px)`，
  chip 換新樣式，`.clear` 用 `--glacier`。
- 雪場卡 `.resort-card` 改新圓角卡。卡片左側或頂部加一條 4px 的地區色帶：
  北海道 `#3d9bff`／東北 `#5bd0c9`／長野 `#9277c9`／新潟 `#ffb8a8`。
  tag 小標籤用 `--frost` 底 `--glacier` 字。
- 卡片 hover／地圖 marker 連動的 `.marker-active` 與 `.flash` 動畫：顏色換成冰藍，行為不變。
- Leaflet：底圖維持 Esri World_Light_Gray（**CARTO 要 key，不准用**）。
  marker 與 cluster 圖示改成冰藍（`--glacier`），cluster 外圈用半透明白。popup 圓角 14px。
- 手機的 `.mobile-switch` 列表／地圖切換：沿用邏輯，樣式換成新 chip。

### 2. `articles/index.html`（文章列表）

- 頁首同上，深色雪夜 header 縮短版（高度約 260px），標題「文章」。
- 分類篩選 chip 換新樣式。
- 文章卡換成**首頁的 `.article-card`**：頂部 96px 分類漸層色帶 + 白色波浪 SVG 收邊，
  分類色照首頁 `bandColors`（beginner 藍／resort 青／advanced 紫／travel 暖）。
- 列表改 grid：桌機三欄、平板兩欄、手機一欄；卡片 `.reveal` 依序 `transition-delay` 每張 +.08s。

### 3. `articles/view.html`（閱讀頁）

- 深色雪夜 header 放標題、日期、分類、（若有）雪場名。**內文區維持白底，不要放飄雪、不要放背景圖**，閱讀優先。
- 內文排版：`max-width:720px`、`font-size:17px`、`line-height:1.95`、段落間距 1.5em。
  h2 前加雪花小圖示；`blockquote` 左邊 3px 冰藍線 + `--frost` 底。
- 加**閱讀進度條**：固定在導覽列底緣，2px 高，`--ice`，寬度 = 捲動百分比（rAF 節流，reduced-motion 時直接顯示）。
- 來源／引用區塊：`--frost` 底圓角卡，上標數字用 `--glacier`。連結 hover 才加底線。
- 底部加「上一篇／下一篇」或「回文章列表」的新按鈕樣式。

## 驗收（自己跑過再回報）

- [ ] 三頁在 375px、768px、1440px 都沒有橫向捲動、沒有重疊
- [ ] 全站 grep 不到 `#d9412b`、`#f6f5f1`、`IBM Plex Mono`
- [ ] 篩選、地圖連動、`?m=` `?lv=` `?t=` `?focus=` `?slug=` 全部照舊可用
- [ ] console 無錯誤
- [ ] 開系統「減少動態效果」後，三頁不閃不動但內容完整可讀
- [ ] 從首頁點進三頁，視覺上是同一個站

完成後回報改了哪些檔案、哪些地方你判斷跟首頁不一致而自行決定的，**不要自己 push**。
