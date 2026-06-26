# 📚 进销存管理系统 - 文档索引

> **最后更新**: 2026-06-22

---

## 🎯 快速导航

### 按角色

| 角色 | 起点文档 |
|------|----------|
| **AI Agent** | [AI_AGENT_GUIDE.md](./AI_AGENT_GUIDE.md) |
| **开发者** | [开发速查表.md](./开发速查表.md) |
| **架构师** | [架构参考.md](./架构参考.md) |
| **新成员** | [README.md](../README.md) |

### 按任务

| 我想要... | 文档位置 |
|-----------|----------|
| 调用 API | [AI_AGENT_GUIDE.md §3](./AI_AGENT_GUIDE.md#3-api-速查表) |
| 了解架构 | [架构参考.md](./架构参考.md) |
| 查看文件位置 | [文件索引.md](./文件索引.md) |
| 开发新功能 | [开发速查表.md](./开发速查表.md) |
| 了解功能模块 | [功能模块说明.md](./功能模块说明.md) |
| 查看枚举值 | [AI_AGENT_GUIDE.md §5](./AI_AGENT_GUIDE.md#5-关键字段速查) |
| 排查错误 | [AI_AGENT_GUIDE.md §7](./AI_AGENT_GUIDE.md#7-错误码) |
| 查会计公式 | [小企业会计准则.md](./小企业会计准则.md) |
| 选 AI 技能 | [agent_skills.md](./agent_skills.md) |
| 提交 Issue | [agents/issue-tracker.md](./agents/issue-tracker.md) |

---

## 📂 文档清单

### 核心文档

| 文档 | 用途 | 重要性 |
|------|------|--------|
| [INDEX.md](./INDEX.md) | 本文件 - 文档总索引 | ⭐⭐⭐ |
| [AI_AGENT_GUIDE.md](./AI_AGENT_GUIDE.md) | AI Agent 操作手册 | ⭐⭐⭐ |
| [架构参考.md](./架构参考.md) | 系统架构、ER图、数据流 | ⭐⭐⭐ |
| [开发速查表.md](./开发速查表.md) | 开发规范、反模式红线 | ⭐⭐⭐ |
| [文件索引.md](./文件索引.md) | 全仓库文件分类 | ⭐⭐⭐ |
| [功能模块说明.md](./功能模块说明.md) | 各功能模块详解 | ⭐⭐ |
| [小企业会计准则.md](./小企业会计准则.md) | 会计法规速查 | ⭐⭐ |
| [测试规范.md](./测试规范.md) | 测试编写指南 | ⭐⭐ |
| [架构改进方案_定稿.md](./架构改进方案_定稿.md) | 架构改进方案定稿（5大方案） | ⭐⭐ |
| [前端重构方案.md](./前端重构方案.md) | 前端代码重构优化方案（TDD） | ⭐⭐ |
| [agent_skills.md](./agent_skills.md) | Agent 技能目录使用指南 | ⭐⭐ |

### Agent 协作文档

| 文档 | 用途 |
|------|------|
| [agent_skills.md](./agent_skills.md) | `.agents/skills/` 19 个技能分类与使用时机 |
| [agents/domain.md](./agents/domain.md) | 领域文档消费指南 |
| [agents/issue-tracker.md](./agents/issue-tracker.md) | Issue 追踪规范 |
| [agents/triage-labels.md](./agents/triage-labels.md) | 分类标签映射 |

### 项目根目录文档

| 文档 | 用途 |
|------|------|
| [README.md](../README.md) | 项目说明、快速开始 |
| [CONTEXT.md](../CONTEXT.md) | 项目上下文、领域语言 |
| [AGENTS.md](../AGENTS.md) | Agent 配置入口 |

---

## 🔗 文档关系

```
README.md (项目入口)
    │
    ├──→ CONTEXT.md (项目上下文 + 业务规则)
    │        │
    │        └──→ docs/架构参考.md (架构详解)
    │
    ├──→ docs/INDEX.md (文档索引) ⭐
    │        │
    │        ├──→ docs/AI_AGENT_GUIDE.md (AI 操作手册)
    │        ├──→ docs/架构参考.md (架构详解)
    │        ├──→ docs/开发速查表.md (开发规范)
    │        ├──→ docs/文件索引.md (文件分类)
    │        ├──→ docs/功能模块说明.md (模块详解)
    │        ├──→ docs/小企业会计准则.md (会计公式 + 法规依据)
    │        ├──→ docs/架构改进方案_定稿.md (架构改进5大方案)
    │        └──→ docs/前端重构方案.md (前端重构优化)
    │
    └──→ AGENTS.md (Agent 配置)
             │
             └──→ docs/agents/ (Agent 协作文档)
```

---

## 🚀 快速开始

### 对于 AI Agent

```bash
# 1. 读取操作手册
cat docs/AI_AGENT_GUIDE.md

# 2. 查看功能模块说明
cat docs/功能模块说明.md
```

### 对于开发者

```bash
# 1. 阅读开发速查表
cat docs/开发速查表.md

# 2. 查看文件索引
cat docs/文件索引.md
```

### 对于架构师

```bash
# 1. 阅读架构参考
cat docs/架构参考.md

# 2. 查看文件索引
cat docs/文件索引.md
```

---

## 📋 文档贡献

### 添加新文档

1. 将文档放入 `docs/` 目录
2. 更新本索引文件
3. 在相关文档中添加交叉引用

### 文档命名规范

- 使用中文命名（与 README 引用一致）
- 简洁明了
- 避免特殊字符

---

*文档索引 v1.6 | 2026-06-22*
