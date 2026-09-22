# CODEX 派工：22 個雪場資料覆核管線

2026-09-23 開單。目標：**雪季 12 月開始前，把 `data/resorts.json` 全部 22 個雪場覆核一輪**。
現有資料是 2026-09-22 開站時寫的，`verify:true` 的欄位（雪季月份、交通時間）每年都會變。

## 最重要的一條

**這支管線只產出「覆核報告」，永遠不准自動改 `data/resorts.json`。**
Sarayuki 是中立指南，資料正確性是唯一的護城河，改資料一律由人看過報告後決定。
腳本也不准執行任何 git 指令（跟 `enrich_content.py` 同規矩）。

## 交付物

1. `_pipeline/verify_resorts.py`
2. `.github/workflows/resort-verification.yml`
3. 報告輸出 `data/verify_report.json`（由 workflow commit）＋ GitHub Actions Summary 的人類可讀摘要

## 技術限制（照抄 `_pipeline/enrich_content.py` 的做法，先讀過它再動手）

- Python 3，**只用標準庫**，不准 `pip install`、不准加相依
- 引擎：Gemini `generateContent` REST + Google Search grounding，模型 `gemini-2.5-flash`
- 金鑰只從環境變數 `GEMINI_API_KEY` 讀，**不准寫進檔案或 log**
- 寫檔一律先寫 temp 再 atomic replace（沿用現有寫法）
- 支援 `--dry-run`、`--resort <id>`（單一雪場）、`--batch <n>`（一次跑幾個，預設 6）

## 覆核哪些欄位

| 欄位 | 怎麼查 | 判定 |
|---|---|---|
| `url` | **不要問模型**，用 `urllib` 直接發請求（GET、follow redirect、timeout 10s、帶現成的 UA 常數） | 非 2xx／3xx＝🔴；轉址到不同網域＝🟡（官網可能換址） |
| `months` 開放月份 | Gemini grounding，來源限官網／官方觀光機構 | 與現值差 ≥ 2 個月＝🔴；差 1 個月＝🟡 |
| `peak` 雪況最佳月 | 同上 | 有差異＝🟡（本來就是概略值） |
| `access` / `accessMin` | 同上，重點看巴士／鐵路是否停駛、班次改動 | 交通方式消失＝🔴；時間差 ≥ 30 分＝🟡 |
| `name` / `nameJa` / `place` | 同上 | 雪場改名、易主、停業＝🔴 |
| 新增雪場 | 不在這次範圍，別自己加 | — |

另外：模型回應**沒有 `groundingMetadata` 就不准給建議值**，該欄位標 `"unverified"`（現有腳本已有這個判斷，照抄）。
每個建議值都要附來源 URL，沒有來源的建議一律丟掉。

## 報告格式

```json
{
  "generated": "2026-11-01T11:05:00+09:00",
  "checked": ["niseko", "rusutsu", "..."],
  "results": [
    {
      "id": "niseko",
      "status": "red",              // red / yellow / green / unverified
      "url_check": {"code": 200, "final_url": "https://..."},
      "findings": [
        {
          "field": "accessMin",
          "current": 165,
          "suggested": 180,
          "severity": "yellow",
          "note": "2026-27 季巴士改點，新千歲→比羅夫約 3 小時",
          "sources": ["https://..."]
        }
      ]
    }
  ]
}
```

Actions Summary 要印成人看得懂的表：先列 🔴，再 🟡，🟢 只印一行統計。
標題要寫清楚「這是建議，未套用到 resorts.json」。

## 排程

- workflow `on: schedule` 用 `cron: "0 3 * * *"`（12:00 JST，**跟現有每日內容的 02:00 UTC 錯開，共用同一把 key**）
- 每次跑 `--batch 6`，依 `data/verify_report.json` 裡的 `last_checked` 挑最久沒覆核的 6 個 → 4 天輪完 22 個
- 也要支援 `workflow_dispatch`，input：`resort`（單一 id）、`batch`（數量）
- `permissions: contents: write`、`concurrency` group 比照現有 workflow
- 失敗不寄信，只留 Actions Summary

## 驗收

- [ ] `python3 _pipeline/verify_resorts.py --dry-run` 不打 API 也能跑完並印出計畫
- [ ] `--resort niseko` 單跑正常，報告格式符合上面的 schema
- [ ] 沒有 `GEMINI_API_KEY` 時給清楚錯誤訊息，不是 traceback
- [ ] 腳本內找不到任何 `git ` 指令呼叫
- [ ] `data/resorts.json` 在任何情況下都不被寫入（自己 grep 確認）
- [ ] 跑完後 `git status` 只有 `data/verify_report.json` 是新增/修改

完成後回報你怎麼設計批次輪替、以及哪些判定門檻是你自己定的。**不要自己 push。**
