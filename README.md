<<<<<<< Updated upstream
﻿---
doc-type: reference
---
# 杩涢攢瀛樼鐞嗙郴缁燂紙Inventory System锛?
=======
---
doc-type: reference
---

---
doc-type: reference
---

# 进销存管理系统（Inventory System）
>>>>>>> Stashed changes

> 闈㈠悜涓皬浼佷笟鐨勫叏鏍堜笟鍔＄鐞嗗钩鍙?鈥斺€?搴撳瓨 路 閲囪喘閿€鍞?路 璐㈠姟绋庡姟鎶ヨ〃 路 涓汉娴佹按锛屼竴绔欏紡璁拌处銆?

![Vue](https://img.shields.io/badge/Vue-3.4-42b883) ![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688) ![SQLite](https://img.shields.io/badge/SQLite-sqlalchemy2-003b57) ![Python](https://img.shields.io/badge/Python-3.10+-blue) ![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey)

---

## 鐩綍

- [蹇€熷紑濮媇(#蹇€熷紑濮?
- [涓€閿墦鍖匽(#涓€閿墦鍖?
- [馃 AI Agent 浣跨敤鎵嬪唽](#-ai-agent-浣跨敤鎵嬪唽)
- [鐜鍙橀噺](#鐜鍙橀噺)
- [娴嬭瘯](#娴嬭瘯)
- [鏂囨。瀵艰埅](#鏂囨。瀵艰埅)
- [璐＄尞涓庤鍙痌(#璐＄尞涓庤鍙?

---

椤圭洰璇︽儏锛堟妧鏈爤銆佹灦鏋勫垎灞傘€佺洰褰曠粨鏋勩€佷笟鍔¤鍒欙級鍙傝 [CONTEXT.md](./CONTEXT.md)銆?

## 蹇€熷紑濮?

### 鐜瑕佹眰

- **Python 3.10+**锛堝缓璁?3.10 / 3.11锛?
- **Node.js 18+**锛堝惈 npm锛?

### 1. 鍏嬮殕浠撳簱

```bash
git clone https://github.com/bingolol/-inventory-system.git
cd -inventory-system
```

### 2. 鍚庣

```bash
# 鍒涘缓骞舵縺娲昏櫄鎷熺幆澧?
python -m venv venv
# Windows (PowerShell)
.\venv\Scripts\Activate.ps1
# Windows (cmd)
venv\Scripts\activate.bat

# 瀹夎渚濊禆
pip install -r backend/requirements.txt
```

### 3. 鍓嶇

```bash
cd frontend
npm install
npm run build      # 鏋勫缓鐢熶骇浜х墿鍒?frontend/dist
cd ..
```

### 4. 鍚姩搴旂敤

**鎺ㄨ崘锛氫娇鐢ㄥ惎鍔ㄥ櫒锛堜笌鎵撳寘鍚庤涓轰竴鑷达級**

```bash
python launcher.py
```

`launcher.py` 浼氾細鑷姩閫夋嫨 8000~8099 鐨勫彲鐢ㄧ鍙ｏ紙鍙敤 `INVENTORY_PORT` 鎸囧畾锛夈€佸垵濮嬪寲宸ヤ綔鍖猴紙`%APPDATA%\杩涢攢瀛樼鐞嗙郴缁焋锛夈€佸苟鍦ㄦ祻瑙堝櫒鎵撳紑搴旂敤銆?

**璋冭瘯妯″紡锛氱洿鎺ョ敤 uvicorn**

```bash
cd backend
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

璁块棶 [http://localhost:8000](http://localhost:8000) 鍗冲彲浣跨敤銆?

## 涓€閿墦鍖?

浠撳簱鏍圭洰褰曠殑 `build.py` 涓茶仈锛氬墠绔瀯寤?鈫?鏁版嵁搴撴ā鏉垮垱寤?鈫?PyInstaller 鎵撳寘 鈫?瀹夎鍣ㄧ敓鎴愩€?

```bash
# 纭繚鍓嶇宸叉瀯寤猴紙frontend/dist 瀛樺湪锛?
python build.py
```

浜х墿锛?

- `dist/杩涢攢瀛樼鐞嗙郴缁?` 鈥斺€?搴旂敤涓荤▼搴忥紙exe + 璧勬簮锛?
- `dist/杩涢攢瀛樼鐞嗙郴缁熷畨瑁呭寘.exe` 鈥斺€?鍗曟枃浠跺畨瑁呭櫒锛坱kinter GUI锛?

> 鑻?PyInstaller 鎶?`missing module`锛屽湪铏氭嫙鐜涓畨瑁呯己澶卞寘锛屾垨灏嗗叾鍔犲叆 `inventory.spec` 鐨?`hiddenimports`銆?

---

## 馃 AI Agent 浣跨敤鎵嬪唽

鏈郴缁熶负 AI Agent锛圕laude / GPT / GLM 绛夛級鎻愪緵**瀹屾暣鐨?REST API 鎿嶄綔鑳藉姏**銆傛墍鏈夎璐︽搷浣滈兘搴旈€氳繃 API 瀹屾垚锛岀姝㈢敤鏂囨湰/琛ㄦ牸/绗旇鏇夸唬銆?

### 蹇€熷叆闂紙30 绉掍笂鎵嬶級

```bash
# 1. 鍋ュ悍妫€鏌?
curl http://localhost:8000/api/health

# 2. 纭璐︽湰锛堜笉纭畾鏃跺厛闂敤鎴凤級
curl -H "X-Account-ID: 1" http://localhost:8000/api/accounts

# 3. 璁颁竴绗旈攢鍞紙AI 璇锋眰甯?X-Operator: ai锛?
curl -X POST http://localhost:8000/api/sales \
  -H "X-Account-ID: 1" \
  -H "X-Operator: ai" \
  -H "Content-Type: application/json" \
  -d '{"customer_name":"寮犱笁","items":[{"product_id":1,"quantity":2,"unit_price":25.00}]}'
```

**蹇呭～璇锋眰澶?*锛?

| Header | 璇存槑 |
|--------|------|
| `X-Account-ID` | 璐︽湰 ID锛堝尯鍒嗗濂楄处鏈紝缂哄け杩斿洖 401锛?|
| `X-Operator: ai` | AI 璇锋眰鏍囪瘑锛堝啓鍏ユ搷浣滄棩蹇楋級 |
| `Content-Type: application/json` | 鍐欐搷浣滃繀闇€ |

### 瀹屾暣鎵嬪唽锛堟寜闇€娣卞叆锛?

| 鏂囨。 | 鍐呭 | 閫傜敤鍦烘櫙 |
|------|------|----------|
| 馃摉 **[docs/璐㈠姟Agent鎵嬪唽.md](./docs/璐㈠姟Agent鎵嬪唽.md)** | 鎿嶄綔閾佸緥 + API 閫熸煡琛?+ 璁拌处鍦烘櫙 + 瀛楁閫熸煡 | **AI 鍔犺浇涓?skill锛屽揩閫熻璐?* |
| 馃摉 **[docs/寮€鍙慉gent鎵嬪唽.md](./docs/寮€鍙慉gent鎵嬪唽.md)** | 寮€鍙戞祦绋?+ 缂栫爜瑙勮寖 + 鏋舵瀯瀵艰埅 | **AI 鍔犺浇涓?skill锛屽紑鍙戜唬鐮?* |
| 馃梻锔?**[CONTEXT.md](./CONTEXT.md)** | 椤圭洰涓婁笅鏂?+ Agent 宸ヤ綔娴?+ 涓氬姟瑙勫垯 | Agent 鍗忎綔寮€鍙戞湰浠撳簱浠ｇ爜鏃?|

**鎿嶄綔閾佸緥**锛堣瑙?[`docs/璐㈠姟Agent鎵嬪唽.md`](./docs/璐㈠姟Agent鎵嬪唽.md)锛夛細

1. 蹇呴』璋冪敤 API 鑾峰彇鐪熷疄鏁版嵁锛岀姝㈠亣璁?缂栭€?
2. 鎵€鏈夎璐﹁蛋鏈郴缁?API锛岀姝㈢敤鏂囨湰/琛ㄦ牸鏇夸唬
3. 鎵€鏈夎姹傚繀椤诲甫 `X-Account-ID` header
4. 鍏堟煡鍚庡啓锛堝箓绛夊垱寤猴紝閬垮厤閲嶅锛?
5. 鍙戠エ褰曞叆浼樺厛鐢?`POST /api/invoices/quick`锛堣嚜鍔ㄧ畻绋庯級

### 榛樿璐︽湰

| 璐︽湰鍚嶇О | 浠ｇ爜 | 绫诲瀷 |
|---------|------|------|
| 鏃ヨ繍鍔炲叕 | riyun | 鍏徃 |
| 宸ф父鐢靛瓙绉戞妧鏈夐檺鍏徃 | qiaoyou | 鍏徃 |
| 涓汉 | personal | 涓汉 |
| 鏉庡弸宸т釜浜烘祦姘磋处 | liyouqiao | 涓汉 |

> ID 鍙兘鍙樺寲锛屽缁堜互 `GET /api/accounts` 杩斿洖涓哄噯銆?

---

## 鐜鍙橀噺

| 鍙橀噺 | 榛樿 | 璇存槑 |
|------|------|------|
| `INVENTORY_PORT` | 鑷姩 8000~8099 | 鎸囧畾绔彛鍒欒烦杩囪嚜鍔ㄦ娴?|
| `INVENTORY_WORKSPACE` | `%APPDATA%\杩涢攢瀛樼鐞嗙郴缁焋 | 鑷畾涔夊伐浣滃尯鏍圭洰褰曪紙浼樺厛绾ф渶楂橈級 |
| `CORS_ORIGINS` | localhost 鐧藉悕鍗?| 杩藉姞鍏佽鐨勫墠绔簮锛堥€楀彿鍒嗛殧锛?|

```bash
# Windows (cmd)
set INVENTORY_PORT=8080
# Windows (PowerShell)
$env:INVENTORY_PORT = '8080'
```

**宸ヤ綔鍖哄竷灞€**锛氭暟鎹簱 `inventory.db`銆佷笂浼犳枃浠?`uploads/images`銆佹棩蹇?`app.log`銆佺鍙ｈ褰?`port.txt` 鍧囦綅浜庡伐浣滃尯鏍圭洰褰曘€?

## 娴嬭瘯

```bash
pytest
```

鍖呭惈鍗曞厓娴嬭瘯锛坄tests/unit/`锛夈€侀泦鎴愭祴璇曪紙`tests/integration/`锛夈€丒2E 娴嬭瘯锛坄tests/e2e/`锛屽熀浜?FastAPI TestClient + 鐪熷疄 SQLite锛夈€?

## 鏂囨。瀵艰埅

| 鏂囨。 | 鍐呭 |
|------|------|
| [CONTEXT.md](./CONTEXT.md) | 椤圭洰涓婁笅鏂囥€丄gent 宸ヤ綔娴併€佹妧鏈爤銆佹灦鏋勫垎灞傘€佷笟鍔¤鍒?|
| [docs/INDEX.md](./docs/INDEX.md) | 瀹屾暣鏂囨。绱㈠紩 |
| [docs/璐㈠姟Agent鎵嬪唽.md](./docs/璐㈠姟Agent鎵嬪唽.md) | 璐㈠姟Agent 鎿嶄綔鎵嬪唽 |
| [docs/寮€鍙慉gent鎵嬪唽.md](./docs/寮€鍙慉gent鎵嬪唽.md) | 寮€鍙慉gent 鎵嬪唽 |

## 璐＄尞涓庤鍙?

- 娆㈣繋 Issue 涓?PR锛欶ork 鈫?鏂板垎鏀?鈫?娣诲姞/鏇存柊娴嬭瘯 鈫?PR
- Issue 杩借釜锛欸itHub Issues (gh CLI)锛岃瑙?[`CONTEXT.md`](./CONTEXT.md#agent-宸ヤ綔娴?
- 浠撳簱褰撳墠鏈寘鍚?LICENSE 鏂囦欢锛屽彂甯冨墠寤鸿琛ュ厖鍚堥€傜殑璁稿彲璇侊紙濡?MIT锛?

---

<p align="center">Built with Vue 3 路 FastAPI 路 Element Plus</p>

