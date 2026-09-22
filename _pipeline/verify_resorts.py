#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sarayuki 雪場資料覆核：只產出報告，不修改來源資料。"""

import argparse
import datetime
import hashlib
import html
import json
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


MODEL = "gemini-2.5-flash"
API_URL = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{MODEL}:generateContent")
DB_ROOT = Path(__file__).resolve().parent.parent
RESORTS = Path("data") / "resorts.json"
REPORT = Path("data") / "verify_report.json"
JST = datetime.timezone(datetime.timedelta(hours=9))
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36")
MODEL_FIELDS = ("months", "peak", "access", "accessMin", "name", "nameJa", "place")
SEVERITY_ORDER = {"green": 0, "unverified": 1, "yellow": 2, "red": 3}

SYSTEM_PROMPT = """你是 Sarayuki さら雪的資料覆核員。請使用 Google 搜尋 grounding，查核指定日本雪場的當季官方資訊。

嚴格規則：
1. 來源只可使用雪場官網、營運公司官網、政府或官方觀光機構、官方鐵路與巴士業者。不要使用部落格、訂房平台、百科、論壇或彙整網站。
2. 查核 months（實際營業月份）、peak（通常雪況最佳月份）、access、accessMin，以及 name、nameJa、place 是否因改名、易主或停業而失效。
3. accessMin 必須以資料中的 hub 為起點，代表一般大眾運輸的約略總分鐘數。若官方交通方式停駛或消失，access 的 state 用 transport_removed。
4. name/nameJa/place 的重大事件 state 使用 renamed、ownership_changed 或 closed；普通資料差異使用 changed。
4a. **name 是 Sarayuki 自訂的繁體中文顯示名，不是官方名稱**。只有雪場真的改名、易主或停業時才回報；官方英文或日文名稱與它不同是正常的，這種情況 state 必須是 same。
4b. place 只在行政區劃或所在地真的變更時回報；寫法差異（市／町／村、括號、順序）一律 same。
5. 找不到足以支持某欄位的官方資料，該欄位 state 必須是 unverified，不可憑記憶猜測。
6. suggested 必須是完整替代值；months/peak 為 1–12 的整數陣列，access/name/nameJa/place 為字串，accessMin 為整數。same 或 unverified 時 suggested 必須是 null。
7. 只輸出下列形狀的合法 JSON，不要 Markdown code fence、引用標記、URL、前言或額外欄位：
{"fields":{"months":{"state":"same|changed|unverified","suggested":null,"note":""},"peak":{"state":"same|changed|unverified","suggested":null,"note":""},"access":{"state":"same|changed|transport_removed|unverified","suggested":null,"note":""},"accessMin":{"state":"same|changed|unverified","suggested":null,"note":""},"name":{"state":"same|changed|renamed|ownership_changed|closed|unverified","suggested":null,"note":""},"nameJa":{"state":"same|changed|renamed|ownership_changed|closed|unverified","suggested":null,"note":""},"place":{"state":"same|changed|renamed|ownership_changed|closed|unverified","suggested":null,"note":""}}}
"""


def now_jst():
    return datetime.datetime.now(JST).replace(microsecond=0).isoformat()


def write_github_output(name, value):
    """安全寫入 GitHub Actions output；本機執行時不做事。"""
    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        return
    value = str(value)
    marker = "SARA_" + hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
    with open(path, "a", encoding="utf-8") as output:
        output.write(f"{name}<<{marker}\n{value}\n{marker}\n")


def load_resorts(db_root):
    path = db_root / RESORTS
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"找不到雪場資料：{path}")
    except json.JSONDecodeError as error:
        raise ValueError(f"雪場資料不是合法 JSON：{error}")
    resorts = data.get("resorts") if isinstance(data, dict) else None
    if not isinstance(resorts, list) or not resorts:
        raise ValueError("雪場資料缺少非空的 resorts 陣列")
    seen = set()
    for resort in resorts:
        resort_id = resort.get("id") if isinstance(resort, dict) else None
        if not isinstance(resort_id, str) or not resort_id or resort_id in seen:
            raise ValueError("雪場資料含有空白或重複的 id")
        seen.add(resort_id)
    return resorts


def load_previous_report(db_root):
    path = db_root / REPORT
    if not path.exists():
        return {"last_checked": {}, "results": []}
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"既有覆核報告不是合法 JSON：{error}")
    if not isinstance(report, dict):
        raise ValueError("既有覆核報告頂層必須是物件")
    if not isinstance(report.get("last_checked", {}), dict):
        raise ValueError("既有覆核報告的 last_checked 必須是物件")
    if not isinstance(report.get("results", []), list):
        raise ValueError("既有覆核報告的 results 必須是陣列")
    return report


def select_resorts(resorts, previous, resort_id=None, batch=6):
    if resort_id:
        selected = next((resort for resort in resorts if resort["id"] == resort_id), None)
        if selected is None:
            valid = ", ".join(resort["id"] for resort in resorts)
            raise ValueError(f"未知雪場 id：{resort_id}（可用：{valid}）")
        return [selected]

    last_checked = previous.get("last_checked", {})
    positions = {resort["id"]: index for index, resort in enumerate(resorts)}

    def rotation_key(resort):
        checked = last_checked.get(resort["id"])
        return (checked is not None, str(checked or ""), positions[resort["id"]])

    return sorted(resorts, key=rotation_key)[:batch]


def build_user_prompt(resort, timestamp):
    current = {field: resort.get(field) for field in MODEL_FIELDS}
    current["hub"] = resort.get("hub")
    current["official_url"] = resort.get("url")
    return (f"覆核時間：{timestamp}\n雪場 id：{resort['id']}\n"
            f"目前資料：{json.dumps(current, ensure_ascii=False)}\n"
            "請查核當季或目前最新的官方資訊，依 system instruction 只回傳 JSON。")


def build_request(resort, timestamp):
    return {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [
            {"text": build_user_prompt(resort, timestamp)},
        ]}],
        "tools": [{"google_search": {}}],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 4096,
        },
    }


def call_gemini(key, payload, retries=2):
    """單次 API request 最長 120 秒；暫時性失敗最多再試 2 次。"""
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    last_error = "未知錯誤"
    for attempt in range(retries + 1):
        request = urllib.request.Request(
            API_URL,
            data=body,
            headers={"Content-Type": "application/json", "x-goog-api-key": key},
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                return json.loads(response.read()), None
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", "ignore")[:500]
            last_error = f"Gemini HTTP {error.code}: {detail}"
            retryable = error.code in (429, 500, 502, 503, 504)
            if not retryable or attempt >= retries:
                return None, last_error
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            last_error = f"Gemini 呼叫失敗：{error}"
            if attempt >= retries:
                return None, last_error
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            return None, f"Gemini 回應不是合法 JSON：{error}"
        wait = 30 * (attempt + 1)
        print(f"  …Gemini 暫時失敗，{wait}s 後重試（{attempt + 1}/{retries}）")
        time.sleep(wait)
    return None, last_error


def get_candidate(response):
    try:
        candidate = response["candidates"][0]
        parts = candidate["content"]["parts"]
        text = "".join(part.get("text", "") for part in parts).strip()
    except (KeyError, IndexError, TypeError):
        raise ValueError("Gemini 回應格式異常，可能被安全過濾或沒有候選內容")
    if not text:
        raise ValueError("Gemini 沒有回傳文字內容")
    finish = candidate.get("finishReason")
    if finish and finish != "STOP":
        raise ValueError(f"Gemini 未正常結束（finishReason={finish}）")
    return candidate, text


def strip_code_fence(text):
    match = re.fullmatch(r"\s*```(?:json)?\s*\n(.*?)\n```\s*", text,
                         flags=re.S | re.I)
    return match.group(1).strip() if match else text.strip()


def resolve_source_url(url):
    """跟隨 grounding 轉址，取得實際來源網址；失敗時保留 API URI。"""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return None
    resolved = None
    for headers in ({"User-Agent": UA, "Range": "bytes=0-0"}, {"User-Agent": UA}):
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=12) as response:
                resolved = response.geturl()
                break
        except urllib.error.HTTPError as error:
            final = error.geturl()
            if final and "grounding-api-redirect" not in final:
                resolved = final
                break
        except (urllib.error.URLError, TimeoutError, OSError):
            continue
    if not resolved:
        print(f"  ⚠️ 來源轉址解析失敗，保留 grounding URL：{url[:60]}…")
        resolved = url
    return urllib.parse.urlsplit(resolved)._replace(fragment="").geturl()


def extract_grounding_sources(candidate, resolver=resolve_source_url):
    """只採用 groundingMetadata 中實際存在的來源網址。"""
    metadata = candidate.get("groundingMetadata") or {}
    chunks = metadata.get("groundingChunks") or []
    supports = metadata.get("groundingSupports") or []
    used = []
    for support in supports:
        for index in support.get("groundingChunkIndices") or []:
            if isinstance(index, int) and index not in used:
                used.append(index)
    if not used:
        used = list(range(len(chunks)))

    sources = []
    seen = set()
    for index in used:
        if not 0 <= index < len(chunks):
            continue
        web = chunks[index].get("web") or {}
        raw_url = web.get("uri")
        url = resolver(raw_url) if raw_url else None
        if not url or url in seen:
            continue
        seen.add(url)
        title = html.unescape((web.get("title") or "").strip())
        sources.append({"title": title, "url": url})
    return sources


def parse_model_json(text):
    try:
        payload = json.loads(strip_code_fence(text))
    except json.JSONDecodeError as error:
        raise ValueError(f"Gemini 文字不是指定的 JSON 格式：{error}")
    fields = payload.get("fields") if isinstance(payload, dict) else None
    if not isinstance(fields, dict):
        raise ValueError("Gemini JSON 缺少 fields 物件")
    return fields


def normalized_host(url):
    hostname = (urllib.parse.urlparse(url).hostname or "").casefold()
    return hostname.removeprefix("www.")


def check_official_url(url, opener=urllib.request.urlopen):
    if not isinstance(url, str) or not url.strip():
        return {
            "check": {"code": None, "final_url": None, "error": "未提供官網 URL"},
            "findings": [{
                "field": "url", "current": url, "suggested": None,
                "severity": "red", "note": "目前資料未提供官網 URL", "sources": [],
            }],
        }

    request = urllib.request.Request(url, headers={"User-Agent": UA}, method="GET")
    try:
        with opener(request, timeout=10) as response:
            code = response.getcode()
            final_url = response.geturl()
            error_text = None
    except urllib.error.HTTPError as error:
        code = error.code
        final_url = error.geturl() or url
        error_text = f"HTTP {error.code}"
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        code = None
        final_url = url
        error_text = str(error)

    check = {"code": code, "final_url": final_url}
    if error_text:
        check["error"] = error_text
    findings = []
    if not isinstance(code, int) or not 200 <= code < 400:
        findings.append({
            "field": "url", "current": url, "suggested": None,
            "severity": "red", "note": error_text or f"官網回應 HTTP {code}",
            "sources": [],
        })
    elif normalized_host(url) != normalized_host(final_url):
        findings.append({
            "field": "url", "current": url, "suggested": final_url,
            "severity": "yellow", "note": "官網轉址到不同網域，請人工確認是否換址",
            "sources": [final_url],
        })
    return {"check": check, "findings": findings}


def unverified_findings(note, resort=None):
    resort = resort or {}
    return [{
        "field": field, "current": resort.get(field), "suggested": None,
        "severity": "unverified", "note": note, "sources": [],
    } for field in MODEL_FIELDS]


def valid_months(value):
    return (isinstance(value, list) and not isinstance(value, (str, bytes))
            and value and all(isinstance(month, int) and not isinstance(month, bool)
                              and 1 <= month <= 12 for month in value))


def valid_suggestion(field, value):
    if field in ("months", "peak"):
        return valid_months(value)
    if field == "accessMin":
        return isinstance(value, int) and not isinstance(value, bool) and value >= 0
    return isinstance(value, str) and bool(value.strip())


def field_finding(field, current, item, source_urls):
    if not isinstance(item, dict):
        return {
            "field": field, "current": current, "suggested": None,
            "severity": "unverified", "note": "模型未回傳合法欄位物件", "sources": [],
        }
    state = item.get("state")
    note = item.get("note") if isinstance(item.get("note"), str) else ""
    if state == "same":
        return None
    if state == "unverified":
        return {
            "field": field, "current": current, "suggested": None,
            "severity": "unverified", "note": note or "官方來源不足，無法覆核",
            "sources": [],
        }

    # name 是自訂繁中顯示名，place 寫法也由我們決定：
    # 只收停業／改名／易主這類事件，單純「跟官方寫法不同」不算問題。
    if field in ("name", "place") and state == "changed":
        return None

    allowed = {
        "months": {"changed"},
        "peak": {"changed"},
        "access": {"changed", "transport_removed"},
        "accessMin": {"changed"},
        "name": {"changed", "renamed", "ownership_changed", "closed"},
        "nameJa": {"changed", "renamed", "ownership_changed", "closed"},
        "place": {"changed", "renamed", "ownership_changed", "closed"},
    }
    suggested = item.get("suggested")
    if state not in allowed[field]:
        return {
            "field": field, "current": current, "suggested": None,
            "severity": "unverified", "note": note or "模型回傳狀態不合法",
            "sources": [],
        }
    if not source_urls:
        return {
            "field": field, "current": current, "suggested": None,
            "severity": "unverified", "note": "沒有 groundingMetadata 來源，不採用建議值",
            "sources": [],
        }

    red_events = {"transport_removed", "renamed", "ownership_changed", "closed"}
    if state in red_events:
        if suggested is not None and not valid_suggestion(field, suggested):
            suggested = None
        return {
            "field": field, "current": current, "suggested": suggested,
            "severity": "red", "note": note or "官方資料顯示重大狀態變更",
            "sources": source_urls,
        }

    if not valid_suggestion(field, suggested):
        return {
            "field": field, "current": current, "suggested": None,
            "severity": "unverified", "note": note or "模型回傳建議值不合法",
            "sources": [],
        }

    if field in ("months", "peak"):
        suggested = sorted(set(suggested), key=lambda month: (month < 7, month))
        if set(suggested) == set(current or []):
            return None
    elif suggested == current:
        return None

    if field == "months":
        severity = "red" if len(set(current or []) ^ set(suggested)) >= 2 else "yellow"
    elif field == "peak":
        severity = "yellow"
    elif field == "access":
        severity = "yellow"
    elif field == "accessMin":
        if not isinstance(current, int) or abs(suggested - current) < 30:
            return None
        severity = "yellow"
    else:
        severity = "red"

    return {
        "field": field, "current": current, "suggested": suggested,
        "severity": severity, "note": note or "官方資料與目前值不同",
        "sources": source_urls,
    }


def model_findings(resort, candidate, text, resolver=resolve_source_url):
    sources = extract_grounding_sources(candidate, resolver)
    if not sources:
        return unverified_findings(
            "Gemini 回應沒有可用的 groundingMetadata，未採用建議值", resort)
    fields = parse_model_json(text)
    source_urls = [source["url"] for source in sources]
    findings = []
    for field in MODEL_FIELDS:
        finding = field_finding(field, resort.get(field), fields.get(field), source_urls)
        if finding:
            findings.append(finding)
    return findings


def resort_status(findings):
    return max((finding["severity"] for finding in findings),
               key=lambda severity: SEVERITY_ORDER[severity], default="green")


def verify_resort(resort, key, timestamp, api_caller=call_gemini,
                  url_opener=urllib.request.urlopen, resolver=resolve_source_url):
    print(f"覆核 {resort['id']}：{resort.get('name', '')}")
    url_result = check_official_url(resort.get("url"), url_opener)
    response, error = api_caller(key, build_request(resort, timestamp))
    if error:
        print(f"  ⚠️ {error}")
        findings = unverified_findings(error, resort)
    else:
        try:
            candidate, text = get_candidate(response)
            findings = model_findings(resort, candidate, text, resolver)
        except (ValueError, TypeError) as parse_error:
            print(f"  ⚠️ {parse_error}")
            findings = unverified_findings(str(parse_error), resort)
    findings = url_result["findings"] + findings
    return {
        "id": resort["id"],
        "status": resort_status(findings),
        "url_check": url_result["check"],
        "findings": findings,
    }


def merge_report(previous, selected_results, timestamp):
    selected_ids = [result["id"] for result in selected_results]
    by_id = {result.get("id"): result for result in previous.get("results", [])
             if isinstance(result, dict) and isinstance(result.get("id"), str)}
    for result in selected_results:
        by_id[result["id"]] = result
    last_checked = dict(previous.get("last_checked", {}))
    for resort_id in selected_ids:
        last_checked[resort_id] = timestamp
    return {
        "generated": timestamp,
        "checked": selected_ids,
        "last_checked": last_checked,
        "results": list(by_id.values()),
    }


def atomic_write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                         prefix=f".{path.name}.", delete=False) as temp:
            temp.write(text.rstrip() + "\n")
            temp_name = temp.name
        os.replace(temp_name, path)
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)


def markdown_value(value):
    if value is None:
        return "—"
    if isinstance(value, (list, dict)):
        rendered = json.dumps(value, ensure_ascii=False)
    else:
        rendered = str(value)
    return rendered.replace("|", "\\|").replace("\n", " ")


def summary_markdown(results, timestamp):
    lines = [
        "## 雪場資料覆核建議（未套用到 `data/resorts.json`）",
        "",
        f"覆核時間：{timestamp}；本批共 {len(results)} 個雪場。",
        "",
    ]
    for severity, icon, heading in (("red", "🔴", "需人工處理"),
                                    ("yellow", "🟡", "建議人工確認")):
        rows = [(result["id"], finding) for result in results
                for finding in result["findings"] if finding["severity"] == severity]
        lines.extend([f"### {icon} {heading}", ""])
        if not rows:
            lines.extend(["本批沒有。", ""])
            continue
        lines.extend(["| 雪場 | 欄位 | 目前值 | 建議值 | 說明 | 來源 |",
                      "|---|---|---|---|---|---|"])
        for resort_id, finding in rows:
            source_links = "<br>".join(
                f"[來源 {index}]({url})" for index, url in enumerate(finding["sources"], 1)
            ) or "—"
            lines.append(
                f"| {resort_id} | {finding['field']} | "
                f"{markdown_value(finding['current'])} | "
                f"{markdown_value(finding['suggested'])} | "
                f"{markdown_value(finding['note'])} | {source_links} |"
            )
        lines.append("")

    unverified = [(result["id"], finding) for result in results
                  for finding in result["findings"] if finding["severity"] == "unverified"]
    if unverified:
        lines.extend(["### ⚪ 無法覆核", "",
                      "| 雪場 | 欄位 | 原因 |", "|---|---|---|"])
        for resort_id, finding in unverified:
            lines.append(f"| {resort_id} | {finding['field']} | "
                         f"{markdown_value(finding['note'])} |")
        lines.append("")

    green_count = sum(result["status"] == "green" for result in results)
    lines.append(f"🟢 本批無差異：{green_count} / {len(results)} 個雪場。")
    return "\n".join(lines) + "\n"


def append_actions_summary(markdown):
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as summary:
        summary.write(markdown)


def run(dry_run=False, resort_id=None, batch=6, db_root=DB_ROOT,
        key=None, api_caller=call_gemini, url_opener=urllib.request.urlopen,
        resolver=resolve_source_url):
    resorts = load_resorts(db_root)
    previous = load_previous_report(db_root)
    selected = select_resorts(resorts, previous, resort_id, batch)
    selected_ids = [resort["id"] for resort in selected]

    if dry_run:
        mode = f"單一雪場 {resort_id}" if resort_id else f"最久未覆核的 {len(selected)} 個"
        print("===== 雪場覆核計畫（--dry-run；不連網、不寫檔）=====")
        print(f"模式：{mode}")
        print(f"選中：{', '.join(selected_ids)}")
        for resort in selected:
            checked = previous.get("last_checked", {}).get(resort["id"], "從未覆核")
            print(f"- {resort['id']}: URL GET + Gemini grounding（上次：{checked}）")
        print(f"預定報告：{db_root / REPORT}")
        return None

    key = key or os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("缺少 GEMINI_API_KEY 環境變數；可先用 --dry-run 檢查批次計畫")

    timestamp = now_jst()
    results = [verify_resort(resort, key, timestamp, api_caller, url_opener, resolver)
               for resort in selected]
    report = merge_report(previous, results, timestamp)
    report_path = db_root / REPORT
    if report_path.exists() and report_path.is_symlink():
        raise ValueError("覆核報告路徑是 symlink，拒絕寫入")
    atomic_write(report_path, json.dumps(report, ensure_ascii=False, indent=2))
    append_actions_summary(summary_markdown(results, timestamp))
    write_github_output("report_path", str(REPORT))
    write_github_output("checked", ",".join(selected_ids))
    print(f"✅ 已寫入 {REPORT}；本批 {len(results)} 個雪場")
    return report_path


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="覆核雪場資料並產出人工審查報告")
    parser.add_argument("--dry-run", action="store_true",
                        help="只印出批次計畫，不連網也不寫檔")
    parser.add_argument("--resort", help="只覆核指定雪場 id")
    parser.add_argument("--batch", type=int, default=6,
                        help="依輪替順序覆核幾個雪場（預設 6）")
    args = parser.parse_args(argv)
    if args.batch < 1:
        parser.error("--batch 必須大於 0")
    return args


def main(argv=None):
    args = parse_args(argv)
    try:
        run(dry_run=args.dry_run, resort_id=args.resort, batch=args.batch)
    except (OSError, ValueError, RuntimeError) as error:
        print(f"::error::{error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
