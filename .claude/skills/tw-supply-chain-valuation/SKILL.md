---
name: Taiwan Supply Chain Valuation
description: Analyze Taiwan-listed stocks with supply-chain customer revenue momentum and produce a text-only valuation report. Use when the user asks whether a Taiwan stock is buyable, undervalued, overvalued, or wants FinanceX industry-chain analysis. Do not build or launch Streamlit or any web UI for this workflow.
---

# Taiwan Supply Chain Valuation

## Operating Mode

Run this workflow as a text-mode financial analysis inside Claude Code.

- Do not create, start, or depend on Streamlit, dashboards, browser UIs, or long-running services.
- Return the analysis directly in chat as structured Markdown.
- Prefer current, source-backed data. If the stock price, financial data, management, regulation, or market context could have changed, verify it before using it.
- Use absolute dates for prices and financial periods.
- State currency and market clearly, usually `TWD` for Taiwan prices and `USD` for US-listed customers.
- Treat the result as decision support, not a guarantee. Do not claim a trade is certain to profit.

## Input Handling

Accept short requests such as:

```text
/tw-supply-chain-valuation 2330.TW 台積電 是否可買
/tw-supply-chain-valuation 3529.TWO 力旺 因 AI ASIC 需求是否有上修空間
```

If the user gives only a Taiwan stock code, infer the company name when possible. If the user gives a 4-digit Taiwan code without a suffix, resolve whether it is listed or OTC:

- Listed Taiwan stocks use `.TW`, for example `2330.TW`.
- OTC Taiwan stocks use `.TWO`, for example `3529.TWO`.

If the request includes a thesis or reason, make it the focal hypothesis. If a required input cannot be inferred safely, ask one concise question before continuing.

## Bundled Data Tools

Use the bundled scripts before making the final valuation whenever current market or quarterly revenue data is needed.

Run all Python scripts through `uv`; do not call `python3` or a local virtualenv directly. Use `uv --cache-dir .cache/uv run python` for bundled scripts because they only depend on the Python standard library and should not require this repository to have a `pyproject.toml`. Keep the uv cache under `.cache/uv` so execution does not depend on writable global cache directories. If `uv` is unavailable, report that as an environment blocker instead of silently switching runtimes.

If you need to write a temporary source-specific scraper that uses third-party packages, put it under `.cache/tw-supply-chain-valuation/<target>/` and run it with `uv --cache-dir .cache/uv run --with <package> python <script>`.

1. Collect recent news candidates for current supply-chain evidence:

```bash
uv --cache-dir .cache/uv run python ${CLAUDE_SKILL_DIR}/scripts/fetch_recent_news.py \
  --target-name "<target-company-name>" \
  --target-ticker <target-ticker> \
  --thesis "<user-thesis-or-catalyst>" \
  --days 45 \
  --out .cache/tw-supply-chain-valuation/<target>/news
```

Read `.cache/tw-supply-chain-valuation/<target>/news/news_candidates.md`. Keep only articles that contain concrete supply-chain claims: named customer, named supplier, order, shipment, product allocation, capacity change, pricing, or end-market demand. Discard generic stock-price commentary and unsourced rumors.

2. Download the selected articles and primary documents:

```bash
uv --cache-dir .cache/uv run python ${CLAUDE_SKILL_DIR}/scripts/fetch_source_pages.py \
  --out .cache/tw-supply-chain-valuation/<target>/sources \
  --url "https://example.com/selected-news-1" \
  --url "https://example.com/selected-news-2"
```

Read `.cache/tw-supply-chain-valuation/<target>/sources/sources.md` and relevant extracted text files before finalizing customer relationships or weights.

3. Rewrite the task-local customer map from the news evidence. This is mandatory.

```text
${CLAUDE_SKILL_DIR}/templates/customers.json
```

Write or overwrite the working copy under `.cache/tw-supply-chain-valuation/<target>/customers.json`. Do not reuse a previous `customers.json` row unless the current news/source review still supports it. Fill in:

- `target.ticker` and `target.name`
- up to five `customers`
- `ticker`, `relation`, `revenue_weight_pct`, `pass_through_factor`, `confidence`, `source`, `last_verified`, and `evidence`

Every customer row must include at least one concrete evidence item with `type`, `title`, `url`, `published_date`, and `claim`. If recent evidence changes the ranking or weight, update the ranking and weight. For example, if recent sources show Nvidia has overtaken Apple as TSMC's largest customer, Nvidia must be first and Apple must not remain the largest row.

4. Validate the customer map before using it:

```bash
uv --cache-dir .cache/uv run python ${CLAUDE_SKILL_DIR}/scripts/validate_customer_map.py \
  --customers-file .cache/tw-supply-chain-valuation/<target>/customers.json \
  --max-age-days 180 \
  --strict
```

If validation fails, fix `customers.json` and rerun validation. Do not continue to quote/revenue fetching until validation passes.

5. If you later find additional source URLs for annual reports, investor presentations, customer disclosures, or financial news, download them with:

```bash
uv --cache-dir .cache/uv run python ${CLAUDE_SKILL_DIR}/scripts/fetch_source_pages.py \
  --out .cache/tw-supply-chain-valuation/<target>/sources \
  --url "https://example.com/source-1" \
  --url "https://example.com/source-2"
```

Read `.cache/tw-supply-chain-valuation/<target>/sources/sources.md` and any relevant extracted text files before finalizing customer relationships or weights.

6. Fetch quote and quarterly revenue data:

```bash
uv --cache-dir .cache/uv run python ${CLAUDE_SKILL_DIR}/scripts/fetch_financial_data.py \
  --target <target-ticker> \
  --target-name "<target-company-name>" \
  --customers-file .cache/tw-supply-chain-valuation/<target>/customers.json \
  --out .cache/tw-supply-chain-valuation/<target>/financials
```

Read `.cache/tw-supply-chain-valuation/<target>/financials/finance_data.md` first, then inspect `finance_data.json` or `quarterly_revenue.csv` if the numbers need auditing.

If a bundled script fails because the network, Yahoo Finance endpoint, or a source page is unavailable, do not invent data. Use available web/search tools or write a small source-specific scraper in the task cache, run it, and continue only after you have source-backed data. Mark unresolved gaps as `N/A` or `資料不足`.

## Current Supply-Chain News Workflow

Use recent news to discover current supply-chain changes, then corroborate with primary or high-quality sources.

1. Set the lookback window
   - Default to the last 45 days for event-driven questions.
   - Expand to 90 days for structural supply-chain relationships or slow-moving capacity changes.
   - Use the article publication date, not the date you fetched it.

2. Generate search surfaces
   - Search target company aliases: local name, English name, ticker, and common abbreviations.
   - Combine each alias with terms such as `供應鏈`, `客戶`, `大客戶`, `最大客戶`, `前十大客戶`, `訂單`, `出貨`, `產能`, `營收`, `合作`, `supply chain`, `customer`, `major customer`, `largest customer`, `top customer`, `orders`, `shipments`, `supplier`, and thesis-specific terms.
   - Add known product or end-market words from the user's thesis, such as `AI ASIC`, `CoWoS`, `iPhone`, `GPU`, `EV`, or `server`.

3. Triage candidate articles
   - Keep articles with a concrete claim: who buys from whom, who supplies whom, what product is involved, what changed, and when.
   - Prefer articles that name at least one counterparty and one product, process, capacity, or order signal.
   - Discard articles that only discuss stock price movement, analyst targets, message-board rumors, or broad sector sentiment without supply-chain facts.

4. Assign evidence confidence
   - `high`: official company disclosure, filing, earnings call, or two independent reputable recent sources support the same relationship.
   - `medium`: one reputable recent source supports the relationship and it is consistent with known business lines.
   - `low`: only market rumor, unnamed supply-chain source, single local repost, or indirect inference is available.
   - Never mark `high` when the source is only `supply-chain estimates` without a URL, publication date, or document title.

5. Extract supply-chain edges
   - Convert evidence into rows with: `customer_or_proxy`, `ticker`, `relation`, `product_or_driver`, `evidence_claim`, `source_url`, `published_date`, `confidence`.
   - For revenue exposure, use exact disclosure when available. If not available, use ranges and explain the basis; put the midpoint in `revenue_weight_pct` only when the range is needed for calculation.
   - Use `pass_through_factor` to discount weak, indirect, or lagged evidence.

6. Update `customers.json`
   - Overwrite stale rows rather than appending around them.
   - Include at least one evidence item for every customer row.
   - Set `last_verified` to the most recent evidence date.
   - Sort rows by current `revenue_weight_pct` descending when weights are available.
   - If a previous largest customer is no longer largest according to newer evidence, demote it immediately and explain the evidence in `claim`.
   - Keep unavailable or weakly supported relationships as `confidence: low`; do not remove uncertainty from the final report.

## Analysis Workflow

1. Normalize the target
   - Identify target ticker, company name, exchange, sector, and main business lines.
   - Record the latest verified stock price, price date/time, and data source.
   - If the latest price cannot be verified, do not make a buy/sell conclusion; mark the conclusion as `資料不足`.

2. Frame the hypothesis
   - Restate the user's reason, catalyst, or concern in one sentence.
   - If no reason was provided, use the supply-chain customer revenue momentum hypothesis: customer growth can transmit into the target company's revenue and valuation.

3. Build the supply-chain map
   - Run the current supply-chain news workflow before finalizing the map.
   - Identify up to five important customers, demand drivers, or end-market proxies.
   - Prefer primary filings, annual reports, investor presentations, and reputable financial sources.
   - If exact customer disclosure is unavailable and you must infer, label the row as `推估` and lower confidence.
   - Map customer names to yfinance-compatible tickers when possible:
     - US stocks: use the ticker directly, for example `AAPL`, `NVDA`.
     - Taiwan listed: append `.TW`.
     - Taiwan OTC: append `.TWO`.
     - Private or unlisted entities: use `N/A` and explain how they are proxied.
   - Estimate revenue exposure weights. If reliable weights are unavailable, use ranges and explain the basis.
   - Write the working customer map to `.cache/tw-supply-chain-valuation/<target>/customers.json`.

4. Measure customer momentum
   - Run `scripts/fetch_financial_data.py` after the customer map is ready.
   - For each public customer or proxy, collect the latest quarterly revenue and calculate YoY revenue growth.
   - Add QoQ growth when it helps explain turning points.
   - If yfinance data is incomplete, cross-check against company releases or filings.
   - Do not silently treat missing data as zero. Mark missing values as `N/A` and explain the impact.

5. Estimate transmitted growth
   - Use this base calculation:

```text
expected_revenue_growth =
  sum(customer_revenue_weight_pct / 100 * customer_revenue_yoy_pct * pass_through_factor)
```

   - Default `pass_through_factor` is `1.0` for direct revenue exposure when no better evidence exists.
   - Use a lower factor for indirect end-market proxies, inventory digestion, pricing pressure, or low visibility.
   - Produce base, bull, and bear scenarios when uncertainty is high.

6. Convert momentum into valuation
   - Use at least one valuation lens that fits available data: P/E, EV/Sales, PEG, peer multiple, dividend yield, or DCF-lite.
   - Prefer ranges over false precision.
   - Compare estimated fair value with the latest verified market price.
   - The final rating should be one of: `可買`, `觀望`, `不建議買`, or `資料不足`.

7. Check contrary evidence
   - Explicitly list risks that could break the thesis: customer concentration, margin compression, inventory cycles, FX, capex cycles, export controls, product delays, valuation multiple contraction, and data quality.
   - If the conclusion depends on one weak assumption, call that out.

## Output Format

Use this structure by default:

```markdown
## 結論

- 判斷：可買 / 觀望 / 不建議買 / 資料不足
- 目前股價：TWD x.xx（YYYY-MM-DD，source）
- 合理價值區間：TWD x.xx - x.xx
- 隱含上漲/下跌空間：x% - y%
- 信心：高 / 中 / 低

## 核心理由

1. ...
2. ...
3. ...

## 供應鏈動量

| 客戶/代理變數 | Ticker | 關係 | 營收權重 | 最新營收 YoY | 傳導係數 | 加權貢獻 | 信心 |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| ... | ... | ... | ... | ... | ... | ... | ... |

## 估值

- Base：...
- Bull：...
- Bear：...
- 使用的倍數或折現假設：...

## 反向證據與風險

- ...

## 需要追蹤

- ...

## Sources

- ...
```

Keep the answer concise enough for an investor to act on, but include the assumptions needed to audit the conclusion.
