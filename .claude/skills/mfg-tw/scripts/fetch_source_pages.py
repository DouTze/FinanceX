#!/usr/bin/env python3
"""Download source pages and extract readable text for FinanceX reports."""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from typing import Any


USER_AGENT = "FinanceX-ClaudeCode-Skill/1.0"


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.title_parts: list[str] = []
        self.skip_depth = 0
        self.in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "svg"}:
            self.skip_depth += 1
        if tag == "title":
            self.in_title = True
        if tag in {"p", "div", "section", "article", "tr", "li", "br", "h1", "h2", "h3"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "svg"} and self.skip_depth:
            self.skip_depth -= 1
        if tag == "title":
            self.in_title = False
        if tag in {"p", "div", "section", "article", "tr", "li", "h1", "h2", "h3"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self.skip_depth:
            return
        text = data.strip()
        if not text:
            return
        if self.in_title:
            self.title_parts.append(text)
        self.parts.append(text)
        self.parts.append(" ")

    def output(self) -> tuple[str | None, str]:
        title = " ".join(self.title_parts).strip() or None
        text = html.unescape("".join(self.parts))
        text = re.sub(r"[ \t\r\f\v]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = "\n".join(line.strip() for line in text.splitlines())
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        return title, text


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def safe_name(value: str) -> str:
    parsed = urllib.parse.urlparse(value)
    host = parsed.netloc or "source"
    path = parsed.path.strip("/") or "index"
    name = f"{host}_{path}"
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    return name[:120].strip("_") or "source"


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def fetch_url(url: str, timeout: int) -> tuple[bytes, str | None, int | None]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/pdf,text/plain,*/*",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read()
        content_type = response.headers.get("content-type")
        status = getattr(response, "status", None)
    return body, content_type, status


def decode_body(body: bytes, content_type: str | None) -> str:
    charset = "utf-8"
    if content_type:
        match = re.search(r"charset=([^;]+)", content_type, flags=re.I)
        if match:
            charset = match.group(1).strip()
    try:
        return body.decode(charset, errors="replace")
    except LookupError:
        return body.decode("utf-8", errors="replace")


def extract_text(body: bytes, content_type: str | None) -> tuple[str | None, str]:
    text = decode_body(body, content_type)
    if content_type and "html" not in content_type.lower():
        return None, text.strip()

    parser = TextExtractor()
    parser.feed(text)
    return parser.output()


def write_markdown(path: str, records: list[dict[str, Any]]) -> None:
    lines = ["# Downloaded Sources", ""]
    for index, record in enumerate(records, start=1):
        lines.append(f"## {index}. {record.get('title') or record.get('url')}")
        lines.append("")
        lines.append(f"- URL: {record.get('url')}")
        lines.append(f"- Fetched at: {record.get('fetched_at_utc')}")
        lines.append(f"- Status: {record.get('status') or 'N/A'}")
        lines.append(f"- Content type: {record.get('content_type') or 'N/A'}")
        if record.get("error"):
            lines.append(f"- Error: {record['error']}")
        else:
            lines.append(f"- Text file: {record.get('text_file')}")
            lines.append(f"- Raw file: {record.get('raw_file')}")
        lines.append("")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Download source URLs and extract readable text.")
    parser.add_argument("urls", nargs="*", help="URLs to fetch.")
    parser.add_argument("--url", action="append", default=[], help="URL to fetch. Can be repeated.")
    parser.add_argument("--out", default=None, help="Output directory. Defaults to .cache/mfg-tw/sources_<timestamp>.")
    parser.add_argument("--timeout", type=int, default=25, help="HTTP timeout in seconds.")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    urls = list(args.urls) + list(args.url or [])
    if not urls:
        print("No URLs provided.", file=sys.stderr)
        return 2

    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = args.out or os.path.join(".cache", "mfg-tw", f"sources_{stamp}")
    raw_dir = os.path.join(out_dir, "raw")
    text_dir = os.path.join(out_dir, "text")
    ensure_dir(raw_dir)
    ensure_dir(text_dir)

    records: list[dict[str, Any]] = []
    for url in urls:
        base = safe_name(url)
        record: dict[str, Any] = {
            "url": url,
            "fetched_at_utc": now_utc(),
        }
        try:
            body, content_type, status = fetch_url(url, timeout=args.timeout)
            title, text = extract_text(body, content_type)

            raw_path = os.path.join(raw_dir, f"{base}.raw")
            text_path = os.path.join(text_dir, f"{base}.txt")
            with open(raw_path, "wb") as handle:
                handle.write(body)
            with open(text_path, "w", encoding="utf-8") as handle:
                handle.write(text)

            record.update(
                {
                    "status": status,
                    "content_type": content_type,
                    "title": title,
                    "raw_file": raw_path,
                    "text_file": text_path,
                    "text_chars": len(text),
                }
            )
        except Exception as exc:  # noqa: BLE001 - preserve per-URL failure details
            record["error"] = str(exc)
        records.append(record)

    json_path = os.path.join(out_dir, "sources.json")
    md_path = os.path.join(out_dir, "sources.md")
    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(records, handle, ensure_ascii=False, indent=2)
    write_markdown(md_path, records)

    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
