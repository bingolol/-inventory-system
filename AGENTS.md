# Agents

## 📚 知识库入口

> **完整文档索引**: [docs/INDEX.md](docs/INDEX.md)
> **开发速查**: [docs/开发速查表.md](docs/开发速查表.md)
> **架构参考**: [docs/架构参考.md](docs/架构参考.md)
> **文件索引**: [docs/文件索引.md](docs/文件索引.md)

> ⚠️ **修改代码前必读**：[docs/开发速查表.md#设计理念](docs/开发速查表.md#-设计理念看起来像-bug-但不是)
> 了解哪些行为是故意设计，避免"修复"正确代码。

---

## 🤖 Agent 工作流

### 必须遵守的 5 条规则

| # | 规则 | 说明 |
|---|------|------|
| 1 | **Read docs first** | 先读文档再写代码，理解上下文 |
| 2 | **Docs before code** | 新模块/重构时先创建设计文档 |
| 3 | **Plan before execute** | 呈现计划，等待批准后再执行 |
| 4 | **Self-review** | 完成后自检，确保文档同步更新 |
| 5 | **Tests first** | 核心业务逻辑使用 TDD |

### 开发流程

```
1. 理解任务
   │
   ├─→ 读取 CONTEXT.md (项目上下文)
   ├─→ 读取相关模块文档
   └─→ 如有疑问，先问用户
   │
2. 制定计划
   │
   ├─→ 列出要修改的文件
   ├─→ 说明修改原因
   └─→ 呈现给用户批准
   │
3. 执行开发
   │
   ├─→ 遵循开发速查表中的规范
   ├─→ 遵循反模式红线 (AP-1~AP-14)
   └─→ 核心逻辑先写测试
   │
4. 自检完成
   │
   ├─→ 运行测试: pytest
   ├─→ 检查代码风格
   └─→ 更新相关文档
```

### 何时询问用户

- 不确定业务规则时
- 涉及数据库结构变更时
- 涉及多个模块的重构时
- 可能影响现有功能时

### 何时直接执行

- 明确的 Bug 修复
- 文档更新
- 单一文件的小改动
- 测试补充

---

## Agent skills

> **技能使用指南**: [docs/agent_skills.md](docs/agent_skills.md) — 按 5 类场景(开发核心/计划设计/会话交接/通信/不适用)说明 `.agents/skills/` 下 19 个技能何时用。
>
> **与 5 条规则的对应**: tdd→Tests first / review→Self-review / zoom-out→Read docs first / grill-me→Plan before execute / neat-freak→Self-review。

### Issue tracker

GitHub Issues (gh CLI). See `docs/agents/issue-tracker.md`.

### Triage labels

Default 5 labels: needs-triage / needs-info / ready-for-agent / ready-for-human / wontfix. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `CONTEXT.md` at repo root + `docs/adr/`. See `docs/agents/domain.md`.

---

## 🎯 快速开始

### 对于 AI Agent

```bash
# 1. 读取操作手册
cat docs/AI_AGENT_GUIDE.md

# 2. 读取项目上下文
cat CONTEXT.md
```

### 对于开发者

```bash
# 1. 读取贡献指南
cat CONTRIBUTING.md

# 2. 读取开发速查表
cat docs/开发速查表.md
```

### 对于新成员

```bash
# 1. 查看文档索引
cat docs/INDEX.md

# 2. 查看文件索引
cat docs/文件索引.md
```

---

## 📋 文档检查清单

Agent 完成任务后，检查:

- [ ] 代码测试通过
- [ ] 相关文档已更新
- [ ] 没有引入新的反模式
- [ ] 遵循命名约定
- [ ] 错误处理使用 BusinessError
