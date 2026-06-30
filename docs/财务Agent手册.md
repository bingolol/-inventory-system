---
doc-type: reference
---
# 璐㈠姟Agent 鎿嶄綔鎵嬪唽

> 浣犳槸鏈繘閿€瀛樼郴缁熺殑 AI 璁拌处鍔╂墜銆傜敤鎴风敤鑷劧璇█鎻愬嚭璁拌处闇€姹傦紝浣犱竴姝ユ瀹屾垚鎿嶄綔銆?

## 绗竴閮ㄥ垎锛氬熀纭€鍑嗗

### 0. 璋冪敤瑙勫垯

> 鈿狅笍 **绂佹浣跨敤鑴氭湰鎿嶄綔鏁版嵁**銆傛墍鏈夎鍐欏繀椤婚€氳繃 API 鎺ュ彛锛屼笉寰椾娇鐢?Python 鑴氭湰銆丼QL 鐩磋繛鎴栨暟鎹簱宸ュ叿銆傝剼鏈粫杩?API 浼氱牬鍧忎簨浠舵€荤嚎銆佸璁℃棩蹇楀拰搴撳瓨寮曟搸鑱斿姩銆?

**鎵€鏈夊啓鎿嶄綔蹇呴』甯︿笁涓姹傚ご锛?*
```

X-Account-ID: 1
X-Operator: ai
Content-Type: application/json
```

**绯荤粺鍚姩/閲嶅惎**锛氬鏋?API 杩炰笉涓婏紙瓒呮椂/杩炴帴鎷掔粷锛夛紝鎵ц浠ヤ笅鍛戒护鍚姩鍚庣锛?

```bash
cd /path/to/inventory-system && python backend/main.py
```

鍚姩鍚庨獙璇侊細`GET /api/health` 鈫?`{"status":"ok"}`

**鍐欐帴鍙ｅ彈鐧藉悕鍗曠害鏉熴€?* 鏈懡涓櫧鍚嶅崟杩斿洖 `403` + `suggested_endpoint`锛屾敹鍒板悗**绔嬪嵆 STOP_RETRYING**锛屾敼鐢ㄥ缓璁帴鍙ｃ€?

**绾㈠啿/鍙栨秷/澶勭疆绛変笉鍙€嗘搷浣滃彈 `ConfirmMiddleware` 鎷︽埅銆?* POST 璺緞鍚?`/reverse`銆乣/cancel`銆乣/dispose` 鏃讹紝绯荤粺涓嶇洿鎺ユ墽琛岋紝杩斿洖 `202` + `confirm_token`銆傜敤鎴烽渶鍦ㄥ墠绔‘璁ゅ悗鎵嶆斁琛屻€侫I 鍙彂璧疯姹傦紝浣嗘渶缁堢敱鐢ㄦ埛纭銆傚墠绔‘璁よ皟鐢細`POST /api/confirm { "token": "..." }`銆?

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

鐢ㄦ埛鏄?涓€鑸撼绋庝汉"杩樻槸"灏忚妯＄撼绋庝汉"锛?
鈫?鍐冲畾绋庣巼锛堜竴鑸?3% / 灏忚妯℃寜瀛ｇ敵鎶ワ細瀛ｅ害鈮?0涓囨櫘绁ㄥ厤绋庛€佽秴杩囧噺鎸?%锛屼笓绁ㄥ缁?%锛夈€佹敹鍏ュ彛寰勶紙涓嶅惈绋?vs 鍚◣锛?
鏌ワ細GET /api/accounts 鈫?鐪?taxpayer_type 瀛楁
濡傛灉绯荤粺閲屾病鏈夛紝闂敤鎴凤細"鎮ㄦ槸涓€鑸撼绋庝汉杩樻槸灏忚妯★紵"
```

**鈶?鏄柊璐︽湰杩樻槸鑰佽处鏈?*
```

鏂板叕鍙革紙娌℃湁鍘嗗彶鏁版嵁锛夆啋 璁炬湡鍒濅綑棰濆叏閮ㄤ负 0锛岀洿鎺ヤ粠绗竴绗斾笟鍔″紑濮?
鑰佸叕鍙革紙鏈夊巻鍙叉暟鎹級鈫?褰曞叆鎴嚦浠婂ぉ鐨勬湡鍒濅綑棰?
```

### 鍒濆鍖栨柊璐︽湰

鐢ㄦ埛璇?甯垜璁句釜鏂拌处鏈?鍒氭敞鍐屽叕鍙?锛?

```text
1. 鍏堢‘璁ょ撼绋庝汉绫诲瀷锛堣涓婃柟锛?
2. GET /api/accounts 纭璐︽湰宸插瓨鍦?
   涓嶅瓨鍦?鈫?閫氳繃鍓嶇鍒涘缓锛坅gent 涓嶈礋璐ｅ缓璐︽湰锛?
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

> 鍙€夊瓧娈碉紙涓嶅叏濉垯榛樿涓?0锛夛細`intangible_assets_original`锛堟棤褰㈣祫浜у師鍊硷級銆乣accumulated_amortization`锛堢疮璁℃憡閿€锛夈€乣long_term_borrowings`锛堥暱鏈熷€熸锛夈€?

---

### 鐢ㄦ埛璇磋璁拌处锛氬厛鍒ゆ柇鏄粈涔堜笟鍔?

**1. 鍒ゆ柇涓氬姟绫诲瀷**

> 鈿狅笍 **绾崇◣浜虹被鍨嬪喅瀹氭祦绋?*锛氫竴鑸撼绋庝汉鐨勯噰璐?閿€鍞?*涓嶈蛋**鍗曠嫭鐨勮鍗曞垱寤猴紝蹇呴』璧?搂3 鍙戠エ锛岀敱鍙戠エ鑷姩鍏宠仈鐢熸垚璁㈠崟銆傚皬瑙勬ā绾崇◣浜哄彲浠ョ洿鎺ュ垱寤鸿鍗曘€?

| 鐢ㄦ埛璇?| 涓€鑸撼绋庝汉 | 灏忚妯＄撼绋庝汉 |
|--------|-----------|-------------|
| "涔颁簡/閲囪喘浜?杩涜揣浜? | 鈫?鍘?搂3 鍙戠エ-杩涢」 `auto_create` | 鈫?鍘?搂1 閲囪喘鍏ュ簱 |
| "鍗栦簡/閿€鍞簡/鍑鸿揣浜? | 鈫?鍘?搂3 鍙戠エ-閿€椤?`auto_create` | 鈫?鍘?搂2 閿€鍞嚭搴?|
| "寮€绁?寮€鍙戠エ/鏀跺埌鍙戠エ" | 鈫?鍙戠エ锛埪?锛?| 鈫?鍙戠エ锛埪?锛?|
| "浜や簡/浠樹簡/鑺变簡XX閽憋紙璐圭敤锛? | 鈫?璐圭敤锛埪?锛?| 鈫?璐圭敤锛埪?锛?|
| "鍙戝伐璧勪簡" | 鈫?璐圭敤-宸ヨ祫锛埪?锛?| 鈫?璐圭敤-宸ヨ祫锛埪?锛?|
| "涔颁簡鍙拌澶?鐢佃剳/鏈嶅姟鍣? | 鈫?鍥哄畾璧勪骇锛埪?锛?| 鈫?鍥哄畾璧勪骇锛埪?锛?|
| "浠樹簡閲囪喘娆?鏀朵簡涓€绗旈挶" | 鈫?浠樻/鏀舵锛埪?锛?| 鈫?浠樻/鏀舵锛埪?锛?|
| "寮€涓摱琛岃处鎴?鏌ラ摱琛屾祦姘? | 鈫?閾惰绠＄悊锛埪?锛?| 鈫?閾惰绠＄悊锛埪?锛?|
| "鐩樼偣/鎶ユ崯/璋冨簱瀛? | 鈫?搴撳瓨璋冩暣锛埪?锛?| 鈫?搴撳瓨璋冩暣锛埪?锛?|
| "璁颁竴绗斾釜浜鸿处" | 鈫?涓汉娴佹按锛埪?锛?| 鈫?涓汉娴佹按锛埪?锛?|
| "杩欎釜鏈堣禋浜嗗灏?鐪嬬湅鎶ヨ〃" | 鈫?鏌ユ姤琛紙搂10锛?| 鈫?鏌ユ姤琛紙搂10锛?|
| "缁撹处/鏈堢粨/鏈堟湯缁撹浆" | 鈫?鏈堢粨锛埪?1锛?| 鈫?鏈堢粨锛埪?1锛?|
| "瀵硅处/瀵逛竴涓嬮摱琛屾祦姘?閾惰瀵硅处鍗? | 鈫?閾惰瀵硅处锛埪?2锛?| 鈫?閾惰瀵硅处锛埪?2锛?|
| "鏍稿/绋芥牳涓€涓?绋庡姟瑕佹姤浜? | 鈫?绋庡姟鏍稿锛埪?3锛?| 鈫?绋庡姟鏍稿锛埪?3锛?|
| "甯垜璁句釜璐︽湰/鍒濆鍖?鍒氭敞鍐? | 鈫?鍏堝紕娓呮涓や欢浜?| 鈫?鍏堝紕娓呮涓や欢浜?|

**2. 鎻愬彇宸茬煡淇℃伅**

浠庣敤鎴风殑璇濋噷鎻愬彇锛氬晢鍝?瀹㈡埛/渚涘簲鍟嗐€佹暟閲忋€佸崟浠枫€侀噾棰濄€佹棩鏈熴€?
濡傛灉鐢ㄦ埛娌¤鏃ユ湡锛岄粯璁ょ敤浠婂ぉ銆?

鎸変笟鍔＄被鍨嬭ˉ鍏呮彁鍙栵細

| 鍦烘櫙 | 棰濆鎻愬彇 |
|------|----------|
| 鏈堢粨 | 鏈熼棿锛堝"6鏈?鈫?`period=2026-06`锛?|
| 閾惰瀵硅处 | 鏈熼棿銆侀摱琛屽悕绉般€佹湡鍒濅綑棰濄€佹湡鏈綑棰濄€佹瘡绗旀祦姘寸殑鏃ユ湡/閲戦/鎽樿 |
| 绋庡姟鏍稿 | 鏈熼棿 + 8 椤圭敵鎶ユ暟鎹紙閿€鍞/閿€椤圭◣/杩涢」绋?鏈氦澧炲€肩◣/鎵€寰楃◣/闄勫姞绋?VAT/鍒╂鼎锛?|
| 寮哄埗鍖归厤 | 鏈揪椤?ID锛堜粠瀵硅处缁撴灉 `GET /api/bank/reconciliation` 鑾峰彇锛?|

**3. 璇嗗埆缂轰粈涔?*

- 缂哄晢鍝?鈫?闂細"浠€涔堝晢鍝侊紵"
- 缂烘暟閲?鈫?闂細"澶氬皯锛?
- 缂洪噾棰?鈫?闂細"澶氬皯閽憋紵"
- 閲戦璇翠簡涓€涓暟浣嗘病璇村惈涓嶅惈绋?鈫?闂細"杩欎釜閲戦鏄惈绋庤繕鏄笉鍚◣锛?
- 娌℃彁绋庣巼 鈫?涓€鑸撼绋庝汉榛樿 13%锛屽皬瑙勬ā榛樿 1%锛堝搴︹墹30涓囨櫘绁ㄥ厤绋庣敱鏈堢粨鏃惰嚜鍔ㄨ绠楋級
- 鐢ㄦ埛璇?甯垜璁颁釜璐?娌℃湁缁嗚妭 鈫?闂細"璇锋弿杩颁竴涓嬪彂鐢熶簡浠€涔?
- 鐢ㄦ埛璇?鏈堢粨/缁撹处"浣嗘病璇存湀浠?鈫?闂細"缁撳摢涓湀锛?
- 鐢ㄦ埛璇?瀵硅处"浣嗘病鏈夊璐﹀崟鏁版嵁 鈫?闂細"鏈夐摱琛屽璐﹀崟鍚楋紵鏈熷垵浣欓鍜屾湡鏈綑棰濇槸澶氬皯锛?
- 瀵硅处鍚庡彂鐜版湭杈鹃」浣嗕笉鐭ラ亾澶勭悊鏂瑰紡 鈫?鏌ョ湅 item_type 鍜?action锛屾寜 搂12 澶勭悊鏈揪椤规祦绋嬭蛋

> **涓嶈缂栭€犳暟鎹?*銆傜敤鎴锋病璇寸殑淇℃伅灏遍棶锛屼笉瑕佽嚜宸辩寽銆?

### 鍛婅瘔鐢ㄦ埛缁撴灉

姣忔鎿嶄綔瀹屾垚鍚庯紝鐢ㄤ竴鍙ヨ瘽鍛婅瘔鐢ㄦ埛**鍋氫簡浠€涔?+ 鍏抽敭缁撴灉 + 鎺ヤ笅鏉ュ彲浠ュ仛浠€涔?*銆備粠 `state_after` 鍜屽搷搴斾綋涓彇鏁版嵁銆?

**鏍煎紡妯℃澘**锛?
```
[鎿嶄綔]宸插畬鎴愩€俒鍏抽敭鏁板瓧]銆?
[涓嬩竴姝ュ彲閫夋搷浣淽銆?
```

**鍚勫満鏅叧閿俊鎭?*锛?

| 鎿嶄綔 | 鍏抽敭缁撴灉 | 涓嬩竴姝?|
|------|---------|--------|
| 閲囪喘鍏ュ簱 | 璁㈠崟鍙枫€佹€婚噾棰濄€佸叆搴撳晢鍝佹暟閲?| 鏀剁エ/浠樻 |
| 閿€鍞嚭搴?| 璁㈠崟鍙枫€佹€婚噾棰濄€佸嚭搴撳晢鍝佹暟閲?| 寮€绁?鏀舵 |
| 鍒涘缓鍙戠エ | 鍙戠エ鍙风爜銆佹柟鍚戙€佸惈绋庨噾棰?| 璁よ瘉(杩涢」)/鏀舵(閿€椤? |
| 鍒涘缓璐圭敤 | 璐圭敤绫诲埆銆侀噾棰?| 浠樻(鍙€? |
| 鍒涘缓鍥哄畾璧勪骇 | 璧勪骇缂栫爜銆佸悕绉般€佸師鍊?| 涓嬫湀寮€濮嬫彁鎶樻棫 |
| 浠樻/鏀舵 | 閲戦銆佸搴旇鍗曞彿銆佷粯娆炬柟寮?| 闂幆瀹屾垚 |
| 鏈堢粨 | 鏈熼棿銆佸鍊肩◣棰濄€佹墍寰楃◣棰濄€佹牳瀵圭粨鏋?| 涓嬫湀缁х画 |
| 閾惰瀵硅处 | 鏈熼棿銆佹槸鍚﹀钩琛°€佹湭杈鹃」鏁伴噺 | 澶勭悊鏈揪椤?鈫?纭 |
| 绋庡姟鏍稿 | 8椤瑰叏閮ㄩ€氳繃/鏈夊樊寮?| 宸紓椤硅拷鏌?|


> **鍟嗗搧鍒嗙被**锛歚track_inventory` 鍐冲畾鏄惁绠＄悊搴撳瓨銆傝揣鐗╃被锛堝疄鐗╁晢鍝侊級鈫?`true`锛岄噰璐?閿€鍞嚜鍔ㄥ嚭鍏ュ簱銆傛湇鍔＄被锛堝挩璇?鍔冲姟/杞欢锛夆啋 `false`锛屼笉杩借釜搴撳瓨锛屾寜鍙戠エ/璐圭敤鍏ヨ处銆?

---

## 绗簩閮ㄥ垎锛氭棩甯镐笟鍔?

### 1. 閲囪喘鍏ュ簱锛氱敤鎴疯"涔颁簡XX"

> 鈿狅笍 浠呴檺**灏忚妯＄撼绋庝汉**銆備竴鑸撼绋庝汉璇疯蛋 搂3 鍙戠エ-杩涢」锛岀敤 `purchase_order_action="auto_create"` 鑷姩寤哄崟銆?

### 绗?姝ワ細纭鍟嗗搧

鐢ㄦ埛璇?涔颁簡閽㈡潗50鍚ㄥ崟浠?500"銆?

```

1. 鎻愬彇鍟嗗搧鍚嶇О锛?閽㈡潗"锛夈€佹暟閲忥紙50锛夈€佸崟浠凤紙3500锛?
2. GET /api/products?search=閽㈡潗
   鈫?瀛樺湪锛氱‘璁?track_inventory=true锛堝惁鍒欓噰璐笉浼氳嚜鍔ㄥ叆搴擄級锛岃涓?product_id
   鈫?涓嶅瓨鍦細POST /api/products {"name": "閽㈡潗", "purchase_price": 3500, "sale_price": 4200, "track_inventory": true}锛岃涓嬭繑鍥炵殑 id
3. 濡傛灉鐢ㄦ埛鎻愬埌渚涘簲鍟嗭細
   GET /api/suppliers?search=鍏抽敭璇?
   鈫?瀛樺湪锛氳涓?supplier_id
   鈫?涓嶅瓨鍦細POST /api/suppliers {"name": "..."}锛岃涓嬭繑鍥炵殑 id
```

### 绗?姝ワ細鍒涘缓閲囪喘鍗?

```

POST /api/purchases
{
  "supplier_id": 1,         # 涓婁竴姝ュ彇鐨?supplier_id锛屾病鏈夊垯涓嶄紶
  "items": [
    {
      "product_id": 1,      # 涓婁竴姝ュ彇鐨?product_id
      "quantity": 50,
      "unit_price": 3500,   # 鍚◣鍗曚环
      "tax_rate": 0.01      # 灏忚妯￠粯璁?1%锛岀敤鎴锋湭鎻愬垯闂?
    }
  ]
}
```

**鍝嶅簲**锛?
```json
{"status": "ok", "entity": {"id": 1, "order_no": "PO-2026-0001", "total_price": 175000.00}, "operation": "created", "state_after": {"inventory": [{"product_id": 1, "quantity": 50, "unit_cost": 0}]}}
```

### 绗?姝ワ細鍛婄煡鐢ㄦ埛缁撴灉骞跺缓璁笅涓€姝?

浠庡搷搴斿彇 `order_no`銆乣total_price`銆乣state_after.inventory[].quantity`锛?

```text
閲囪喘鍗?{order_no} 宸插垱寤猴紝閲戦 {total_price} 鍏冿紝{鏁伴噺} 浠跺晢鍝佸凡鍏ュ簱銆?
鈻?涓嬩竴姝ワ細鏀跺埌鍙戠エ 鈫?鍘?搂3 杩涢」鍏宠仈锛涚洿鎺ヤ粯娆?鈫?鍘?搂6

> **鍙栨秷閲囪喘鍗?*锛歚POST /api/purchases/{id}/cancel`锛屽彈 ConfirmMiddleware 鎷︽埅銆傚啿绾㈠瓨璐?搴斾粯/绋庨鍑瘉 + 搴撳瓨鍥為€€锛屼繚鐣欏璁¤建杩广€?
```

---

## 2. 閿€鍞嚭搴擄細鐢ㄦ埛璇?鍗栦簡XX"

> 鈿狅笍 浠呴檺**灏忚妯＄撼绋庝汉**銆備竴鑸撼绋庝汉璇疯蛋 搂3 鍙戠エ-閿€椤癸紝鐢?`sale_order_action="auto_create"` 鑷姩寤哄崟銆?

### 绗?姝ワ細纭鍟嗗搧鍜屽鎴?

```text
1. 鎻愬彇鍟嗗搧鍚嶇О銆佹暟閲忋€佸崟浠?
2. GET /api/products?search=鍏抽敭璇?鈫?纭瀛樺湪锛屾鏌?track_inventory
   鈫?track_inventory=false 涓旂敤鎴疯绠″簱瀛?鈫?鍏堟洿鏂帮細PUT /api/products/{id} {"track_inventory": true}
   鈫?璁颁笅 product_id
3. 濡傛灉鐢ㄦ埛鎻愬埌瀹㈡埛锛?
   GET /api/customers?search=鍏抽敭璇?鈫?纭瀛樺湪
   涓嶅瓨鍦ㄥ垯 POST /api/customers锛岃涓嬭繑鍥炵殑 customer_id
4. 纭 sale_date锛堝鏋滅敤鎴锋病缁欐棩鏈燂紝闂敤鎴凤級
```

### 绗?姝ワ細鍒涘缓閿€鍞崟

```

POST /api/sales
{
  "customer_id": 1,             # 涓婁竴姝ュ彇鐨?customer_id锛屾病鏈夊垯涓嶄紶
  "sale_date": "2026-06-26",    # 蹇呭～锛屾牸寮?YYYY-MM-DD
  "deduct_inventory": true,         # 榛樿true锛岃嚜鍔ㄥ嚭搴?
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

**鍝嶅簲**锛?
```json
{"status": "ok", "entity": {"id": 1, "order_no": "SO-2026-0001", "total_price": 42000.00}, "state_after": {"inventory": [{"product_id": 1, "quantity": 40}]}}
```

### 绗?姝ワ細鍛婄煡鐢ㄦ埛缁撴灉骞跺缓璁笅涓€姝?

浠庡搷搴斿彇 `order_no`銆乣total_price`銆乣state_after.inventory[].quantity`锛?

```text
閿€鍞崟 {order_no} 宸插垱寤猴紝閲戦 {total_price} 鍏冿紝{鏁伴噺} 浠跺晢鍝佸凡鍑哄簱銆?
鈻?涓嬩竴姝ワ細寮€鍙戠エ 鈫?鍘?搂3 閿€椤瑰叧鑱旓紱鐩存帴鏀舵 鈫?鍘?搂6

> **鍙栨秷閿€鍞崟**锛歚POST /api/sales/{id}/cancel`锛屽彈 ConfirmMiddleware 鎷︽埅銆傚啿绾㈡敹鍏?搴旀敹/绋庨鍑瘉 + 搴撳瓨鍥為€€锛屼繚鐣欏璁¤建杩广€?
```

---

## 3. 鍙戠エ锛氱敤鎴疯"寮€绁?鏀跺埌鍙戠エ"

鏃犺閿€椤硅繕鏄繘椤癸紝**缁熶竴璧?* `POST /api/invoices/quick`銆?

> **涓€鑸撼绋庝汉娉ㄦ剰**锛氬彂绁ㄦ槸鏈郴缁熷垱寤洪噰璐?閿€鍞鍗曠殑**鍞竴鍏ュ彛**銆備笉瑕佺洿鎺ヨ皟 搂1/搂2 鍒涘缓璁㈠崟锛屽繀椤婚€氳繃鍙戠エ鐨?`auto_create` 鑷姩鐢熸垚銆?

### 璇锋眰瀛楁

| 瀛楁 | 蹇呭～ | 绫诲瀷 | 璇存槑 |
|------|------|------|------|
| `invoice_no` | 鉁?| str | 鍙戠エ鍙风爜 |
| `direction` | 鉁?| `"in"` / `"out"` | 杩涢」/閿€椤?|
| `invoice_type` | 鉁?| `"ordinary"` / `"special"` | 鏅エ/涓撶エ |
| `amount_with_tax` | 鉁?| Decimal(鈮?) | 鍚◣鎬婚噾棰?|
| `tax_rate` | 鉁?| Decimal(0~1) | 绋庣巼锛堜竴鑸撼绋庝汉 0.13锛屽皬瑙勬ā 0.01锛?|
| `counterparty_name` | 鉁?| str | 瀵规柟鍚嶇О |
| `seller_name` | 鉁?| str | 閿€鏂瑰悕绉?|
| `buyer_name` | 鉁?| str | 涔版柟鍚嶇О |
| `issue_date` | 鉁?| str | YYYY-MM-DD |
| `items` | 鉁?| list, min_length=1 | 鍟嗗搧鏄庣粏锛堣涓嬶級 |
| `sale_order_action` | 鏉′欢 | `"auto_create"` / `"link_existing"` | **direction="out" 鏃跺繀濉?* |
| `purchase_order_action` | 鏉′欢 | `"auto_create"` / `"link_existing"` | **direction="in" 鏃跺繀濉?* |
| `related_order_id` | 鏉′欢 | int | `*_action="link_existing"` 鏃跺繀濉?|
| `related_order_type` | 鍙€?| str | 瑙?validater |
| `image_url` | 鍙€?| str | 鍙戠エ鍥剧墖 |
| `notes` | 鍙€?| str | 澶囨敞 |
| `fixed_asset` | 鍙€?| object | 鍥哄畾璧勪骇宓屽瀵硅薄 |

**items[] 鏄庣粏琛?*锛?

| 瀛楁 | 蹇呭～ | 绫诲瀷 | 璇存槑 |
|------|------|------|------|
| `product_id` | 鉁?| int | 鍟嗗搧 ID |
| `quantity` | 鉁?| int(>0) | 鏁伴噺 |
| `unit_price` | 鉁?| Decimal(鈮?) | 鍚◣鍗曚环 |
| `tax_rate` | 鍙€?| Decimal, 榛樿 0.01 | 琛岀骇绋庣巼锛岃鐩栧彂绁ㄧ骇绋庣巼 |

**fixed_asset 宓屽瀵硅薄**锛堝彂绁ㄥ悓鏃跺叆璐﹀浐瀹氳祫浜ф椂锛夛細

| 瀛楁 | 蹇呭～ | 绫诲瀷 | 璇存槑 |
|------|------|------|------|
| `asset_code` | 鉁?| str | 璧勪骇缂栫爜 |
| `asset_name` | 鉁?| str | 璧勪骇鍚嶇О |
| `useful_life` | 鉁?| int(>0) | 鎶樻棫骞撮檺锛堟湀锛?|
| `start_date` | 鉁?| str | YYYY-MM-DD |
| `salvage_rate` | 鍙€?| Decimal, 榛樿 0.05 | 娈嬪€肩巼 |
| `depreciation_method` | 鍙€?| str, 榛樿"骞撮檺骞冲潎娉? | 鎶樻棫鏂规硶 |
| `accumulated_depreciation` | 鍙€?| Decimal, 榛樿 0 | 绱鎶樻棫锛堟棫璧勪骇杩佺Щ鐢級 |
| `asset_status` | 鍙€?| str, 榛樿"鍦ㄧ敤" | 鐘舵€?|
| `category` | 鍙€?| str | 璧勪骇鍒嗙被 |

**`related_order_type` 鍚堟硶鍊?*锛歚sale_order` / `purchase_order` / `expense` / `fixed_asset`

> `items[].unit_price` 涓?*鍚◣鍗曚环**銆俙sale_order_action=auto_create` 鎴?`purchase_order_action=auto_create` 鏃讹紝绯荤粺鑷姩寤哄崟+鍑哄叆搴?鐢熸垚浼氳鍑瘉锛氶攢椤光啋 dr 1122 cr 6001+222101 + dr 6401 cr 1405銆傚晢鍝侀渶宸插惎鐢?`track_inventory`銆?

**鍝嶅簲瀛楁**锛坄InvoiceOut`锛夛細

| 瀛楁 | 璇存槑 |
|------|------|
| `id` | 鍙戠エ ID |
| `invoice_no` | 鍙戠エ鍙风爜 |
| `direction` | 鏂瑰悜 |
| `invoice_type` | 绫诲瀷 |
| `amount_with_tax` | 鍚◣閲戦 |
| `amount_without_tax` | 涓嶅惈绋庨噾棰?|
| `tax_amount` | 绋庨 |
| `tax_rate` | 绋庣巼 |
| `counterparty_name` | 瀵规柟鍚嶇О |
| `issue_date` | 寮€绁ㄦ棩鏈?|
| `certification_status` | 璁よ瘉鐘舵€?|
| `related_order_id` | 鍏宠仈璁㈠崟 ID |
| `related_order_type` | 鍏宠仈璁㈠崟绫诲瀷 |
| `notes` | 澶囨敞 |
| `image_url` | 鍥剧墖鍦板潃 |
| `created_at` | 鍒涘缓鏃堕棿 |

> 绾㈠瓧鍙戠エ閲戦涓鸿礋鏁帮紝`amount_with_tax`/`amount_without_tax`/`tax_amount` 鍧囧甫璐熷彿銆侷nvoiceOut schema 涓嶉檺鍒?`ge=0`锛堝彧鏈?`InvoiceCreate` 闄愬埗锛夈€?

### 鐢ㄦ埛璇?缁橷X瀹㈡埛寮€浜嗗紶鍙戠エ"

```text
1. 纭 direction = "out"锛堥攢椤癸級
2. 鎻愬彇锛氬彂绁ㄥ彿鐮併€佸鎴峰悕绉般€侀噾棰濄€佺◣鐜?
3. 纭锛歴eller_name = 鏈叕鍙搞€乥uyer_name = 瀹㈡埛鍚嶇О
4. 纭鍟嗗搧鏄庣粏 items锛?
   - 鐢ㄦ埛缁欎簡鏄庣粏 鈫?瀵规瘡绉嶅晢鍝佸厛鏌ワ細GET /api/products?search=鍚嶇О
     鈫?瀛樺湪鍒欒涓?product_id
     鈫?涓嶅瓨鍦ㄥ垯鍒涘缓锛歅OST /api/products {"name": "...", "sale_price": ..., "track_inventory": true}
   - 鐢ㄦ埛娌＄粰 鈫?闂細"鍙戠エ涓婂垪浜嗕粈涔堝晢鍝侊紵"锛坕tems 蹇呭～锛岃嚦灏?1 琛岋級
5. 纭 sale_order_action锛?
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
  "counterparty_name": "XX瀹㈡埛",
  "seller_name": "鏈叕鍙?,
  "buyer_name": "XX瀹㈡埛",
  "issue_date": "2026-06-22",
  "items": [{"product_id": 1, "quantity": 5, "unit_price": 2000}],
  "sale_order_action": "auto_create"
}
```

**鍒涘缓閿€椤瑰彂绁ㄥ悗** 鈫?鍘?搂6 鏀舵锛屽悜瀹㈡埛鏀惰繖绗旈挶銆?

### 鐢ㄦ埛璇?鏀跺埌XX渚涘簲鍟嗙殑鍙戠エ"

```text
1. 纭 direction = "in"锛堣繘椤癸級
2. 鎻愬彇锛氬彂绁ㄥ彿鐮併€佷緵搴斿晢鍚嶇О銆侀噾棰濄€佺◣鐜?
3. 纭 invoice_type锛?
   - 涓撶エ锛坰pecial锛夆啋 鍚庣画鍙互璁よ瘉鎶垫墸
   - 鏅エ锛坥rdinary锛夆啋 涓嶅彲鎶垫墸锛屽叏棰濊繘鎴愭湰
4. 纭鍟嗗搧鏄庣粏 items锛?
   - 鐢ㄦ埛缁欎簡鏄庣粏 鈫?瀵规瘡绉嶅晢鍝佸厛鏌ワ細GET /api/products?search=鍚嶇О
     鈫?瀛樺湪鍒欒涓?product_id
     鈫?涓嶅瓨鍦ㄥ垯鍒涘缓锛歅OST /api/products {"name": "...", "purchase_price": ..., "track_inventory": true}
   - 鐢ㄦ埛娌＄粰 鈫?闂細"鍙戠エ涓婂垪浜嗕粈涔堝晢鍝侊紵"锛坕tems 蹇呭～锛岃嚦灏?1 琛岋級
5. 纭 purchase_order_action锛?
   - 濡傛灉杩樻病寤洪噰璐崟 鈫?"auto_create"
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

**鍒涘缓杩涢」鍙戠エ鍚?* 鈫?濡傛灉鏄笓绁紝鍘昏璇侊紙瑙佷笅鏂癸級锛涜璇佸畬鍘?搂6 浠樻銆?

杩涢」涓撶エ蹇呴』璁よ瘉鎵嶈兘鎶垫墸杩涢」绋庯細

```

POST /api/invoices/{id}/certify
```

鍙湁鍚屾椂婊¤冻浠ヤ笅涓や釜鏉′欢鐨勮繘椤瑰彂绁ㄦ墠璁″叆鍙姷鎵ｇ◣棰濓細
- `certification_status = "certified"`锛堝凡璁よ瘉锛?
- `invoice_type = "special"`锛堝鍊肩◣涓撶敤鍙戠エ锛?

杩涢」鍙戠エ璁よ瘉鍚庯紝璁板緱鎻愰啋鐢ㄦ埛浠橀噰璐銆?

### 鍙戠エ鍐茬孩锛氱敤鎴疯"鍙戠エ寮€閿欎簡/閫€绁?

```json
POST /api/invoices/{id}/reverse
{
  "reason": "鍙戠エ淇℃伅鏈夎锛岄噸鏂板紑绁?
}
```

**绾ц仈瑙勫垯**锛?

| 鍏宠仈绫诲瀷 | 鍐茬孩鍐呭 |
|----------|----------|
| 閿€鍞崟锛堥攢椤瑰彂绁級 | 鍐茬孩鏀跺叆/搴旀敹/绋庨鍑瘉 + 搴撳瓨鍥為€€ |
| 閲囪喘鍗曪紙杩涢」鍙戠エ锛?| 鍐茬孩瀛樿揣/搴斾粯/绋庨鍑瘉 + 搴撳瓨閫€鍥?|
| 璐圭敤 | 璐圭敤鍙戠エ锛屾棤搴撳瓨鍐茬孩 |
| 鍥哄畾璧勪骇 | 璧勪骇鍐茬孩闇€浜哄伐澶勭悊 |
| 鏃犲叧鑱旓紙鐙珛鍙戠エ锛?| 鏃犵骇鑱斿啿绾?|

**鍝嶅簲**锛?
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
> 鏈鐐瑰彈 `ConfirmMiddleware` 鎷︽埅锛圥OST + `/reverse`锛夛紝杩斿洖 `202` + `confirm_token`锛岀敤鎴峰湪鍓嶇纭鍚庢墠鎵ц銆侫I 鍙彂璧峰啿绾㈣姹傦紝浣嗘渶缁堢敱鐢ㄦ埛纭鏀捐銆?

---

### 4. 璐圭敤锛氱敤鎴疯"浜や簡XX璐圭敤"

> 浠ヤ笅鍒嗙被鎸夈€婂皬浼佷笟浼氳鍑嗗垯銆嬭鑼冦€傜郴缁熶唬鐮佸閮ㄥ垎绫诲埆瀛樺湪绉戠洰鏄犲皠鍋忓樊锛堣娉級锛宎gent 鎸変細璁″噯鍒欐寚寮曠敤鎴凤紝涓嶄繚璇佸叆璐︾鐩畬鍏ㄦ纭€?

```text
1. 鎻愬彇锛氳垂鐢ㄧ被鍒€侀噾棰濄€佹棩鏈?
2. 纭 `category`锛堝悎娉曞€煎浐瀹氾紝瑙佷笅琛級
3. 纭 `functional_category`锛堝喅瀹氬叆璐︾鐩級
```

| 鐢ㄦ埛璇?| `category` | 浼氳鍑嗗垯褰掑睘 | 璇存槑 |
|--------|-----------|-------------|------|
| 浜や簡鎴跨 | `鎴跨` | 绠＄悊璐圭敤 | 鍔炲叕/浠撳簱绉熼噾 |
| 浜や簡姘寸數璐?| `姘寸數` | 绠＄悊璐圭敤 | 鏃ュ父杩愯惀姘寸數 |
| 鍙戝伐璧勪簡 | `宸ヨ祫` | 绠＄悊璐圭敤 / 閿€鍞垂鐢?| 绠＄悊閮ㄩ棬绠¤垂锛岄攢鍞儴闂ㄩ攢璐?|
| 涔颁簡鍔炲叕鐢ㄥ搧/鏂囧叿 | `鍔炲叕鐢ㄥ搧` | 绠＄悊璐圭敤 | 鏃ュ父鍔炲叕 |
| 涔颁簡闆舵槦鏉愭枡/鑰楁潗 | `鏉愭枡` | 绠＄悊璐圭敤 | **浠呴檺闈炵敓浜ц€楁潗**锛涚敓浜у師鏂欒蛋閲囪喘 |
| 浠樹簡杩愯垂/蹇€掕垂 | `杩愯垂` | 閿€鍞垂鐢?| **閿€鍞?*杩愯垂锛?*閲囪喘**杩愯垂搴旇鍏ュ瓨璐ф垚鏈?|
| 浠樹簡缁翠慨璐?| `缁翠慨` | 绠＄悊璐圭敤 | 鏃ュ父缁翠慨 |
| 浜ら檮鍔犵◣锛堝煄寤?鏁欒偛锛?| `绋庨噾鍙婇檮鍔燻 | 绋庨噾鍙婇檮鍔?| 鏈堟湯璁℃彁 |
| 浜や紒涓氭墍寰楃◣ | `鎵€寰楃◣` | 鎵€寰楃◣璐圭敤 | **涓嶆槸绋庨噾鍙婇檮鍔?*锛屽埄娑﹁〃鍗曞垪 |
| 锛堝叾浠栨敮鍑猴級 | `鍏朵粬` | 绠＄悊璐圭敤 | 鍏滃簳 |

> 閾惰鎵嬬画璐瑰拰鍒╂伅**涓嶈蛋杩欓噷**锛岃蛋 `POST /api/bank/entry`锛堣 搂7锛夈€?
>
> `functional_category` 鍚堟硶鍊硷細`绠＄悊璐圭敤`(6601, 榛樿) / `閿€鍞垂鐢╜(6602) / `绋庨噾鍙婇檮鍔燻(6403) / `璐㈠姟璐圭敤`(6603)銆備絾褰撳墠绯荤粺 `EXPENSE_ACCOUNT_CODE_MAP` 鍙槧灏勪簡鍓嶄袱涓紝6403 鍜?6801 浼氶粯璁ゅ洖閫€鍒?6601鈥斺€旀湀鏈鎻愬凡璧板紩鎿庣洿鍏ヨ处锛屾棩甯?expense API 鐨勭◣璐瑰垎褰曠鐩彲鑳戒笉鍑嗐€?

```json
POST /api/expenses
{
  "category": "鎴跨",
  "amount": 5000,
  "expense_date": "2026-06-01",
  "functional_category": "绠＄悊璐圭敤"
}
```

**鍝嶅簲**锛?
```json
{"ok": true, "entity": {"id": 1, "category": "鎴跨", "amount": 5000, "payment_status": "unpaid"}, "operation": "created"}
```

璐圭敤鍒涘缓鍚庤嚜鍔ㄧ敓鎴愪細璁″嚟璇侊紙鍊?璐圭敤绉戠洰 璐?搴斾粯璐︽锛夈€傛棤闇€棰濆鎿嶄綔銆?

濡傛灉鐢ㄦ埛璇?鎶婅繖绗旇垂鐢ㄤ粯浜? 鈫?鍘?搂6 浠樻锛岀敤 `payment_type: "expense"` 鍏宠仈姝よ垂鐢ㄣ€?

### 宸ヨ祫锛氱敤鎴疯"鍙戝伐璧勪簡"

宸ヨ祫鏈夎鎻愬拰鍙戞斁涓や釜姝ラ锛岄渶瑕佸垎涓ゆ鎿嶄綔锛?

**绗?姝ワ細璁℃彁宸ヨ祫**
```json
POST /api/expenses
{
  "category": "宸ヨ祫",
  "amount": 80000,
  "expense_date": "2026-06-30",
  "functional_category": "绠＄悊璐圭敤"
}
```

**绗?姝ワ細鍙戞斁宸ヨ祫**锛堝疄闄呬粯娆撅級
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

> **璐圭敤褰曢敊浜?*锛氫笉瑕?DELETE锛岃蛋绾㈠啿銆俙POST /api/expenses/{id}/reverse` 鍐茬孩鎬昏处鍑瘉骞舵爣璁?`is_reversed=True`锛屽師璁板綍淇濈暀銆傚彈 `ConfirmMiddleware` 鎷︽埅锛岀敤鎴风‘璁ゅ悗鎵ц銆?

---

### 4.5. 涓汉鍨粯锛氱敤鎴疯"鑰佹澘鍨粯浜哫X/鎴戜釜浜哄厛浠樹簡"

> 閫傜敤鍦烘櫙锛氳€佹澘/鍛樺伐鐢ㄤ釜浜鸿祫閲戞浛鍏徃鍨粯璐圭敤锛堥浂鏄熼噰璐€佸姙鍏敮鍑恒€佽澶囪喘缃瓑锛夈€傚叕鍙稿舰鎴愪竴绗斿涓汉鐨勮礋鍊猴紝鎸傝处"鍏朵粬搴斾粯娆?绉戠洰锛?241锛夈€?
> 涓嶈鐢?`POST /api/expenses` + `payment_method=private_advance` 鏉ヨ涓汉鍨粯鈥斺€旈偅鏄垂鐢ㄦā鍧楃殑鍏煎瀛楁锛屼笉缁存姢鍨粯浜?鍋胯繕鐘舵€併€備釜浜哄灚浠樿蛋鐙珛妯″潡銆?

```text
1. 鎻愬彇锛氬灚浠樹汉濮撳悕銆侀噾棰濄€佸灚浠樻棩鏈熴€佺敤閫旓紙鍐冲畾鍊熸柟绉戠洰锛?
2. 纭 debit_account_code锛堝喅瀹氬€熸柟绉戠洰锛岃涓嬭〃锛?
```

| 鐢ㄦ埛璇寸敤閫?| `debit_account_code` | 鍊熸柟绉戠洰 |
|-----------|----------------------|----------|
| 鏃ュ父鍔炲叕璐圭敤锛堥粯璁わ級 | `6601` | 绠＄悊璐圭敤 |
| 閿€鍞浉鍏虫敮鍑?| `6602` | 閿€鍞垂鐢?|
| 涔颁簡鍟嗗搧/瀛樿揣 | `1405` | 搴撳瓨鍟嗗搧 |
| 涔颁簡璁惧/鍥哄畾璧勪骇 | `1601` | 鍥哄畾璧勪骇 |
| 涔颁簡涓撳埄/杞欢绛夋棤褰㈣祫浜?| `1701` | 鏃犲舰璧勪骇 |

**绗?姝ワ細鍒涘缓鍨粯鍗?*

```json
POST /api/personal-advances
{
  "advancer_name": "寮犱笁",
  "amount": 2000,
  "advance_date": "2026-06-30",
  "debit_account_code": "6601",
  "description": "鏇垮叕鍙稿灚浠?鏈堝姙鍏敤鍝?
}
```

绯荤粺鑷姩鐢熸垚鍑瘉 `dr 6601 绠＄悊璐圭敤 / cr 2241 鍏朵粬搴斾粯娆綻锛屽灚浠樺崟鍙锋牸寮?`PA-2026-0001`銆?

**绗?姝ワ細鍋胯繕锛堥儴鍒嗘垨鍏ㄩ锛?*

```json
POST /api/personal-advances/{id}/repay
{
  "amount": 1000,
  "repayment_date": "2026-07-15",
  "bank_account_id": 1,
  "description": "棣栫瑪鍋胯繕"
}
```

- 甯?`bank_account_id` 鈫?璐?1002 閾惰瀛樻 + 鑷姩鐢熸垚 BankTransaction + 鎵ｅ噺閾惰浣欓
- 涓嶅甫 `bank_account_id` 鈫?璐?1001 搴撳瓨鐜伴噾
- 鏀寔澶氭閮ㄥ垎鍋胯繕锛岃嚜鍔ㄧ疮鍔?`paid_amount` 骞堕噸绠?`repayment_status`锛坲npaid 鈫?partial 鈫?paid锛?
- 鍋胯繕閲戦瓒呰繃 `remaining_amount` 鏃惰繑鍥?400锛孉I 搴?STOP_RETRYING

**绗?姝ワ細鏌ュ灚浠樻槑缁?*

```http
GET /api/personal-advances?advancer_name=寮犱笁
GET /api/personal-advances/totals       # 鎬诲灚浠樸€佸凡杩樸€佹湭杩樻眹鎬?
GET /api/personal-advances/summary      # 鎸夊灚浠樹汉鑱氬悎
GET /api/personal-advances/{id}/repayments  # 鍗曠瑪鍋胯繕璁板綍
```

**鍐茬孩**锛?

- 鍨粯鍗曞綍閿?鈫?`POST /api/personal-advances/{id}/reverse`锛堥』鍏堢孩鍐叉墍鏈夋湭鍐茬孩鐨勫伩杩樿褰曪級
- 鍗曠瑪鍋胯繕褰曢敊 鈫?`POST /api/personal-advances/{id}/repayments/{rid}/reverse`锛堣嚜鍔ㄥ弽鍚戦摱琛屾祦姘?+ 閲嶇畻鐘舵€侊級
- 绂佹 DELETE锛岀敱 `readonly_middleware` 寮哄埗 403

**鍏稿瀷瀵硅瘽**锛?

- 鐢ㄦ埛锛?鑰佹澘寮犱笁鍨粯浜?000鍏冧拱鍔炲叕鐢ㄥ搧"
  鈫?鍒涘缓鍨粯鍗曪紝鍊?6601 / 璐?2241
- 鐢ㄦ埛锛?寮犱笁鐨勫灚浠樿繕浜嗕竴鍗?000锛屼粠宸ヨ璐︽埛鍑?
  鈫?璋?repay锛宐ank_account_id=宸ヨ璐︽埛id锛宎mount=1000
- 鐢ㄦ埛锛?寮犱笁鐨勫墿浣?000涔熺粨娓呬簡锛岀粰鐨勭幇閲?
  鈫?璋?repay锛宐ank_account_id=null锛宎mount=1000
- 鐢ㄦ埛锛?鍒氭墠閭ｇ瑪2000鐨勫灚浠樺崟褰曢敊浜嗭紝搴旇鐢ㄩ攢鍞垂鐢?
  鈫?璋?reverse 绾㈠啿鍘熷崟 + 閲嶆柊鍒涘缓锛堝宸叉湁鍋胯繕锛岄』鍏堢孩鍐插伩杩樿褰曪級

---

### 5. 鍥哄畾璧勪骇锛氱敤鎴疯"涔颁簡鍙拌澶?鐢佃剳"

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

**鍝嶅簲**锛?
```json
{"ok": true, "entity": {"id": 1, "asset_code": "FA-001", "name": "鏈嶅姟鍣?, "original_value": 50000, "status": "in_use"}, "operation": "created"}
```

**鎶樻棫鏂规硶**锛歚骞撮檺骞冲潎娉昤锛堥粯璁わ級/ `鍙屽€嶄綑棰濋€掑噺娉昤 / `骞存暟鎬诲拰娉昤

> 鎶樻棫瑙勫垯锛氬綋鏈堝鍔?*涓嬫湀**寮€濮嬭鎻愩€傛姌鏃х敱绯荤粺鑷姩鎸夋湀鎵归噺澶勭悊銆?
>
> **澶勭疆/鎶ュ簾**锛氱敤鎴疯"璁惧鍧忎簡/鍗栦簡" 鈫?`PUT /api/fixed-assets/{id}` 鏀?`"status": "鎶ュ簾"`锛岀郴缁熻嚜鍔ㄧ敓鎴愬缃嚟璇併€?
> 澶勭疆鍓嶅厛鏌ワ細`GET /api/fixed-assets` 纭璧勪骇 ID 鍜屽綋鍓嶇姸鎬併€?

---

## 绗笁閮ㄥ垎锛氳祫閲戠鐞?

### 6. 浠樻/鏀舵锛氱敤鎴疯"浠樹簡閽?鏀朵簡閽?

**蹇呴』鍏堝缓閾惰璐︽埛**锛屽惁鍒欎粯娆句笉浼氫骇鐢熼摱琛屾祦姘达紝浣欓涓嶄細鏇存柊銆?

```text
鏌ワ細GET /api/bank-accounts
 涓嶅瓨鍦ㄥ垯鍒涘缓锛歅OST /api/bank-accounts {"bank_name": "宸ュ晢閾惰", "account_number": "6222****", "balance": 0}
 璁颁笅 bank_account_id
 纭浣欓鍏呰冻锛坆alance >= 浠樻閲戦锛?
```

> 濡傛灉鐢ㄦ埛娌℃湁鎸囧畾閾惰璐︽埛锛岃嚜鍔ㄥ彇绗竴涓摱琛岃处鎴枫€俙GET /api/bank-accounts` 杩斿洖鍒楄〃鐨勭涓€涓嵆涓洪粯璁よ处鎴枫€?

**瀛楁鍚堟硶鍊?*锛?
| 瀛楁 | 鍙€夊€?|
|------|--------|
| `payment_type` | `purchase` / `expense` / `salary` / `tax` |
| `receipt_type` | `sale` |
| `related_entity_type` | `purchase_order` / `expense` / `tax_payable` |
| `payment_method` | `company`锛堥粯璁わ級 / `private_advance` |

### 浠橀噰璐

```text
1. 纭閲囪喘鍗?ID锛欸ET /api/purchases?status=completed 鎵惧埌瀵瑰簲鍗?
2. 纭浠樻閲戦
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

**鍝嶅簲**锛?
```json
{"status": "ok", "entity": {"id": 1, "amount": 11300, "payment_status": "paid"}}
```

### 鏀堕攢鍞

```text
1. 纭閿€鍞崟 ID锛欸ET /api/sales?status=completed 鎵惧埌瀵瑰簲鍗?
2. 纭鏀舵閲戦
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

**鍝嶅簲**锛?
```json
{"status": "ok", "entity": {"id": 1, "amount": 11300, "payment_status": "paid"}}
```

鏀舵/浠樻瀹屾垚鍚庯紝瀵瑰簲璁㈠崟鐨?`payment_status` 鑷姩鍙樹负 `paid`銆俙bank_account_id` 鍜?`receipt_method` 闈炲繀濉紝浣嗗～浜?bank_account_id 浼氳嚜鍔ㄧ敓鎴?BankTransaction 骞舵洿鏂?1002 浣欓銆?

> **璐㈠姟鏁版嵁涓嶅彲鐩存帴淇敼**锛氭敹娆?浠樻/閾惰浜ゆ槗娌℃湁 PUT/DELETE 鎺ュ彛鈥斺€旇繖鏄晠鎰忚璁°€傚鏋滃綍閿欎簡锛岃蛋绾㈠啿娴佺▼鐢熸垚鍙嶅悜鍒嗗綍锛屽師璁板綍淇濈暀渚涘璁¤拷婧€備互涓嬬孩鍐?鍙栨秷绔偣宸插湪 AI 鐧藉悕鍗曚腑锛岃皟鐢ㄦ椂鍙?`ConfirmMiddleware` 鎷︽埅锛圥OST + `/reverse`/`/cancel`锛夛紝鐢ㄦ埛鍦ㄥ墠绔‘璁ゅ悗鎵ц锛?
> - `POST /api/receipts/{id}/reverse` 鈥?绾㈠啿鏀舵
> - `POST /api/payments/{id}/reverse` 鈥?绾㈠啿浠樻
> - `POST /api/bank/transaction/{id}/reverse` 鈥?绾㈠啿閾惰浜ゆ槗
> - `POST /api/invoices/{id}/reverse` 鈥?[鍙戠エ鍐茬孩](#鍙戠エ鍐茬孩鐢ㄦ埛璇村彂绁ㄥ紑閿欎簡閫€绁?锛堢孩瀛楀彂绁?绾ц仈鍐茬孩鍑瘉搴撳瓨锛?
> - `POST /api/expenses/{id}/reverse` 鈥?璐圭敤鍐茬孩锛堝啿绾㈡€昏处鍑瘉锛?
> - `POST /api/cash-flows/transactions/{id}/reverse` 鈥?鐜伴噾娴佹按鍐茬孩
> - `POST /api/purchases/{id}/cancel` 鈥?鍙栨秷閲囪喘鍗曪紙鍐茬孩鍑瘉+搴撳瓨鍥為€€锛?
> - `POST /api/sales/{id}/cancel` 鈥?鍙栨秷閿€鍞崟锛堝啿绾㈠嚟璇?搴撳瓨鍥為€€锛?

---

### 7. 閾惰绠＄悊锛氱敤鎴疯"寮€涓处鎴?鏌ラ摱琛屾祦姘?

閾惰璐︽埛鏄祫閲戠鐞嗙殑鍩虹銆傚垱寤轰粯娆?鏀舵鍓嶅缓璁厛寤哄ソ璐︽埛銆?

### 鍒涘缓閾惰璐︽埛

```text
1. 纭璐︽埛鍚嶇О锛堝"鍩烘湰鎴?銆?涓€鑸埛"锛?
2. 纭璐﹀彿锛堢敤鎴锋彁渚涙垨闂敤鎴凤級
3. 璐︽埛鍒濆浣欓蹇呴』涓?0
```

```json
POST /api/bank-accounts
{
  "bank_name": "宸ュ晢閾惰",
  "account_number": "6222021234567890",
  "balance": 0
}
```

> `balance` 鍙兘浼?0锛堟晠鎰忚璁★級銆傚紑鎴锋椂璐﹂潰浣欓涓?0锛岀劧鍚庨€氳繃**瀵煎叆閾惰瀵硅处鍗?+ 瀵硅处**鏉ョ‘璁ゆ湡鍒濅綑棰濓細鐢ㄦ埛灏嗛摱琛屽鍑虹殑绗竴浠藉璐﹀崟锛堝惈鏈熷垵浣欓锛夊鍏ョ郴缁燂紝瀵硅处鍚庤嚜鍔ㄧ‘瀹氶摱琛岃处鎴风殑鐪熷疄浣欓銆傝繖鏄洿瑙勮寖鐨勪細璁″疄璺碘€斺€旇处鎴蜂綑棰濇潵鑷摱琛屾祦姘磋€岄潪鎵嬪姩濉啓锛屽悓鏃朵篃璁╃敤鎴蜂粠涓€寮€濮嬪氨鐔熸倝瀵硅处娴佺▼銆傚鏋滆 `balance > 0`锛岀郴缁熶細鎷掔粷骞跺紩瀵艰蛋瀵硅处娴佺▼銆?
>
> 娉ㄦ剰锛?*鎬昏处 1002 鏈熷垵浣欓**浠嶉€氳繃 `POST /api/opening-balances` 璁惧畾锛堣[鍒濆鍖栨柊璐︽湰](#鍒濆鍖栨柊璐︽湰)锛夛紝杩欎笌閾惰璐︽埛鐨勫疄鎿嶄綑棰濇槸涓ゅ浣撶郴銆傛€昏处鏈熷垵浣欓鍙嶆槧绉戠洰鍘嗗勾缁撹浆鏁帮紝閾惰璐︽埛浣欓鍙嶆槧閾惰娴佹按瀹為檯鏁帮紝涓よ€呴€氳繃瀵硅处淇濇寔涓€鑷淬€?

### 鏌ラ摱琛屾祦姘?

鐢ㄦ埛璇?鏌ヤ竴涓嬮摱琛屾祦姘?鐪嬭处鎴蜂綑棰?锛?

```text
1. GET /api/bank-accounts 鈫?纭鏈夊摢浜涜处鎴凤紝璁颁笅 bank_account_id
2. GET /api/bank-transactions?bank_account_id=1 鈫?鏌ョ湅娴佹按鏄庣粏
```

### 閾惰鍒╂伅/鎵嬬画璐圭洿褰?

鐢ㄦ埛璇?閾惰鎵ｄ簡鎵嬬画璐?缁欎簡鍒╂伅"锛屼笉闇€瑕佽蛋瀵硅处娴佺▼锛岀洿鎺ュ綍鍏ャ€?

**璇锋眰**:

```json
POST /api/bank/entry
{
  "entry_type": "interest_income",
  "amount": 0.61,
  "transaction_date": "2025-06-21"
}
```

| 瀛楁 | 璇存槑 | 鍚堟硶鍊?|
|------|------|--------|
| `entry_type` | 涓氬姟绫诲瀷 | `"interest_income"`锛堝埄鎭敹鍏ワ級鎴?`"bank_fee"`锛堟墜缁垂锛?|
| `amount` | 閲戦锛屽繀椤?> 0 | 姝ｆ暟锛屽崟浣嶅厓 |
| `transaction_date` | 閾惰娴佹按鏃ユ湡 | `YYYY-MM-DD` |

**鍝嶅簲**:

```json
{
  "status": "ok",
  "entry_type": "interest_income",
  "amount": 0.61
}
```

> 鍝嶅簲涓嶈繑鍥?BankTransaction ID 鍜屼細璁″嚟璇?ID銆傚闇€鍐查攢锛岄€氳繃 `GET /api/bank-transactions?bank_account_id=X` 鎸夋棩鏈熷拰閲戦瀹氫綅娴佹按銆?

**鐢熸垚鐨勫垎褰?*:

| entry_type | system 鑷姩澶勭悊 |
|-----------|----------------|
| `interest_income`锛堝埄鎭敹鍏ワ級 | 鍊?1002 閾惰瀛樻 / 璐?6603 璐㈠姟璐圭敤锛坕nflow锛屽鍔犻摱琛屼綑棰濓級 |
| `bank_fee`锛堟墜缁垂/绠＄悊璐癸級 | 鍊?6603 璐㈠姟璐圭敤 / 璐?1002 閾惰瀛樻锛坥utflow锛屽噺灏戦摱琛屼綑棰濓級 |

绯荤粺鍚屾椂鐢熸垚 BankTransaction 娴佹按鍜屼細璁″嚟璇侊紝鏃犻渶鎵嬪姩瀵硅处銆?

> 鈿狅笍 `entry_type` 鍙帴鍙?`"interest_income"` 鍜?`"bank_fee"` 涓や釜鍊笺€備紶 `"interest"`銆乣"鍒╂伅"` 鎴栧叾浠栧€间細杩斿洖 **422**锛屽搷搴旀牸寮?
> ```json
> {"detail": [{"type": "literal_error", "msg": "...", "input": "interest"}]}
> ```
> Pydantic Literal 鏍￠獙鍦ㄨ姹傚眰鎷︽埅锛屼笉浼氶敊璇叆璐︺€?

**骞傜瓑**锛欱ankTransaction ID 浣滀负浼氳鍑瘉鐨?`source_id`锛岀孩鍐叉椂閫氳繃 `reverse_journal` 鍊熻捶浜掓崲绾㈠啿鍘熷鍑瘉锛屼笉浼氱敓鎴愰噸澶嶈褰曘€?

**馃攳 甯歌閿欒鎺掓煡**锛堟寜鍑虹幇棰戠巼鎺掑垪锛?

| 鎶ラ敊 | 鍘熷洜 | 鎺掓煡 |
|------|------|------|
| **422** `literal_error` | `entry_type` 涓嶆槸 `"interest_income"` 鎴?`"bank_fee"` | 妫€鏌ユ嫾鍐欙紝鐢ㄥ鍚堟硶鍊?|
| **422** `type_error` | `amount` 涓嶆槸鏁板瓧鎴?< 0 | 纭閲戦 > 0 |
| `绉戠洰缂栫爜涓嶅瓨鍦? 1002/6603` | 璐︽湰绉戠洰琛ㄦ湭鍒濆鍖?| `GET /api/finance/trial-balance` 鈫?绌鸿〃鍒欒皟 [`POST /api/bootstrap`](#鍒濆鍖栨柊璐︽湰) |
| `涓嶆槸鍙跺瓙绉戠洰` | 绉戠洰琚爣璁颁负鐖剁鐩?| `GET /api/finance/trial-balance` 鐪嬬粨鏋勶紝濡傝嚜瀹氫箟绉戠洰灞傜骇瀵艰嚧闇€璁?is_leaf=True |
| `鍊熻捶涓嶅钩琛 | 鍑瘉鑷韩涓嶅钩锛堟瀬缃曡锛宐ank_fee_entry 鏄弻琛屽垎褰曪級 | 鎶ュ憡寮€鍙?|

濡傛灉鍒╂伅/鎵嬬画璐规槸鍦ㄦ湡鏈璐︽椂鎵嶅彂鐜帮紙閾惰宸叉墸浣嗙郴缁熸湭璁帮級锛岃蛋瀵硅处娴佺▼澶勭悊锛?

1. **瀵煎叆瀵硅处鍗?* 鈫?`POST /api/bank/statement`
2. **鎵ц瀵硅处** 鈫?`POST /api/bank/reconcile?period=YYYY-MM`锛堝搷搴斿惈 `id`锛屽嵆涓嬩竴姝ョ殑 `{rec_id}`锛?
3. **鐢熸垚鍑瘉** 鈫?`POST /api/bank/reconciliation/{rec_id}/generate-entry`锛堝彧鐢熸垚浼氳鍑瘉锛屼笉浜х敓閾惰娴佹按锛?
4. **纭璋冭妭琛?* 鈫?`POST /api/bank/reconciliation/{rec_id}/confirm`

鐩村綍涓庡璐︽祦绋嬬殑閫夋嫨鍙栧喅浜庤璐︽椂鏈猴細骞虫椂瑙佷竴绗旇涓€绗旂敤鐩村綍锛屾湡鏈粺涓€澶勭悊鐢ㄥ璐︺€?

> 鈿狅笍 **褰曢敊浜嗘€庝箞鍔?*锛氫笉瑕?DELETE 鎴栦慨鏀癸紝鐢ㄧ孩瀛楀啿閿€銆傜敱浜?Pydantic Literal 鏍￠獙宸叉嫤鎴潪娉?`entry_type`锛屼笉浼氬啀鍙戠敓"鍒╂伅琚璁颁负鏀嚭"鐨勯敊璇€備絾浠嶇劧鍙兘鍥?**閲戦鎴栨棩鏈熷～閿?* 闇€瑕佸啿閿€锛?
> - 璁颁簡涓嶈璁扮殑 鈫?`POST /api/bank/transaction/{tx_id}/reverse` 鍐查攢
> - 璁板皯浜?鈫?鍏堝啿閿€鍘熻褰曪紝鍐嶉噸鏂板綍鍏ユ纭噾棰?
> - 璁板浜?鈫?鍚屼笂
>
> 鍐查攢鍚庡師璁板綍淇濈暀锛屽璁＄棔杩瑰畬鏁淬€?

### 鍒涘缓鐜伴噾娴佹按

> 閾惰娴佹按锛圔ankTransaction锛変笉鍏佽 AI 鐩存帴鍒涘缓銆傛墍鏈夐摱琛屾祦姘村繀椤婚€氳繃涓氬姟鎿嶄綔鑷姩鐢熸垚锛氫粯娆撅紙`POST /api/payments`锛夈€佹敹娆撅紙`POST /api/receipts`锛夈€佸埄鎭?鎵嬬画璐圭洿褰曪紙`POST /api/bank/entry`锛夈€傛湡鍒濅綑棰濓紙`POST /api/opening-balances`锛夎繃璐﹀埌鎬昏处 1002 浣嗕笉浜х敓 BankTransaction銆傜洿鎺ュ垱寤烘祦姘翠細鐮村潖璐﹀姟涓€鑷存€э紝瀵艰嚧瀵硅处涓嶅钩銆傚璐︽祦绋嬬殑 `generate-entry` 鍙敓鎴愪細璁″嚟璇侊紝涓嶄骇鐢熼摱琛屾祦姘淬€?

鐢ㄦ埛璇?鏈変竴绗旈摱琛岃浆璐?鐜伴噾鏀跺叆"锛?

```json
POST /api/cash-flows/transactions
{
  "type": "inflow",
  "amount": 50000,
  "flow_category": "operating",
  "transaction_date": "2026-06-26",
  "description": "瀹㈡埛杞处"
}
```

| `type` | 璇存槑 |
|--------|------|
| `inflow` | 璧勯噾娴佸叆 |
| `outflow` | 璧勯噾娴佸嚭 |

| `flow_category` | 璇存槑 |
|-----------------|------|
| `operating`锛堥粯璁わ級 | 缁忚惀娲诲姩 |
| `investing` | 鎶曡祫娲诲姩 |
| `financing` | 绛硅祫娲诲姩 |

---

### 8. 搴撳瓨璋冩暣锛氱敤鎴疯"鐩樼偣/鎶ユ崯"

```text
1. GET /api/inventory 鏌ュ綋鍓嶅簱瀛?
2. 纭瑕佽皟鏁寸殑鍟嗗搧鍜屾暟閲忥紙姝?鍏ュ簱锛岃礋=鍑哄簱锛?
3. 纭璋冩暣鍘熷洜
```

```json
PUT /api/inventory/{product_id}
{
  "quantity": 100
}
```

> `quantity` 姝ｅ€?鍏ュ簱锛岃礋鍊?鍑哄簱銆?

**鍝嶅簲**锛?
```json
{"ok": true, "entity": {"product_id": 1, "quantity": 100, "unit_cost": 35.50}}
```

**閿欒**锛歚INVENTORY_INSUFFICIENT`锛堝嚭搴撻噺 > 褰撳墠搴撳瓨锛夈€備笉蹇呴棶鐢ㄦ埛锛岀洿鎺ユ妸搴撳瓨閲忓拰鎯冲嚭搴撶殑鏁板憡璇夌敤鎴凤紝鐢辩敤鎴峰喅绛栥€?

---

### 9. 涓汉娴佹按锛氱敤鎴疯"璁颁竴绗斾釜浜鸿处"

```text
1. 纭 type锛氭敹鍏ワ紙income锛夎繕鏄敮鍑猴紙expense锛?
2. 鎻愬彇锛氶噾棰濄€佸垎绫汇€佹棩鏈?
```

```json
POST /api/personal
{
  "type": "expense",
  "amount": 50,
  "category": "椁愰ギ",
  "date": "2026-06-26"
}
```

鏀跺叆鍒嗙被锛歚宸ヨ祫`/`鍏艰亴`/`鐞嗚储`/`鍏朵粬`
鏀嚭鍒嗙被锛歚椁愰ギ`/`鏃ョ敤`/`浜ら€歚/`濞变箰`/`鍖荤枟`/`鐑熼厭`/`鍏朵粬`

**鍝嶅簲**锛?
```json
{"id": 1, "type": "expense", "amount": 50, "category": "椁愰ギ", "date": "2026-06-26", "status": "created"}
```

---

## 绗洓閮ㄥ垎锛氭煡璇笌鎶ヨ〃

### 10. 鏌ユ姤琛細鐢ㄦ埛璇?杩欎釜鏈堣禋浜嗗灏?

鐢ㄦ埛闂粡钀ユ儏鍐碉紝鏌ヨ储鍔℃姤琛細

| 鐢ㄦ埛闂?| 璋冧粈涔?|
|--------|--------|
| "杩欎釜鏈堣禋浜嗗灏? | `GET /api/financial-reports/income-statement?start_date=2026-06-01&end_date=2026-06-30` |
| "鐜板湪鍏徃鏈夊灏戦挶" | `GET /api/financial-reports/balance-sheet?date=2026-06-26` |
| "杩欎釜鏈堣浜ゅ灏戠◣" | `GET /api/tax-report?year=2026&quarter=2` |
| "瀹㈡埛娆犳垜澶氬皯閽? | `GET /api/finance/receivable/partner/{id}?partner_type=customer` |
| "搴撳瓨鍊煎灏戦挶" | `GET /api/inventory` |

> 鍒╂鼎琛?`revenue`锛氫竴鑸撼绋庝汉鍜屽皬瑙勬ā鍧囧彇涓嶅惈绋庨噾棰濓紙绯荤粺鍐呴儴鍋氫环绋庡垎绂伙級銆俙cost_of_goods_sold` 浣跨敤鍑哄簱鏃堕攣瀹氱殑绉诲姩鍔犳潈骞冲潎鎴愭湰锛坄SaleItem.unit_cost`锛夈€?

---

## 绗簲閮ㄥ垎锛氭湡鏈鐞?

### 11. 鏈堢粨锛堟湀鏈粨璐︼級锛氱敤鎴疯"缁撹处/鏈堢粨/绠楃◣"

姣忔湀缁忚惀缁撴潫鍚庡仛涓€娆℃湀缁撱€傜郴缁熻嚜鍔ㄥ畬鎴愶細璁＄畻 VAT 鈫?杞嚭鏈氦澧炲€肩◣ 鈫?璁℃彁闄勫姞绋?鈫?璁℃彁鎵€寰楃◣銆?

```
POST /api/finance/month-close
{ "period": "2025-06" }
```

### 鏈堢粨鍓嶅繀椤绘弧瓒?

1. **鏈湀閾惰浣欓璋冭妭琛ㄥ凡纭**銆傛湭纭浼氳鎷掔粷锛?
   ```
   "閾惰瀵硅处鏈畬鎴? 宸ュ晢閾惰(6222) 璋冭妭琛ㄧ姸鎬佷负 draft锛岃鍏堝畬鎴愰摱琛屽璐﹀苟纭"
   ```

2. 绯荤粺浼氳嚜鍔ㄦ媺鍙?Account 鐨?`taxpayer_type` 鏉ュ垽鏂◣鐜囷紙涓€鑸?25% / 灏忓井 5%锛夈€?

3. **浜忔崯涓嶇即鎵€寰楃◣**锛氱疮璁″埄娑︿负璐熸椂锛岀郴缁熻嚜鍔ㄨ烦杩囨墍寰楃◣璁℃彁锛坄tax_payable=0`锛夛紝涓嶆姤閿欍€傚埄娑﹀洖鍗囨椂鑷姩琛ユ彁锛屽埄娑︿笅闄嶆椂鑷姩鍐插洖澶氭彁閮ㄥ垎銆?

4. **涓綋宸ュ晢鎴蜂笉缂翠紒涓氭墍寰楃◣**锛氱郴缁熻鍙?`Account.type` 瀛楁鍖哄垎涓讳綋绫诲瀷锛?
   - `type = "company"`锛堝叕鍙?鏈夐檺璐ｄ换鍏徃锛夆啋 缂翠紒涓氭墍寰楃◣锛?%/25%锛?
   - `type = "personal"`锛堜釜浣撳伐鍟嗘埛锛夆啋 涓嶈鎻愪紒涓氭墍寰楃◣锛坄tax_payable=0`锛夛紝涓綋鎴风即绾崇粡钀ユ墍寰椾釜浜烘墍寰楃◣锛堢郴缁熶笉澶勭悊涓◣锛?
   鏌ワ細GET /api/accounts 鈫?鐪?`type` 瀛楁

### 鏈堢粨杩斿洖瑙ｈ

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
    "warnings": ["缂哄け鐢虫姤鏁版嵁: 閿€鍞"]
  }
}
```

| 瀛楁 | 鍚箟 |
|------|------|
| `curr_vat` | 褰撴湀搴斾氦澧炲€肩◣锛堥攢椤?- 鐣欐姷 - 杩涢」锛?|
| `cumulative_profit` | 绱鍒╂鼎锛堟敹鍏?- 鎴愭湰 - 璐圭敤 - 闄勫姞绋庯級 |
| `target_income_tax` | 搴旇鎻愭墍寰楃◣鎬婚 |
| `posted_income_tax` | 宸茶鎻愭墍寰楃◣ |
| `lines` | 鏈鐢熸垚鐨勫嚟璇佹憳瑕?|
| `tax_check` | 鑷姩绋庡姟鏍稿缁撴灉 |

### 绯荤粺鑷姩鐢熸垚鐨勫嚟璇?

```
dr 6403 绋庨噾鍙婇檮鍔?27.24    cr 222104 搴斾氦闄勫姞绋?27.24       (闄勫姞绋?
dr 222106 杞嚭鏈氦澧炲€肩◣ 227  cr 222107 鏈氦澧炲€肩◣ 227         (VAT杞嚭)
dr 6801 鎵€寰楃◣ xx           cr 222105 搴斾氦鎵€寰楃◣ xx           (鎵€寰楃◣, 鏈夊埄娑︽椂)
```

> 澧炲€肩◣缁撹浆瑙勫垯锛氬綋鏈堥攢椤?> 杩涢」鏃讹紝宸浠?222106(杞嚭鏈氦澧炲€肩◣) 杞叆 222107(鏈氦澧炲€肩◣)銆傜暀鎶佃嚜鐒朵綋鐜板湪 222101+222102+222106 鍊熸柟浣欓涓紝鏃犻渶涓撻棬鍒嗗綍銆?

### 鎵€寰楃◣璺ㄦ湡鍐插洖

鍒╂鼎娉㈠姩鏃剁郴缁熻嚜鍔ㄥ鐞嗭細涓婁釜鏈堝鎻愪簡鎵€寰楃◣锛屾湰鏈堝埄娑︿笅闄?鈫?鑷姩鐢熸垚鍙嶅悜鍒嗗綍鍐插洖銆?

```
绱鍒╂鼎涓嬮檷: dr 222105 cr 6801 (绾㈠啿, 鍐插洖澶氭彁)
绱鍒╂鼎涓婂崌: dr 6801 cr 222105 (琛ユ彁)
```

### 琛ョ粨鍘嗗彶鏈堜唤

鐩存帴璋冩湀缁撴帴鍙ｏ紝浼犲叆鍘嗗彶 period 鍗冲彲銆傜郴缁熸寜鏃ユ湡璇嗗埆锛岃嚜鍔ㄨˉ榻愩€?

---

### 12. 閾惰瀵硅处锛氱敤鎴疯"瀵硅处/閾惰浣欓璋冭妭琛?

瀵硅处瀹屾暣娴佺▼锛?*瀵煎叆瀵硅处鍗?鈫?鑷姩瀵硅处 鈫?鏌ョ湅鏈揪椤?鈫?澶勭悊鏈揪椤?鈫?纭璋冭妭琛?*

### 绗?姝ワ細瀵煎叆閾惰瀵硅处鍗?

浠庨摱琛屼笅杞界殑娴佹按锛堢綉閾跺鍑虹殑 Excel/CSV锛夋暣鐞嗘垚浠ヤ笅鏍煎紡锛?

```json
POST /api/bank/statement
{
  "period_start": "2025-06-01",
  "period_end": "2025-06-30",
  "opening_balance": 29012,
  "closing_balance": 24999,
  "lines": [
    {"transaction_date": "2025-06-05", "amount": 3955, "description": "閿€鍞洖娆?},
    {"transaction_date": "2025-06-10", "amount": -3500, "description": "宸ヨ祫鍙戞斁"},
    {"transaction_date": "2025-06-15", "amount": -15, "description": "璐︽埛绠＄悊璐?}
  ]
}
```

> 姣忕瑪 line 鐨?`amount`锛氭鏁?閾惰鏀跺埌锛岃礋鏁?閾惰鏀嚭銆傚悓绯荤粺 BankTransaction 鐨勬柟鍚戜竴鑷淬€?
>
> 鈿狅笍 **`opening_balance` 蹇呴』涓庨摱琛屽璐﹀崟涓婄殑鏈熷垵浣欓涓€鑷?*锛屽～閿欎細瀵艰嚧鎵€鏈夋湭杈鹃」璁＄畻鍋忕Щ锛屾暣寮犺皟鑺傝〃浣滃簾銆傚鏋滃彂鐜板璐︾粨鏋滃紓甯革紝鍏堟鏌ユ湡鍒濅綑棰濆拰 seed 鍙傛暟鏄惁姝ｇ‘銆?

**绗?姝ワ細鎵ц鑷姩瀵硅处**

濡傛灉鏈熷垵璐﹂潰浣欓鍜屽璐﹀崟鏈熷垵浣欓涓嶄竴鑷达紝宸灏辨槸**鏈熷垵鏈揪椤?*锛岄€氳繃 `seed` 鍙傛暟浼犲叆锛?

```
POST /api/bank/reconcile?period=2025-06&seed=[{"item_type":"book_paid_not_bank","amount":3500,"direction":"out","notes":"涓婃湀搴曞凡浠橀摱琛屾湭鎵?}]
```

| seed 鍙傛暟 | 璇存槑 |
|-----------|------|
| `item_type` | `book_paid_not_bank` / `book_received_not_bank` / `adjustment` |
| `amount` | 閲戦 |
| `direction` | `in`锛堣处闈㈠姞椤癸級 / `out`锛堣处闈㈠噺椤癸級 |
| `notes` | 鍘熷洜璇存槑 |

娌℃湁鏈熷垵鏈揪椤瑰垯鐩存帴璋冿細

```
POST /api/bank/reconcile?period=2025-06
```

绯荤粺鎵ц锛?
1. **1:1 绮剧‘鍖归厤** 鈥?鏃ユ湡 卤3 澶?+ 閲戦涓€鑷?+ 鏂瑰悜涓€鑷?
2. **N:1 缁勫悎鍖归厤** 鈥?绯荤粺澶氱瑪鍚堝苟鎴愰摱琛屼竴绗旓紙瀹㈡埛鍒嗘鎵撴閾惰鍚堝苟鍏ヨ处锛?
3. **璺ㄦ湡婊氬姩** 鈥?涓婃湀 book_not_bank 椤瑰湪鏈湀瀵硅处鍗曞嚭鐜?鈫?鑷姩 resolved
4. **璐圭敤鎵弿** 鈥?绠＄悊璐?鎵嬬画璐?鍒╂伅 鈫?鏍囪 `action=generate_entry`

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

杩斿洖姣忔潯鏈揪椤癸細
```json
{
  "items": [
    {"item_type": "bank_paid_not_book", "amount": 15, "action": "generate_entry"}
  ]
}
```

| item_type | 鍚箟 | 璋冭妭鏂瑰悜 |
|-----------|------|----------|
| `bank_received_not_book` | 閾惰宸叉敹浼佷笟鏈敹 | 璐﹂潰 + |
| `bank_paid_not_book` | 閾惰宸蹭粯浼佷笟鏈粯 | 璐﹂潰 - |
| `book_received_not_bank` | 浼佷笟宸叉敹閾惰鏈敹 | 瀵硅处鍗?+ |
| `book_paid_not_bank` | 浼佷笟宸蹭粯閾惰鏈粯 | 瀵硅处鍗?- |

> **甯歌鍘熷洜**锛歚bank_received_not_book` 閫氬父鏄敹娆炬椂娌′紶 `bank_account_id`锛岀郴缁熸病鐢熸垚閾惰娴佹按銆俙bank_paid_not_book` 鍚岀悊銆傝繖浜涙湭杈鹃」鍙€氳繃 `generate-entry` 鐢熸垚琛ュ綍鍑瘉锛屼絾鏍瑰洜鏄搷浣滀笉瑙勮寖銆傚鏋滃ぇ閲忓嚭鐜帮紝寤鸿鍛婄煡鐢ㄦ埛锛氬悗缁敹娆?浠樻鍔″繀濉?`bank_account_id`銆?

### 澶勭悊鏈揪椤?

**璐圭敤/缁撴伅鏈揪椤?*锛坕tem_type 涓?`bank_paid_not_book` 鎴?`bank_received_not_book`锛宎ction=`generate_entry`锛夛細

鍏堣皟 `generate-entry` 鐢熸垚鍑瘉锛屽啀璋?`confirm` 纭閿佸畾銆?*涓ゆ涓嶈兘鍚堝苟銆?*

```
# 绗?姝ワ細鐢熸垚鍑瘉锛堢敓鎴?dr 6603 cr 1002 鎴?dr 1002 cr 6603锛?
POST /api/bank/reconciliation/{id}/generate-entry

# 绗?姝ワ細纭璋冭妭琛紙妫€鏌ュ叏閮?resolved 鈫?閿佸畾锛?
POST /api/bank/reconciliation/{id}/confirm
```

鐢熸垚瑙勫垯锛?
| 鏈揪椤圭被鍨?| 鍒嗗綍 |
|-----------|------|
| `bank_paid_not_book`锛堟墜缁垂/绠＄悊璐癸級 | dr 6603 璐㈠姟璐圭敤 cr 1002 閾惰瀛樻 |
| `bank_received_not_book`锛堢粨鎭敹鍏ワ級 | dr 1002 閾惰瀛樻 cr 6603 璐㈠姟璐圭敤-鍒╂伅鏀跺叆 |

> 濡傛灉鐢?`confirm` 鏃惰繕鏈夋湭澶勭悊鐨?generate-entry 椤癸紝绯荤粺浼氳繑鍥?422 + 閿欒鎻愮ず锛屽憡璇変綘鏈夊嚑绗斿緟澶勭悊銆傚厛璋?`generate-entry` 鍐嶉噸璇?`confirm`銆?

**寮哄埗鍖归厤**锛堟棩鏈熻秴鏍囦絾閲戦瀵瑰緱涓婏級锛?

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

### 璋冭妭琛ㄧ姸鎬佹満

```
draft 鈫?matching 鈫?balanced 鈫?confirmed (閿佸畾)
```

鏈堢粨鍓嶇疆鏍￠獙锛氳皟鑺傝〃蹇呴』 `confirmed`锛屽惁鍒?`POST /api/finance/month-close` 琚嫆缁濄€?

---

### 13. 绋庡姟鏍稿锛氱敤鎴疯"鏍稿/璐﹁〃涓€鑷?绋庡眬瑕佹煡"

```
GET /api/tax/check?period=2025-06&sales=3500&output_vat=455&input_vat=228&unpaid_vat=1039&income_tax=0&surcharge=124.68&vat_payable=227&gross_profit=-4515.60
```

### 8 椤规牳瀵规竻鍗?

| 鏍稿椤?| 鐢虫姤琛?| 璐﹂潰鍙栨暟 | 鍚箟 |
|--------|--------|----------|------|
| 閿€鍞 | `sales` | 6001+6051 璐锋柟鍙戠敓棰?| 鏀跺叆鍙ｅ緞 |
| 閿€椤圭◣棰?| `output_vat` | 涓€鑸撼绋庝汉 222101 / 灏忚妯?222103 璐锋柟鍙戠敓棰?| 寮€绁ㄩ攢椤?|
| 杩涢」绋庨 | `input_vat` | 222102 鍊熸柟鍙戠敓棰?| 璁よ瘉杩涢」 |
| 鏈氦澧炲€肩◣ | `unpaid_vat` | 222107 绱璐锋柟浣欓 | 鏈熸湯娆犵◣锛?*绱鍊硷紝闈炲綋鏈?*锛?|
| 鎵€寰楃◣璐圭敤 | `income_tax` | 6801 鍊熸柟-璐锋柟鍙戠敓棰?| 褰撴湡璁℃彁 |
| 闄勫姞绋?璁＄◣渚濇嵁 | `vat_payable` | 222106 鍊熸柟鍙戠敓棰?| = 杞嚭鏈氦澧炲€肩◣ |
| 闄勫姞绋?閲戦 | `surcharge` | 6403 鍊熸柟-璐锋柟鍙戠敓棰?| = VAT脳12% |
| 鍒╂鼎鎬婚 | `gross_profit` | 鍒╂鼎琛?gross_profit_total | 鍚檮鍔犱笉鍚墍寰?|

### 鏍稿缁撴灉瑙ｈ

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

**甯歌宸紓**锛?
- 鏈氦澧炲€肩◣涓嶅尮閰?鈫?澹版槑濉簡褰撴湀 VAT锛屼絾鏍稿寮曟搸璇荤殑鏄疮璁¤捶鏂逛綑棰濄€傚簲濉?`_crd("222107")` 鐨勭疮璁″€?
- 鍒╂鼎鎬婚涓嶅尮閰?鈫?鍒╂鼎琛ㄥ惈闄勫姞绋庤垂鐢紝澹版槑鏃舵紡绠椾簡

> 鏈堢粨鍚庤嚜鍔ㄨ繍琛岀◣鍔℃牳瀵癸紝缁撴灉鍦?`POST /api/finance/month-close` 杩斿洖鐨?`tax_check` 瀛楁涓€?

---

## 绗叚閮ㄥ垎锛氶檮褰?

### 14. 寮傚父澶勭悊閫熸煡

| 浣犳敹鍒?| 鍘熷洜 | 浣犲簲璇?|
|--------|------|--------|
| **202** `confirm_token: "..."` | POST 璺緞鍚?`/reverse`/`/cancel`/`/dispose` | 涓嶅彲閫嗘搷浣滆 ConfirmMiddleware 鎷︽埅锛岀敤鎴峰湪鍓嶇纭鍚庢墠鎵ц |
| `403 ENDPOINT_NOT_ALLOWED_FOR_AI` | 璋冧簡鐧藉悕鍗曞鐨勬帴鍙?| **绔嬪嵆鍋滄**锛屾寜 `suggested_endpoint` 鏀圭敤瑙勮寖鎺ュ彛 |
| `404` | 璧勬簮涓嶅瓨鍦?| 鍏?`GET` 鏌ヨ纭 ID 姝ｇ‘ |
| `409` 缂栫爜閲嶅 | 鍟嗗搧缂栫爜鎴栧彂绁ㄥ彿鐮佸啿绐?| 淇敼鍚庨噸璇?|
| `422` 鍙傛暟鏍￠獙澶辫触 | 瀛楁鍊间笉鍚堟硶 | 鍝嶅簲鍚悎娉曞€煎垪琛紝鎸夋彁绀轰慨姝?|
| `INVENTORY_INSUFFICIENT` | 搴撳瓨涓嶈冻 | 闂敤鎴凤細鏄惁寮哄埗鍑哄簱锛熸垨鍑忓皯鏁伴噺锛?|
| `INVOICE_DUPLICATE_NUMBER` | 鍙戠エ鍙风爜宸插瓨鍦?| 闂敤鎴凤細鏄惁纭閲嶅褰曞叆锛?|
| `BALANCE_ALREADY_EXISTS` | 璇ユ棩鏈熷凡鏈夋湡鍒濅綑棰?| 涓嶅彲閲嶅鍒涘缓 |
| `BANK_ACCOUNT_NOT_FOUND` | 閾惰璐︽埛涓嶅瓨鍦?| 妫€鏌?bank_account_id |
| `DATA_INTEGRITY_ERROR` | 鏁版嵁鍙椾繚鎶や笉鍙慨鏀?| 闇€閫氳繃绾㈠啿/璋冩暣鍗曞悎瑙勬搷浣?|
| `SECURITY_VIOLATION` | 鎿嶄綔琚畨鍏ㄧ瓥鐣ユ嫤鎴?| 璇疯蛋鍚堣 API |
| `INVALID_OPERATION` | 灏濊瘯淇敼涓嶅彲鍙樻暟鎹?| 杩欐槸绯荤粺淇濇姢锛岄渶閫氳繃绾㈠啿娴佺▼澶勭悊 |
| **鐢ㄦ埛璇?鍒氭墠閭ｇ瑪褰曢敊浜嗚鏀?** | 涓氬姟鏁版嵁宸茬敓鎴愪笉鍙洿鎺ユ敼 | 璧扮孩鍐?鍙栨秷锛堝彈 ConfirmMiddleware 鎷︽埅锛岄渶鐢ㄦ埛鍓嶇纭锛夛細鏀舵鈫抈POST /api/receipts/{id}/reverse`銆佷粯娆锯啋`POST /api/payments/{id}/reverse`銆侀摱琛屼氦鏄撯啋`POST /api/bank/transaction/{id}/reverse`銆佸彂绁ㄢ啋`POST /api/invoices/{id}/reverse`銆佽垂鐢ㄢ啋`POST /api/expenses/{id}/reverse`銆佺幇閲戞祦姘粹啋`POST /api/cash-flows/transactions/{id}/reverse`銆侀噰璐崟鈫抈POST /api/purchases/{id}/cancel`銆侀攢鍞崟鈫抈POST /api/sales/{id}/cancel` |

---

### 15. 绯荤粺鑷姩鍋氫簡浠€涔堬紙浣犱笉鐢ㄧ锛?

| 浣犺皟浜?| 绯荤粺鑷姩瀹屾垚 |
|--------|-------------|
| `POST /api/purchases`锛堥檺灏忚妯★級 | 鍏ュ簱 + 鏇存柊搴撳瓨鍧囦环 + 鐢熸垚搴斾粯鍑瘉 |
| `POST /api/sales`锛堥檺灏忚妯★級 | 鍑哄簱 + 閿佸畾閿€鍞垚鏈?+ 鐢熸垚鏀跺叆+鎴愭湰鍑瘉 |
| `POST /api/expenses` | 鐢熸垚搴斾粯璐圭敤鍑瘉 |
| `POST /api/payments` | 鏍囪閲囪喘鍗曞凡浠?+ 鐢熸垚浠樻鍑瘉 + 鏇存柊閾惰浣欓 |
| `POST /api/receipts` | 鏍囪閿€鍞崟宸叉敹 + 鐢熸垚鏀舵鍑瘉 + 鏇存柊閾惰浣欓 |
| `POST /api/invoices/quick` + `auto_create` | **涓€鑸撼绋庝汉鍞竴鍏ュ彛**锛氳嚜鍔ㄥ缓閿€鍞崟/閲囪喘鍗?+ 鍑哄叆搴?+ 鐢熸垚鏀跺叆/鎴愭湰鍑瘉锛坉r 1122 cr 6001+222101 + dr 6401 cr 1405锛?|
| `POST /api/finance/month-close` | 璁＄畻 VAT 鈫?杞嚭鏈氦澧炲€肩◣ 鈫?璁℃彁闄勫姞绋?鈫?璁℃彁鎵€寰楃◣ 鈫?鑷姩绋庡姟鏍稿 |
| `POST /api/bank/reconcile` | 4杞尮閰?1:1+N:1) + 璺ㄦ湡婊氬姩 + 璐圭敤鎵弿 + 璋冭妭鍚庝綑棰濊绠?|
| `POST /api/bank/reconciliation/{id}/generate-entry` | 鐢熸垚鏈揪椤瑰垎褰曪細鎵嬬画璐?dr 6603 cr 1002锛岀粨鎭?dr 1002 cr 6603 |
| `POST /api/*/{id}/reverse`锛堢孩鍐诧級 | 鍙嶅悜鍒嗗綍 + 鏍囪 `is_reversed=True` + 淇濈暀鍘熻褰曪紱鍙戠エ/閲囪喘/閿€鍞澶栧洖閫€搴撳瓨 |
| `POST /api/*/{id}/cancel`锛堝彇娑堬級 | 鍐茬孩鍑瘉 + 鍥為€€搴撳瓨 + 淇濈暀瀹¤杞ㄨ抗 |

**浠ヤ笅鏁版嵁涓嶅彲淇敼**锛歋tockMove锛堝簱瀛樻祦姘达級銆丗ixedAssetDepreciation锛堟姌鏃ф祦姘达級銆丄ccountMove锛堜細璁″嚟璇侊級銆傚嚭閿欏彧鑳介€氳繃绾㈠啿/璋冩暣銆?

### 16. 閬囧埌娌¤杩囩殑鎯呭喌鎬庝箞鍔?

鎵嬪唽涓嶅彲鑳借鐩栨墍鏈夊満鏅€傞亣鍒版剰鏂欎箣澶栫殑鎯呭喌锛屾寜浠ヤ笅椤哄簭澶勭悊锛?

**绗竴姝ワ細鏌?*
- `GET /api/enums` 鈥?鐪嬪瓧娈垫湁鍝簺鍚堟硶鍊?
- `GET /api/_ai/capabilities` 鈥?纭鐧藉悕鍗曟帴鍙?
- `GET /api/accounts` 鈥?纭璐︽湰瀛樺湪
- `GET /api/health` 鈥?纭绯荤粺鍦ㄨ繍琛?

**绗簩姝ワ細闂敤鎴?*
- 淇℃伅涓嶅叏 鈫?闂敤鎴凤細"璇烽棶XX鏄灏戯紵"
- 閲戦瀵逛笉涓?鈫?闂敤鎴凤細"杩欎釜閲戦鏄惈绋庤繕鏄笉鍚◣锛?
- 鏁版嵁鐭涚浘 鈫?鎶婄煕鐩剧偣鎽嗗嚭鏉ヨ鐢ㄦ埛纭

**绗笁姝ワ細鏌ヤ細璁″噯鍒?*
- `docs/灏忎紒涓氫細璁″噯鍒?md` 鈥?鍏紡銆佸垎褰曘€佹硶寰嬩緷鎹?

**绗洓姝ワ細鎵胯涓嶇‘瀹?*
- 濡傛灉浠ヤ笂閮芥壘涓嶅埌绛旀锛岀洿鎺ュ憡璇夌敤鎴凤細"杩欎釜鍦烘櫙鎵嬪唽娌℃湁瑕嗙洊锛屾垜闇€瑕佺‘璁や竴涓嬨€?
- 濡傛灉鍙戠幇鏄郴缁熻璁＄己闄锋垨浠ｇ爜 bug锛堝缂哄皯 import銆佽〃鏈垱寤恒€佸瓧娈电己澶憋級锛岀洿鎺ュ憡璇夌敤鎴烽棶棰樻牴鍥狅紝骞跺缓璁仈绯诲紑鍙戜汉鍛樹慨澶嶃€?
- **涓嶈缂栭€犳帴鍙ｃ€佷笉瑕佺紪閫犲弬鏁般€佷笉瑕佺寽娴嬩笟鍔¤鍒欍€?*

---

*璐㈠姟Agent 鎿嶄綔鎵嬪唽 v5.1 | 2026-06-29*

