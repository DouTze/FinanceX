# FinanceX Claude Code Skill

已將「台股供應鏈動量估值」流程整理為專案層級 Claude Code skill。

## Skill 位置

```text
.claude/skills/tw-supply-chain-valuation/SKILL.md
```

## 內建資料腳本

```text
.claude/skills/tw-supply-chain-valuation/scripts/fetch_recent_news.py
.claude/skills/tw-supply-chain-valuation/scripts/validate_customer_map.py
.claude/skills/tw-supply-chain-valuation/scripts/fetch_financial_data.py
.claude/skills/tw-supply-chain-valuation/scripts/fetch_source_pages.py
.claude/skills/tw-supply-chain-valuation/templates/customers.json
```

- `fetch_recent_news.py`：用近期新聞搜尋供應鏈候選證據，輸出 `news_candidates.md`、`news_candidates.json`、`news_candidates.csv`。
- `validate_customer_map.py`：檢查 `customers.json` 是否已寫入可查證新聞/官方文件證據，避免沿用舊資料或模糊來源。
- `fetch_source_pages.py`：下載年報、法說會、客戶揭露或新聞 URL，輸出 `sources.md`、`sources.json`、原始檔與抽取文字。
- `fetch_financial_data.py`：抓取 Yahoo Finance quote 與季度營收，輸出 `finance_data.md`、`finance_data.json`、`quarterly_revenue.csv`。
- `templates/customers.json`：讓 Claude Code 先整理目標公司、客戶、營收權重、傳導係數與新聞證據，再交給資料腳本計算。

執行腳本時一律使用 `uv --cache-dir .cache/uv run python`，不直接呼叫 `python3` 或本機 venv。uv cache 固定放在 `.cache/uv`，避免依賴全域 cache 目錄權限。

## 使用方式

在 Claude Code 中直接呼叫：

```text
/tw-supply-chain-valuation 2330.TW 台積電 是否可買
```

也可以帶入特定投資假設：

```text
/tw-supply-chain-valuation 3529.TWO 力旺 因 AI ASIC 需求是否有上修空間
```

如果 `.claude/skills` 是在目前 Claude Code session 中才新增的，請重啟 Claude Code 後再呼叫；之後修改 `SKILL.md` 會自動被偵測。

分析時，skill 會要求 Claude Code 先建立：

```text
.cache/tw-supply-chain-valuation/<target>/news/news_candidates.md
.cache/tw-supply-chain-valuation/<target>/sources/sources.md
```

再從近期新聞和來源全文萃取供應鏈關係，建立：

```text
.cache/tw-supply-chain-valuation/<target>/customers.json
```

然後執行：

```bash
uv --cache-dir .cache/uv run python ${CLAUDE_SKILL_DIR}/scripts/fetch_financial_data.py \
  --target <target-ticker> \
  --target-name "<target-company-name>" \
  --customers-file .cache/tw-supply-chain-valuation/<target>/customers.json \
  --out .cache/tw-supply-chain-valuation/<target>/financials
```

後續分析會優先讀回 `finance_data.md` 和 `finance_data.json`，再輸出文字版估值結論。

## 近期新聞供應鏈流程

1. 用 `fetch_recent_news.py` 搜尋最近 45 天的公司別供應鏈新聞。
2. 篩掉只談股價、目標價或大盤情緒的文章。
3. 保留明確提到客戶、供應商、訂單、出貨、產品、產能或價格的文章。
4. 用 `fetch_source_pages.py` 下載入選文章或官方文件全文。
5. 依照新聞證據重寫 `customers.json`，不能沿用舊 rows。
6. 用 `validate_customer_map.py --strict` 驗證；未通過前不能抓行情與營收。
7. 信心分級：
   - `high`：官方揭露，或兩個獨立可信近期來源互相支持。
   - `medium`：單一可信近期來源，且符合既有業務邏輯。
   - `low`：市場傳聞、未具名供應鏈消息、轉載文或間接推論。

## 輸出原則

- 不啟動 Streamlit。
- 不建立 Web UI 或長時間執行的服務。
- 所有結果都由 Claude Code 直接以 Markdown 文字輸出。
- 分析會包含：結論、目前股價、合理價值區間、供應鏈客戶動量、估值假設、反向證據與資料來源。

## 核心流程

1. 正規化台股代號與公司名稱。
2. 查核最新股價與關鍵市場資料。
3. 找出主要客戶、需求來源或 end-market proxy。
4. 將客戶名稱映射成 yfinance 可用 ticker。
5. 計算或整理客戶營收 YoY / QoQ。
6. 用營收權重與傳導係數估算目標公司預期營收成長。
7. 用 P/E、EV/Sales、PEG、同業倍數或 DCF-lite 做合理價值區間。
8. 比較目前股價與合理價值，輸出 `可買`、`觀望`、`不建議買` 或 `資料不足`。
