# CODEX work order: a reason to look every day (daily snow report, Live Cam/lift buttons, cover images, article rules)

Opened 2026-11-09. Ski season starts in December; this has to ship before then.
Diagnosis: the site currently has nothing that changes from day to day, and none of its 18 articles has an image. Visitors look once and never come back.

Reference images (attached with -i): `ref_home.png` (homepage hero, the reference implementation of the snow-night visual system) and `ref_resorts.png` (find-a-resort page).

## Hard rules

1. **Pure static, zero dependencies, no build step.** Front end: no new packages or frameworks. Python: **standard library only**, no `pip install`.
2. **Do not commit, do not touch `.git`.** I commit after reviewing. Python scripts must not run git either (workflows handle commits).
3. Do not touch the logic of `_pipeline/verify_resorts.py` or `.github/workflows/resort-verification.yml`.
4. Do not change existing filtering, maps, URL parameters (`?m=` `?lv=` `?t=` `?focus=` `?slug=`) or marked/DOMPurify rendering behavior.
5. Visuals follow the existing snow-night tokens (`--night` `--glacier` `--ice` `--frost`, etc., copied from the homepage `:root`). Fonts: Outfit / Noto Sans TC / Noto Serif TC. No new colors.
6. CJK headline typesetting floor: `line-height` ≥ 1.05, `letter-spacing` ≥ -0.01em.
7. Every page must degrade under `prefers-reduced-motion`; no horizontal scroll at 375px width.
8. **Weather law**: the snow report may only present Japan Meteorological Agency (JMA) **observed values as-is**. Never write forecasts, scores, or "go today / good day to ski" style recommendations (publishing self-made forecasts to users in Japan requires a JMA license). The one-line headline may only state facts about the past ("過去 24 小時降雪最多：…"). Do not use words like 「推薦」「適合去」「粉雪日」「明天」.

---

## A. Add fields to `data/resorts.json` (data has been verified; write it in exactly as given)

The data is in `docs/resort_live_links.json` (keyed by resort id). Merge it into each resort object as these four fields:

```json
"camUrl": "https://… | null",        // official Live Cam page
"liftUrl": "https://… | null",       // official lift/trail status page
"youtube": [{"id":"xrn4ifcQwj4","label":"山麓"}],  // embeddable YouTube live streams; [] if none
"amedas": {"code":"48141","name":"白馬","alt":703,"km":2.8}  // nearest AMeDAS station with snow depth observations
```

Add explanations for these four fields to the `schema` section as well. Do not change any other field. Keep `null` as `null`; do not fill in URLs on your own.

## B. Daily snow report pipeline

### `_pipeline/fetch_snow.py`

Data sources (free, no key needed; verified 2026-11-09):

- Latest observation time: `https://www.jma.go.jp/bosai/amedas/data/latest_time.txt` (e.g. `2026-11-09T03:30:00+09:00`)
- Station table: `https://www.jma.go.jp/bosai/amedas/const/amedastable.json` (not needed: the station code is already in `resorts.json`)
- Per-station observations: `https://www.jma.go.jp/bosai/amedas/data/point/{code}/{YYYYMMDD}_{HH}.json`
  - `HH` is the 3-hour block (00/03/06/…/21), computed from latest_time in **JST**
  - The content is `{ "20261109021000": { "temp":[4.1,0], "snow":[85,0], "snow24h":[12,0], ... } }`. Keys are JST timestamps; the second number in each value pair is a quality flag (0 = normal)
  - **Snow fields (`snow` snow depth cm, `snow1h` `snow6h` `snow12h` `snow24h` snowfall cm) only appear when there is snow to report, and none are present in November.** If a field is missing it is `null`. Do not treat it as 0 and do not throw an error
  - Take the **most recent** timestamp in the block that has `temp`. If the current block is empty, fall back one block (3 hours earlier)
- Only keep values whose flag is 0; otherwise write `null`
- There are about 17 unique stations; deduplicate before fetching. Request timeout 15s, set a UA, 0.5s between requests. If one station fails, mark it as `null` and keep going; the script fails only when every station fails (exit 1)
- Write to temp first, then atomic replace

Output `data/snow.json`:

```json
{
  "generated": "2026-12-10T06:12:00+09:00",
  "source": "気象庁 アメダス（観測値をそのまま掲載）",
  "stations": {
    "48141": {"name":"白馬","alt":703,"observedAt":"2026-12-10T06:00:00+09:00",
              "snow":85,"snow24h":12,"temp":-5.2}
  },
  "headline": {"text":"過去 24 小時降雪最多：白馬 18 cm", "stationCode":"48141"},
  "season": true
}
```

Headline rules (written by the script, facts only):
- Some station has `snow24h` ≥ 1 → `過去 24 小時降雪最多：{station name} {n} cm` (ties go to whichever comes first)
- Otherwise, some station has `snow` ≥ 1 → `目前積雪最深：{station name} {n} cm`
- Neither → `各觀測站目前還沒有積雪紀錄`, and `season:false`

Also support `--dry-run` (print without writing).

### `.github/workflows/snow-observation.yml`

- cron `10 21,3,9 * 11,12,1,2,3,4,5 *` (JST 06:10 / 12:10 / 18:10, November–May only) + `workflow_dispatch`
- `python3 _pipeline/fetch_snow.py` → if `data/snow.json` changed then `git add data/snow.json` → commit `雪況更新 {JST time}` → `git pull --rebase origin main` → push
- On failure, follow the same approach as `daily-content-enrichment.yml`: write to the Summary and do not turn the job red
- `permissions: contents: write`, concurrency group `sarayuki-snow`

## C. Front end

### Homepage `index.html`: new「今日雪況」section

Placement: right below the hero, **before**「你是哪一種滑雪人？」. Use the existing `.section` + `.reveal` style.

- eyebrow `TODAY'S SNOW`, heading「今日雪況」
- The large text line is `headline.text`; below it, small text: `觀測時間 {MM/DD HH:mm}・資料：氣象廳 AMeDAS`
- Then a grid of up to 6 resort cards: sort by the station's `snow24h` descending, then `snow` descending. Each card shows: resort name, nearest station name and altitude, three numbers (積雪 cm／24h 降雪 cm／氣溫 °C; show `—` when there is no value). Numbers in Outfit. Clicking a card → `resorts/?focus={id}`
- Bottom button「看全部 22 個雪場的雪況 →」→ `resorts/`
- When `season:false` or loading fails: show one line「雪季觀測從 12 月開始，各站目前還沒有積雪紀錄。」plus the button. No cards
- Fixed footnote (small text, required):「數值為氣象廳 AMeDAS 觀測站原始觀測值，未經加工。觀測站多在山腳，山上積雪通常更深；出發前請看雪場官方雪況。出典：気象庁ホームページ」

### Find-a-resort page `resorts/index.html`: add three things to each card

1. **Snow line** (only when the station has data): `❄ 積雪 85 cm · 24h +12 cm · −5.2°C` followed by small grey text `白馬站 703m・2.8km`
2. **Two buttons** `🎥 Live Cam` and `🚡 纜車運行`: open the official page in a new tab (`rel="noopener"`). **If the field is null, don't render the button** (no grey disabled button). Button style uses the existing chip style
3. **YouTube live stream**: when `youtube` is non-empty, add a `▶ 看直播` button. Clicking it expands, inside the card, a 16:9 `youtube-nocookie.com/embed/{id}` iframe (insert the iframe **only after the click**, never preload it). With multiple streams, use small chips to switch between `label`s. Below it, small text:「直播由雪場官方提供，畫面中斷時請看官網。」
4. **Photo** (see D-2): when there is a photo, the card top shows a 16:9 thumbnail (`loading="lazy"`) with a credit line below it `Photo: {author} / {license} / Wikimedia Commons` (linked to the file page). Without a photo, show nothing

Load snow.json and photos.json with `fetch`; if they fail to load, simply omit those sections. **The page must not break.**

### Article list / home "Latest articles" / reading page: covers

- The `content/index.json` entry gets a new `"cover": "content/covers/{slug}.svg"`. If the front end finds no `cover`, it derives the same path from the slug
- **Article cards on the article list and the homepage**: swap the existing 96px gradient band for the cover image (16:9 or a 200px-tall `object-fit:cover`, keeping the white wave that closes the band)
- **Reading page `articles/view.html`**: the dark header uses the cover as its background (with a dark overlay `linear-gradient(rgba(10,22,40,.55),rgba(10,22,40,.85))` so the white text stays readable). The body stays on white with no background image

## D. Images

### D-1. `_pipeline/make_covers.py` (cover generator, standard library, outputs SVG)

Follow the approach in `okidayz/tools/brand_assets.py`: **deterministic** generation seeded by the slug (same slug → same image), shapes only, no text (the title is overlaid by HTML).

- Size `viewBox="0 0 1200 675"`; output to `content/covers/{slug}.svg`, each file < 30KB
- Base: snow-night gradient (`#0a1628` → `#12284a` → `#2b4a7a`), sharing the palette of the homepage hero
- Composition (randomized from the seed): 2–3 layers of mountain ridges with snowcaps (like the hero), stars / falling snow dots, optional crescent moon
- **Category motifs** (so you can tell articles apart at a glance):
  - `beginner`: gentle slope + a row of little flags marking the course
  - `resort`: high ridge + gondola cable line and cabins
  - `advanced`: steep slope + a band of conifers (tree run)
  - `travel`: train / bus silhouette + onsen steam curves
- Accent colors come from the homepage `bandColors` for each category (blue/teal/purple/warm); use them only on small elements. Do not paint the whole image in the category color
- CLI: `python3 _pipeline/make_covers.py` (generate any missing ones) / `--all` (regenerate everything) / `--slug x`. It also writes the `cover` field into each entry of `content/index.json`
- Generate the covers for the existing 18 articles; add a `content/covers/preview.html` that lays out every cover in one view for my review

### D-2. `_pipeline/fetch_commons_photos.py` (just write the script; I'll run it. Your sandbox has no network)

- For each resort, query the Wikimedia Commons API (`https://commons.wikimedia.org/w/api.php`, `generator=search`, `gsrnamespace=6`, query `"{nameJa}" スキー` and fall back to `"{English name}" ski`), `prop=imageinfo&iiprop=url|extmetadata|size&iiurlwidth=960`
- **Only accept** licenses where `extmetadata.LicenseShortName` is CC0 / Public domain / CC BY * / CC BY-SA *; drop NC/ND and anything else
- Prefer landscape images with width ≥ 1200, ideally ones that show snow (title/description contains snow/ski/スキー/雪)
- Output `data/photos.json`: `{ "niseko": {"thumb":"…960px url","file":"https://commons.wikimedia.org/wiki/File:…","author":"(strip HTML)","license":"CC BY-SA 4.0","licenseUrl":"…"} }`; resorts with no match are simply absent
- `--resort id` re-queries just one; `--exclude-file "File:xxx.jpg"` excludes an image (for when I reject one during review). Running again must not overwrite resorts already in `photos.json` unless `--force` is given
- The front end hotlinks `thumb` (upload.wikimedia.org); do not download images into the repo

## E. Article rules (`_pipeline/enrich_content.py`)

1. Add this to the system prompt's rules, and keep the banned word list as a constant `BANNED_PHRASES` (shared by the prompt and the check):
   ```
   至關重要, 不容錯過, 絕佳, 完美, 無與倫比, 首選, 一站式, 讓我們, 夢想, 終極, 必去, 必玩,
   輕鬆踏上, 盡情享受, 不二之選, 令人難忘, 獨一無二, 深度體驗, 帶你, 一次搞懂, 總而言之, 綜上所述,
   這篇文章將, 本文將, 希望這篇, 您
   ```
   Also add a rule: use「你」not「您」; the first paragraph must not open with「X 是……的滑雪場」; every paragraph must contain at least one concrete fact (number, place name, time, or a rule), and adjective-only sentences are not allowed.
2. **Length**: the body (`body_length`) must be 800–1400 characters.
   - If > 1500: make **one** follow-up Gemini call (no grounding, same content) asking it to "condense to under 1300 characters, keeping all facts and the 「⚠️需覆核」 markers, without changing the paragraph order of claims that carry citations". Citation markers are inserted afterwards by the program from groundingMetadata, so the compression must happen before `insert_grounding_citations`. **Note**: grounding's segment offsets correspond to the original text, so after compression the citations cannot be reattached by offset. Approach: after compression, still list all sources under「## 來源」but skip inline superscripts (decide this yourself; whichever way you go, describe it in your report)
   - Still > 1600 after compression → do not write (raise), and the workflow records it in the Summary
   - < 300 is rejected as before
3. **Banned words**: if any appear after writing, make one call to replace them (like-for-like substitution in the original sentences, no new content). If any remain, print a warning and still write the article
4. New mode `--rewrite <slug>`: rewrite an existing article on the same topic (take title/category/resort from `index.json`), allowed to overwrite the original; the `date` in `index.json` stays unchanged, add `"updated": today`. Regenerate the cover after rewriting (if one already exists, leave it alone)
5. New workflow `.github/workflows/rewrite-articles.yml`: `workflow_dispatch` input `slugs` (comma-separated). Runs `--rewrite` for each in order, 30s apart, timeout 40 min, **one commit at the end**, and if one article fails the rest still run. Summary lists each article's old/new character count
6. In `daily-content-enrichment.yml`, after writing the article run `python3 _pipeline/make_covers.py` and add `content/covers` to the commit paths

## Acceptance (run these yourself before reporting back)

- [ ] `python3 -m py_compile _pipeline/*.py` passes
- [ ] `python3 _pipeline/make_covers.py --all` produces 18 SVGs, each < 30KB, deterministic (running it twice gives an identical hash)
- [ ] `fetch_snow.py`: write a small unit test (`_pipeline/test_fetch_snow.py`, using unittest + fake JSON) covering "has snow / missing snow fields / bad flag / current block empty → fall back one block / one station fails"
- [ ] `enrich_content.py`: banned word detection, length branching and `--rewrite` path have unittests (mock the Gemini call)
- [ ] With a hand-written fake `data/snow.json` (one with snow, one with `season:false`) and a fake `data/photos.json`, both front-end states render. **Remove the fakes afterwards and keep only the real files** (see below)
- [ ] `resorts.json` is still valid JSON, every resort has all 4 new fields, and no other fields changed (use a diff script to show this)

Committed real files: `data/snow.json` for now holds a blank version with `{"generated":null,"stations":{},"headline":{"text":"各觀測站目前還沒有積雪紀錄"},"season":false}`; I'll replace it after running the real script. Leave `data/photos.json` absent (I'll generate it).

When done, report: which files you changed, the citation-handling decision in E-2, any places where you departed from the spec on your own judgment, and the commands I need to run myself (fetch_commons_photos / fetch_snow). **Do not push.**
