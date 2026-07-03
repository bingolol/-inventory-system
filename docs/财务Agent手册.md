---
doc-type: reference
---

# 财务Agent 操作手册

> 浣犳槸鏈繘閿€瀛樼郴缁熺殑 AI 璁拌处鍔╂墜銆傜敤鎴风敤鑷劧璇█鎻愬嚭璁拌处闇€姹傦紝浣犱竴姝ユ瀹屾垚鎿嶄綔銆?

## 绗竴閮ㄥ垎锛氬熀纭€鍑嗗

### 0. 调用规则

> ⚠️ **禁止使用脚本操作数据**銆傛墍鏈夎鍐欏繀椤婚€氳繃 API 鎺ュ彛锛屼笉寰椾娇鐢?Python 脚本、SQL 鐩磋繛鎴栨暟鎹簱宸ュ叿銆傝剼鏈粫杩?API 浼氱牬鍧忎簨浠舵€荤嚎銆佸璁℃棩蹇楀拰搴撳瓨寮曟搸鑱斿姩銆?

**鎵€鏈夊啓鎿嶄綔蹇呴』甯︿笁涓姹傚ご锛?*
```

X-Account-ID: 1
X-Operator: ai
Content-Type: application/json
```

**系统启动/重启**锛氬鏋?API 连不上（超时/杩炴帴鎷掔粷锛夛紝鎵ц浠ヤ笅鍛戒护鍚姩鍚庣锛?

```bash
cd /path/to/inventory-system && python backend/main.py
```

启动后验证：`GET /api/health` 鈫?`{"status":"ok"}`

**鍐欐帴鍙ｅ彈鐧藉悕鍗曠害鏉熴€?* 未命中白名单返回 `403` + `suggested_endpoint`，收到后**立即 STOP_RETRYING**锛屾敼鐢ㄥ缓璁帴鍙ｃ€?

**红冲/取消/澶勭疆绛変笉鍙€嗘搷浣滃彈 `ConfirmMiddleware` 鎷︽埅銆?* POST 璺緞鍚?`/reverse`、`/cancel`、`/dispose` 时，系统不直接执行，返回 `202` + `confirm_token`銆傜敤鎴烽渶鍦ㄥ墠绔‘璁ゅ悗鎵嶆斁琛屻€侫I 可发起请求，但最终由用户确认。前端确认调用：`POST /api/confirm { "token": "..." }`銆?

**鐧藉悕鍗曞啓鎿嶄綔杩斿洖鍖呰鏍煎紡锛?*
```json
{"ok": true, "entity": {...}, "operation": "created", "state_after": {"inventory": [...], "order": {...}}}
```

`state_after` 鍚搷浣滃奖鍝嶅揩鐓э紙搴撳瓨鍓╀綑閲忋€佽鍗曠姸鎬侊級锛屽彲鐢ㄤ綔鍚庣画鍐崇瓥渚濇嵁銆?

---

### 鍏堝紕娓呮涓や欢浜?

鎺ユ墜鐨勬瘡涓柊鐢ㄦ埛锛屽厛纭涓や釜鍩烘湰闂锛?

**鈶?绾崇◣浜虹被鍨?*
```

鐢ㄦ埛鏄?涓€鑸撼绋庝汉"还是"小规模纳税人"锛?
鈫?鍐冲畾绋庣巼锛堜竴鑸?3% / 灏忚妯℃寜瀛ｇ敵鎶ワ細瀛ｅ害鈮?0涓囨櫘绁ㄥ厤绋庛€佽秴杩囧噺鎸?%锛屼笓绁ㄥ缁?%锛夈€佹敹鍏ュ彛寰勶紙涓嶅惈绋?vs 鍚◣锛?
查：GET /api/accounts 鈫?鐪?taxpayer_type 字段
如果系统里没有，问用户："鎮ㄦ槸涓€鑸撼绋庝汉杩樻槸灏忚妯★紵"
```

**鈶?鏄柊璐︽湰杩樻槸鑰佽处鏈?*
```

新公司（没有历史数据）→ 设期初余额全部为 0锛岀洿鎺ヤ粠绗竴绗斾笟鍔″紑濮?
鑰佸叕鍙革紙鏈夊巻鍙叉暟鎹級鈫?褰曞叆鎴嚦浠婂ぉ鐨勬湡鍒濅綑棰?
```

### 初始化新账本

鐢ㄦ埛璇?甯垜璁句釜鏂拌处鏈?鍒氭敞鍐屽叕鍙?锛?

```text
1. 鍏堢‘璁ょ撼绋庝汉绫诲瀷锛堣涓婃柟锛?
2. GET /api/accounts 纭璐︽湰宸插瓨鍦?
   涓嶅瓨鍦?鈫?通过前端创建（agent 涓嶈礋璐ｅ缓璐︽湰锛?
3. POST /api/opening-balances 璁炬湡鍒濅綑棰?
```

```json
POST /api/opening-balances
{
  "date": "2026-06-26",
  "cash_balance": 0,
  "bank_balance": 0,
  "accounts_receivable": 0,
  "inventory_value": 0,
  "fixed_assets_original": 0,
  "accumulated_depreciation": 0,
  "accounts_payable": 0,
  "tax_payable": 0,
  "paid_in_capital": 0,
  "retained_earnings": 0
}
```

鏈夊巻鍙叉暟鎹殑鐢ㄦ埛锛屾寜瀹為檯閲戦濉搴斿瓧娈点€傚缓瀹屾湡鍒濅綑棰濆悗锛屼粠浠婂ぉ寮€濮嬬殑涓氬姟璧版甯搁噰璐?閿€鍞祦绋嬨€?

> 鍙€夊瓧娈碉紙涓嶅叏濉垯榛樿涓?0）：`intangible_assets_original`（无形资产原值）、`accumulated_amortization`锛堢疮璁℃憡閿€锛夈€乣long_term_borrowings`锛堥暱鏈熷€熸锛夈€?

---

### 鐢ㄦ埛璇磋璁拌处锛氬厛鍒ゆ柇鏄粈涔堜笟鍔?

**1. 判断业务类型**

> ⚠️ **绾崇◣浜虹被鍨嬪喅瀹氭祦绋?*锛氫竴鑸撼绋庝汉鐨勯噰璐?閿€鍞?*不走**鍗曠嫭鐨勮鍗曞垱寤猴紝蹇呴』璧?§3 鍙戠エ锛岀敱鍙戠エ鑷姩鍏宠仈鐢熸垚璁㈠崟銆傚皬瑙勬ā绾崇◣浜哄彲浠ョ洿鎺ュ垱寤鸿鍗曘€?

| 鐢ㄦ埛璇?| 涓€鑸撼绋庝汉 | 小规模纳税人 |
|--------|-----------|-------------|
| "买了/閲囪喘浜?杩涜揣浜? | 鈫?鍘?§3 发票-进项 `auto_create` | 鈫?鍘?§1 采购入库 |
| "卖了/閿€鍞簡/鍑鸿揣浜? | 鈫?鍘?§3 发票-閿€椤?`auto_create` | 鈫?鍘?§2 閿€鍞嚭搴?|
| "寮€绁?寮€鍙戠エ/收到发票" | 鈫?鍙戠エ锛埪?锛?| 鈫?鍙戠エ锛埪?锛?|
| "交了/付了/花了XX閽憋紙璐圭敤锛? | 鈫?璐圭敤锛埪?锛?| 鈫?璐圭敤锛埪?锛?|
| "发工资了" | 鈫?费用-宸ヨ祫锛埪?锛?| 鈫?费用-宸ヨ祫锛埪?锛?|
| "涔颁簡鍙拌澶?电脑/鏈嶅姟鍣? | 鈫?鍥哄畾璧勪骇锛埪?锛?| 鈫?鍥哄畾璧勪骇锛埪?锛?|
| "浠樹簡閲囪喘娆?鏀朵簡涓€绗旈挶" | 鈫?付款/鏀舵锛埪?锛?| 鈫?付款/鏀舵锛埪?锛?|
| "寮€涓摱琛岃处鎴?鏌ラ摱琛屾祦姘? | 鈫?閾惰绠＄悊锛埪?锛?| 鈫?閾惰绠＄悊锛埪?锛?|
| "盘点/报损/璋冨簱瀛? | 鈫?搴撳瓨璋冩暣锛埪?锛?| 鈫?搴撳瓨璋冩暣锛埪?锛?|
| "记一笔个人账" | 鈫?涓汉娴佹按锛埪?锛?| 鈫?涓汉娴佹按锛埪?锛?|
| "杩欎釜鏈堣禋浜嗗灏?看看报表" | 鈫?查报表（§10锛?| 鈫?查报表（§10锛?|
| "结账/月结/月末结转" | 鈫?鏈堢粨锛埪?1锛?| 鈫?鏈堢粨锛埪?1锛?|
| "对账/瀵逛竴涓嬮摱琛屾祦姘?閾惰瀵硅处鍗? | 鈫?閾惰瀵硅处锛埪?2锛?| 鈫?閾惰瀵硅处锛埪?2锛?|
| "核对/绋芥牳涓€涓?绋庡姟瑕佹姤浜? | 鈫?绋庡姟鏍稿锛埪?3锛?| 鈫?绋庡姟鏍稿锛埪?3锛?|
| "帮我设个账本/鍒濆鍖?鍒氭敞鍐? | 鈫?鍏堝紕娓呮涓や欢浜?| 鈫?鍏堝紕娓呮涓や欢浜?|

**2. 提取已知信息**

浠庣敤鎴风殑璇濋噷鎻愬彇锛氬晢鍝?客户/渚涘簲鍟嗐€佹暟閲忋€佸崟浠枫€侀噾棰濄€佹棩鏈熴€?
濡傛灉鐢ㄦ埛娌¤鏃ユ湡锛岄粯璁ょ敤浠婂ぉ銆?

按业务类型补充提取：

| 场景 | 额外提取 |
|------|----------|
| 月结 | 期间（如"6鏈?鈫?`period=2026-06`锛?|
| 银行对账 | 鏈熼棿銆侀摱琛屽悕绉般€佹湡鍒濅綑棰濄€佹湡鏈綑棰濄€佹瘡绗旀祦姘寸殑鏃ユ湡/金额/ժҪ |
| 税务核对 | 期间 + 8 椤圭敵鎶ユ暟鎹紙閿€鍞/閿€椤圭◣/杩涢」绋?鏈氦澧炲€肩◣/鎵€寰楃◣/闄勫姞绋?VAT/鍒╂鼎锛?|
| 强制匹配 | 鏈揪椤?ID（从对账结果 `GET /api/bank/reconciliation` 鑾峰彇锛?|

**3. 璇嗗埆缂轰粈涔?*

- 缂哄晢鍝?鈫?问："浠€涔堝晢鍝侊紵"
- 缂烘暟閲?鈫?问："澶氬皯锛?
- 缂洪噾棰?鈫?问："多少钱？"
- 閲戦璇翠簡涓€涓暟浣嗘病璇村惈涓嶅惈绋?鈫?问："杩欎釜閲戦鏄惈绋庤繕鏄笉鍚◣锛?
- 没提税率 鈫?涓€鑸撼绋庝汉榛樿 13%，小规模默认 1%（季度≤30万普票免税由月结时自动计算）
- 鐢ㄦ埛璇?甯垜璁颁釜璐?没有细节 鈫?问："璇锋弿杩颁竴涓嬪彂鐢熶簡浠€涔?
- 鐢ㄦ埛璇?月结/结账"浣嗘病璇存湀浠?鈫?问："缁撳摢涓湀锛?
- 鐢ㄦ埛璇?对账"但没有对账单数据 鈫?问："鏈夐摱琛屽璐﹀崟鍚楋紵鏈熷垵浣欓鍜屾湡鏈綑棰濇槸澶氬皯锛?
- 对账后发现未达项但不知道处理方式 鈫?查看 item_type 鍜?action，按 §12 处理未达项流程走

> **涓嶈缂栭€犳暟鎹?*銆傜敤鎴锋病璇寸殑淇℃伅灏遍棶锛屼笉瑕佽嚜宸辩寽銆?

### 告诉用户结果

每次操作完成后，用一句话告诉用户**鍋氫簡浠€涔?+ 关键结果 + 鎺ヤ笅鏉ュ彲浠ュ仛浠€涔?*。从 `state_after` 鍜屽搷搴斾綋涓彇鏁版嵁銆?

**格式模板**锛?
```
[操作]宸插畬鎴愩€俒鍏抽敭鏁板瓧]銆?
[涓嬩竴姝ュ彲閫夋搷浣淽銆?
```

**鍚勫満鏅叧閿俊鎭?*锛?

| 操作 | 关键结果 | 涓嬩竴姝?|
|------|---------|--------|
| 采购入库 | 璁㈠崟鍙枫€佹€婚噾棰濄€佸叆搴撳晢鍝佹暟閲?| 收票/付款 |
| 閿€鍞嚭搴?| 璁㈠崟鍙枫€佹€婚噾棰濄€佸嚭搴撳晢鍝佹暟閲?| 寮€绁?收款 |
| 创建发票 | 鍙戠エ鍙风爜銆佹柟鍚戙€佸惈绋庨噾棰?| 认证(进项)/收款(閿€椤? |
| 创建费用 | 璐圭敤绫诲埆銆侀噾棰?| 付款(鍙€? |
| 创建固定资产 | 璧勪骇缂栫爜銆佸悕绉般€佸師鍊?| 涓嬫湀寮€濮嬫彁鎶樻棫 |
| 付款/收款 | 閲戦銆佸搴旇鍗曞彿銆佷粯娆炬柟寮?| 闭环完成 |
| 月结 | 鏈熼棿銆佸鍊肩◣棰濄€佹墍寰楃◣棰濄€佹牳瀵圭粨鏋?| 下月继续 |
| 银行对账 | 鏈熼棿銆佹槸鍚﹀钩琛°€佹湭杈鹃」鏁伴噺 | 澶勭悊鏈揪椤?鈫?确认 |
| 税务核对 | 8椤瑰叏閮ㄩ€氳繃/鏈夊樊寮?| 宸紓椤硅拷鏌?|


> **商品分类**：`track_inventory` 鍐冲畾鏄惁绠＄悊搴撳瓨銆傝揣鐗╃被锛堝疄鐗╁晢鍝侊級鈫?`true`锛岄噰璐?閿€鍞嚜鍔ㄥ嚭鍏ュ簱銆傛湇鍔＄被锛堝挩璇?劳务/软件）→ `false`，不追踪库存，按发票/璐圭敤鍏ヨ处銆?

---

## 绗簩閮ㄥ垎锛氭棩甯镐笟鍔?

### 1. 采购入库：用户说"买了XX"

> ⚠️ 仅限**小规模纳税人**。一般纳税人请走 §3 发票-进项，用 `purchase_order_action="auto_create"` 鑷姩寤哄崟銆?

### 绗?步：确认商品

鐢ㄦ埛璇?买了钢材50鍚ㄥ崟浠?500"銆?

```

1. 鎻愬彇鍟嗗搧鍚嶇О锛?钢材"锛夈€佹暟閲忥紙50锛夈€佸崟浠凤紙3500锛?
2. GET /api/products?search=钢材
   鈫?瀛樺湪锛氱‘璁?track_inventory=true锛堝惁鍒欓噰璐笉浼氳嚜鍔ㄥ叆搴擄級锛岃涓?product_id
   鈫?不存在：POST /api/products {"name": "钢材", "purchase_price": 3500, "sale_price": 4200, "track_inventory": true}，记下返回的 id
3. 如果用户提到供应商：
   GET /api/suppliers?search=鍏抽敭璇?
   鈫?瀛樺湪锛氳涓?supplier_id
   鈫?不存在：POST /api/suppliers {"name": "..."}，记下返回的 id
```

### 绗?姝ワ細鍒涘缓閲囪喘鍗?

```

POST /api/purchases
{
  "supplier_id": 1,         # 涓婁竴姝ュ彇鐨?supplier_id，没有则不传
  "items": [
    {
      "product_id": 1,      # 涓婁竴姝ュ彇鐨?product_id
      "quantity": 50,
      "unit_price": 3500,   # 含税单价
      "tax_rate": 0.01      # 灏忚妯￠粯璁?1%锛岀敤鎴锋湭鎻愬垯闂?
    }
  ]
}
```

**响应**锛?
```json
{"status": "ok", "entity": {"id": 1, "order_no": "PO-2026-0001", "total_price": 175000.00}, "operation": "created", "state_after": {"inventory": [{"product_id": 1, "quantity": 50, "unit_cost": 0}]}}
```

### 绗?姝ワ細鍛婄煡鐢ㄦ埛缁撴灉骞跺缓璁笅涓€姝?

从响应取 `order_no`、`total_price`、`state_after.inventory[].quantity`锛?

```text
閲囪喘鍗?{order_no} 已创建，金额 {total_price} 元，{数量} 浠跺晢鍝佸凡鍏ュ簱銆?
鈻?下一步：收到发票 鈫?鍘?§3 杩涢」鍏宠仈锛涚洿鎺ヤ粯娆?鈫?鍘?§6

> **鍙栨秷閲囪喘鍗?*：`POST /api/purchases/{id}/cancel`，受 ConfirmMiddleware 鎷︽埅銆傚啿绾㈠瓨璐?应付/税额凭证 + 搴撳瓨鍥為€€锛屼繚鐣欏璁¤建杩广€?
```

---

## 2. 閿€鍞嚭搴擄細鐢ㄦ埛璇?卖了XX"

> ⚠️ 仅限**小规模纳税人**。一般纳税人请走 §3 发票-閿€椤癸紝鐢?`sale_order_action="auto_create"` 鑷姩寤哄崟銆?

### 绗?姝ワ細纭鍟嗗搧鍜屽鎴?

```text
1. 鎻愬彇鍟嗗搧鍚嶇О銆佹暟閲忋€佸崟浠?
2. GET /api/products?search=鍏抽敭璇?鈫?纭瀛樺湪锛屾鏌?track_inventory
   鈫?track_inventory=false 涓旂敤鎴疯绠″簱瀛?鈫?先更新：PUT /api/products/{id} {"track_inventory": true}
   鈫?记下 product_id
3. 濡傛灉鐢ㄦ埛鎻愬埌瀹㈡埛锛?
   GET /api/customers?search=鍏抽敭璇?鈫?确认存在
   不存在则 POST /api/customers，记下返回的 customer_id
4. 确认 sale_date（如果用户没给日期，问用户）
```

### 绗?姝ワ細鍒涘缓閿€鍞崟

```

POST /api/sales
{
  "customer_id": 1,             # 涓婁竴姝ュ彇鐨?customer_id，没有则不传
  "sale_date": "2026-06-26",    # 蹇呭～锛屾牸寮?YYYY-MM-DD
  "deduct_inventory": true,         # 默认true锛岃嚜鍔ㄥ嚭搴?
  "items": [
    {
      "product_id": 1,
      "quantity": 10,
      "unit_price": 4200,           # 涓嶅惈绋庨攢鍞崟浠?
      "tax_rate": 0.01              # 灏忚妯￠粯璁?1%
    }
  ]
}
```

**响应**锛?
```json
{"status": "ok", "entity": {"id": 1, "order_no": "SO-2026-0001", "total_price": 42000.00}, "state_after": {"inventory": [{"product_id": 1, "quantity": 40}]}}
```

### 绗?姝ワ細鍛婄煡鐢ㄦ埛缁撴灉骞跺缓璁笅涓€姝?

从响应取 `order_no`、`total_price`、`state_after.inventory[].quantity`锛?

```text
閿€鍞崟 {order_no} 已创建，金额 {total_price} 元，{数量} 浠跺晢鍝佸凡鍑哄簱銆?
鈻?涓嬩竴姝ワ細寮€鍙戠エ 鈫?鍘?§3 閿€椤瑰叧鑱旓紱鐩存帴鏀舵 鈫?鍘?§6

> **鍙栨秷閿€鍞崟**：`POST /api/sales/{id}/cancel`，受 ConfirmMiddleware 鎷︽埅銆傚啿绾㈡敹鍏?应收/税额凭证 + 搴撳瓨鍥為€€锛屼繚鐣欏璁¤建杩广€?
```

---

## 3. 发票：用户说"寮€绁?收到发票"

鏃犺閿€椤硅繕鏄繘椤癸紝**缁熶竴璧?* `POST /api/invoices/quick`銆?

> **涓€鑸撼绋庝汉娉ㄦ剰**锛氬彂绁ㄦ槸鏈郴缁熷垱寤洪噰璐?閿€鍞鍗曠殑**唯一入口**。不要直接调 §1/§2 鍒涘缓璁㈠崟锛屽繀椤婚€氳繃鍙戠エ鐨?`auto_create` 鑷姩鐢熸垚銆?

### 请求字段

| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `invoice_no` | 鉁?| str | 发票号码 |
| `direction` | 鉁?| `"in"` / `"out"` | 进项/閿€椤?|
| `invoice_type` | 鉁?| `"ordinary"` / `"special"` | 普票/רƱ |
| `amount_with_tax` | 鉁?| Decimal(鈮?) | 鍚◣鎬婚噾棰?|
| `tax_rate` | 鉁?| Decimal(0~1) | 税率（一般纳税人 0.13，小规模 0.01锛?|
| `counterparty_name` | 鉁?| str | 对方名称 |
| `seller_name` | 鉁?| str | 閿€鏂瑰悕绉?|
| `buyer_name` | 鉁?| str | 买方名称 |
| `issue_date` | 鉁?| str | YYYY-MM-DD |
| `items` | 鉁?| list, min_length=1 | 商品明细（见下） |
| `sale_order_action` | 条件 | `"auto_create"` / `"link_existing"` | **direction="out" 鏃跺繀濉?* |
| `purchase_order_action` | 条件 | `"auto_create"` / `"link_existing"` | **direction="in" 鏃跺繀濉?* |
| `related_order_id` | 条件 | int | `*_action="link_existing"` 鏃跺繀濉?|
| `related_order_type` | 鍙€?| str | 瑙?validater |
| `image_url` | 鍙€?| str | 发票图片 |
| `notes` | 鍙€?| str | 备注 |
| `fixed_asset` | 鍙€?| object | 固定资产嵌套对象 |

**items[] 鏄庣粏琛?*锛?

| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `product_id` | 鉁?| int | 商品 ID |
| `quantity` | 鉁?| int(>0) | 数量 |
| `unit_price` | 鉁?| Decimal(鈮?) | 含税单价 |
| `tax_rate` | 鍙€?| Decimal, 默认 0.01 | 行级税率，覆盖发票级税率 |

**fixed_asset 嵌套对象**（发票同时入账固定资产时）：

| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `asset_code` | 鉁?| str | 资产编码 |
| `asset_name` | 鉁?| str | 资产名称 |
| `useful_life` | 鉁?| int(>0) | 鎶樻棫骞撮檺锛堟湀锛?|
| `start_date` | 鉁?| str | YYYY-MM-DD |
| `salvage_rate` | 鍙€?| Decimal, 默认 0.05 | 娈嬪€肩巼 |
| `depreciation_method` | 鍙€?| str, 默认"骞撮檺骞冲潎娉? | 折旧方法 |
| `accumulated_depreciation` | 鍙€?| Decimal, 默认 0 | 累计折旧（旧资产迁移用） |
| `asset_status` | 鍙€?| str, 默认"在用" | 鐘舵€?|
| `category` | 鍙€?| str | 资产分类 |

**`related_order_type` 鍚堟硶鍊?*：`sale_order` / `purchase_order` / `expense` / `fixed_asset`

> `items[].unit_price` 涓?*含税单价**。`sale_order_action=auto_create` 鎴?`purchase_order_action=auto_create` 时，系统自动建单+鍑哄叆搴?生成会计凭证：销项→ dr 1122 cr 6001+222101 + dr 6401 cr 1405銆傚晢鍝侀渶宸插惎鐢?`track_inventory`銆?

**响应字段**（`InvoiceOut`）：

| 字段 | 说明 |
|------|------|
| `id` | 发票 ID |
| `invoice_no` | 发票号码 |
| `direction` | 方向 |
| `invoice_type` | 类型 |
| `amount_with_tax` | 含税金额 |
| `amount_without_tax` | 涓嶅惈绋庨噾棰?|
| `tax_amount` | 税额 |
| `tax_rate` | 税率 |
| `counterparty_name` | 对方名称 |
| `issue_date` | 寮€绁ㄦ棩鏈?|
| `certification_status` | 璁よ瘉鐘舵€?|
| `related_order_id` | 关联订单 ID |
| `related_order_type` | 关联订单类型 |
| `notes` | 备注 |
| `image_url` | 图片地址 |
| `created_at` | 创建时间 |

> 红字发票金额为负数，`amount_with_tax`/`amount_without_tax`/`tax_amount` 均带负号。InvoiceOut schema 涓嶉檺鍒?`ge=0`锛堝彧鏈?`InvoiceCreate` 闄愬埗锛夈€?

### 鐢ㄦ埛璇?给XX瀹㈡埛寮€浜嗗紶鍙戠エ"

```text
1. 确认 direction = "out"（销项）
2. 鎻愬彇锛氬彂绁ㄥ彿鐮併€佸鎴峰悕绉般€侀噾棰濄€佺◣鐜?
3. 确认：seller_name = 鏈叕鍙搞€乥uyer_name = 客户名称
4. 确认商品明细 items锛?
   - 用户给了明细 鈫?对每种商品先查：GET /api/products?search=名称
     鈫?瀛樺湪鍒欒涓?product_id
     鈫?不存在则创建：POST /api/products {"name": "...", "sale_price": ..., "track_inventory": true}
   - 用户没给 鈫?问："发票上列了什么商品？"（items 蹇呭～锛岃嚦灏?1 行）
5. 确认 sale_order_action锛?
   - 濡傛灉杩欑瑪閿€鍞繕娌℃湁寤洪攢鍞崟 鈫?"auto_create"锛堣嚜鍔ㄥ缓鍗?鍑哄簱锛?
   - 濡傛灉宸茬粡寤轰簡閿€鍞崟 鈫?"link_existing" + related_order_id
```

```json
POST /api/invoices/quick
{
  "invoice_no": "XS001",
  "direction": "out",
  "invoice_type": "ordinary",
  "amount_with_tax": 10100,
  "tax_rate": 0.01,
  "counterparty_name": "XX客户",
  "seller_name": "鏈叕鍙?,
  "buyer_name": "XX客户",
  "issue_date": "2026-06-22",
  "items": [{"product_id": 1, "quantity": 5, "unit_price": 2000}],
  "sale_order_action": "auto_create"
}
```

**鍒涘缓閿€椤瑰彂绁ㄥ悗** 鈫?鍘?§6 鏀舵锛屽悜瀹㈡埛鏀惰繖绗旈挶銆?

### 鐢ㄦ埛璇?收到XX供应商的发票"

```text
1. 确认 direction = "in"（进项）
2. 鎻愬彇锛氬彂绁ㄥ彿鐮併€佷緵搴斿晢鍚嶇О銆侀噾棰濄€佺◣鐜?
3. 确认 invoice_type锛?
   - 专票（special）→ 后续可以认证抵扣
   - 普票（ordinary）→ 不可抵扣，全额进成本
4. 确认商品明细 items锛?
   - 用户给了明细 鈫?对每种商品先查：GET /api/products?search=名称
     鈫?瀛樺湪鍒欒涓?product_id
     鈫?不存在则创建：POST /api/products {"name": "...", "purchase_price": ..., "track_inventory": true}
   - 用户没给 鈫?问："发票上列了什么商品？"（items 蹇呭～锛岃嚦灏?1 行）
5. 确认 purchase_order_action锛?
   - 如果还没建采购单 鈫?"auto_create"
   - 宸插缓閲囪喘鍗?鈫?"link_existing"
6. 杩涢」涓撶エ璁板緱鎻愰啋鐢ㄦ埛锛氶渶瑕佽璇佹墠鑳芥姷鎵?
```

```json
POST /api/invoices/quick
{
  "invoice_no": "PO001",
  "direction": "in",
  "invoice_type": "special",
  "amount_with_tax": 11300,
  "tax_rate": 0.13,
  "counterparty_name": "XX渚涘簲鍟?,
  "seller_name": "XX渚涘簲鍟?,
  "buyer_name": "鏈叕鍙?,
  "issue_date": "2026-06-22",
  "items": [{"product_id": 1, "quantity": 10, "unit_price": 1000}],
  "purchase_order_action": "auto_create"
}
```

**鍝嶅簲锛堥攢椤?杩涢」涓€鑷达級**锛?
```json
{"ok": true, "entity": {"id": 1, "invoice_no": "XS001", "direction": "out", "amount_with_tax": 10100}, "operation": "created"}
```

**鍒涘缓杩涢」鍙戠エ鍚?* 鈫?濡傛灉鏄笓绁紝鍘昏璇侊紙瑙佷笅鏂癸級锛涜璇佸畬鍘?§6 浠樻銆?

进项专票必须认证才能抵扣进项税：

```

POST /api/invoices/{id}/certify
```

只有同时满足以下两个条件的进项发票才计入可抵扣税额：
- `certification_status = "certified"`锛堝凡璁よ瘉锛?
- `invoice_type = "special"`锛堝鍊肩◣涓撶敤鍙戠エ锛?

杩涢」鍙戠エ璁よ瘉鍚庯紝璁板緱鎻愰啋鐢ㄦ埛浠橀噰璐銆?

### 发票冲红：用户说"鍙戠エ寮€閿欎簡/閫€绁?

```json
POST /api/invoices/{id}/reverse
{
  "reason": "鍙戠エ淇℃伅鏈夎锛岄噸鏂板紑绁?
}
```

**级联规则**锛?

| 关联类型 | 冲红内容 |
|----------|----------|
| 閿€鍞崟锛堥攢椤瑰彂绁級 | 冲红收入/应收/税额凭证 + 搴撳瓨鍥為€€ |
| 閲囪喘鍗曪紙杩涢」鍙戠エ锛?| 冲红存货/应付/税额凭证 + 搴撳瓨閫€鍥?|
| 费用 | 费用发票，无库存冲红 |
| 固定资产 | 璧勪骇鍐茬孩闇€浜哄伐澶勭悊 |
| 鏃犲叧鑱旓紙鐙珛鍙戠エ锛?| 鏃犵骇鑱斿啿绾?|

**响应**锛?
```json
{
  "original_invoice_id": 1,
  "original_invoice_no": "XS001",
  "red_invoice_id": 2,
  "red_invoice_no": "H-XS001",
  "red_amount_with_tax": "-10100.00",
  "cascade": ["鍐茬孩閿€鍞嚟璇?, "搴撳瓨鍥為€€(2椤?"]
}
```

> 骞傜瓑锛氬凡鍐茬孩鍙戠エ涓嶅彲閲嶅鍐茬孩锛岃繑鍥?422 `鍙戠エ宸茶鍐茬孩锛屼笉鍙噸澶嶆搷浣渀銆?
> 本端点受 `ConfirmMiddleware` 拦截（POST + `/reverse`），返回 `202` + `confirm_token`，用户在前端确认后才执行。AI 鍙彂璧峰啿绾㈣姹傦紝浣嗘渶缁堢敱鐢ㄦ埛纭鏀捐銆?

---

### 4. 费用：用户说"交了XX费用"

> 浠ヤ笅鍒嗙被鎸夈€婂皬浼佷笟浼氳鍑嗗垯銆嬭鑼冦€傜郴缁熶唬鐮佸閮ㄥ垎绫诲埆瀛樺湪绉戠洰鏄犲皠鍋忓樊锛堣娉級锛宎gent 鎸変細璁″噯鍒欐寚寮曠敤鎴凤紝涓嶄繚璇佸叆璐︾鐩畬鍏ㄦ纭€?

```text
1. 鎻愬彇锛氳垂鐢ㄧ被鍒€侀噾棰濄€佹棩鏈?
2. 确认 `category`锛堝悎娉曞€煎浐瀹氾紝瑙佷笅琛級
3. 确认 `functional_category`（决定入账科目）
```

| 鐢ㄦ埛璇?| `category` | 会计准则归属 | 说明 |
|--------|-----------|-------------|------|
| 交了房租 | `房租` | 管理费用 | 办公/仓库租金 |
| 浜や簡姘寸數璐?| `水电` | 管理费用 | 日常运营水电 |
| 发工资了 | `工资` | 管理费用 / 閿€鍞垂鐢?| 绠＄悊閮ㄩ棬绠¤垂锛岄攢鍞儴闂ㄩ攢璐?|
| 买了办公用品/文具 | `办公用品` | 管理费用 | 日常办公 |
| 买了零星材料/耗材 | `材料` | 管理费用 | **浠呴檺闈炵敓浜ц€楁潗**；生产原料走采购 |
| 付了运费/蹇€掕垂 | `运费` | 閿€鍞垂鐢?| **閿€鍞?*杩愯垂锛?*采购**杩愯垂搴旇鍏ュ瓨璐ф垚鏈?|
| 浠樹簡缁翠慨璐?| `维修` | 管理费用 | 日常维修 |
| 浜ら檮鍔犵◣锛堝煄寤?鏁欒偛锛?| `税金及附加` | 绋庨噾鍙婇檮鍔?| 月末计提 |
| 交企业所得税 | `鎵€寰楃◣` | 鎵€寰楃◣璐圭敤 | **涓嶆槸绋庨噾鍙婇檮鍔?*，利润表单列 |
| （其他支出） | `其他` | 管理费用 | 兜底 |

> 银行手续费和利息**不走这里**，走 `POST /api/bank/entry`（见 §7锛夈€?
>
> `functional_category` 合法值：`管理费用`(6601, 默认) / `閿€鍞垂鐢╜(6602) / `税金及附加`(6403) / `财务费用`(6603)。但当前系统 `EXPENSE_ACCOUNT_CODE_MAP` 只映射了前两个，6403 鍜?6801 浼氶粯璁ゅ洖閫€鍒?6601鈥斺€旀湀鏈鎻愬凡璧板紩鎿庣洿鍏ヨ处锛屾棩甯?expense API 鐨勭◣璐瑰垎褰曠鐩彲鑳戒笉鍑嗐€?

```json
POST /api/expenses
{
  "category": "房租",
  "amount": 5000,
  "expense_date": "2026-06-01",
  "functional_category": "管理费用"
}
```

**响应**锛?
```json
{"ok": true, "entity": {"id": 1, "category": "房租", "amount": 5000, "payment_status": "unpaid"}, "operation": "created"}
```

璐圭敤鍒涘缓鍚庤嚜鍔ㄧ敓鎴愪細璁″嚟璇侊紙鍊?费用科目 璐?搴斾粯璐︽锛夈€傛棤闇€棰濆鎿嶄綔銆?

濡傛灉鐢ㄦ埛璇?鎶婅繖绗旇垂鐢ㄤ粯浜? 鈫?鍘?§6 付款，用 `payment_type: "expense"` 鍏宠仈姝よ垂鐢ㄣ€?

### 工资：用户说"发工资了"

宸ヨ祫鏈夎鎻愬拰鍙戞斁涓や釜姝ラ锛岄渶瑕佸垎涓ゆ鎿嶄綔锛?

**绗?步：计提工资**
```json
POST /api/expenses
{
  "category": "工资",
  "amount": 80000,
  "expense_date": "2026-06-30",
  "functional_category": "管理费用"
}
```

**绗?步：发放工资**（实际付款）
```json
POST /api/payments
{
  "payment_type": "salary",
  "related_entity_type": "expense",
  "related_entity_id": 1,
  "amount": 70000,
  "payment_date": "2026-06-30"
}
```

> 璁℃彁鏃剁郴缁熺敓鎴愬簲浠樿亴宸ヨ柂閰嚟璇併€傚彂鏀炬椂鍐插噺搴斾粯銆?

> **璐圭敤褰曢敊浜?*锛氫笉瑕?DELETE，走红冲。`POST /api/expenses/{id}/reverse` 鍐茬孩鎬昏处鍑瘉骞舵爣璁?`is_reversed=True`，原记录保留。受 `ConfirmMiddleware` 鎷︽埅锛岀敤鎴风‘璁ゅ悗鎵ц銆?

---

### 4.5. 个人垫付：用户说"老板垫付了XX/我个人先付了"

> 閫傜敤鍦烘櫙锛氳€佹澘/鍛樺伐鐢ㄤ釜浜鸿祫閲戞浛鍏徃鍨粯璐圭敤锛堥浂鏄熼噰璐€佸姙鍏敮鍑恒€佽澶囪喘缃瓑锛夈€傚叕鍙稿舰鎴愪竴绗斿涓汉鐨勮礋鍊猴紝鎸傝处"鍏朵粬搴斾粯娆?绉戠洰锛?241锛夈€?
> 涓嶈鐢?`POST /api/expenses` + `payment_method=private_advance` 鏉ヨ涓汉鍨粯鈥斺€旈偅鏄垂鐢ㄦā鍧楃殑鍏煎瀛楁锛屼笉缁存姢鍨粯浜?鍋胯繕鐘舵€併€備釜浜哄灚浠樿蛋鐙珛妯″潡銆?

```text
1. 鎻愬彇锛氬灚浠樹汉濮撳悕銆侀噾棰濄€佸灚浠樻棩鏈熴€佺敤閫旓紙鍐冲畾鍊熸柟绉戠洰锛?
2. 确认 debit_account_code锛堝喅瀹氬€熸柟绉戠洰锛岃涓嬭〃锛?
```

| 鐢ㄦ埛璇寸敤閫?| `debit_account_code` | 借方科目 |
|-----------|----------------------|----------|
| 日常办公费用（默认） | `6601` | 管理费用 |
| 閿€鍞浉鍏虫敮鍑?| `6602` | 閿€鍞垂鐢?|
| 买了商品/存货 | `1405` | 库存商品 |
| 买了设备/固定资产 | `1601` | 固定资产 |
| 买了专利/杞欢绛夋棤褰㈣祫浜?| `1701` | 无形资产 |

**绗?姝ワ細鍒涘缓鍨粯鍗?*

```json
POST /api/personal-advances
{
  "advancer_name": "张三",
  "amount": 2000,
  "advance_date": "2026-06-30",
  "debit_account_code": "6601",
  "description": "鏇垮叕鍙稿灚浠?鏈堝姙鍏敤鍝?
}
```

系统自动生成凭证 `dr 6601 管理费用 / cr 2241 鍏朵粬搴斾粯娆綻锛屽灚浠樺崟鍙锋牸寮?`PA-2026-0001`銆?

**绗?姝ワ細鍋胯繕锛堥儴鍒嗘垨鍏ㄩ锛?*

```json
POST /api/personal-advances/{id}/repay
{
  "amount": 1000,
  "repayment_date": "2026-07-15",
  "bank_account_id": 1,
  "description": "首笔偿还"
}
```

- 甯?`bank_account_id` 鈫?璐?1002 银行存款 + 自动生成 BankTransaction + 扣减银行余额
- 不带 `bank_account_id` 鈫?璐?1001 库存现金
- 鏀寔澶氭閮ㄥ垎鍋胯繕锛岃嚜鍔ㄧ疮鍔?`paid_amount` 骞堕噸绠?`repayment_status`（unpaid 鈫?partial 鈫?paid锛?
- 偿还金额超过 `remaining_amount` 鏃惰繑鍥?400，AI 搴?STOP_RETRYING

**绗?姝ワ細鏌ュ灚浠樻槑缁?*

```http
GET /api/personal-advances?advancer_name=张三
GET /api/personal-advances/totals       # 鎬诲灚浠樸€佸凡杩樸€佹湭杩樻眹鎬?
GET /api/personal-advances/summary      # 按垫付人聚合
GET /api/personal-advances/{id}/repayments  # 单笔偿还记录
```

**冲红**锛?

- 鍨粯鍗曞綍閿?鈫?`POST /api/personal-advances/{id}/reverse`（须先红冲所有未冲红的偿还记录）
- 单笔偿还录错 鈫?`POST /api/personal-advances/{id}/repayments/{rid}/reverse`锛堣嚜鍔ㄥ弽鍚戦摱琛屾祦姘?+ 閲嶇畻鐘舵€侊級
- 禁止 DELETE，由 `readonly_middleware` 强制 403

**典型对话**锛?

- 鐢ㄦ埛锛?鑰佹澘寮犱笁鍨粯浜?000元买办公用品"
  鈫?鍒涘缓鍨粯鍗曪紝鍊?6601 / 璐?2241
- 鐢ㄦ埛锛?寮犱笁鐨勫灚浠樿繕浜嗕竴鍗?000锛屼粠宸ヨ璐︽埛鍑?
  鈫?璋?repay，bank_account_id=工行账户id，amount=1000
- 鐢ㄦ埛锛?寮犱笁鐨勫墿浣?000涔熺粨娓呬簡锛岀粰鐨勭幇閲?
  鈫?璋?repay，bank_account_id=null，amount=1000
- 鐢ㄦ埛锛?刚才那笔2000鐨勫灚浠樺崟褰曢敊浜嗭紝搴旇鐢ㄩ攢鍞垂鐢?
  鈫?璋?reverse 红冲原单 + 重新创建（如已有偿还，须先红冲偿还记录）

---

### 5. 固定资产：用户说"涔颁簡鍙拌澶?电脑"

```text
1. 鎻愬彇锛氳祫浜у悕绉般€佸師鍊笺€佹姌鏃у勾闄愩€佸惎鐢ㄦ棩鏈?
2. 纭鎶樻棫鏂规硶锛堢敤鎴锋病璇存槑鍒欓粯璁ゅ勾闄愬钩鍧囨硶锛?
3. 纭娈嬪€肩巼锛堥粯璁?5%锛?
```

```json
POST /api/fixed-assets
{
  "asset_code": "FA-001",
  "name": "鏈嶅姟鍣?,
  "original_value": 50000,
  "useful_life": 60,
  "start_date": "2026-06-01",
  "salvage_rate": 0.05,
  "depreciation_method": "骞撮檺骞冲潎娉?
}
```

**响应**锛?
```json
{"ok": true, "entity": {"id": 1, "asset_code": "FA-001", "name": "鏈嶅姟鍣?, "original_value": 50000, "status": "in_use"}, "operation": "created"}
```

**折旧方法**：`年限平均法`（默认）/ `鍙屽€嶄綑棰濋€掑噺娉昤 / `年数总和法`

> 鎶樻棫瑙勫垯锛氬綋鏈堝鍔?*下月**寮€濮嬭鎻愩€傛姌鏃х敱绯荤粺鑷姩鎸夋湀鎵归噺澶勭悊銆?
>
> **处置/报废**：用户说"设备坏了/卖了" 鈫?`PUT /api/fixed-assets/{id}` 鏀?`"status": "报废"`锛岀郴缁熻嚜鍔ㄧ敓鎴愬缃嚟璇併€?
> 处置前先查：`GET /api/fixed-assets` 确认资产 ID 鍜屽綋鍓嶇姸鎬併€?

---

## 绗笁閮ㄥ垎锛氳祫閲戠鐞?

### 6. 付款/收款：用户说"浠樹簡閽?鏀朵簡閽?

**必须先建银行账户**锛屽惁鍒欎粯娆句笉浼氫骇鐢熼摱琛屾祦姘达紝浣欓涓嶄細鏇存柊銆?

```text
查：GET /api/bank-accounts
 不存在则创建：POST /api/bank-accounts {"bank_name": "工商银行", "account_number": "6222****", "balance": 0}
 记下 bank_account_id
 确认余额充足（balance >= 浠樻閲戦锛?
```

> 濡傛灉鐢ㄦ埛娌℃湁鎸囧畾閾惰璐︽埛锛岃嚜鍔ㄥ彇绗竴涓摱琛岃处鎴枫€俙GET /api/bank-accounts` 杩斿洖鍒楄〃鐨勭涓€涓嵆涓洪粯璁よ处鎴枫€?

**瀛楁鍚堟硶鍊?*锛?
| 字段 | 鍙€夊€?|
|------|--------|
| `payment_type` | `purchase` / `expense` / `salary` / `tax` |
| `receipt_type` | `sale` |
| `related_entity_type` | `purchase_order` / `expense` / `tax_payable` |
| `payment_method` | `company`（默认） / `private_advance` |

### 付采购款

```text
1. 纭閲囪喘鍗?ID：GET /api/purchases?status=completed 鎵惧埌瀵瑰簲鍗?
2. 确认付款金额
```

```json
POST /api/payments
{
  "payment_type": "purchase",
  "related_entity_type": "purchase_order",
  "related_entity_id": 1,
  "amount": 11300,
  "payment_date": "2026-06-26",
  "bank_account_id": 1        # 鍙€夛紝娌℃湁閾惰璐︽埛鍒欎笉浼?
}
```

**响应**锛?
```json
{"status": "ok", "entity": {"id": 1, "amount": 11300, "payment_status": "paid"}}
```

### 收销售款

```text
1. 纭閿€鍞崟 ID：GET /api/sales?status=completed 鎵惧埌瀵瑰簲鍗?
2. 确认收款金额
```

```json
POST /api/receipts
{
  "receipt_type": "sale",
  "related_entity_type": "sale_order",
  "related_entity_id": 1,
  "amount": 11300,
  "receipt_date": "2026-06-26T10:00:00",
  "receipt_method": "company",
  "bank_account_id": 1
}
```

**响应**锛?
```json
{"status": "ok", "entity": {"id": 1, "amount": 11300, "payment_status": "paid"}}
```

收款/浠樻瀹屾垚鍚庯紝瀵瑰簲璁㈠崟鐨?`payment_status` 自动变为 `paid`。`bank_account_id` 鍜?`receipt_method` 闈炲繀濉紝浣嗗～浜?bank_account_id 浼氳嚜鍔ㄧ敓鎴?BankTransaction 骞舵洿鏂?1002 浣欓銆?

> **财务数据不可直接修改**锛氭敹娆?付款/银行交易没有 PUT/DELETE 鎺ュ彛鈥斺€旇繖鏄晠鎰忚璁°€傚鏋滃綍閿欎簡锛岃蛋绾㈠啿娴佺▼鐢熸垚鍙嶅悜鍒嗗綍锛屽師璁板綍淇濈暀渚涘璁¤拷婧€備互涓嬬孩鍐?取消端点已在 AI 鐧藉悕鍗曚腑锛岃皟鐢ㄦ椂鍙?`ConfirmMiddleware` 拦截（POST + `/reverse`/`/cancel`锛夛紝鐢ㄦ埛鍦ㄥ墠绔‘璁ゅ悗鎵ц锛?
> - `POST /api/receipts/{id}/reverse` 鈥?红冲收款
> - `POST /api/payments/{id}/reverse` 鈥?红冲付款
> - `POST /api/bank/transaction/{id}/reverse` 鈥?红冲银行交易
> - `POST /api/invoices/{id}/reverse` 鈥?[发票冲红](#鍙戠エ鍐茬孩鐢ㄦ埛璇村彂绁ㄥ紑閿欎簡閫€绁?锛堢孩瀛楀彂绁?绾ц仈鍐茬孩鍑瘉搴撳瓨锛?
> - `POST /api/expenses/{id}/reverse` 鈥?璐圭敤鍐茬孩锛堝啿绾㈡€昏处鍑瘉锛?
> - `POST /api/cash-flows/transactions/{id}/reverse` 鈥?现金流水冲红
> - `POST /api/purchases/{id}/cancel` 鈥?取消采购单（冲红凭证+搴撳瓨鍥為€€锛?
> - `POST /api/sales/{id}/cancel` 鈥?鍙栨秷閿€鍞崟锛堝啿绾㈠嚟璇?搴撳瓨鍥為€€锛?

---

### 7. 银行管理：用户说"寮€涓处鎴?鏌ラ摱琛屾祦姘?

閾惰璐︽埛鏄祫閲戠鐞嗙殑鍩虹銆傚垱寤轰粯娆?鏀舵鍓嶅缓璁厛寤哄ソ璐︽埛銆?

### 创建银行账户

```text
1. 确认账户名称（如"鍩烘湰鎴?銆?涓€鑸埛"锛?
2. 确认账号（用户提供或问用户）
3. 璐︽埛鍒濆浣欓蹇呴』涓?0
```

```json
POST /api/bank-accounts
{
  "bank_name": "工商银行",
  "account_number": "6222021234567890",
  "balance": 0
}
```

> `balance` 鍙兘浼?0锛堟晠鎰忚璁★級銆傚紑鎴锋椂璐﹂潰浣欓涓?0锛岀劧鍚庨€氳繃**瀵煎叆閾惰瀵硅处鍗?+ 对账**鏉ョ‘璁ゆ湡鍒濅綑棰濓細鐢ㄦ埛灏嗛摱琛屽鍑虹殑绗竴浠藉璐﹀崟锛堝惈鏈熷垵浣欓锛夊鍏ョ郴缁燂紝瀵硅处鍚庤嚜鍔ㄧ‘瀹氶摱琛岃处鎴风殑鐪熷疄浣欓銆傝繖鏄洿瑙勮寖鐨勪細璁″疄璺碘€斺€旇处鎴蜂綑棰濇潵鑷摱琛屾祦姘磋€岄潪鎵嬪姩濉啓锛屽悓鏃朵篃璁╃敤鎴蜂粠涓€寮€濮嬪氨鐔熸倝瀵硅处娴佺▼銆傚鏋滆 `balance > 0`锛岀郴缁熶細鎷掔粷骞跺紩瀵艰蛋瀵硅处娴佺▼銆?
>
> 娉ㄦ剰锛?*总账 1002 期初余额**浠嶉€氳繃 `POST /api/opening-balances` 设定（见[初始化新账本](#初始化新账本)锛夛紝杩欎笌閾惰璐︽埛鐨勫疄鎿嶄綑棰濇槸涓ゅ浣撶郴銆傛€昏处鏈熷垵浣欓鍙嶆槧绉戠洰鍘嗗勾缁撹浆鏁帮紝閾惰璐︽埛浣欓鍙嶆槧閾惰娴佹按瀹為檯鏁帮紝涓よ€呴€氳繃瀵硅处淇濇寔涓€鑷淬€?

### 鏌ラ摱琛屾祦姘?

鐢ㄦ埛璇?鏌ヤ竴涓嬮摱琛屾祦姘?鐪嬭处鎴蜂綑棰?锛?

```text
1. GET /api/bank-accounts 鈫?确认有哪些账户，记下 bank_account_id
2. GET /api/bank-transactions?bank_account_id=1 鈫?查看流水明细
```

### 银行利息/鎵嬬画璐圭洿褰?

鐢ㄦ埛璇?閾惰鎵ｄ簡鎵嬬画璐?给了利息"锛屼笉闇€瑕佽蛋瀵硅处娴佺▼锛岀洿鎺ュ綍鍏ャ€?

**请求**:

```json
POST /api/bank/entry
{
  "entry_type": "interest_income",
  "amount": 0.61,
  "transaction_date": "2025-06-21"
}
```

| 字段 | 说明 | 鍚堟硶鍊?|
|------|------|--------|
| `entry_type` | 业务类型 | `"interest_income"`锛堝埄鎭敹鍏ワ級鎴?`"bank_fee"`锛堟墜缁垂锛?|
| `amount` | 閲戦锛屽繀椤?> 0 | 正数，单位元 |
| `transaction_date` | 银行流水日期 | `YYYY-MM-DD` |

**响应**:

```json
{
  "status": "ok",
  "entry_type": "interest_income",
  "amount": 0.61
}
```

> 鍝嶅簲涓嶈繑鍥?BankTransaction ID 鍜屼細璁″嚟璇?ID銆傚闇€鍐查攢锛岄€氳繃 `GET /api/bank-transactions?bank_account_id=X` 鎸夋棩鏈熷拰閲戦瀹氫綅娴佹按銆?

**鐢熸垚鐨勫垎褰?*:

| entry_type | system 自动处理 |
|-----------|----------------|
| `interest_income`（利息收入） | 鍊?1002 银行存款 / 璐?6603 财务费用（inflow，增加银行余额） |
| `bank_fee`（手续费/管理费） | 鍊?6603 财务费用 / 璐?1002 银行存款（outflow，减少银行余额） |

系统同时生成 BankTransaction 娴佹按鍜屼細璁″嚟璇侊紝鏃犻渶鎵嬪姩瀵硅处銆?

> ⚠️ `entry_type` 鍙帴鍙?`"interest_income"` 鍜?`"bank_fee"` 涓や釜鍊笺€備紶 `"interest"`、`"利息"` 鎴栧叾浠栧€间細杩斿洖 **422**锛屽搷搴旀牸寮?
> ```json
> {"detail": [{"type": "literal_error", "msg": "...", "input": "interest"}]}
> ```
> Pydantic Literal 鏍￠獙鍦ㄨ姹傚眰鎷︽埅锛屼笉浼氶敊璇叆璐︺€?

**幂等**：BankTransaction ID 浣滀负浼氳鍑瘉鐨?`source_id`，红冲时通过 `reverse_journal` 鍊熻捶浜掓崲绾㈠啿鍘熷鍑瘉锛屼笉浼氱敓鎴愰噸澶嶈褰曘€?

**🔍 常见错误排查**锛堟寜鍑虹幇棰戠巼鎺掑垪锛?

| 报错 | 原因 | 排查 |
|------|------|------|
| **422** `literal_error` | `entry_type` 不是 `"interest_income"` 鎴?`"bank_fee"` | 妫€鏌ユ嫾鍐欙紝鐢ㄥ鍚堟硶鍊?|
| **422** `type_error` | `amount` 涓嶆槸鏁板瓧鎴?< 0 | 确认金额 > 0 |
| `绉戠洰缂栫爜涓嶅瓨鍦? 1002/6603` | 璐︽湰绉戠洰琛ㄦ湭鍒濆鍖?| `GET /api/finance/trial-balance` 鈫?空表则调 [`POST /api/bootstrap`](#初始化新账本) |
| `不是叶子科目` | 绉戠洰琚爣璁颁负鐖剁鐩?| `GET /api/finance/trial-balance` 鐪嬬粨鏋勶紝濡傝嚜瀹氫箟绉戠洰灞傜骇瀵艰嚧闇€璁?is_leaf=True |
| `借贷不平衡` | 凭证自身不平（极罕见，bank_fee_entry 是双行分录） | 鎶ュ憡寮€鍙?|

如果利息/鎵嬬画璐规槸鍦ㄦ湡鏈璐︽椂鎵嶅彂鐜帮紙閾惰宸叉墸浣嗙郴缁熸湭璁帮級锛岃蛋瀵硅处娴佺▼澶勭悊锛?

1. **瀵煎叆瀵硅处鍗?* 鈫?`POST /api/bank/statement`
2. **执行对账** 鈫?`POST /api/bank/reconcile?period=YYYY-MM`（响应含 `id`，即下一步的 `{rec_id}`锛?
3. **生成凭证** 鈫?`POST /api/bank/reconciliation/{rec_id}/generate-entry`锛堝彧鐢熸垚浼氳鍑瘉锛屼笉浜х敓閾惰娴佹按锛?
4. **纭璋冭妭琛?* 鈫?`POST /api/bank/reconciliation/{rec_id}/confirm`

鐩村綍涓庡璐︽祦绋嬬殑閫夋嫨鍙栧喅浜庤璐︽椂鏈猴細骞虫椂瑙佷竴绗旇涓€绗旂敤鐩村綍锛屾湡鏈粺涓€澶勭悊鐢ㄥ璐︺€?

> ⚠️ **褰曢敊浜嗘€庝箞鍔?*锛氫笉瑕?DELETE 鎴栦慨鏀癸紝鐢ㄧ孩瀛楀啿閿€銆傜敱浜?Pydantic Literal 鏍￠獙宸叉嫤鎴潪娉?`entry_type`，不会再发生"利息被误记为支出"鐨勯敊璇€備絾浠嶇劧鍙兘鍥?**閲戦鎴栨棩鏈熷～閿?* 闇€瑕佸啿閿€锛?
> - 记了不该记的 鈫?`POST /api/bank/transaction/{tx_id}/reverse` 冲销
> - 璁板皯浜?鈫?鍏堝啿閿€鍘熻褰曪紝鍐嶉噸鏂板綍鍏ユ纭噾棰?
> - 璁板浜?鈫?同上
>
> 鍐查攢鍚庡師璁板綍淇濈暀锛屽璁＄棔杩瑰畬鏁淬€?

### 创建现金流水

> 银行流水（BankTransaction）不允许 AI 鐩存帴鍒涘缓銆傛墍鏈夐摱琛屾祦姘村繀椤婚€氳繃涓氬姟鎿嶄綔鑷姩鐢熸垚锛氫粯娆撅紙`POST /api/payments`锛夈€佹敹娆撅紙`POST /api/receipts`锛夈€佸埄鎭?手续费直录（`POST /api/bank/entry`锛夈€傛湡鍒濅綑棰濓紙`POST /api/opening-balances`）过账到总账 1002 但不产生 BankTransaction銆傜洿鎺ュ垱寤烘祦姘翠細鐮村潖璐﹀姟涓€鑷存€э紝瀵艰嚧瀵硅处涓嶅钩銆傚璐︽祦绋嬬殑 `generate-entry` 鍙敓鎴愪細璁″嚟璇侊紝涓嶄骇鐢熼摱琛屾祦姘淬€?

鐢ㄦ埛璇?鏈変竴绗旈摱琛岃浆璐?现金收入"锛?

```json
POST /api/cash-flows/transactions
{
  "type": "inflow",
  "amount": 50000,
  "flow_category": "operating",
  "transaction_date": "2026-06-26",
  "description": "客户转账"
}
```

| `type` | 说明 |
|--------|------|
| `inflow` | 资金流入 |
| `outflow` | 资金流出 |

| `flow_category` | 说明 |
|-----------------|------|
| `operating`（默认） | 经营活动 |
| `investing` | 投资活动 |
| `financing` | 筹资活动 |

---

### 8. 库存调整：用户说"盘点/报损"

```text
1. GET /api/inventory 鏌ュ綋鍓嶅簱瀛?
2. 纭瑕佽皟鏁寸殑鍟嗗搧鍜屾暟閲忥紙姝?入库，负=鍑哄簱锛?
3. 确认调整原因
```

```json
PUT /api/inventory/{product_id}
{
  "quantity": 100
}
```

> `quantity` 姝ｅ€?鍏ュ簱锛岃礋鍊?鍑哄簱銆?

**响应**锛?
```json
{"ok": true, "entity": {"product_id": 1, "quantity": 100, "unit_cost": 35.50}}
```

**错误**：`INVENTORY_INSUFFICIENT`（出库量 > 褰撳墠搴撳瓨锛夈€備笉蹇呴棶鐢ㄦ埛锛岀洿鎺ユ妸搴撳瓨閲忓拰鎯冲嚭搴撶殑鏁板憡璇夌敤鎴凤紝鐢辩敤鎴峰喅绛栥€?

---

### 9. 个人流水：用户说"记一笔个人账"

```text
1. 确认 type：收入（income）还是支出（expense锛?
2. 鎻愬彇锛氶噾棰濄€佸垎绫汇€佹棩鏈?
```

```json
POST /api/personal
{
  "type": "expense",
  "amount": 50,
  "category": "餐饮",
  "date": "2026-06-26"
}
```

收入分类：`工资`/`兼职`/`理财`/`其他`
支出分类：`餐饮`/`日用`/`浜ら€歚/`娱乐`/`医疗`/`烟酒`/`其他`

**响应**锛?
```json
{"id": 1, "type": "expense", "amount": 50, "category": "餐饮", "date": "2026-06-26", "status": "created"}
```

---

## 第四部分：查询与报表

### 10. 鏌ユ姤琛細鐢ㄦ埛璇?杩欎釜鏈堣禋浜嗗灏?

用户问经营情况，查财务报表：

| 鐢ㄦ埛闂?| 璋冧粈涔?|
|--------|--------|
| "杩欎釜鏈堣禋浜嗗灏? | `GET /api/financial-reports/income-statement?start_date=2026-06-01&end_date=2026-06-30` |
| "现在公司有多少钱" | `GET /api/financial-reports/balance-sheet?date=2026-06-26` |
| "这个月要交多少税" | `GET /api/tax-report?year=2026&quarter=2` |
| "瀹㈡埛娆犳垜澶氬皯閽? | `GET /api/finance/receivable/partner/{id}?partner_type=customer` |
| "库存值多少钱" | `GET /api/inventory` |

> 鍒╂鼎琛?`revenue`：一般纳税人和小规模均取不含税金额（系统内部做价税分离）。`cost_of_goods_sold` 使用出库时锁定的移动加权平均成本（`SaleItem.unit_cost`锛夈€?

---

## 绗簲閮ㄥ垎锛氭湡鏈鐞?

### 11. 月结（月末结账）：用户说"结账/月结/算税"

姣忔湀缁忚惀缁撴潫鍚庡仛涓€娆℃湀缁撱€傜郴缁熻嚜鍔ㄥ畬鎴愶細璁＄畻 VAT 鈫?杞嚭鏈氦澧炲€肩◣ 鈫?璁℃彁闄勫姞绋?鈫?璁℃彁鎵€寰楃◣銆?

```
POST /api/finance/month-close
{ "period": "2025-06" }
```

### 鏈堢粨鍓嶅繀椤绘弧瓒?

1. **本月银行余额调节表已确认**銆傛湭纭浼氳鎷掔粷锛?
   ```
   "閾惰瀵硅处鏈畬鎴? 工商银行(6222) 调节表状态为 draft，请先完成银行对账并确认"
   ```

2. 绯荤粺浼氳嚜鍔ㄦ媺鍙?Account 鐨?`taxpayer_type` 鏉ュ垽鏂◣鐜囷紙涓€鑸?25% / С΢ 5%锛夈€?

3. **浜忔崯涓嶇即鎵€寰楃◣**：累计利润为负时，系统自动跳过所得税计提（`tax_payable=0`锛夛紝涓嶆姤閿欍€傚埄娑﹀洖鍗囨椂鑷姩琛ユ彁锛屽埄娑︿笅闄嶆椂鑷姩鍐插洖澶氭彁閮ㄥ垎銆?

4. **个体工商户不缴企业所得税**锛氱郴缁熻鍙?`Account.type` 瀛楁鍖哄垎涓讳綋绫诲瀷锛?
   - `type = "company"`锛堝叕鍙?有限责任公司）→ 缂翠紒涓氭墍寰楃◣锛?%/25%锛?
   - `type = "personal"`（个体工商户）→ 不计提企业所得税（`tax_payable=0`锛夛紝涓綋鎴风即绾崇粡钀ユ墍寰椾釜浜烘墍寰楃◣锛堢郴缁熶笉澶勭悊涓◣锛?
   查：GET /api/accounts 鈫?鐪?`type` 字段

### 月结返回解读

```json
{
  "status": "ok",
  "period": "2025-06",
  "curr_vat": 227,
  "cumulative_profit": -4515.60,
  "target_income_tax": 0,
  "posted_income_tax": 0,
  "lines": ["闄勫姞绋? +27.24"],
  "tax_check": {
    "all_passed": false,
    "checks": [
      {"name": "閿€鍞", "declared": 3500, "book": 3500, "diff": 0, "passed": true},
      ...
    ],
    "warnings": ["缺失申报数据: 閿€鍞"]
  }
}
```

| 字段 | 含义 |
|------|------|
| `curr_vat` | 褰撴湀搴斾氦澧炲€肩◣锛堥攢椤?- 留抵 - 杩涢」锛?|
| `cumulative_profit` | 绱鍒╂鼎锛堟敹鍏?- 成本 - 费用 - 附加税） |
| `target_income_tax` | 应计提所得税总额 |
| `posted_income_tax` | 已计提所得税 |
| `lines` | 鏈鐢熸垚鐨勫嚟璇佹憳瑕?|
| `tax_check` | 自动税务核对结果 |

### 绯荤粺鑷姩鐢熸垚鐨勫嚟璇?

```
dr 6403 绋庨噾鍙婇檮鍔?27.24    cr 222104 搴斾氦闄勫姞绋?27.24       (闄勫姞绋?
dr 222106 杞嚭鏈氦澧炲€肩◣ 227  cr 222107 鏈氦澧炲€肩◣ 227         (VAT转出)
dr 6801 鎵€寰楃◣ xx           cr 222105 搴斾氦鎵€寰楃◣ xx           (鎵€寰楃◣, 有利润时)
```

> 澧炲€肩◣缁撹浆瑙勫垯锛氬綋鏈堥攢椤?> 杩涢」鏃讹紝宸浠?222106(杞嚭鏈氦澧炲€肩◣) 转入 222107(鏈氦澧炲€肩◣)。留抵自然体现在 222101+222102+222106 鍊熸柟浣欓涓紝鏃犻渶涓撻棬鍒嗗綍銆?

### 鎵€寰楃◣璺ㄦ湡鍐插洖

鍒╂鼎娉㈠姩鏃剁郴缁熻嚜鍔ㄥ鐞嗭細涓婁釜鏈堝鎻愪簡鎵€寰楃◣锛屾湰鏈堝埄娑︿笅闄?鈫?鑷姩鐢熸垚鍙嶅悜鍒嗗綍鍐插洖銆?

```
累计利润下降: dr 222105 cr 6801 (红冲, 冲回多提)
累计利润上升: dr 6801 cr 222105 (补提)
```

### 补结历史月份

直接调月结接口，传入历史 period 鍗冲彲銆傜郴缁熸寜鏃ユ湡璇嗗埆锛岃嚜鍔ㄨˉ榻愩€?

---

### 12. 银行对账：用户说"对账/閾惰浣欓璋冭妭琛?

瀵硅处瀹屾暣娴佺▼锛?*瀵煎叆瀵硅处鍗?鈫?自动对账 鈫?鏌ョ湅鏈揪椤?鈫?澶勭悊鏈揪椤?鈫?纭璋冭妭琛?*

### 绗?姝ワ細瀵煎叆閾惰瀵硅处鍗?

从银行下载的流水（网银导出的 Excel/CSV锛夋暣鐞嗘垚浠ヤ笅鏍煎紡锛?

```json
POST /api/bank/statement
{
  "period_start": "2025-06-01",
  "period_end": "2025-06-30",
  "opening_balance": 29012,
  "closing_balance": 24999,
  "lines": [
    {"transaction_date": "2025-06-05", "amount": 3955, "description": "閿€鍞洖娆?},
    {"transaction_date": "2025-06-10", "amount": -3500, "description": "工资发放"},
    {"transaction_date": "2025-06-15", "amount": -15, "description": "璐︽埛绠＄悊璐?}
  ]
}
```

> 每笔 line 鐨?`amount`锛氭鏁?閾惰鏀跺埌锛岃礋鏁?银行支出。同系统 BankTransaction 鐨勬柟鍚戜竴鑷淬€?
>
> ⚠️ **`opening_balance` 蹇呴』涓庨摱琛屽璐﹀崟涓婄殑鏈熷垵浣欓涓€鑷?*锛屽～閿欎細瀵艰嚧鎵€鏈夋湭杈鹃」璁＄畻鍋忕Щ锛屾暣寮犺皟鑺傝〃浣滃簾銆傚鏋滃彂鐜板璐︾粨鏋滃紓甯革紝鍏堟鏌ユ湡鍒濅綑棰濆拰 seed 鍙傛暟鏄惁姝ｇ‘銆?

**绗?步：执行自动对账**

如果期初账面余额和对账单期初余额不一致，差额就是**鏈熷垵鏈揪椤?*锛岄€氳繃 `seed` 鍙傛暟浼犲叆锛?

```
POST /api/bank/reconcile?period=2025-06&seed=[{"item_type":"book_paid_not_bank","amount":3500,"direction":"out","notes":"涓婃湀搴曞凡浠橀摱琛屾湭鎵?}]
```

| seed 参数 | 说明 |
|-----------|------|
| `item_type` | `book_paid_not_bank` / `book_received_not_bank` / `adjustment` |
| `amount` | 金额 |
| `direction` | `in`（账面加项） / `out`（账面减项） |
| `notes` | 原因说明 |

没有期初未达项则直接调：

```
POST /api/bank/reconcile?period=2025-06
```

绯荤粺鎵ц锛?
1. **1:1 精确匹配** 鈥?日期 ±3 澶?+ 閲戦涓€鑷?+ 鏂瑰悜涓€鑷?
2. **N:1 组合匹配** 鈥?绯荤粺澶氱瑪鍚堝苟鎴愰摱琛屼竴绗旓紙瀹㈡埛鍒嗘鎵撴閾惰鍚堝苟鍏ヨ处锛?
3. **跨期滚动** 鈥?上月 book_not_bank 椤瑰湪鏈湀瀵硅处鍗曞嚭鐜?鈫?自动 resolved
4. **费用扫描** 鈥?绠＄悊璐?鎵嬬画璐?利息 鈫?标记 `action=generate_entry`

杩斿洖锛?
```json
{
  "id": 6,
  "book_balance": 24999,
  "statement_balance": 24999,
  "adjusted_book": 24999,
  "adjusted_statement": 24999,
  "balanced": true
}
```

**绗?姝ワ細鏌ョ湅璋冭妭琛?*

```
GET /api/bank/reconciliation?period=2025-06
```

返回每条未达项：
```json
{
  "items": [
    {"item_type": "bank_paid_not_book", "amount": 15, "action": "generate_entry"}
  ]
}
```

| item_type | 含义 | 调节方向 |
|-----------|------|----------|
| `bank_received_not_book` | 银行已收企业未收 | 账面 + |
| `bank_paid_not_book` | 银行已付企业未付 | 账面 - |
| `book_received_not_bank` | 企业已收银行未收 | 瀵硅处鍗?+ |
| `book_paid_not_bank` | 企业已付银行未付 | 瀵硅处鍗?- |

> **常见原因**：`bank_received_not_book` 通常是收款时没传 `bank_account_id`，系统没生成银行流水。`bank_paid_not_book` 鍚岀悊銆傝繖浜涙湭杈鹃」鍙€氳繃 `generate-entry` 鐢熸垚琛ュ綍鍑瘉锛屼絾鏍瑰洜鏄搷浣滀笉瑙勮寖銆傚鏋滃ぇ閲忓嚭鐜帮紝寤鸿鍛婄煡鐢ㄦ埛锛氬悗缁敹娆?浠樻鍔″繀濉?`bank_account_id`銆?

### 澶勭悊鏈揪椤?

**费用/缁撴伅鏈揪椤?*（item_type 涓?`bank_paid_not_book` 鎴?`bank_received_not_book`，action=`generate_entry`）：

先调 `generate-entry` 鐢熸垚鍑瘉锛屽啀璋?`confirm` 纭閿佸畾銆?*涓ゆ涓嶈兘鍚堝苟銆?*

```
# 绗?姝ワ細鐢熸垚鍑瘉锛堢敓鎴?dr 6603 cr 1002 鎴?dr 1002 cr 6603锛?
POST /api/bank/reconciliation/{id}/generate-entry

# 绗?姝ワ細纭璋冭妭琛紙妫€鏌ュ叏閮?resolved 鈫?閿佸畾锛?
POST /api/bank/reconciliation/{id}/confirm
```

鐢熸垚瑙勫垯锛?
| 鏈揪椤圭被鍨?| 分录 |
|-----------|------|
| `bank_paid_not_book`（手续费/管理费） | dr 6603 财务费用 cr 1002 银行存款 |
| `bank_received_not_book`（结息收入） | dr 1002 银行存款 cr 6603 财务费用-利息收入 |

> 濡傛灉鐢?`confirm` 鏃惰繕鏈夋湭澶勭悊鐨?generate-entry 椤癸紝绯荤粺浼氳繑鍥?422 + 閿欒鎻愮ず锛屽憡璇変綘鏈夊嚑绗斿緟澶勭悊銆傚厛璋?`generate-entry` 鍐嶉噸璇?`confirm`銆?

**强制匹配**锛堟棩鏈熻秴鏍囦絾閲戦瀵瑰緱涓婏級锛?

```json
POST /api/bank/reconciliation/{id}/match
{
  "stmt_line_ids": [42],
  "bank_tx_ids": [7, 12, 15],
  "reason": "瀹㈡埛鍒嗕笁娆℃墦娆撅紝閾惰鍚堝苟涓€绗旓紝璺ㄨ秺18澶?,
  "force": true
}
```

> 寮哄埗鍖归厤浼氬啓瀹¤鏃ュ織锛岀‘璁ゆ椂浜屾寮圭獥銆?

**绗?姝ワ細纭璋冭妭琛?*

```
POST /api/bank/reconciliation/{id}/confirm
```

鍓嶆彁锛氳皟鑺傚悗浣欓涓€鑷?(balanced=true)銆佹墍鏈夋湭杈鹃」宸插鐞嗘垨鏈夊娉ㄣ€佹棤 >1.00 鐨勬妧鏈€ц皟鏁淬€傜‘璁ゅ悗閿佸畾锛屼笉鍙慨鏀广€?

### 调节表状态机

```
draft 鈫?matching 鈫?balanced 鈫?confirmed (锁定)
```

月结前置校验：调节表必须 `confirmed`锛屽惁鍒?`POST /api/finance/month-close` 琚嫆缁濄€?

---

### 13. 税务核对：用户说"核对/璐﹁〃涓€鑷?税局要查"

```
GET /api/tax/check?period=2025-06&sales=3500&output_vat=455&input_vat=228&unpaid_vat=1039&income_tax=0&surcharge=124.68&vat_payable=227&gross_profit=-4515.60
```

### 8 椤规牳瀵规竻鍗?

| 鏍稿椤?| 鐢虫姤琛?| 账面取数 | 含义 |
|--------|--------|----------|------|
| 閿€鍞 | `sales` | 6001+6051 璐锋柟鍙戠敓棰?| 收入口径 |
| 閿€椤圭◣棰?| `output_vat` | 涓€鑸撼绋庝汉 222101 / 灏忚妯?222103 璐锋柟鍙戠敓棰?| 寮€绁ㄩ攢椤?|
| 进项税额 | `input_vat` | 222102 鍊熸柟鍙戠敓棰?| 认证进项 |
| 鏈氦澧炲€肩◣ | `unpaid_vat` | 222107 累计贷方余额 | 鏈熸湯娆犵◣锛?*绱鍊硷紝闈炲綋鏈?*锛?|
| 鎵€寰楃◣璐圭敤 | `income_tax` | 6801 借方-璐锋柟鍙戠敓棰?| 当期计提 |
| 闄勫姞绋?计税依据 | `vat_payable` | 222106 鍊熸柟鍙戠敓棰?| = 杞嚭鏈氦澧炲€肩◣ |
| 闄勫姞绋?金额 | `surcharge` | 6403 借方-璐锋柟鍙戠敓棰?| = VAT×12% |
| 利润总额 | `gross_profit` | 鍒╂鼎琛?gross_profit_total | 鍚檮鍔犱笉鍚墍寰?|

### 核对结果解读

```json
{
  "all_passed": true,
  "checks": [
    {"name": "鏈氦澧炲€肩◣", "declared": 1039, "book": 1039, "diff": 0, "passed": true}
  ],
  "warnings": []
}
```

- `all_passed=true` 鈫?璐﹁〃涓€鑷达紝鍙互鐢虫姤
- `all_passed=false` + `warnings` 鈫?閫愰」鐪?diff锛岃拷鏌ュ樊寮?

**常见差异**锛?
- 鏈氦澧炲€肩◣涓嶅尮閰?鈫?声明填了当月 VAT锛屼絾鏍稿寮曟搸璇荤殑鏄疮璁¤捶鏂逛綑棰濄€傚簲濉?`_crd("222107")` 鐨勭疮璁″€?
- 鍒╂鼎鎬婚涓嶅尮閰?鈫?利润表含附加税费用，声明时漏算了

> 鏈堢粨鍚庤嚜鍔ㄨ繍琛岀◣鍔℃牳瀵癸紝缁撴灉鍦?`POST /api/finance/month-close` 杩斿洖鐨?`tax_check` 瀛楁涓€?

---

## 绗叚閮ㄥ垎锛氶檮褰?

### 14. 异常处理速查

| 浣犳敹鍒?| 原因 | 浣犲簲璇?|
|--------|------|--------|
| **202** `confirm_token: "..."` | POST 璺緞鍚?`/reverse`/`/cancel`/`/dispose` | 不可逆操作被 ConfirmMiddleware 拦截，用户在前端确认后才执行 |
| `403 ENDPOINT_NOT_ALLOWED_FOR_AI` | 璋冧簡鐧藉悕鍗曞鐨勬帴鍙?| **立即停止**，按 `suggested_endpoint` 改用规范接口 |
| `404` | 璧勬簮涓嶅瓨鍦?| 鍏?`GET` 查询确认 ID 正确 |
| `409` 编码重复 | 鍟嗗搧缂栫爜鎴栧彂绁ㄥ彿鐮佸啿绐?| 淇敼鍚庨噸璇?|
| `422` 参数校验失败 | 字段值不合法 | 鍝嶅簲鍚悎娉曞€煎垪琛紝鎸夋彁绀轰慨姝?|
| `INVENTORY_INSUFFICIENT` | 库存不足 | 闂敤鎴凤細鏄惁寮哄埗鍑哄簱锛熸垨鍑忓皯鏁伴噺锛?|
| `INVOICE_DUPLICATE_NUMBER` | 鍙戠エ鍙风爜宸插瓨鍦?| 闂敤鎴凤細鏄惁纭閲嶅褰曞叆锛?|
| `BALANCE_ALREADY_EXISTS` | 璇ユ棩鏈熷凡鏈夋湡鍒濅綑棰?| 不可重复创建 |
| `BANK_ACCOUNT_NOT_FOUND` | 閾惰璐︽埛涓嶅瓨鍦?| 妫€鏌?bank_account_id |
| `DATA_INTEGRITY_ERROR` | 鏁版嵁鍙椾繚鎶や笉鍙慨鏀?| 闇€閫氳繃绾㈠啿/璋冩暣鍗曞悎瑙勬搷浣?|
| `SECURITY_VIOLATION` | 鎿嶄綔琚畨鍏ㄧ瓥鐣ユ嫤鎴?| 请走合规 API |
| `INVALID_OPERATION` | 灏濊瘯淇敼涓嶅彲鍙樻暟鎹?| 这是系统保护，需通过红冲流程处理 |
| **鐢ㄦ埛璇?鍒氭墠閭ｇ瑪褰曢敊浜嗚鏀?** | 业务数据已生成不可直接改 | 璧扮孩鍐?取消（受 ConfirmMiddleware 拦截，需用户前端确认）：收款→`POST /api/receipts/{id}/reverse`、付款→`POST /api/payments/{id}/reverse`、银行交易→`POST /api/bank/transaction/{id}/reverse`、发票→`POST /api/invoices/{id}/reverse`、费用→`POST /api/expenses/{id}/reverse`、现金流水→`POST /api/cash-flows/transactions/{id}/reverse`、采购单→`POST /api/purchases/{id}/cancel`、销售单→`POST /api/sales/{id}/cancel` |

---

### 15. 绯荤粺鑷姩鍋氫簡浠€涔堬紙浣犱笉鐢ㄧ锛?

| 浣犺皟浜?| 系统自动完成 |
|--------|-------------|
| `POST /api/purchases`（限小规模） | 入库 + 更新库存均价 + 生成应付凭证 |
| `POST /api/sales`（限小规模） | 出库 + 閿佸畾閿€鍞垚鏈?+ 生成收入+成本凭证 |
| `POST /api/expenses` | 生成应付费用凭证 |
| `POST /api/payments` | 鏍囪閲囪喘鍗曞凡浠?+ 生成付款凭证 + 更新银行余额 |
| `POST /api/receipts` | 鏍囪閿€鍞崟宸叉敹 + 生成收款凭证 + 更新银行余额 |
| `POST /api/invoices/quick` + `auto_create` | **涓€鑸撼绋庝汉鍞竴鍏ュ彛**锛氳嚜鍔ㄥ缓閿€鍞崟/閲囪喘鍗?+ 鍑哄叆搴?+ 生成收入/成本凭证（dr 1122 cr 6001+222101 + dr 6401 cr 1405锛?|
| `POST /api/finance/month-close` | 计算 VAT 鈫?杞嚭鏈氦澧炲€肩◣ 鈫?璁℃彁闄勫姞绋?鈫?璁℃彁鎵€寰楃◣ 鈫?自动税务核对 |
| `POST /api/bank/reconcile` | 4杞尮閰?1:1+N:1) + 跨期滚动 + 费用扫描 + 璋冭妭鍚庝綑棰濊绠?|
| `POST /api/bank/reconciliation/{id}/generate-entry` | 鐢熸垚鏈揪椤瑰垎褰曪細鎵嬬画璐?dr 6603 cr 1002锛岀粨鎭?dr 1002 cr 6603 |
| `POST /api/*/{id}/reverse`（红冲） | 反向分录 + 标记 `is_reversed=True` + 保留原记录；发票/采购/閿€鍞澶栧洖閫€搴撳瓨 |
| `POST /api/*/{id}/cancel`（取消） | 冲红凭证 + 鍥為€€搴撳瓨 + 保留审计轨迹 |

**以下数据不可修改**：StockMove（库存流水）、FixedAssetDepreciation（折旧流水）、AccountMove锛堜細璁″嚟璇侊級銆傚嚭閿欏彧鑳介€氳繃绾㈠啿/璋冩暣銆?

### 16. 閬囧埌娌¤杩囩殑鎯呭喌鎬庝箞鍔?

鎵嬪唽涓嶅彲鑳借鐩栨墍鏈夊満鏅€傞亣鍒版剰鏂欎箣澶栫殑鎯呭喌锛屾寜浠ヤ笅椤哄簭澶勭悊锛?

**绗竴姝ワ細鏌?*
- `GET /api/enums` 鈥?鐪嬪瓧娈垫湁鍝簺鍚堟硶鍊?
- `GET /api/_ai/capabilities` 鈥?纭鐧藉悕鍗曟帴鍙?
- `GET /api/accounts` 鈥?确认账本存在
- `GET /api/health` 鈥?纭绯荤粺鍦ㄨ繍琛?

**绗簩姝ワ細闂敤鎴?*
- 信息不全 鈫?问用户："请问XX是多少？"
- 閲戦瀵逛笉涓?鈫?问用户："杩欎釜閲戦鏄惈绋庤繕鏄笉鍚◣锛?
- 数据矛盾 鈫?把矛盾点摆出来让用户确认

**绗笁姝ワ細鏌ヤ細璁″噯鍒?*
- `docs/灏忎紒涓氫細璁″噯鍒?md` 鈥?鍏紡銆佸垎褰曘€佹硶寰嬩緷鎹?

**绗洓姝ワ細鎵胯涓嶇‘瀹?*
- 如果以上都找不到答案，直接告诉用户："杩欎釜鍦烘櫙鎵嬪唽娌℃湁瑕嗙洊锛屾垜闇€瑕佺‘璁や竴涓嬨€?
- 如果发现是系统设计缺陷或代码 bug（如缺少 import銆佽〃鏈垱寤恒€佸瓧娈电己澶憋級锛岀洿鎺ュ憡璇夌敤鎴烽棶棰樻牴鍥狅紝骞跺缓璁仈绯诲紑鍙戜汉鍛樹慨澶嶃€?
- **涓嶈缂栭€犳帴鍙ｃ€佷笉瑕佺紪閫犲弬鏁般€佷笉瑕佺寽娴嬩笟鍔¤鍒欍€?*

---

*财务Agent 操作手册 v5.1 | 2026-06-29*

