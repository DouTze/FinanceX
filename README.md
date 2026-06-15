# FinanceX

FinanceX 是一個製造業供應鏈與股票估值分析專案。它會蒐集近期新聞與公司資料、更新客戶關係、估算供應鏈需求傳導，並以適合製造業的估值方法產生分析報告。

目前專案以 Claude Code skill 作為個股分析流程的 prototype。這個階段的目的，是快速驗證資料蒐集、供應鏈建模、估值方法、風險檢查與報告格式是否合理，而不是將 Claude Code 當成一般使用者最終操作 FinanceX 的唯一方式。

現階段不需要啟動 Streamlit、Web Server 或其他圖形介面，開發者與研究人員可直接在 Claude Code 中執行流程並檢查分析結果。

## 未來方向

未來 FinanceX 可能把 Claude Code skill 所驗證的流程轉為正式的分析服務：

1. 將資料蒐集、供應鏈判斷、估值與報告生成交由後端 agent 或服務執行。
2. 隱藏 prompt、agent 編排、工具呼叫與中間資料處理等內部細節。
3. 透過網頁或應用程式提供一般使用者輸入股票、閱讀報告及比較情境。
4. 保留來源、估值假設、風險與資料日期，使分析結果仍可追溯與檢查。

因此，本 README 以下內容描述的是目前 prototype 的開發與測試方式。未來若加入網頁、應用程式或 API，Claude Code skill 仍可作為分析流程規格、測試介面與迭代工具。

## 分析 Skill

| Skill | 適用範圍 | 使用指令 |
| --- | --- | --- |
| 台股製造業分析 | 台灣上市、上櫃製造業 | `/mfg-tw` |
| 全球製造業分析 | 美國、日本、歐洲、台灣及其他市場的上市製造業 | `/mfg-global` |

兩個 skill 皆適合半導體、電子、機械、零組件、材料、汽車及其他產品型製造業。銀行、保險、純軟體平台、REITs 與營建開發商不屬於主要適用範圍。

## 環境需求

使用前需要安裝 Claude Code 與 `uv`，並確認可連線至新聞網站、公司投資人關係網站、交易所及 Yahoo Finance。

### 安裝 Claude Code

macOS 可透過 Homebrew 安裝：

```bash
brew install --cask claude-code
```

Windows 可透過 WinGet 安裝：

```powershell
winget install Anthropic.ClaudeCode
```

安裝後執行 `claude`，依照瀏覽器提示完成登入。其他安裝方式請參考 [Claude Code 官方安裝文件](https://code.claude.com/docs/en/setup)。

### 安裝 uv

macOS 可透過 Homebrew 安裝：

```bash
brew install uv
```

Windows 可透過 Scoop 安裝：

```powershell
scoop install main/uv
```

若尚未安裝 Scoop，請先依照 [Scoop 官方網站](https://scoop.sh/) 的說明完成安裝。其他 `uv` 安裝方式請參考 [uv 官方安裝文件](https://docs.astral.sh/uv/getting-started/installation/)。

### 驗證環境

安裝完成後執行：

```bash
claude --version
uv --version
```

本專案於 2026-06-15 驗證使用：

```text
Claude Code 2.1.177
uv 0.11.21
```

skill 內的 Python 腳本只使用標準函式庫，Claude Code 會透過以下形式執行，不需要另外建立虛擬環境：

```bash
uv --cache-dir .cache/uv run python <script>
```

## 開始使用

先在終端機進入 FinanceX 專案根目錄：

```bash
cd /path/to/FinanceX
claude
```

首次開啟時，請確認並信任此專案。Claude Code 會自動載入 `.claude/skills/` 下的兩個 project skill。

進入 Claude Code 後，直接輸入 skill 指令與分析問題即可。

### 分析台股製造業

```text
/mfg-tw 2330 台積電 是否可買
```

```text
/mfg-tw 2327.TW 國巨 AI 伺服器需求是否能推升未來一年營收與合理價
```

```text
/mfg-tw 3529.TWO 力旺 因 AI ASIC 需求是否有上修空間
```

只輸入四位數代碼時，skill 會判斷應使用上市 `.TW` 或上櫃 `.TWO` 代碼；無法安全判斷時會先詢問。

### 分析全球製造業

```text
/mfg-global CAT Caterpillar 是否低估
```

```text
/mfg-global 7203.T Toyota 混合動力車需求是否帶來上修空間
```

```text
/mfg-global SIE.DE Siemens 工業自動化循環是否落底
```

全球股票請盡量提供資料供應商可辨識的完整代碼。不同市場可能需要交易所後綴，例如 `.T`、`.HK` 或 `.DE`。若輸入 ADR、GDR 或雙重上市股票，skill 會先辨識主要上市股票與換股比例。

輸入 `/mfg` 後也可以使用 Claude Code 的指令選單自動完成 skill 名稱。

## 建議的提問方式

至少提供股票代碼或公司名稱。若能同時提供投資假設、催化劑或疑慮，分析會更聚焦：

```text
/mfg-tw 2330 台積電 CoWoS 擴產與 AI GPU 需求是否已反映在股價
```

```text
/mfg-global 7203.T Toyota 請比較混合動力車成長、匯率與正常化本益比後的合理價
```

也可以指定分析要求，例如：

- 關注特定客戶、產品或終端市場。
- 比較 Bear、Base、Bull 三種情境。
- 指定同業或估值期間。
- 檢查客戶集中、庫存、產能利用率、毛利率或資本支出風險。

## 分析流程

Claude Code 會依序執行：

1. 辨識公司、交易所、主要產品與製造業類型。
2. 蒐集近期新聞、公司公告、財報及投資人資料。
3. 根據最新證據重建主要客戶與供應鏈關係。
4. 驗證客戶資料的來源、日期與信心水準。
5. 取得股價、營收及客戶成長資料。
6. 估算客戶需求對目標公司營收的傳導效果。
7. 建立正常化或預估 EPS，避免直接套用景氣高峰或谷底獲利。
8. 以正常化本益比為製造業主要方法，並視情況使用 EV/EBITDA、EV/Sales、P/B 或 DCF 交叉檢查。
9. 在 Claude Code 對話中輸出結論、合理價區間、情境分析、風險與來源。

近期新聞只用於發現供應鏈變化。skill 必須根據實際來源更新客戶資料並通過驗證後，才能繼續估值，不會直接沿用過期的客戶排序。

## 分析輸出

報告會直接顯示在 Claude Code 對話中，通常包含：

- `可買`、`觀望`、`不建議買` 或 `資料不足`。
- 最新股價、資料日期與合理價值區間。
- 主要客戶、營收權重、成長率與傳導貢獻。
- Bear、Base、Bull 的 EPS、估值倍數及合理價。
- 客戶集中、毛利率、庫存、匯率、產能與景氣循環風險。
- 使用的新聞、公告、財報與其他資料來源。

分析過程產生的中間資料會存放在：

```text
.cache/mfg-tw/<target>/
.cache/mfg-global/<target>/
```

其中可能包含：

```text
news/             近期新聞候選資料
sources/          下載並擷取的來源內容
customers.json    經證據更新的客戶關係
financials/       股價、季度營收與計算結果
```

`.cache/` 已加入 `.gitignore`，不會納入版本控制。

## 常見問題

### 找不到 `/mfg-tw` 或 `/mfg-global`

確認 Claude Code 是從 FinanceX 專案根目錄啟動，且以下檔案存在：

```text
.claude/skills/mfg-tw/SKILL.md
.claude/skills/mfg-global/SKILL.md
```

若 skill 是在 Claude Code 啟動後才新增或重新命名，可重新啟動 Claude Code。

### 顯示 `uv` 不存在

安裝 `uv` 後重新執行分析。skill 不會在找不到 `uv` 時自行改用其他 Python 執行環境。

### 新聞、股價或財務資料抓取失敗

確認網路權限，或允許 Claude Code 改用公司公告、交易所、監管機關及其他可驗證來源。缺少關鍵資料時，報告會標示 `N/A` 或 `資料不足`，不會自行編造數字。

### 全球股票代碼無法辨識

補充公司名稱、上市國家與交易所。例如不要只輸入可能跨市場重複的數字代碼，改為：

```text
/mfg-global 7203.T Toyota 是否低估
```

## 注意事項

FinanceX 的結果是研究與決策輔助，不是保證獲利的投資建議。估值高度依賴財務資料、供應鏈證據與情境假設；下單前仍應自行核對最新公告、價格、風險承受能力與投資限制。
