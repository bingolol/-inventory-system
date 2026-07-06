---
name: doc-mgmt
description: >-
  Classify, triage, and clean up project markdown documentation. For each file: determine if it's stale, whether it can be deleted, and what the project loses if deleted. Also automates doc updates after code changes via git diff analysis → affected doc mapping → concrete edit suggestions. Use when user mentions doc audit, document cleanup, stale docs, orphaned files, sync docs, update docs, or asks to review markdown files.
---

# Doc Management v3

## ⚠️ 使用本技能前：先搞清楚你要回答什么问题

不要抱着"把文档同步一下"的心态来。同步是手段，不是目的。

目的只有一个：**让下一个读到这份文档的人，能做出正确的决定。**

所以动手前，先对自己说清楚三件事：

1. **我要更新哪个文档？** — 不是"全部文档"，是哪一份。
2. **这份文档的下一个读者，在什么场景下读它？** — 是 Agent 启动时？是记账前？是查报表时？
3. **这个读者读完更新后的内容，会比现在多知道什么？少误解什么？** — 如果回答不上来，说明你根本不需要更新这份文档。

带着这三个问题去改，才能有的放矢。不然就是在 dump 信息——你的 diff 看起来很忙，但没人在意。

---

## 核心原则：不给不该看的人看

更新文档的第一原则不是"同步"，是**克制**。

一个代码变更影响范围多大，不等于文档更新范围多大。引擎内部重构了、函数签名变了——跟记账 Agent 没半毛钱关系，它调的是 API，API 没变就别往它手册里塞。

**反模式**：看到一个变更"很重要"，就把它同步到所有文档。结果每个文档都膨胀、每个 Agent 都读到一堆跟自己无关的东西、token 浪费、信噪比下降。

**正确做法**：拿着变更，逐个文档问——**这个读者需要因为这次变更调整行为吗？** 不需要 = 不写。

### 更新前先三问

| # | 问题 | 倾向 |
|---|------|------|
| 1 | **这份文档是给谁看的？** 开发 Agent？记账 Agent？人？ | 决定了要不要写。不是给这个人看的 → **一个字都别塞** |
| 2 | **这个读者需要因为这次变更调整行为吗？** 引擎重构但 API 没变 → 记账 Agent 不需要知道。BR 规则变了 → 开发 Agent 必须知道 | 不需要调整行为 → 不写 |
| 3 | **这次更新值得花 token 吗？** 每次启动都读、每次操作都读，塞进去的东西在永远地被消费 | 不值得 → 写成 git commit message |

### 同一变更，不同读者，只写给对的人

`engine_tax.py` 附加税减半改为读 `surcharge_halved`：

| 读者 | 要不要写 | 写什么 |
|------|---------|--------|
| **开发 Agent**（CONTEXT.md）| ✅ 写 | BR-25：`income_type` → `Account.surcharge_halved` |
| **记账 Agent**（财务Agent手册）| ✅ 写 | §11：附加税减半不再跟所得税走，创建账本时独立配置 |
| **人类开发者**（会计实务.md）| ✅ 写 | §3.2：原因和背景 |
| **测试规范.md** | ❌ 不写 | 跟测试无关 |
| **功能模块说明.md** | ❌ 不写 | 引擎没新增，只是改了内部逻辑 |

### 不更新的代价

1. Agent 读旧文档 → 按错误规则决策 → 写出 bug
2. 新人读旧文档 → 理解偏差 → 在别处重复同样的错
3. 多个文档互相矛盾 → 不知道该信哪一个

---

## Quick start

```
场景 A — 文档审计: 全量遍历 → 三问 → doc-type → classify → triage
场景 B — 代码变更同步: git diff → 变更分类 → 映射文档 → 逐个问"这人需要知道吗？"→ 写
```

---

## 一、场景 A：文档审计

### 0. Check `doc-type` header

```yaml
---
doc-type: catalog     # 目录索引 — 代码变则更新
doc-type: snapshot    # 代码快照 — 代码变则重验
doc-type: reference   # 参考/约定 — 不需同步但应保持准确
---
```

- Missing → **needs header**
- `catalog` stale → **must update**
- `snapshot` stale → **reverify affected chapters**
- `reference` → check accuracy, no forced sync

### 1. Inventory

List all `.md` files. Cross-reference `INDEX.md` and `文件索引.md`.

### 2. Classify

| Class | Label | Description |
|-------|-------|-------------|
| A | **Active** | Cross-linked, accurate |
| B | **Stale** | Referenced but outdated — update, don't delete |
| C | **Historical** | Valuable record but no longer active |
| D | **Orphaned** | No index or cross-link references |
| E | **Superseded** | Replaced by newer doc — check inbound links |

### 3. Triage deletion

| Class | Default | Keep if |
|-------|---------|---------|
| C | **Delete** (git preserves) | Compliance required |
| D | Ask user | External links or unique content |
| E | Delete after confirming no inbound links | Update links first |

### 4. Cross-reference health

- Broken links
- Encoding issues (garbled Chinese)
- Stale anchors
- Obsolete references to deleted files
- Missing entries in INDEX/文件索引
- Missing `doc-type`
- Content references non-existent entities

### 5. Apply doc-type headers

- INDEX.md, 文件索引.md → `catalog`
- 数据因果链.md → `snapshot`
- All others → `reference`

---

## 二、场景 B：代码变更后文档同步

### Step 1: 提取变更

```bash
git diff --stat HEAD
git diff HEAD
```

### Step 2: 分类变更

| 变更类型 | 判别 | 文档动作 |
|---------|------|---------|
| **新文件** | untracked / `A` | catalog 新增条目；snapshot 新增章节 |
| **删除** | `D` | catalog 移除引用；check inbound links |
| **重构** | 签名变更、参数重塑 | reference 更新；snapshot 重验 |
| **Bug 修复** | 逻辑修正 | 涉及 BR 则更新 BR 章节 |
| **新功能** | 新函数/类/引擎/API | catalog + snapshot + reference |
| **新 BR** | 业务规则、税务政策 | CONTEXT.md + 会计实务.md + 业务因果链.md |

### Step 3: 模块→文档映射

拿着变更文件，找到映射的文档，然后**逐个文档问：这人需要知道吗？**

```
backend/models.py, models_finance.py
  → CONTEXT.md, 架构参考.md, 数据因果链.md, 功能模块说明.md, 单一真相源原则.md

backend/engine_*.py
  → 会计实务.md, 单一真相源原则.md, CONTEXT.md
  ⚠️ 内部重构 API 不变 → 财务Agent手册 不写

backend/policy/*.py
  → CONTEXT.md (BR), 会计实务.md, 业务因果链.md

backend/commands/*.py
  → 财务Agent手册.md, 数据因果链.md, 会计实务.md

backend/crud/finance/*.py
  → 会计实务.md, 单一真相源原则.md, CONTEXT.md

backend/utils/*.py
  → 功能模块说明.md, 单一真相源原则.md, CONTEXT.md

backend/routers/*.py
  → 财务Agent手册.md, INDEX.md, 文件索引.md

backend/domain/*.py
  → 功能模块说明.md, CONTEXT.md, 会计实务.md

backend/scripts/qiaoyou_sim/*.py
  → scripts/qiaoyou_sim/CALCULATION_LOGIC.md, scripts/qiaoyou_sim/MATH_PROOF.md

tests/*.py
  → 测试规范.md

frontend/src/**/*.vue
  → 前端规范.md, 功能模块说明.md
```

### Step 4: 按读者粒度写

| 文档 | 读者 | 只写什么 |
|------|------|---------|
| CONTEXT.md | 开发 Agent（每次启动必读） | BR 一字不差，架构约束精确 |
| 财务Agent手册.md | 记账 Agent（每次操作必读） | API 参数、流程、规则。**不写引擎内部实现** |
| 会计实务.md | 人 | 解释为什么，不罗列改了什么 |
| 业务因果链.md | 人 + Agent | 因果链正确，不需要 API 级细节 |
| 功能模块说明.md | 人（快速了解） | 新增模块要列，内部重构不写 |
| 单一真相源原则.md | 开发 Agent（审计时） | 字段映射、读写权限精确 |

### Step 5: 一致性检查

同一个事实，在所有需要它的文档中描述一致：

- [ ] 新 BR 在 CONTEXT.md / 会计实务.md / 业务因果链.md 中都有？
- [ ] INDEX.md 和 文件索引.md 覆盖所有 docs/ 下 .md 文件？
- [ ] CONTEXT.md 目录树包含所有新增模块？
- [ ] 功能模块说明.md 的表格覆盖所有新增模块？
- [ ] 财务Agent手册.md 覆盖新增 router？（但不要写引擎内部实现）
- [ ] 测试规范.md 列出新增测试文件？
- [ ] 所有被修改的文档 footer 日期已更新？

---

## 三、编码问题检测与修复

```python
def file_is_healthy(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read(5000)
    pua = sum(1 for c in text if '\ue000' <= c <= '\uf8ff')
    return pua < 5
```

修复：用 Python 直接操作字节，绕开终端编码：

```python
with open('file.md', 'r', encoding='utf-8') as f:
    content = f.read()
content = content.replace(old_str, new_str)
with open('file.md', 'w', encoding='utf-8') as f:
    f.write(content)
```

---

## Report format

### 审计
```
### [filename] — [Class] — [doc-type] — [读者]
- Stale? yes/no
- Deletable? yes/no
- Loss: high/medium/low
- Action: keep/update/delete
```

### 代码变更同步
```
## 变更
| 文件 | 模块 | 类型 | 哪些读者需要知道？ |

## 逐文档
### docs/xxx.md → 读者: X
- [ ] 需要写 A — 原因
- [ ] 不需要写 B — API 没变，跟这个读者无关

## 一致性
- [ ] BR-XX 在三份文档中一致
```

---

## Doc rot speed

| 类型 | 速度 | 原因 |
|------|------|------|
| API routes / file index | 🚀 Fast | 端点常变 |
| 调用链 / 因果链 (snapshot) | 🚀 Fast | 每次重构重验 |
| 功能模块说明 | 🐢 Medium | 新模块才变 |
| Business rules / BRs | 🐌 Slow | 已确认少变 |
| Coding conventions | 🐌 Slow | 稳定 |

---

## References

- `docs/INDEX.md` — master index (`catalog`)
- `docs/文件索引.md` — file inventory (`catalog`)
- `CONTEXT.md` — project context & BRs
- `docs/开发规范.md` — doc classification + sync rules
- `docs/架构参考.md` — architecture
- `docs/功能模块说明.md` — feature modules
- `docs/财务Agent手册.md` — finance agent manual
- `docs/会计实务.md` — accounting practices
- `docs/业务因果链.md` — business causality
- `docs/单一真相源原则.md` — single source of truth
- `docs/测试规范.md` — testing standards
