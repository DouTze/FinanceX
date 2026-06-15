# Git 規範

關於這份 git 的各項規範，在這邊進行描述。

## Branch 的規範

本規範目前主要分支有：

- `master`：正式環境上的版本分支
- `develop`：用於開發的基礎分支
- `feature`：新功能開發的分支
- `hotfix`：正式環境 Bug 處理的分支

`master` 分支用於發佈在正式機上，所有異動都只能由 `develop` 分支合併到這個分支上。目前正式機已套用自動上版，因此在該 branch 節點更新的同時就會觸發上版流程，所以 **請勿自行將分支整合進 `master` 中**，若有需求請洽詢專門負責該部分的同仁。

`develop` 分支是用於開發的基礎分支，所有分支皆由此分支建立。當完成測試且確認異動正式環境，即將此分支合併至主線 `master`。

`feature` 分支為新功能開發之分支，由分支 `develop` 所建立，當完成測試且確認異動正式環境，即將此分支合併至分支 `develop`。分支格式為：`feature/YYYYMMDD-topic`，其中 `YYYYMMDD` 為創建分支日期，`topic` 為上版日期或簡稱（可不填）。

`hotfix` 分支為正式環境 Bug 處理之分支，由分支 `develop` 所建立，當完成測試且確認異動正式環境，即將此分支合併至分支 `develop`。分支格式為：`hotfix/YYYYMMDD-topic`，其中 `YYYYMMDD` 為創建分支日期，`topic` 為上版日期或簡稱（可不填）。

## Pull 時的規範

為了讓分支不會因為共同開發而變得凌亂，於 `pull` 時使用以下指令以避免分支分岔的情況：

```bash
git pull --rebase
```

## Commit message 的規範

> 這邊的 `commit message` 規範僅作為撰寫時使用的**參考**，實際上僅需撰寫 `Header` 與 `Body` 的部分，並遵守 `type` 的使用場景即可。**請不要因為規範過於複雜而不上 `commit`**。

```markdown
Header: <type>(<scope>): <subject>
- type: 代表commit的類別：feat, fix, docs, style, refactor, test, chore，必要欄位。
- scope: 代表commit影響的範圍，例如資料庫、控制層、模板層等等，視專案不同而
不同，為可選欄位。
- subject: 代表此commit的簡短描述，不超過50個字元，結尾不加句號，為必要欄
位。

Body: 72-character wrapped. This should answer:
- Body部分是對本次Commit的詳細描述，可以分成多行，每一行不超過72字元。
- 說明程式碼變動的項目與原因，還有與先前行為的對比。

Footer:
- 填寫任務編號（如果有的話）。
- BREAKING CHANGE（可忽略），紀錄不兼容的變動，
  以 BREAKING CHANGE: 開頭，後面是對變動的描述，以及變動原因和遷移方法。
```

- `type:subject` 是簡述，不超過 50 字元。
- 標題與內文間需空一行，內文與註腳間也需空一行。
- 內文當遇到全半形單字切換時，需將半形字以兩個空格分隔，例如：「新增一個 feature進資料庫」，需改為「新增一個 feature 進資料庫」。
- 內文當遇到需要使用列表或清單條列項目時，需要在編號與條列內文間以一個空格區隔，例如：「1.條列項目」需要改成「1. 條列項目」。

## Type

用來告訴進行 Code Review 的人應該以什麼態度來檢視 Commit 內容。

例如：

- 看到 Type 為 `fix`，進行 Code Review 的人就可以用「觀察 Commit 如何解決錯誤」的角度來閱讀程式碼。
- 看到 Type 為 `refactor`，進行 Code Review 的人可以放輕鬆閱讀程式碼是如何被重構，因為重構的本質是不會影響既有的功能。

利用不同 Type 來決定進行 Code Review 檢視的角度，可以提升 Code Review 的速度，因此開發團隊應該對這些 Type 的使用時機有一致的認同。

只允許使用以下類別：

- `feat`：新增/修改功能（feature）。
- `fix`：修補 bug（bug fix）。
- `docs`：文件（documentation）。
- `style`：格式（不影響程式碼運行的變動 white-space, formatting, missing semi colons, etc）。
- `refactor`：重構（既不是新增功能，也不是修補 bug 的變動）。
- `perf`：改善效能（A code change that improves performance）。
- `test`：增加測試（when adding missing tests）。
- `chore`：建構程序或輔助工具的變動（maintain）。
- `revert`：撤銷回復先前的 commit，例如：revert: type(scope): subject（回復版本：xxxx）。

以下將進行各項型別的詳細描述。

---

### feat

```git
feat:

需求描述：

因應新需求做調整：

調整項目：

```

內文應包含下列三項：

- **需求描述**
  針對本次新增的需求進行描述，主要是對於 Title 無法完整描述需求時的輔助說明。若 Title 已經能夠完整描述需求，則可以與 Title 相同。需求描述能夠以短述或是條列進行說明，無硬性規定。
- **因應新需求做調整**
  需將新需求如何調整進行條列式描述。
- **調整項目**
  對調整的檔案進行條列式描述，格式為：

  ```
  編號. 調整的檔案，調整內容
  ```

  調整內容若需要以列表呈現時，則使用以下方式呈現（注意『 - 』的縮排）：

  ```
   - 內容1
   - 內容2
  ```

**Example**

```bash
feat: message 信件通知功能

需求描述：
 - 通知和 message 都要寄發每日郵件，通知和 message 都放在同一封信裡面就好，
 不然信件太多可能也不會有人想去看。

因應新需求做調整：
1. 在每日信件任務中增加 message 部分。

調整項目：
1. mail_template.php，新增 message 區塊。
2. Send_today_notify_mail.php，新增/取得每日 Message 邏輯。
3. Message_model_api.php，新增 $where 參數，以便取得每日訊息。
4. Message_api.php 、 Message_group_user_model_api.php 、 新增 **取得訊息
使用者** 邏輯，以便撈取每日訊息。

issue #863
```

```bash
feat: 表單統計，多顯示計畫名稱欄位

需求描述：
在匯出、統計或取得查詢表單時，需要額外顯示訓練計畫名稱的欄位

因應新需求做調整：
1. 列表資訊多加「計畫名稱」欄位，以利後續匯出資料處理。

調整項目：
1. Assessment_form.php，匯出表單統計時，新增訓練計畫名欄位。
2. customize.php，表單統計查詢時，多顯示訓練計畫名欄位。
3. Complex_assessment_form_api.php、Complex_assessment_form_model_api：
- 取得表單統計資料時，多取得計畫名稱。

issue #863
```

---

### fix

```bash
fix:

問題：

原因：

調整項目:

```

內文應包含以下三項：

- **問題**
  以條列方式描述本次修正的問題為何。
- **原因**
  以條列的方式解釋造成本次修正問題的原因為何。
- **調整項目**
  以條列的方式描述修正了那些檔案，並且該檔修正了哪些部分。格式為：

  ```
  編號. 調整的檔案，調整內容
  ```

  調整內容若需要以列表呈現時，則使用以下方式呈現（注意『 - 』的縮排）：

  ```
  -    內容1
  -    內容2
  ```

**Example**

```bash
fix: 自訂表單新增/編輯畫面，修正離開葉面提醒邏輯

問題：
1. 原程式碼進入新增頁面後，沒做任何動作之下，離開頁面會跳提醒。
2. 原程式碼從新增/編輯頁面回到上一頁後（表單列表頁面），離開頁面會跳提醒。

原因：
1. 新增頁面時，頁面自動建立空白題組會調用 sort_item，造成初始化 unload
   事件處理器。
2. 回到上衣頁後，就不需要監聽 unload 事件，應該把 unload 事件取消掉。

調整項目:
1. 初始化 unload 事件處理器：排除新增表單時，葉面自動建立空白題組調用
   sort_item 的情境。
2. 回到上一頁後，復原表單被異動狀態且清除 unload 事件處理器。

issue #1335
```

```bash
fix: 意見反應

問題：
1. 客戶反應：意見反應的信件都看不到圖片。

原因：
1. 目前程式碼都會要求先登入後才可查看使用者上傳的檔案，造成在信件上會看
   不見圖片的問題。

調整項目:
1. File.php，經討論後，開放讓意見反應頁面上傳的檔案，不用登入就可以查
   看/下載。

issue #1229
```

---

### docs

```bash
docs: 新增註解/修正註解/移除過期的註解

[詳細內容]

```

Docs 的 Title 中僅包含三項：新增註解、修正註解以及移除過期的註解。詳細內容則可以彈性填寫。

**Example**

```bash
docs: 新增註解
```

```bash
docs: 修正型別註解

讓 IDE 可以讀取到正確的類別
```

```bash
docs: 移除過期的註解

issue #1229
```

---

### style

```bash
style:

調整原因：

調整項目：

```

調整原因中描述為何對更動的區塊做撰寫風格調整。調整項目中針對各調整檔案條列並進行描述。

**Example**

```bash
style: message 頁面，對 Component 做 Beautifier

調整原因：
經 IE 瀏覽器測試後發現 Component 裡面仍然夾帶 ES6 語法，
但是目前 Component 的程式碼都被壓縮成一行，
為了日後修改程式方便，故先對所有被壓縮的程式碼做 Beautifier

調整項目：
1. View_component.php：
- 針對所有被壓縮的程式碼做 Beautifier。
- 移除被註解的程式碼，原本被註解的程式碼應該是壓縮前的程式碼，
但是經測試後發現這些被註解的程式碼都是舊 Code，故移除。
```

---

### refactor

```bash
refactor:

需求描述：

因應需求做調整：

調整項目：

```

需求描述中描述為何進行重構（移除過時程式碼也算）。因應需求做調整中描述如何進行重構以達成目標。調整項目中針對各調整檔案條列並進行描述。

**Example**

```bash
refactor: 重構取得「簽核流程種類名稱」邏輯

需求描述：
原程式碼取得流程名稱的邏輯散落在多個檔案，為了讓未來
新增/修改種類名稱時，不必到多個檔案中查找程式，需進行重構

因應效能需求做調整：
1. 統一透過 Process::get_type_name($process_type) 方法，
   取得流程種類名稱。

調整項目：
1. Process.php，新增 get_type_name() 方法，供取得流程名稱使用。
2. workflow_type_name.php，此 View 檔案只是為了取得流程名稱，現在以
   Process::get_type_name() 取代，故刪除。
```

---

### perf

```bash
perf:

需求描述：

因應效能需求做調整：

調整方式：

結果：

```

- 因應效能需求做調整以條列方式進行描述。
- 調整方式以條列方式進行說明。
- 結果以條列方式進行描述，需描述改進部分與改進幅度。

**Example**

```bash
perf: 評核表單列表，優化取得受評者速度

需求描述：
原本取得受評者的邏輯會造成載入頁面緩慢（開發機約 52 秒），故作優化。

因應效能需求做調整：
1. 修改取得時的邏輯，縮短頁面載入時間。

調整方式：
1. 原程式碼每個表單迴圈進入 DB 取得受評者資料改成進 DB 一次撈取全部
   受評者資料，再回到 PHP 分配資料。

結果：
1. 開發機載入頁面時間 52 秒 => 5 秒
```

---

### test

- 動到測試，但是沒有動到功能的皆算在這個項目。
- 新增、修改、刪除、重構遺漏的測試項目。

---

### chore

系統使用的檔案更新皆使用本項目，例如：環境的組態設定更新、系統執行的批次等等。

---

### revert

待編輯。
