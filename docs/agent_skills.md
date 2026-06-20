# 🤖 Agent Skills 技能目录使用指南

> 本项目 `.agents/skills/` 下内置 19 个技能(Skill),用于规范 AI Agent 在开发流程中的行为。
> 本文档按**使用场景**分类,指导开发人员和 Agent 何时调用哪个技能。
>
> 技能加载方式:Agent 通过 `skill` 工具按名称加载,加载后获得该技能的完整工作流指令。
> 开发人员可阅读对应 `.agents/skills/<name>/SKILL.md` 了解细节。

---

## 📋 技能分类速查

### 🔴 开发核心流程(高频使用)

| 技能 | 触发场景 | 何时用 | 何时**不**用 |
|------|----------|--------|-------------|
| **tdd** | 写功能/修 bug | 核心业务逻辑开发,要求 red-green-refactor | 纯文档更新、单文件小改 |
| **diagnose** | 报 bug/报错/性能回退 | "诊断这个"、"坏了"、抛异常、性能退化 | 已知原因的明确 bug |
| **review** | 审查分支/PR | "review since X"、审查 WIP 改动 | 未开始写代码 |
| **zoom-out** | 不熟悉某段代码 | 需要理解代码如何融入全局 | 已理解上下文 |

### 🟡 计划与设计(中频)

| 技能 | 触发场景 | 何时用 |
|------|----------|--------|
| **to-issues** | 有 plan/PRD 要拆 | 把 plan 拆成可独立领取的 issues(tracer-bullet vertical slices) |
| **to-prd** | 要把对话转 PRD | 当前对话有明确需求,需发布到 issue tracker |
| **triage** | 管理 issue 流 | 创建 issue、分类、为 AFK agent 准备可执行 issue |
| **grill-me** | 压测计划 | "grill me"、想压力测试设计是否站得住 |
| **grill-with-docs** | 压测计划+对齐文档 | 同上,但需对照 CONTEXT.md/ADR 检验领域语言 |
| **prototype** | 探索设计 | "prototype this"、试几个 UI 变体、验证数据模型 |
| **improve-codebase-architecture** | 架构改进 | 找重构机会、合并紧耦合模块、提升可测性 |

### 🟢 会话与交接(低频但关键)

| 技能 | 触发场景 | 何时用 |
|------|----------|--------|
| **handoff** | 会话要交接 | 把当前对话压成 handoff 文档给下个 agent |
| **neat-freak** | 阶段收尾 | "同步一下"、"整理文档"、"更新记忆"、里程碑后知识对齐 |
| **teach** | 学新概念 | 在本 workspace 教用户一个技能/概念 |
| **write-a-skill** | 创建新技能 | 要写结构正确、支持 progressive disclosure 的新技能 |

### ⚙️ 通信模式

| 技能 | 触发场景 | 说明 |
|------|----------|------|
| **caveman** | "caveman mode"、"less tokens" | 超压缩通信,砍填充词省 ~75% token,保留技术准确性 |

### ⛔ 本项目不适用(开发人员可忽略)

| 技能 | 原因 |
|------|------|
| **migrate-to-shoehorn** | 针对 TypeScript `as` 断言迁移;本项目是 Python |
| **scaffold-exercises** | 课程练习脚手架;本项目非教学仓库 |
| **setup-pre-commit** | Husky/lint-staged 面向 JS;本项目用 pytest + Python |
| **git-guardrails-claude-code** | Claude Code hooks;本项目用 OpenCode |
| **setup-matt-pocock-skills** | 首次配置 issue tracker/triage/domain;本项目已配过(见 AGENTS.md) |

---

## 🎯 按任务选技能(决策树)

```
我要做的事
│
├─ 写新功能 / 修核心 bug
│   └─→ tdd(先写测试,red-green-refactor)
│       └─ 不熟悉相关代码? 先 zoom-out
│
├─ 诊断 bug / 性能问题
│   └─→ diagnose(reproduce→minimise→hypothesise→instrument→fix→regression)
│
├─ 审查改动
│   └─→ review(Standards + Spec 双轴并行)
│
├─ 拆任务 / 发 issue
│   ├─ 有完整 plan? → to-issues
│   ├─ 需要先写 PRD? → to-prd
│   └─ 要分类现有 issue? → triage
│
├─ 设计 / 架构
│   ├─ 想压测方案? → grill-me(或 grill-with-docs 对齐领域语言)
│   ├─ 要试做原型? → prototype
│   └─ 找重构机会? → improve-codebase-architecture
│
├─ 阶段收尾
│   ├─ 交接给别人? → handoff
│   └─ 文档/记忆同步? → neat-freak
│
└─ 省 token / 快速沟通
    └─→ caveman
```

---

## 🔗 与 AGENTS.md 工作流的关系

`AGENTS.md` 定义了本项目的 **5 条必守规则**(Read docs first / Docs before code / Plan before execute / Self-review / Tests first)。技能是这些规则的**落地工具**:

| AGENTS.md 规则 | 对应技能 |
|----------------|----------|
| Read docs first | zoom-out(理解上下文) |
| Docs before code | to-prd / write-a-skill(先出设计文档) |
| Plan before execute | grill-me / grill-with-docs(压力测试计划) |
| Self-review | review / neat-freak(审查 + 文档同步) |
| Tests first | **tdd**(核心业务逻辑强制 TDD) |

---

## 📂 技能文件位置

```
.agents/skills/
├── caveman/SKILL.md
├── diagnose/SKILL.md
├── git-guardrails-claude-code/SKILL.md   ⛔ 不适用
├── grill-me/SKILL.md
├── grill-with-docs/SKILL.md
├── handoff/SKILL.md
├── improve-codebase-architecture/SKILL.md
├── migrate-to-shoehorn/SKILL.md          ⛔ 不适用
├── prototype/SKILL.md
├── scaffold-exercises/SKILL.md           ⛔ 不适用
├── setup-matt-pocock-skills/SKILL.md     ⛔ 已配过
├── setup-pre-commit/SKILL.md             ⛔ 不适用
├── tdd/SKILL.md
├── teach/SKILL.md
├── to-issues/SKILL.md
├── to-prd/SKILL.md
├── triage/SKILL.md
├── write-a-skill/SKILL.md
└── zoom-out/SKILL.md
```

> 全局还可能有 `~/.config/opencode/skills/` 和 `~/.agents/skills/` 下的技能(如 neat-freak、find-skills、review),这些跨项目共享,不在本仓库版本控制内。

---

*agent_skills v1.0 | 2026-06-20*
