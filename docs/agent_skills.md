---
doc-type: catalog
---

# 🤖 Agent Skills 技能目录使用指南

> 鏈」鐩?`.agents/skills/` 涓嬪唴缃?23 涓妧鑳?Skill),用于规范 AI Agent 鍦ㄥ紑鍙戞祦绋嬩腑鐨勮涓恒€?
> 本文档按**使用场景**分类,鎸囧寮€鍙戜汉鍛樺拰 Agent 浣曟椂璋冪敤鍝釜鎶€鑳姐€?
>
> 鎶€鑳藉姞杞芥柟寮?Agent 通过 `skill` 宸ュ叿鎸夊悕绉板姞杞?鍔犺浇鍚庤幏寰楄鎶€鑳界殑瀹屾暣宸ヤ綔娴佹寚浠ゃ€?
> 寮€鍙戜汉鍛樺彲闃呰瀵瑰簲 `.agents/skills/<name>/SKILL.md` 浜嗚В缁嗚妭銆?

---

## 📋 鎶€鑳藉垎绫婚€熸煡

### 🔴 寮€鍙戞牳蹇冩祦绋?高频使用)

| 鎶€鑳?| 触发场景 | 浣曟椂鐢?| 何时**涓?*鐢?|
|------|----------|--------|-------------|
| **tdd** | 鍐欏姛鑳?淇?bug | 鏍稿績涓氬姟閫昏緫寮€鍙?要求 red-green-refactor | 绾枃妗ｆ洿鏂般€佸崟鏂囦欢灏忔敼 |
| **diagnose** | 鎶?bug/报错/鎬ц兘鍥為€€ | "诊断这个"銆?坏了"銆佹姏寮傚父銆佹€ц兘閫€鍖?| 宸茬煡鍘熷洜鐨勬槑纭?bug |
| **review** | 审查分支/PR | "review since X"銆佸鏌?WIP 改动 | 未开始写代码 |
| **zoom-out** | 涓嶇啛鎮夋煇娈典唬鐮?| 闇€瑕佺悊瑙ｄ唬鐮佸浣曡瀺鍏ュ叏灞€ | 已理解上下文 |
| **audit-truth-source** | 报表读数不对 | 鎵弿浠ｇ爜搴撴煡鎵?鐪熺浉婧愮粫杩?bug鈥斺€旀姤琛ㄨ purchase_price 而非 engine 实际成本 | 仅需单点修复 |
| **bs-diag** | BS/鍒╂鼎琛ㄤ笉骞?| 璧勪骇璐熷€鸿〃/利润表不平等故障诊断 | 鎶ヨ〃娌￠棶棰?|
| **doc-mgmt** | 文档审计/清理 | 鍒嗙被銆佸垎绫汇€佹竻鐞嗚繃鏃剁殑 markdown 文档 | 涓嶉渶瑕佹枃妗ｇ淮鎶?|

### 🟡 璁″垝涓庤璁?中频)

| 鎶€鑳?| 触发场景 | 浣曟椂鐢?|
|------|----------|--------|
| **to-issues** | 鏈?plan/PRD 要拆 | 鎶?plan 拆成可独立领取的 issues(tracer-bullet vertical slices) |
| **to-prd** | 瑕佹妸瀵硅瘽杞?PRD | 褰撳墠瀵硅瘽鏈夋槑纭渶姹?闇€鍙戝竷鍒?issue tracker |
| **triage** | 管理 issue 娴?| 创建 issue銆佸垎绫汇€佷负 AFK agent 鍑嗗鍙墽琛?issue |
| **grill-me** | 压测计划 | "grill me"銆佹兂鍘嬪姏娴嬭瘯璁捐鏄惁绔欏緱浣?|
| **grill-with-docs** | 压测计划+对齐文档 | 同上,但需对照 CONTEXT.md/ADR 妫€楠岄鍩熻瑷€ |
| **prototype** | 探索设计 | "prototype this"、试几个 UI 鍙樹綋銆侀獙璇佹暟鎹ā鍨?|
| **improve-codebase-architecture** | 架构改进 | 鎵鹃噸鏋勬満浼氥€佸悎骞剁揣鑰﹀悎妯″潡銆佹彁鍗囧彲娴嬫€?|

### 🟡 财务操作(中频)

| 鎶€鑳?| 触发场景 | 浣曟椂鐢?|
|------|----------|--------|
| **finance-agent** | 记账/录单/寮€绁?月结 | 鐢ㄨ嚜鐒惰瑷€瀹屾垚閲囪喘/閿€鍞?发票/费用/资产/鏀朵粯娆?银行/库存/报表/鏈堢粨绛?13 绫昏储鍔℃搷浣?|

### 🟢 浼氳瘽涓庝氦鎺?浣庨浣嗗叧閿?

| 鎶€鑳?| 触发场景 | 浣曟椂鐢?|
|------|----------|--------|
| **handoff** | 浼氳瘽瑕佷氦鎺?| 鎶婂綋鍓嶅璇濆帇鎴?handoff 鏂囨。缁欎笅涓?agent |
| **teach** | 学新概念 | 在本 workspace 鏁欑敤鎴蜂竴涓妧鑳?概念 |
| **write-a-skill** | 鍒涘缓鏂版妧鑳?| 瑕佸啓缁撴瀯姝ｇ‘銆佹敮鎸?progressive disclosure 鐨勬柊鎶€鑳?|

### ⚙️ 通信模式

| 鎶€鑳?| 触发场景 | 说明 |
|------|----------|------|
| **caveman** | "caveman mode"銆?less tokens" | 瓒呭帇缂╅€氫俊,鐮嶅～鍏呰瘝鐪?~75% token,淇濈暀鎶€鏈噯纭€?|

### 鉀?本项目不适用(寮€鍙戜汉鍛樺彲蹇界暐)

| 鎶€鑳?| 原因 |
|------|------|
| **migrate-to-shoehorn** | 针对 TypeScript `as` 断言迁移;本项目是 Python |
| **scaffold-exercises** | 璇剧▼缁冧範鑴氭墜鏋?本项目非教学仓库 |
| **setup-pre-commit** | Husky/lint-staged 面向 JS;本项目用 pytest + Python |
| **git-guardrails-claude-code** | Claude Code hooks;本项目用 OpenCode |
| **setup-matt-pocock-skills** | 首次配置 issue tracker/triage/domain;本项目已配过(瑙?CONTEXT.md) |

---

## 🎯 鎸変换鍔￠€夋妧鑳?鍐崇瓥鏍?

```
鎴戣鍋氱殑浜?
鈹?
├─ 写新功能 / 淇牳蹇?bug
鈹?  鈹斺攢鈫?tdd(先写测试,red-green-refactor)
鈹?      └─ 涓嶇啛鎮夌浉鍏充唬鐮? 鍏?zoom-out
鈹?
├─ 诊断 bug / 性能问题
鈹?  鈹斺攢鈫?diagnose(reproduce→minimise→hypothesise→instrument→fix→regression)
鈹?
├─ 审查改动
鈹?  鈹斺攢鈫?review(Standards + Spec 双轴并行)
鈹?
├─ 鎷嗕换鍔?/ 鍙?issue
鈹?  ├─ 鏈夊畬鏁?plan? 鈫?to-issues
鈹?  ├─ 闇€瑕佸厛鍐?PRD? 鈫?to-prd
鈹?  └─ 瑕佸垎绫荤幇鏈?issue? 鈫?triage
鈹?
├─ 设计 / 架构
鈹?  ├─ 鎯冲帇娴嬫柟妗? 鈫?grill-me(鎴?grill-with-docs 对齐领域语言)
鈹?  ├─ 瑕佽瘯鍋氬師鍨? 鈫?prototype
鈹?  └─ 鎵鹃噸鏋勬満浼? 鈫?improve-codebase-architecture
鈹?
├─ 阶段收尾
鈹?  ├─ 浜ゆ帴缁欏埆浜? 鈫?handoff
鈹?  └─ 文档/记忆同步? 鈫?neat-freak
鈹?
└─ 鐪?token / 蹇€熸矡閫?
    鈹斺攢鈫?caveman
```

---

## 🔗 涓?CONTEXT.md 工作流的关系

`CONTEXT.md` 瀹氫箟浜嗘湰椤圭洰鐨?**5 鏉″繀瀹堣鍒?*(Read docs first / Docs before code / Plan before execute / Self-review / Tests first)銆傛妧鑳芥槸杩欎簺瑙勫垯鐨?*落地工具**:

| CONTEXT.md 规则 | 瀵瑰簲鎶€鑳?|
|----------------|----------|
| Read docs first | zoom-out(鐞嗚В涓婁笅鏂? |
| Docs before code | to-prd / write-a-skill(先出设计文档) |
| Plan before execute | grill-me / grill-with-docs(压力测试计划) |
| Self-review | review / neat-freak(审查 + 文档同步) |
| Tests first | **tdd**(核心业务逻辑强制 TDD) |

---

## 📂 鎶€鑳芥枃浠朵綅缃?

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

> 全局还可能有 `~/.config/opencode/skills/` 鍜?`~/.agents/skills/` 涓嬬殑鎶€鑳?濡?neat-freak、find-skills、review),杩欎簺璺ㄩ」鐩叡浜?涓嶅湪鏈粨搴撶増鏈帶鍒跺唴銆?

---

*agent_skills v1.0 | 2026-06-20*

