#!/usr/bin/env python3
"""Fetch recent news candidates for supply-chain evidence discovery.

The script collects candidate articles only. Claude Code should read the output,
triage evidence quality, download selected source pages, and then update the
customer map with source-backed supply-chain claims.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import datetime as dt
import email.utils
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any


USER_AGENT = "FinanceX-ClaudeCode-Skill/1.0"
DEFAULT_KEYWORDS = [
    "supply chain",
    "customer",
    "major customer",
    "largest customer",
    "top customer",
    "orders",
    "shipments",
    "supplier",
    "revenue",
    "production capacity",
    "capacity utilization",
    "backlog",
    "procurement",
    "end-market demand",
]


def now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def safe_name(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return value.strip("_") or "news"


def request_text(url: str, timeout: int = 25) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/rss+xml,application/json,text/xml,text/plain,*/*",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read()
        content_type = response.headers.get("content-type", "")
    charset = "utf-8"
    match = re.search(r"charset=([^;]+)", content_type, flags=re.I)
    if match:
        charset = match.group(1).strip()
    try:
        return body.decode(charset, errors="replace")
    except LookupError:
        return body.decode("utf-8", errors="replace")


def parse_rss_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        parsed = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return value
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc).isoformat()


def parse_gdelt_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        parsed = dt.datetime.strptime(value, "%Y%m%dT%H%M%SZ")
    except ValueError:
        return value
    return parsed.replace(tzinfo=dt.timezone.utc).isoformat()


def build_queries(
    target_name: str,
    target_ticker: str | None,
    aliases: list[str],
    thesis: str | None,
    keywords: list[str],
    explicit_queries: list[str],
) -> list[str]:
    queries: list[str] = []

    for query in explicit_queries:
        if query.strip():
            queries.append(query.strip())

    base_aliases = [target_name]
    if target_ticker:
        base_aliases.append(target_ticker)
        base_aliases.append(target_ticker.split(".")[0])
    base_aliases.extend(aliases)

    cleaned_aliases: list[str] = []
    seen_aliases: set[str] = set()
    for alias in base_aliases:
        alias = alias.strip()
        key = alias.lower()
        if alias and key not in seen_aliases:
            seen_aliases.add(key)
            cleaned_aliases.append(alias)

    if thesis:
        for alias in cleaned_aliases[:3]:
            queries.append(f"{alias} {thesis}")

    for alias in cleaned_aliases[:3]:
        for keyword in keywords:
            queries.append(f"{alias} {keyword}")

    seen_queries: set[str] = set()
    result: list[str] = []
    for query in queries:
        normalized = re.sub(r"\s+", " ", query).strip()
        key = normalized.lower()
        if normalized and key not in seen_queries:
            seen_queries.add(key)
            result.append(normalized)
    return result


def fetch_google_news(
    query: str,
    days: int,
    max_items: int,
    timeout: int,
    language: str,
    country: str,
    ceid: str,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    rss_query = f"{query} when:{days}d"
    params = urllib.parse.urlencode(
        {
            "q": rss_query,
            "hl": language,
            "gl": country,
            "ceid": ceid,
        }
    )
    url = f"https://news.google.com/rss/search?{params}"
    try:
        text = request_text(url, timeout=timeout)
        root = ET.fromstring(text)
    except Exception as exc:  # noqa: BLE001 - report per-query failure
        return [], {"source": "google_news", "query": query, "url": url, "error": str(exc)}

    items: list[dict[str, Any]] = []
    for item in root.findall("./channel/item")[:max_items]:
        source = item.find("source")
        items.append(
            {
                "search_source": "google_news",
                "query": query,
                "title": text_or_none(item.findtext("title")),
                "url": text_or_none(item.findtext("link")),
                "published_at_utc": parse_rss_date(item.findtext("pubDate")),
                "publisher": text_or_none(source.text if source is not None else None),
                "publisher_url": source.attrib.get("url") if source is not None else None,
            }
        )
    return items, None


def fetch_gdelt(
    query: str,
    days: int,
    max_items: int,
    timeout: int,
    retries: int = 3,
    backoff: float = 5.0,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    params = urllib.parse.urlencode(
        {
            "query": query,
            "mode": "artlist",
            "format": "json",
            "maxrecords": max_items,
            "sort": "datedesc",
            "timespan": f"{days}d",
        }
    )
    url = f"https://api.gdeltproject.org/api/v2/doc/doc?{params}"
    # GDELT aggressively rate-limits (HTTP 429). Retry with exponential backoff
    # before giving up so a single throttled response does not drop the query.
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            payload = json.loads(request_text(url, timeout=timeout))
            break
        except urllib.error.HTTPError as exc:
            last_exc = exc
            if exc.code == 429 and attempt < retries - 1:
                time.sleep(backoff * (attempt + 1))
                continue
            return [], {"source": "gdelt", "query": query, "url": url, "error": str(exc)}
        except Exception as exc:  # noqa: BLE001 - report per-query failure
            return [], {"source": "gdelt", "query": query, "url": url, "error": str(exc)}
    else:
        return [], {"source": "gdelt", "query": query, "url": url, "error": str(last_exc)}

    articles = payload.get("articles", [])
    if not isinstance(articles, list):
        return [], {"source": "gdelt", "query": query, "url": url, "error": "unexpected response shape"}

    items: list[dict[str, Any]] = []
    for article in articles[:max_items]:
        if not isinstance(article, dict):
            continue
        items.append(
            {
                "search_source": "gdelt",
                "query": query,
                "title": article.get("title"),
                "url": article.get("url"),
                "published_at_utc": parse_gdelt_date(article.get("seendate")),
                "publisher": article.get("sourcecountry") or article.get("domain"),
                "publisher_url": article.get("domain"),
                "language": article.get("language"),
            }
        )
    return items, None


def text_or_none(value: str | None) -> str | None:
    if value is None:
        return None
    value = re.sub(r"\s+", " ", value).strip()
    return value or None


def normalize_url(url: str | None) -> str:
    if not url:
        return ""
    parsed = urllib.parse.urlparse(url)
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


def dedupe_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    result: list[dict[str, Any]] = []
    for item in items:
        url_key = normalize_url(item.get("url"))
        title_key = re.sub(r"\W+", "", str(item.get("title") or "").lower())
        if url_key and url_key in seen_urls:
            continue
        if title_key and title_key in seen_titles:
            continue
        if url_key:
            seen_urls.add(url_key)
        if title_key:
            seen_titles.add(title_key)
        result.append(item)
    return result


def write_markdown(path: str, result: dict[str, Any]) -> None:
    lines: list[str] = []
    lines.append("# Recent News Candidates")
    lines.append("")
    lines.append(f"- Generated at: {result['generated_at_utc']}")
    lines.append(f"- Target: {result['target_name']} ({result.get('target_ticker') or 'N/A'})")
    lines.append(f"- Lookback days: {result['days']}")
    lines.append("")
    lines.append("## How Claude Code should use this")
    lines.append("")
    lines.append("1. Keep articles that contain concrete supply-chain claims: customer, supplier, order, shipment, product allocation, capacity, or pricing.")
    lines.append("2. Discard generic price commentary, duplicated syndicated pieces, and articles with no identifiable source.")
    lines.append("3. Download selected URLs with `fetch_source_pages.py` before updating `customers.json`.")
    lines.append("4. Assign confidence from evidence quality, not from how plausible the claim feels.")
    lines.append("")
    lines.append("## Search Queries")
    lines.append("")
    for query in result.get("queries", []):
        lines.append(f"- {query}")
    lines.append("")
    lines.append("## Candidates")
    lines.append("")
    lines.append("| # | Date UTC | Source | Publisher | Title | URL | Query |")
    lines.append("| ---: | --- | --- | --- | --- | --- | --- |")
    for index, item in enumerate(result.get("items", []), start=1):
        lines.append(
            "| {index} | {date} | {source} | {publisher} | {title} | {url} | {query} |".format(
                index=index,
                date=item.get("published_at_utc") or "",
                source=item.get("search_source") or "",
                publisher=item.get("publisher") or "",
                title=(item.get("title") or "").replace("|", "\\|"),
                url=item.get("url") or "",
                query=(item.get("query") or "").replace("|", "\\|"),
            )
        )
    lines.append("")

    errors = result.get("errors", [])
    if errors:
        lines.append("## Fetch Errors")
        lines.append("")
        for error in errors:
            lines.append(f"- {json.dumps(error, ensure_ascii=False)}")
        lines.append("")

    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def write_csv(path: str, items: list[dict[str, Any]]) -> None:
    fields = ["search_source", "query", "published_at_utc", "publisher", "publisher_url", "title", "url", "language"]
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in items:
            writer.writerow({field: item.get(field) for field in fields})


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch recent news candidates for supply-chain evidence.")
    parser.add_argument("--target-name", required=True, help="Company name, for example Toyota Motor or Siemens.")
    parser.add_argument("--target-ticker", default=None, help="Optional provider ticker, for example 7203.T or SIE.DE.")
    parser.add_argument("--alias", action="append", default=[], help="Company alias. Can be repeated.")
    parser.add_argument("--thesis", default=None, help="Optional investment thesis or catalyst keywords.")
    parser.add_argument("--keyword", action="append", default=[], help="Supply-chain search keyword. Can be repeated.")
    parser.add_argument("--query", action="append", default=[], help="Explicit query to search. Can be repeated.")
    parser.add_argument("--days", type=int, default=45, help="Lookback window in days.")
    parser.add_argument("--max-per-query", type=int, default=8, help="Maximum items per source query.")
    parser.add_argument("--max-queries", type=int, default=24, help="Cap on the number of generated queries (keeps runtime bounded).")
    parser.add_argument("--workers", type=int, default=8, help="Parallel HTTP workers for Google News fetches.")
    parser.add_argument("--gdelt-delay", type=float, default=6.0, help="Seconds to wait between GDELT requests to avoid HTTP 429 rate limiting.")
    parser.add_argument(
        "--source",
        choices=["google", "gdelt", "both"],
        default="google",
        help="Search source to use. Default 'google'. GDELT is rate-limited and runs sequentially.",
    )
    parser.add_argument("--google-language", default="en-US", help="Google News hl locale. Default: en-US.")
    parser.add_argument("--google-country", default="US", help="Google News gl country. Default: US.")
    parser.add_argument("--google-ceid", default="US:en", help="Google News ceid value. Default: US:en.")
    parser.add_argument("--out", default=None, help="Output directory. Defaults to .cache/mfg-global/news_<target>_<timestamp>.")
    parser.add_argument("--timeout", type=int, default=15, help="HTTP timeout in seconds.")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    generated_at = now_utc()
    keywords = list(DEFAULT_KEYWORDS)
    keywords.extend(args.keyword)
    queries = build_queries(
        target_name=args.target_name,
        target_ticker=args.target_ticker,
        aliases=args.alias,
        thesis=args.thesis,
        keywords=keywords,
        explicit_queries=args.query,
    )

    if args.max_queries and args.max_queries > 0:
        queries = queries[: args.max_queries]

    if args.out:
        out_dir = args.out
    else:
        stamp = generated_at.strftime("%Y%m%dT%H%M%SZ")
        out_dir = os.path.join(".cache", "mfg-global", f"news_{safe_name(args.target_name)}_{stamp}")
    ensure_dir(out_dir)

    all_items: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    # Google News RSS is fast and tolerates concurrency, so fan the queries out.
    if args.source in {"google", "both"}:
        workers = max(1, min(args.workers, len(queries) or 1))
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [
                pool.submit(
                    fetch_google_news,
                    query,
                    args.days,
                    args.max_per_query,
                    args.timeout,
                    args.google_language,
                    args.google_country,
                    args.google_ceid,
                )
                for query in queries
            ]
            for future in futures:
                items, error = future.result()
                all_items.extend(items)
                if error:
                    errors.append(error)

    # GDELT rate-limits hard (HTTP 429); keep it strictly sequential and throttled.
    if args.source in {"gdelt", "both"}:
        for index, query in enumerate(queries):
            if index > 0 and args.gdelt_delay > 0:
                time.sleep(args.gdelt_delay)
            items, error = fetch_gdelt(query, args.days, args.max_per_query, args.timeout)
            all_items.extend(items)
            if error:
                errors.append(error)

    items = dedupe_items(all_items)
    result = {
        "generated_at_utc": generated_at.isoformat(),
        "target_name": args.target_name,
        "target_ticker": args.target_ticker,
        "days": args.days,
        "queries": queries,
        "items": items,
        "errors": errors,
    }

    json_path = os.path.join(out_dir, "news_candidates.json")
    md_path = os.path.join(out_dir, "news_candidates.md")
    csv_path = os.path.join(out_dir, "news_candidates.csv")
    query_path = os.path.join(out_dir, "search_queries.txt")

    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
    write_markdown(md_path, result)
    write_csv(csv_path, items)
    with open(query_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(queries) + "\n")

    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    print(f"Wrote {csv_path}")
    print(f"Wrote {query_path}")
    if errors:
        print(f"Completed with {len(errors)} fetch warning(s). Review news_candidates.md.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
