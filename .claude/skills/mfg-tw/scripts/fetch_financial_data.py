#!/usr/bin/env python3
"""Fetch quote and quarterly revenue data for FinanceX text valuation reports.

This script intentionally uses only the Python standard library so Claude Code
can run it from a fresh project without installing dependencies. Data comes from
Yahoo Finance's public, unofficial endpoints; treat failures as a signal to
cross-check with primary filings or company releases.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


USER_AGENT = "FinanceX-ClaudeCode-Skill/1.0"
REVENUE_TYPE = "quarterlyTotalRevenue"


def now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def request_json(url: str, timeout: int = 20) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json,text/plain,*/*",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")
    return json.loads(body)


def pct_change(current: float | None, previous: float | None) -> float | None:
    if current is None or previous in (None, 0):
        return None
    return (current - previous) / abs(previous) * 100


def parse_number(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        if math.isnan(value):
            return None
        return float(value)
    if isinstance(value, dict):
        return parse_number(value.get("raw"))
    if isinstance(value, str):
        text = value.strip().rstrip("%").replace(",", "")
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            return None
    return None


def safe_name(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return value.strip("_") or "output"


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def load_customer_file(path: str) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    if isinstance(data, list):
        return None, data

    if not isinstance(data, dict):
        raise ValueError("customers file must be a JSON object or a customer list")

    target = data.get("target")
    customers = data.get("customers", [])
    if not isinstance(customers, list):
        raise ValueError("customers must be a list")
    return target if isinstance(target, dict) else None, customers


def parse_customer_args(values: str | None) -> list[dict[str, Any]]:
    if not values:
        return []
    customers: list[dict[str, Any]] = []
    for symbol in values.split(","):
        symbol = symbol.strip()
        if symbol:
            customers.append({"ticker": symbol, "name": symbol})
    return customers


def unique_symbols(target: str, customers: list[dict[str, Any]], extra: str | None) -> list[str]:
    symbols: list[str] = [target]
    for item in customers:
        ticker = str(item.get("ticker") or "").strip()
        if ticker and ticker.upper() != "N/A":
            symbols.append(ticker)
    if extra:
        symbols.extend(s.strip() for s in extra.split(",") if s.strip())

    seen: set[str] = set()
    result: list[str] = []
    for symbol in symbols:
        key = symbol.upper()
        if key not in seen:
            seen.add(key)
            result.append(symbol)
    return result


def fetch_quotes(symbols: list[str], timeout: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not symbols:
        return {}, []
    query = urllib.parse.urlencode({"symbols": ",".join(symbols)})
    url = f"https://query1.finance.yahoo.com/v7/finance/quote?{query}"
    errors: list[dict[str, Any]] = []

    try:
        payload = request_json(url, timeout=timeout)
    except Exception as exc:  # noqa: BLE001 - keep CLI failures explicit
        return {}, [{"scope": "quotes", "url": url, "error": str(exc)}]

    quotes: dict[str, Any] = {}
    for item in payload.get("quoteResponse", {}).get("result", []):
        symbol = item.get("symbol")
        if symbol:
            quotes[symbol] = normalize_quote(item)

    missing = [symbol for symbol in symbols if symbol not in quotes]
    for symbol in missing:
        errors.append({"scope": "quotes", "symbol": symbol, "error": "not returned by Yahoo Finance"})
    return quotes, errors


def normalize_quote(item: dict[str, Any]) -> dict[str, Any]:
    market_time = item.get("regularMarketTime")
    if isinstance(market_time, (int, float)):
        market_time_iso = dt.datetime.fromtimestamp(market_time, dt.timezone.utc).isoformat()
    else:
        market_time_iso = None

    return {
        "symbol": item.get("symbol"),
        "short_name": item.get("shortName"),
        "long_name": item.get("longName"),
        "currency": item.get("currency"),
        "exchange": item.get("fullExchangeName") or item.get("exchange"),
        "market_state": item.get("marketState"),
        "regular_market_price": parse_number(item.get("regularMarketPrice")),
        "regular_market_change_pct": parse_number(item.get("regularMarketChangePercent")),
        "regular_market_time_utc": market_time_iso,
        "market_cap": parse_number(item.get("marketCap")),
        "trailing_pe": parse_number(item.get("trailingPE")),
        "forward_pe": parse_number(item.get("forwardPE")),
        "eps_trailing_12m": parse_number(item.get("epsTrailingTwelveMonths")),
        "eps_forward": parse_number(item.get("epsForward")),
        "price_to_book": parse_number(item.get("priceToBook")),
        "fifty_two_week_low": parse_number(item.get("fiftyTwoWeekLow")),
        "fifty_two_week_high": parse_number(item.get("fiftyTwoWeekHigh")),
    }


def fetch_revenue(symbol: str, timeout: int) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    end = int(time.time()) + 86400
    start = int((now_utc() - dt.timedelta(days=365 * 4)).timestamp())
    encoded_symbol = urllib.parse.quote(symbol, safe="")
    query = urllib.parse.urlencode(
        {
            "symbol": symbol,
            "type": REVENUE_TYPE,
            "period1": start,
            "period2": end,
        }
    )
    url = (
        "https://query1.finance.yahoo.com/ws/fundamentals-timeseries/v1/"
        f"finance/timeseries/{encoded_symbol}?{query}"
    )

    try:
        payload = request_json(url, timeout=timeout)
    except Exception as exc:  # noqa: BLE001 - keep CLI failures explicit
        return [], {"scope": "revenue", "symbol": symbol, "url": url, "error": str(exc)}

    entries = extract_revenue_entries(payload)
    if not entries:
        return [], {"scope": "revenue", "symbol": symbol, "url": url, "error": "no quarterly revenue data"}
    return entries, None


def extract_revenue_entries(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for block in payload.get("timeseries", {}).get("result", []):
        values = block.get(REVENUE_TYPE)
        if not isinstance(values, list):
            continue
        for item in values:
            if not isinstance(item, dict):
                continue
            value = parse_number(item.get("reportedValue"))
            if value is None:
                continue
            period_end = item.get("asOfDate") or item.get("period")
            if not period_end:
                continue
            rows.append(
                {
                    "period_end": period_end,
                    "period_type": item.get("periodType"),
                    "revenue": value,
                    "currency": item.get("currencyCode"),
                }
            )

    rows = sorted(rows, key=lambda row: row["period_end"])
    for index, row in enumerate(rows):
        previous_quarter = rows[index - 1]["revenue"] if index >= 1 else None
        previous_year = rows[index - 4]["revenue"] if index >= 4 else None
        row["qoq_pct"] = pct_change(row["revenue"], previous_quarter)
        row["yoy_pct"] = pct_change(row["revenue"], previous_year)
    return rows


def latest_revenue_stats(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not rows:
        return None
    latest = rows[-1]
    return {
        "period_end": latest.get("period_end"),
        "revenue": latest.get("revenue"),
        "currency": latest.get("currency"),
        "yoy_pct": latest.get("yoy_pct"),
        "qoq_pct": latest.get("qoq_pct"),
    }


def enrich_customers(customers: list[dict[str, Any]], revenue: dict[str, Any]) -> tuple[list[dict[str, Any]], float | None]:
    enriched: list[dict[str, Any]] = []
    contributions: list[float] = []

    for item in customers:
        row = dict(item)
        ticker = str(row.get("ticker") or "").strip()
        latest = latest_revenue_stats(revenue.get(ticker, [])) if ticker and ticker.upper() != "N/A" else None
        row["latest_revenue"] = latest

        weight = parse_number(row.get("revenue_weight_pct"))
        factor = parse_number(row.get("pass_through_factor"))
        yoy = parse_number(latest.get("yoy_pct")) if latest else None
        if factor is None:
            factor = 1.0
            row["pass_through_factor"] = factor

        if weight is not None and yoy is not None:
            contribution = weight / 100 * yoy * factor
            row["weighted_contribution_pct"] = contribution
            contributions.append(contribution)
        else:
            row["weighted_contribution_pct"] = None
        enriched.append(row)

    expected = sum(contributions) if contributions else None
    return enriched, expected


def fmt_pct(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.2f}%"


def fmt_num(value: float | None) -> str:
    if value is None:
        return "N/A"
    if abs(value) >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B"
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    return f"{value:,.2f}"


def write_markdown(path: str, result: dict[str, Any]) -> None:
    lines: list[str] = []
    lines.append("# FinanceX Data Snapshot")
    lines.append("")
    lines.append(f"- Generated at: {result['generated_at_utc']}")
    lines.append(f"- Target: {result['target']['ticker']}")
    if result.get("expected_revenue_growth_pct") is not None:
        lines.append(f"- Expected transmitted revenue growth: {fmt_pct(result['expected_revenue_growth_pct'])}")
    lines.append("")

    lines.append("## Quotes")
    lines.append("")
    lines.append("| Symbol | Name | Price | Currency | Market time UTC | Market cap | Trailing P/E | Forward P/E |")
    lines.append("| --- | --- | ---: | --- | --- | ---: | ---: | ---: |")
    for symbol, quote in sorted(result.get("quotes", {}).items()):
        lines.append(
            "| {symbol} | {name} | {price} | {currency} | {time} | {market_cap} | {trailing_pe} | {forward_pe} |".format(
                symbol=symbol,
                name=quote.get("long_name") or quote.get("short_name") or "",
                price=fmt_num(quote.get("regular_market_price")),
                currency=quote.get("currency") or "",
                time=quote.get("regular_market_time_utc") or "",
                market_cap=fmt_num(quote.get("market_cap")),
                trailing_pe=fmt_num(quote.get("trailing_pe")),
                forward_pe=fmt_num(quote.get("forward_pe")),
            )
        )
    lines.append("")

    lines.append("## Latest Quarterly Revenue")
    lines.append("")
    lines.append("| Symbol | Period end | Revenue | Currency | YoY | QoQ |")
    lines.append("| --- | --- | ---: | --- | ---: | ---: |")
    for symbol, rows in sorted(result.get("quarterly_revenue", {}).items()):
        latest = latest_revenue_stats(rows)
        if latest:
            lines.append(
                "| {symbol} | {period} | {revenue} | {currency} | {yoy} | {qoq} |".format(
                    symbol=symbol,
                    period=latest.get("period_end") or "",
                    revenue=fmt_num(latest.get("revenue")),
                    currency=latest.get("currency") or "",
                    yoy=fmt_pct(latest.get("yoy_pct")),
                    qoq=fmt_pct(latest.get("qoq_pct")),
                )
            )
        else:
            lines.append(f"| {symbol} | N/A | N/A |  | N/A | N/A |")
    lines.append("")

    customers = result.get("customers", [])
    if customers:
        lines.append("## Customer Momentum")
        lines.append("")
        lines.append("| Customer | Ticker | Weight | Latest YoY | Pass-through | Contribution | Confidence |")
        lines.append("| --- | --- | ---: | ---: | ---: | ---: | --- |")
        for item in customers:
            latest = item.get("latest_revenue") or {}
            lines.append(
                "| {name} | {ticker} | {weight} | {yoy} | {factor} | {contribution} | {confidence} |".format(
                    name=item.get("name") or "",
                    ticker=item.get("ticker") or "",
                    weight=fmt_pct(parse_number(item.get("revenue_weight_pct"))),
                    yoy=fmt_pct(parse_number(latest.get("yoy_pct"))),
                    factor=fmt_num(parse_number(item.get("pass_through_factor"))),
                    contribution=fmt_pct(parse_number(item.get("weighted_contribution_pct"))),
                    confidence=item.get("confidence") or "",
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


def write_revenue_csv(path: str, revenue: dict[str, list[dict[str, Any]]]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["symbol", "period_end", "period_type", "revenue", "currency", "yoy_pct", "qoq_pct"],
        )
        writer.writeheader()
        for symbol, rows in sorted(revenue.items()):
            for row in rows:
                csv_row = {"symbol": symbol}
                csv_row.update(row)
                writer.writerow(csv_row)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch Yahoo Finance quote and quarterly revenue data for FinanceX valuation inputs."
    )
    parser.add_argument("--target", required=True, help="Target ticker, for example 2330.TW or 3529.TWO.")
    parser.add_argument("--target-name", default=None, help="Optional target company name.")
    parser.add_argument("--customers", default=None, help="Comma-separated customer tickers, for example AAPL,NVDA.")
    parser.add_argument("--customers-file", default=None, help="JSON file with target and customers metadata.")
    parser.add_argument("--extra-tickers", default=None, help="Additional comma-separated tickers to fetch as proxies.")
    parser.add_argument("--out", default=None, help="Output directory. Defaults to .cache/mfg-tw/<target>_<timestamp>.")
    parser.add_argument("--timeout", type=int, default=20, help="HTTP timeout in seconds.")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    generated_at = now_utc()

    file_target: dict[str, Any] | None = None
    customers: list[dict[str, Any]] = []
    if args.customers_file:
        file_target, customers = load_customer_file(args.customers_file)
    customers.extend(parse_customer_args(args.customers))

    target = {
        "ticker": args.target,
        "name": args.target_name or (file_target or {}).get("name"),
    }
    symbols = unique_symbols(args.target, customers, args.extra_tickers)

    if args.out:
        out_dir = args.out
    else:
        stamp = generated_at.strftime("%Y%m%dT%H%M%SZ")
        out_dir = os.path.join(".cache", "mfg-tw", f"{safe_name(args.target)}_{stamp}")
    ensure_dir(out_dir)

    quotes, quote_errors = fetch_quotes(symbols, timeout=args.timeout)

    quarterly_revenue: dict[str, list[dict[str, Any]]] = {}
    errors: list[dict[str, Any]] = list(quote_errors)
    for symbol in symbols:
        rows, error = fetch_revenue(symbol, timeout=args.timeout)
        quarterly_revenue[symbol] = rows
        if error:
            errors.append(error)

    enriched_customers, expected_growth = enrich_customers(customers, quarterly_revenue)

    result = {
        "generated_at_utc": generated_at.isoformat(),
        "data_source": "Yahoo Finance public unofficial endpoints",
        "target": target,
        "symbols": symbols,
        "quotes": quotes,
        "quarterly_revenue": quarterly_revenue,
        "customers": enriched_customers,
        "expected_revenue_growth_pct": expected_growth,
        "errors": errors,
    }

    json_path = os.path.join(out_dir, "finance_data.json")
    md_path = os.path.join(out_dir, "finance_data.md")
    csv_path = os.path.join(out_dir, "quarterly_revenue.csv")

    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
    write_markdown(md_path, result)
    write_revenue_csv(csv_path, quarterly_revenue)

    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    print(f"Wrote {csv_path}")
    if errors:
        print(f"Completed with {len(errors)} fetch warning(s). Review finance_data.md.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
