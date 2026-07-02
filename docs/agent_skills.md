<<<<<<< Updated upstream
﻿---
doc-type: reference
---
# 馃 Agent Skills 鎶€鑳界洰褰曚娇鐢ㄦ寚鍗?
=======
---
doc-type: catalog
---

# 🤖 Agent Skills 技能目录使用指南
>>>>>>> Stashed changes

> 鏈」鐩?`.agents/skills/` 涓嬪唴缃?23 涓妧鑳?Skill),鐢ㄤ簬瑙勮寖 AI Agent 鍦ㄥ紑鍙戞祦绋嬩腑鐨勮涓恒€?
> 鏈枃妗ｆ寜**浣跨敤鍦烘櫙**鍒嗙被,鎸囧寮€鍙戜汉鍛樺拰 Agent 浣曟椂璋冪敤鍝釜鎶€鑳姐€?
>
> 鎶€鑳藉姞杞芥柟寮?Agent 閫氳繃 `skill` 宸ュ叿鎸夊悕绉板姞杞?鍔犺浇鍚庤幏寰楄鎶€鑳界殑瀹屾暣宸ヤ綔娴佹寚浠ゃ€?
> 寮€鍙戜汉鍛樺彲闃呰瀵瑰簲 `.agents/skills/<name>/SKILL.md` 浜嗚В缁嗚妭銆?

---

## 馃搵 鎶€鑳藉垎绫婚€熸煡

### 馃敶 寮€鍙戞牳蹇冩祦绋?楂橀浣跨敤)

| 鎶€鑳?| 瑙﹀彂鍦烘櫙 | 浣曟椂鐢?| 浣曟椂**涓?*鐢?|
|------|----------|--------|-------------|
| **tdd** | 鍐欏姛鑳?淇?bug | 鏍稿績涓氬姟閫昏緫寮€鍙?瑕佹眰 red-green-refactor | 绾枃妗ｆ洿鏂般€佸崟鏂囦欢灏忔敼 |
| **diagnose** | 鎶?bug/鎶ラ敊/鎬ц兘鍥為€€ | "璇婃柇杩欎釜"銆?鍧忎簡"銆佹姏寮傚父銆佹€ц兘閫€鍖?| 宸茬煡鍘熷洜鐨勬槑纭?bug |
| **review** | 瀹℃煡鍒嗘敮/PR | "review since X"銆佸鏌?WIP 鏀瑰姩 | 鏈紑濮嬪啓浠ｇ爜 |
| **zoom-out** | 涓嶇啛鎮夋煇娈典唬鐮?| 闇€瑕佺悊瑙ｄ唬鐮佸浣曡瀺鍏ュ叏灞€ | 宸茬悊瑙ｄ笂涓嬫枃 |
| **audit-truth-source** | 鎶ヨ〃璇绘暟涓嶅 | 鎵弿浠ｇ爜搴撴煡鎵?鐪熺浉婧愮粫杩?bug鈥斺€旀姤琛ㄨ purchase_price 鑰岄潪 engine 瀹為檯鎴愭湰 | 浠呴渶鍗曠偣淇 |
| **bs-diag** | BS/鍒╂鼎琛ㄤ笉骞?| 璧勪骇璐熷€鸿〃/鍒╂鼎琛ㄤ笉骞崇瓑鏁呴殰璇婃柇 | 鎶ヨ〃娌￠棶棰?|
| **doc-mgmt** | 鏂囨。瀹¤/娓呯悊 | 鍒嗙被銆佸垎绫汇€佹竻鐞嗚繃鏃剁殑 markdown 鏂囨。 | 涓嶉渶瑕佹枃妗ｇ淮鎶?|

### 馃煛 璁″垝涓庤璁?涓)

| 鎶€鑳?| 瑙﹀彂鍦烘櫙 | 浣曟椂鐢?|
|------|----------|--------|
| **to-issues** | 鏈?plan/PRD 瑕佹媶 | 鎶?plan 鎷嗘垚鍙嫭绔嬮鍙栫殑 issues(tracer-bullet vertical slices) |
| **to-prd** | 瑕佹妸瀵硅瘽杞?PRD | 褰撳墠瀵硅瘽鏈夋槑纭渶姹?闇€鍙戝竷鍒?issue tracker |
| **triage** | 绠＄悊 issue 娴?| 鍒涘缓 issue銆佸垎绫汇€佷负 AFK agent 鍑嗗鍙墽琛?issue |
| **grill-me** | 鍘嬫祴璁″垝 | "grill me"銆佹兂鍘嬪姏娴嬭瘯璁捐鏄惁绔欏緱浣?|
| **grill-with-docs** | 鍘嬫祴璁″垝+瀵归綈鏂囨。 | 鍚屼笂,浣嗛渶瀵圭収 CONTEXT.md/ADR 妫€楠岄鍩熻瑷€ |
| **prototype** | 鎺㈢储璁捐 | "prototype this"銆佽瘯鍑犱釜 UI 鍙樹綋銆侀獙璇佹暟鎹ā鍨?|
| **improve-codebase-architecture** | 鏋舵瀯鏀硅繘 | 鎵鹃噸鏋勬満浼氥€佸悎骞剁揣鑰﹀悎妯″潡銆佹彁鍗囧彲娴嬫€?|

### 馃煛 璐㈠姟鎿嶄綔(涓)

| 鎶€鑳?| 瑙﹀彂鍦烘櫙 | 浣曟椂鐢?|
|------|----------|--------|
| **finance-agent** | 璁拌处/褰曞崟/寮€绁?鏈堢粨 | 鐢ㄨ嚜鐒惰瑷€瀹屾垚閲囪喘/閿€鍞?鍙戠エ/璐圭敤/璧勪骇/鏀朵粯娆?閾惰/搴撳瓨/鎶ヨ〃/鏈堢粨绛?13 绫昏储鍔℃搷浣?|

### 馃煝 浼氳瘽涓庝氦鎺?浣庨浣嗗叧閿?

| 鎶€鑳?| 瑙﹀彂鍦烘櫙 | 浣曟椂鐢?|
|------|----------|--------|
| **handoff** | 浼氳瘽瑕佷氦鎺?| 鎶婂綋鍓嶅璇濆帇鎴?handoff 鏂囨。缁欎笅涓?agent |
| **teach** | 瀛︽柊姒傚康 | 鍦ㄦ湰 workspace 鏁欑敤鎴蜂竴涓妧鑳?姒傚康 |
| **write-a-skill** | 鍒涘缓鏂版妧鑳?| 瑕佸啓缁撴瀯姝ｇ‘銆佹敮鎸?progressive disclosure 鐨勬柊鎶€鑳?|

### 鈿欙笍 閫氫俊妯″紡

| 鎶€鑳?| 瑙﹀彂鍦烘櫙 | 璇存槑 |
|------|----------|------|
| **caveman** | "caveman mode"銆?less tokens" | 瓒呭帇缂╅€氫俊,鐮嶅～鍏呰瘝鐪?~75% token,淇濈暀鎶€鏈噯纭€?|

### 鉀?鏈」鐩笉閫傜敤(寮€鍙戜汉鍛樺彲蹇界暐)

| 鎶€鑳?| 鍘熷洜 |
|------|------|
| **migrate-to-shoehorn** | 閽堝 TypeScript `as` 鏂█杩佺Щ;鏈」鐩槸 Python |
| **scaffold-exercises** | 璇剧▼缁冧範鑴氭墜鏋?鏈」鐩潪鏁欏浠撳簱 |
| **setup-pre-commit** | Husky/lint-staged 闈㈠悜 JS;鏈」鐩敤 pytest + Python |
| **git-guardrails-claude-code** | Claude Code hooks;鏈」鐩敤 OpenCode |
| **setup-matt-pocock-skills** | 棣栨閰嶇疆 issue tracker/triage/domain;鏈」鐩凡閰嶈繃(瑙?CONTEXT.md) |

---

## 馃幆 鎸変换鍔￠€夋妧鑳?鍐崇瓥鏍?

```
鎴戣鍋氱殑浜?
鈹?
鈹溾攢 鍐欐柊鍔熻兘 / 淇牳蹇?bug
鈹?  鈹斺攢鈫?tdd(鍏堝啓娴嬭瘯,red-green-refactor)
鈹?      鈹斺攢 涓嶇啛鎮夌浉鍏充唬鐮? 鍏?zoom-out
鈹?
鈹溾攢 璇婃柇 bug / 鎬ц兘闂
鈹?  鈹斺攢鈫?diagnose(reproduce鈫抦inimise鈫抙ypothesise鈫抜nstrument鈫抐ix鈫抮egression)
鈹?
鈹溾攢 瀹℃煡鏀瑰姩
鈹?  鈹斺攢鈫?review(Standards + Spec 鍙岃酱骞惰)
鈹?
鈹溾攢 鎷嗕换鍔?/ 鍙?issue
鈹?  鈹溾攢 鏈夊畬鏁?plan? 鈫?to-issues
鈹?  鈹溾攢 闇€瑕佸厛鍐?PRD? 鈫?to-prd
鈹?  鈹斺攢 瑕佸垎绫荤幇鏈?issue? 鈫?triage
鈹?
鈹溾攢 璁捐 / 鏋舵瀯
鈹?  鈹溾攢 鎯冲帇娴嬫柟妗? 鈫?grill-me(鎴?grill-with-docs 瀵归綈棰嗗煙璇█)
鈹?  鈹溾攢 瑕佽瘯鍋氬師鍨? 鈫?prototype
鈹?  鈹斺攢 鎵鹃噸鏋勬満浼? 鈫?improve-codebase-architecture
鈹?
鈹溾攢 闃舵鏀跺熬
鈹?  鈹溾攢 浜ゆ帴缁欏埆浜? 鈫?handoff
鈹?  鈹斺攢 鏂囨。/璁板繂鍚屾? 鈫?neat-freak
鈹?
鈹斺攢 鐪?token / 蹇€熸矡閫?
    鈹斺攢鈫?caveman
```

---

## 馃敆 涓?CONTEXT.md 宸ヤ綔娴佺殑鍏崇郴

`CONTEXT.md` 瀹氫箟浜嗘湰椤圭洰鐨?**5 鏉″繀瀹堣鍒?*(Read docs first / Docs before code / Plan before execute / Self-review / Tests first)銆傛妧鑳芥槸杩欎簺瑙勫垯鐨?*钀藉湴宸ュ叿**:

| CONTEXT.md 瑙勫垯 | 瀵瑰簲鎶€鑳?|
|----------------|----------|
| Read docs first | zoom-out(鐞嗚В涓婁笅鏂? |
| Docs before code | to-prd / write-a-skill(鍏堝嚭璁捐鏂囨。) |
| Plan before execute | grill-me / grill-with-docs(鍘嬪姏娴嬭瘯璁″垝) |
| Self-review | review / neat-freak(瀹℃煡 + 鏂囨。鍚屾) |
| Tests first | **tdd**(鏍稿績涓氬姟閫昏緫寮哄埗 TDD) |

---

## 馃搨 鎶€鑳芥枃浠朵綅缃?

```
.agents/skills/
鈹溾攢鈹€ caveman/SKILL.md
鈹溾攢鈹€ diagnose/SKILL.md
鈹溾攢鈹€ git-guardrails-claude-code/SKILL.md   鉀?涓嶉€傜敤
鈹溾攢鈹€ grill-me/SKILL.md
鈹溾攢鈹€ grill-with-docs/SKILL.md
鈹溾攢鈹€ handoff/SKILL.md
鈹溾攢鈹€ improve-codebase-architecture/SKILL.md
鈹溾攢鈹€ migrate-to-shoehorn/SKILL.md          鉀?涓嶉€傜敤
鈹溾攢鈹€ prototype/SKILL.md
鈹溾攢鈹€ scaffold-exercises/SKILL.md           鉀?涓嶉€傜敤
鈹溾攢鈹€ setup-matt-pocock-skills/SKILL.md     鉀?宸查厤杩?
鈹溾攢鈹€ setup-pre-commit/SKILL.md             鉀?涓嶉€傜敤
鈹溾攢鈹€ tdd/SKILL.md
鈹溾攢鈹€ teach/SKILL.md
鈹溾攢鈹€ to-issues/SKILL.md
鈹溾攢鈹€ to-prd/SKILL.md
鈹溾攢鈹€ triage/SKILL.md
鈹溾攢鈹€ write-a-skill/SKILL.md
鈹斺攢鈹€ zoom-out/SKILL.md
```

> 鍏ㄥ眬杩樺彲鑳芥湁 `~/.config/opencode/skills/` 鍜?`~/.agents/skills/` 涓嬬殑鎶€鑳?濡?neat-freak銆乫ind-skills銆乺eview),杩欎簺璺ㄩ」鐩叡浜?涓嶅湪鏈粨搴撶増鏈帶鍒跺唴銆?

---

*agent_skills v1.0 | 2026-06-20*

