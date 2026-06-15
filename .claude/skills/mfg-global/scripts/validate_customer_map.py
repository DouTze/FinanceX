#!/usr/bin/env python3
"""Validate a FinanceX supply-chain customer map before valuation."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import urllib.parse
from typing import Any


GENERIC_SOURCE_PATTERNS = [
    re.compile(r"\bsupply[- ]chain estimates?\b", re.I),
    re.compile(r"\bmarket estimates?\b", re.I),
    re.compile(r"\bannual report\s*/\s*supply", re.I),
    re.compile(r"供應鏈推估"),
    re.compile(r"市場推估"),
]
OFFICIAL_EVIDENCE_TYPES = {"official_disclosure", "filing", "annual_report", "earnings_call", "investor_presentation"}


def parse_date(value: Any) -> dt.date | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text == "YYYY-MM-DD":
        return None
    try:
        return dt.date.fromisoformat(text[:10])
    except ValueError:
        return None


def is_url(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urllib.parse.urlparse(value.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def is_generic_source(value: Any) -> bool:
    if not isinstance(value, str):
        return True
    text = value.strip()
    if not text or text == "annual report, investor presentation, or reputable supply-chain source URL":
        return True
    return any(pattern.search(text) for pattern in GENERIC_SOURCE_PATTERNS)


def validate_customer_map(data: dict[str, Any], max_age_days: int) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    today = dt.datetime.now(dt.timezone.utc).date()

    target = data.get("target")
    if not isinstance(target, dict):
        errors.append("missing object: target")
    else:
        for field in ("ticker", "name"):
            if not str(target.get(field) or "").strip():
                errors.append(f"target.{field} is required")

    customers = data.get("customers")
    if not isinstance(customers, list) or not customers:
        errors.append("customers must be a non-empty list")
        return errors, warnings

    for index, customer in enumerate(customers, start=1):
        prefix = f"customers[{index}]"
        if not isinstance(customer, dict):
            errors.append(f"{prefix} must be an object")
            continue

        for field in ("name", "ticker", "relation", "confidence"):
            if not str(customer.get(field) or "").strip():
                errors.append(f"{prefix}.{field} is required")

        confidence = str(customer.get("confidence") or "").strip().lower()
        if confidence not in {"high", "medium", "low"}:
            errors.append(f"{prefix}.confidence must be high, medium, or low")

        if is_generic_source(customer.get("source")):
            errors.append(f"{prefix}.source is generic; use a concrete source title or URL")

        verified = parse_date(customer.get("last_verified"))
        if verified is None:
            errors.append(f"{prefix}.last_verified must be YYYY-MM-DD from the newest supporting evidence")
        elif (today - verified).days > max_age_days:
            warnings.append(f"{prefix}.last_verified is older than {max_age_days} days: {verified.isoformat()}")

        evidence = customer.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"{prefix}.evidence must contain at least one evidence item")
            continue

        official_count = 0
        independent_hosts: set[str] = set()
        for evidence_index, item in enumerate(evidence, start=1):
            item_prefix = f"{prefix}.evidence[{evidence_index}]"
            if not isinstance(item, dict):
                errors.append(f"{item_prefix} must be an object")
                continue
            for field in ("type", "title", "url", "published_date", "claim"):
                if not str(item.get(field) or "").strip():
                    errors.append(f"{item_prefix}.{field} is required")
            if not is_url(item.get("url")):
                errors.append(f"{item_prefix}.url must be http(s)")
            else:
                host = urllib.parse.urlparse(str(item["url"])).netloc.lower()
                if host:
                    independent_hosts.add(host)
            if parse_date(item.get("published_date")) is None:
                errors.append(f"{item_prefix}.published_date must be YYYY-MM-DD")
            if str(item.get("type") or "").strip() in OFFICIAL_EVIDENCE_TYPES:
                official_count += 1

        if confidence == "high" and official_count == 0 and len(independent_hosts) < 2:
            errors.append(f"{prefix}.confidence cannot be high without official evidence or two independent sources")

    weights = []
    for customer in customers:
        if isinstance(customer, dict) and isinstance(customer.get("revenue_weight_pct"), (int, float)):
            weights.append(float(customer["revenue_weight_pct"]))
    if weights and weights != sorted(weights, reverse=True):
        warnings.append("customers are not sorted by revenue_weight_pct descending")

    return errors, warnings


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate FinanceX customers.json before running valuation.")
    parser.add_argument("--customers-file", required=True, help="Path to customers.json")
    parser.add_argument("--max-age-days", type=int, default=90, help="Warn when evidence is older than this many days.")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as failures.")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    with open(args.customers_file, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    errors, warnings = validate_customer_map(data, max_age_days=args.max_age_days)
    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)

    if errors or (args.strict and warnings):
        return 1
    print(f"OK: {args.customers_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
