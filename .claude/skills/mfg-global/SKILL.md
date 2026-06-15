---
name: mfg-global
description: Analyze publicly traded manufacturing companies across global markets using supply-chain customer revenue momentum, normalized earnings, and industry-appropriate valuation methods, then produce a text-only valuation report. Use when the user asks whether a global manufacturing stock is buyable, undervalued, overvalued, or wants FinanceX industry-chain analysis. Do not build or launch Streamlit or any web UI for this workflow.
---

# Global Manufacturing Supply Chain Valuation

## Operating Mode

Run this workflow as a text-mode financial analysis inside Claude Code.

- Do not create, start, or depend on Streamlit, dashboards, browser UIs, or long-running services.
- Return the analysis directly in chat as structured Markdown.
- Prefer current, source-backed data. If the stock price, financial data, management, regulation, or market context could have changed, verify it before using it.
- Use absolute dates for prices and financial periods.
- State the country, primary exchange, ticker, listing currency, reporting currency, and fiscal period clearly. Do not assume `TWD`, `USD`, or a calendar fiscal year.
- Use the primary listing by default. If the user gives an ADR, GDR, secondary listing, or dual-listed share, identify the underlying primary security and disclose the depositary or share-conversion ratio before comparing prices or per-share values.
- Treat the result as decision support, not a guarantee. Do not claim a trade is certain to profit.
- This workflow is optimized for publicly traded manufacturers worldwide, including semiconductor, electronics, machinery, industrial equipment, components, materials, chemicals, automotive, aerospace, medical devices, and other product-based businesses.
- Do not force the manufacturing workflow onto banks, insurers, pure software/platform companies, construction developers, REITs, or other materially different business models. Apply the sector exception rules below and state when the target is outside the workflow's core scope.

## Input Handling

Accept short requests such as:

```text
/mfg-global 2330.TW 台積電 是否可買
/mfg-global CAT Caterpillar 是否低估
/mfg-global 7203.T Toyota 混合動力車需求是否帶來上修空間
/mfg-global SIE.DE Siemens 工業自動化循環是否落底
```

Use `/mfg-global` for this workflow.

Resolve the company's primary exchange and the data provider's exact ticker before fetching data:

- US-listed stocks commonly use the ticker directly, for example `CAT`.
- Other markets commonly require an exchange suffix, for example `2330.TW`, `7203.T`, `0700.HK`, `SIE.DE`, or `VOW3.DE`.
- Exchange suffix conventions vary by data provider. Verify the symbol instead of guessing from the company name.
- Numeric tickers are ambiguous across countries. If the market or company cannot be inferred safely, ask one concise question.
- Distinguish ordinary shares from ADRs, preferred shares, depositary receipts, and different voting classes.

If the request includes a thesis or reason, make it the focal hypothesis. If a required input cannot be inferred safely, ask one concise question before continuing.

## Bundled Data Tools

Use the bundled scripts before making the final valuation whenever current market or quarterly revenue data is needed.

Run all Python scripts through `uv`; do not call `python3` or a local virtualenv directly. Use `uv --cache-dir .cache/uv run python` for bundled scripts because they only depend on the Python standard library and should not require this repository to have a `pyproject.toml`. Keep the uv cache under `.cache/uv` so execution does not depend on writable global cache directories. If `uv` is unavailable, report that as an environment blocker instead of silently switching runtimes.

If you need to write a temporary source-specific scraper that uses third-party packages, put it under `.cache/mfg-global/<target>/` and run it with `uv --cache-dir .cache/uv run --with <package> python <script>`.

1. Collect recent news candidates for current supply-chain evidence:

```bash
uv --cache-dir .cache/uv run python ${CLAUDE_SKILL_DIR}/scripts/fetch_recent_news.py \
  --target-name "<target-company-name>" \
  --target-ticker <target-ticker> \
  --thesis "<user-thesis-or-catalyst>" \
  --days 45 \
  --out .cache/mfg-global/<target>/news
```

Read `.cache/mfg-global/<target>/news/news_candidates.md`. Keep only articles that contain concrete supply-chain claims: named customer, named supplier, order, shipment, product allocation, capacity change, pricing, or end-market demand. Discard generic stock-price commentary and unsourced rumors.

The default Google News locale is global English (`en-US`, `US`, `US:en`). For non-English-speaking markets, search both English and the relevant local language. Rerun the command to a separate `news-local` directory with local aliases, keywords, and locale parameters:

```bash
uv --cache-dir .cache/uv run python ${CLAUDE_SKILL_DIR}/scripts/fetch_recent_news.py \
  --target-name "<local-company-name>" \
  --target-ticker <target-ticker> \
  --alias "<english-company-name>" \
  --keyword "<local-supply-chain-term>" \
  --google-language "<language-locale>" \
  --google-country "<country-code>" \
  --google-ceid "<country-code>:<language-code>" \
  --days 45 \
  --out .cache/mfg-global/<target>/news-local
```

Do not treat the absence of English-language coverage as evidence that no supply-chain change occurred.

2. Download the selected articles and primary documents:

```bash
uv --cache-dir .cache/uv run python ${CLAUDE_SKILL_DIR}/scripts/fetch_source_pages.py \
  --out .cache/mfg-global/<target>/sources \
  --url "https://example.com/selected-news-1" \
  --url "https://example.com/selected-news-2"
```

Read `.cache/mfg-global/<target>/sources/sources.md` and relevant extracted text files before finalizing customer relationships or weights.

3. Rewrite the task-local customer map from the news evidence. This is mandatory.

```text
${CLAUDE_SKILL_DIR}/templates/customers.json
```

Write or overwrite the working copy under `.cache/mfg-global/<target>/customers.json`. Do not reuse a previous `customers.json` row unless the current news/source review still supports it. Fill in:

- `target.ticker` and `target.name`
- up to five `customers`
- `ticker`, `relation`, `revenue_weight_pct`, `pass_through_factor`, `confidence`, `source`, `last_verified`, and `evidence`

Every customer row must include at least one concrete evidence item with `type`, `title`, `url`, `published_date`, and `claim`. If recent evidence changes the ranking or weight, update the ranking and weight. For example, if recent sources show Nvidia has overtaken Apple as TSMC's largest customer, Nvidia must be first and Apple must not remain the largest row.

4. Validate the customer map before using it:

```bash
uv --cache-dir .cache/uv run python ${CLAUDE_SKILL_DIR}/scripts/validate_customer_map.py \
  --customers-file .cache/mfg-global/<target>/customers.json \
  --max-age-days 180 \
  --strict
```

If validation fails, fix `customers.json` and rerun validation. Do not continue to quote/revenue fetching until validation passes.

5. If you later find additional source URLs for annual reports, investor presentations, customer disclosures, or financial news, download them with:

```bash
uv --cache-dir .cache/uv run python ${CLAUDE_SKILL_DIR}/scripts/fetch_source_pages.py \
  --out .cache/mfg-global/<target>/sources \
  --url "https://example.com/source-1" \
  --url "https://example.com/source-2"
```

Read `.cache/mfg-global/<target>/sources/sources.md` and any relevant extracted text files before finalizing customer relationships or weights.

6. Fetch quote and quarterly revenue data:

```bash
uv --cache-dir .cache/uv run python ${CLAUDE_SKILL_DIR}/scripts/fetch_financial_data.py \
  --target <target-ticker> \
  --target-name "<target-company-name>" \
  --customers-file .cache/mfg-global/<target>/customers.json \
  --out .cache/mfg-global/<target>/financials
```

Read `.cache/mfg-global/<target>/financials/finance_data.md` first, then inspect `finance_data.json` or `quarterly_revenue.csv` if the numbers need auditing.

If a bundled script fails because the network, Yahoo Finance endpoint, unsupported ticker, or a source page is unavailable, do not invent data. Use available web/search tools, the relevant exchange or regulator, company filings, or write a small source-specific scraper in the task cache. Continue only after you have source-backed data. Mark unresolved gaps as `N/A` or `資料不足`.

## Current Supply-Chain News Workflow

Use recent news to discover current supply-chain changes, then corroborate with primary or high-quality sources.

1. Set the lookback window
   - Default to the last 45 days for event-driven questions.
   - Expand to 90 days for structural supply-chain relationships or slow-moving capacity changes.
   - Use the article publication date, not the date you fetched it.

2. Generate search surfaces
   - Search target company aliases: legal name, local-language name, English name, ticker, exchange, major brands, and common abbreviations.
   - Combine each alias with terms such as `供應鏈`, `客戶`, `大客戶`, `最大客戶`, `前十大客戶`, `訂單`, `出貨`, `產能`, `營收`, `合作`, `supply chain`, `customer`, `major customer`, `largest customer`, `top customer`, `orders`, `shipments`, `supplier`, and thesis-specific terms.
   - Add known product or end-market words from the user's thesis, such as `AI ASIC`, `CoWoS`, `iPhone`, `GPU`, `EV`, or `server`.
   - Add equivalent local-language supply-chain, order, shipment, capacity, and customer terms for the company's home market.

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
   - Identify the legal company name, country of domicile, headquarters, primary exchange, primary ticker, security type, sector, main business lines, and whether the company is actually a manufacturer.
   - Record listing currency, financial-statement reporting currency, fiscal year end, accounting standard such as IFRS, US GAAP, or local GAAP, and the authoritative filing source.
   - Prefer primary sources from the relevant jurisdiction, such as company investor relations, exchange filings, securities regulators, and statutory annual or interim reports.
   - For manufacturers, classify the earnings pattern as one of: `穩定型製造`, `景氣循環型製造`, `高成長製造`, or `虧損/轉機型製造`.
   - Record the main products, production capacity, utilization rate when available, gross margin drivers, customer concentration, inventory cycle, capital intensity, and net cash or net debt position.
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
     - Japan, Hong Kong, Germany, and other markets: use the verified provider-specific exchange suffix.
     - Private or unlisted entities: use `N/A` and explain how they are proxied.
   - Estimate revenue exposure weights. If reliable weights are unavailable, use ranges and explain the basis.
   - Write the working customer map to `.cache/mfg-global/<target>/customers.json`.

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

6. Build normalized manufacturing earnings
   - Do not apply a valuation multiple directly to unadjusted current EPS when earnings are at a cyclical peak or trough.
   - Start from the latest four quarters and explicitly remove material one-time items, including disposal gains, impairment, litigation, unusual tax effects, large FX gains or losses, and non-recurring subsidies.
   - For `穩定型製造`, estimate forward EPS from current revenue, expected transmitted growth, sustainable gross margin, operating expense ratio, interest, tax, and diluted shares.
   - For `景氣循環型製造`, use mid-cycle or normalized EPS. Prefer a 3-5 year average operating margin or return on capital applied to current-scale revenue or invested capital. Do not treat peak-cycle EPS as sustainable.
   - For `高成長製造`, estimate forward EPS only when capacity, utilization, product mix, and margin assumptions are source-backed. Separate volume growth from ASP and margin changes.
   - For `虧損/轉機型製造`, do not calculate a conventional P/E. First determine whether losses are temporary, cyclical, or structural.
   - Reconcile the earnings forecast with supply-chain momentum. Customer growth is an input, not a direct substitute for the target company's own revenue, margin, capex, and working-capital analysis.
   - If normalized or forward EPS cannot be supported by audited filings, company guidance, or clearly explained assumptions, return `資料不足` instead of inventing a fair value.

7. Select the valuation method
   - Default manufacturing method: normalized forward P/E with same-subsector peer comparison.
   - Use P/E only when normalized or forward EPS is positive and meaningful. Compare the target with peers that have similar products, growth, margin structure, cyclicality, capital intensity, accounting treatment, and country risk; do not use a broad sector or market-wide average as the only benchmark.
   - Set the justified P/E range from the target's own historical normalized range and current comparable-company range. Adjust downward for high customer concentration, weak balance sheet, peak-cycle margins, low visibility, or governance risk. Adjust upward only for source-backed superior growth, margins, return on capital, or competitive advantage.
   - Cross-country peer multiples require explicit judgment. Account for differences in sovereign and currency risk, interest rates, tax rates, governance, liquidity, accounting standards, and where the company earns its revenue. Do not assume two manufacturers deserve the same multiple merely because they make similar products.
   - Calculate manufacturing fair value as:

```text
fair_value_per_share = normalized_or_forward_EPS * justified_PE
```

   - Use separate bear, base, and bull EPS assumptions and corresponding P/E ranges. Do not create scenarios by changing only the multiple while leaving operating assumptions unchanged.
   - Use EV/EBITDA as a secondary cross-check for capital-intensive manufacturers, large depreciation differences, or peer groups with materially different leverage. Convert enterprise value back to equity value:

```text
equity_value = enterprise_value - total_debt + cash_and_equivalents
fair_value_per_share = equity_value / diluted_shares
```

   - Use EV/Sales only as a fallback for a high-growth or temporarily loss-making business whose future positive margin is defensible. It is most relevant to pure software, platform, or subscription businesses and is not the default for hardware manufacturing. State the assumed normalized margin because a revenue multiple without a margin path is not a complete valuation.
   - Use P/B as the primary method for banks and insurers, together with ROE, asset quality, capital adequacy, and growth. For manufacturers, use P/B only as a secondary asset-value or downside check when tangible assets are economically meaningful; do not value an ordinary profitable manufacturer primarily on P/B.
   - Use project NAV, asset value, or normalized earnings for construction and project-based developers. Use DCF only when project timing, contracted cash flows, capex, and working capital can be forecast with reasonable confidence.
   - DCF is a secondary scenario check, not a method selected merely because annual cash flow is volatile. If cash flow is highly unstable or forecast assumptions dominate the result, disclose the sensitivity and do not present DCF as precise.
   - Dividend yield is a secondary return and downside check only for mature companies with stable payout policy and sustainable free cash flow. Do not use dividend yield as the primary valuation method for a growth or cyclical manufacturer.
   - PEG may be shown only as a supplementary sanity check when the earnings growth estimate is positive, durable, and measured consistently. Never use PEG as the sole fair-value method.
   - Prefer ranges over false precision. If two valid methods materially disagree, explain why and lower confidence instead of averaging them mechanically.

8. Compare valuation with market price
   - Compare the fair-value range with the latest verified market price.
   - Show the exact EPS, multiple, net debt, diluted-share, and scenario assumptions used in the calculation.
   - Present fair value in the primary listing currency by default. If the user requests another currency, show the FX rate, rate date, and conversion source.
   - Keep enterprise value, debt, cash, EBITDA, revenue, and equity value in one consistent currency within each calculation. Do not mix local-currency financial statements with a foreign listing price.
   - For ADRs, GDRs, or dual listings, convert the primary-share fair value using the verified share or depositary ratio.
   - Distinguish between operating upside and multiple expansion. A buy case that depends mainly on a higher P/E requires stronger evidence than one supported by earnings growth.
   - The final rating should be one of: `可買`, `觀望`, `不建議買`, or `資料不足`.

9. Check contrary evidence
   - Explicitly list risks that could break the thesis: customer concentration, margin compression, inventory cycles, FX, capex cycles, export controls, product delays, valuation multiple contraction, and data quality.
   - For manufacturers, also test utilization, inventory days, receivable days, order visibility, pricing pressure, yield rate, raw-material costs, and whether customers are double-ordering.
   - If the conclusion depends on one weak assumption, call that out.

## Output Format

Use this structure by default:

```markdown
## 結論

- 判斷：可買 / 觀望 / 不建議買 / 資料不足
- 主要上市地與代碼：Exchange / Ticker
- 目前股價：CCY x.xx（YYYY-MM-DD，source）
- 合理價值區間：CCY x.xx - x.xx
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

- 公司類型：穩定型製造 / 景氣循環型製造 / 高成長製造 / 虧損或轉機型製造 / 非製造業例外
- 主要方法：正常化本益比 / EV/EBITDA / EV/Sales / P/B / Project NAV / DCF
- Bear：EPS 或營運假設 × 倍數 = 合理價
- Base：EPS 或營運假設 × 倍數 = 合理價
- Bull：EPS 或營運假設 × 倍數 = 合理價
- 交叉檢查：...
- 方法限制：...

## 反向證據與風險

- ...

## 需要追蹤

- ...

## Sources

- ...
```

Keep the answer concise enough for an investor to act on, but include the assumptions needed to audit the conclusion.
