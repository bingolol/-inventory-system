# 进销存管理系统（Inventory System）

> 面向中小企业的全栈业务管理平台 —— 库存 · 采购销售 · 财务税务报表 · 个人流水，一站式记账。

![Vue](https://img.shields.io/badge/Vue-3.4-42b883) ![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688) ![SQLite](https://img.shields.io/badge/SQLite-sqlalchemy2-003b57) ![Python](https://img.shields.io/badge/Python-3.10+-blue) ![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey)

---

## 目录

- [核心功能](#核心功能)
- [技术栈](#技术栈)
- [快速开始](#快速开始)
- [一键打包](#一键打包)
- [目录结构](#目录结构)
- [🤖 AI Agent 使用手册](#-ai-agent-使用手册)
- [环境变量](#环境变量)
- [测试](#测试)
- [文档导航](#文档导航)
- [贡献与许可](#贡献与许可)

---

## 核心功能

- **进销存**：商品/库存管理、采购入库、销售出库，库存自动联动扣减/回补
- **财务报表**：资产负债表、利润表（经营口径）、现金流量表、财务汇总
- **税务双口径**：增值税季度/月度报表（发票口径）、企业所得税报表（销项/进项发票口径）
- **发票管理**：进项/销项发票、专票认证、PDF 上传、AI 快捷录入接口
- **多账本隔离**：通过 `X-Account-ID` 请求头隔离多套账本（公司账 / 个人账）
- **对账管理**：按供应商/客户维度实时计算往来账
- **个人流水**：独立的个人收支记账模块
- **备份与日志**：数据热备份、操作日志全程可追溯

## 技术栈

| 层次 | 技术 |
|------|------|
| 前端框架 | Vue 3 + Vite + Element Plus |
| 状态管理 | Pinia |
| 路由 / HTTP | Vue Router 4 + Axios |
| 图表 | ECharts + vue-echarts |
| 后端框架 | FastAPI（Python 3.10+） |
| ORM | SQLAlchemy 2.x |
| 数据库 | SQLite |
| 打包 | PyInstaller（生成 exe + 安装器） |

## 快速开始

### 环境要求

- **Python 3.10+**（建议 3.10 / 3.11）
- **Node.js 18+**（含 npm）

### 1. 克隆仓库

```bash
git clone https://github.com/bingolol/-inventory-system.git
cd -inventory-system
```

### 2. 后端

```bash
# 创建并激活虚拟环境
python -m venv venv
# Windows (PowerShell)
.\venv\Scripts\Activate.ps1
# Windows (cmd)
venv\Scripts\activate.bat

# 安装依赖
pip install -r backend/requirements.txt
```

### 3. 前端

```bash
cd frontend
npm install
npm run build      # 构建生产产物到 frontend/dist
cd ..
```

### 4. 启动应用

**推荐：使用启动器（与打包后行为一致）**

```bash
python launcher.py
```

`launcher.py` 会：自动选择 8000~8099 的可用端口（可用 `INVENTORY_PORT` 指定）、初始化工作区（`%APPDATA%\进销存管理系统`）、并在浏览器打开应用。

**调试模式：直接用 uvicorn**

```bash
cd backend
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

访问 [http://localhost:8000](http://localhost:8000) 即可使用。

## 一键打包

仓库根目录的 `build.py` 串联：前端构建 → 数据库模板创建 → PyInstaller 打包 → 安装器生成。

```bash
# 确保前端已构建（frontend/dist 存在）
python build.py
```

产物：

- `dist/进销存管理系统/` —— 应用主程序（exe + 资源）
- `dist/进销存管理系统安装包.exe` —— 单文件安装器（tkinter GUI）

> 若 PyInstaller 报 `missing module`，在虚拟环境中安装缺失包，或将其加入 `inventory.spec` 的 `hiddenimports`。

## 目录结构

```
inventory-system/
├── backend/
│   ├── main.py              # FastAPI 入口
│   ├── routers/             # API 路由层
│   ├── commands/            # 命令模式（写操作编排）
│   ├── crud/                # 数据访问层
│   ├── domain/              # 领域模型（业务规则校验）
│   ├── schemas/             # Pydantic 模式
│   ├── models.py            # ORM 模型
│   ├── enums.py             # 枚举单一真相源
│   ├── events.py / handlers.py  # 事件总线 + 处理器
│   └── uow.py               # Unit of Work
├── frontend/
│   └── src/
│       ├── views/           # 页面视图
│       ├── components/      # 组件
│       ├── composables/     # 组合式逻辑
│       ├── stores/          # Pinia 状态
│       ├── api/             # API 请求
│       └── utils/           # 工具函数（formatMoney 等）
├── tests/                   # 单元 / 集成 / E2E 测试
├── docs/                    # 文档（含 AI Agent 手册）
├── launcher.py              # 启动器（打包入口）
├── build.py                 # 一键构建脚本
├── installer.py             # tkinter 安装向导
├── CONTEXT.md               # 项目上下文 / 领域语言
└── AGENTS.md                # Agent 工作约定
```

**架构分层**：`Routers → Commands → CRUD / Domain → Events → EventBus`

> Command Handler 显式编排库存联动，保障库存一致性。详见 [`CONTEXT.md`](./CONTEXT.md)。

---

## 🤖 AI Agent 使用手册

本系统为 AI Agent（Claude / GPT / GLM 等）提供**完整的 REST API 操作能力**。所有记账操作都应通过 API 完成，禁止用文本/表格/笔记替代。

### 快速入门（30 秒上手）

```bash
# 1. 健康检查
curl http://localhost:8000/api/health

# 2. 确认账本（不确定时先问用户）
curl -H "X-Account-ID: 1" http://localhost:8000/api/accounts

# 3. 记一笔销售（AI 请求带 X-Operator: ai）
curl -X POST http://localhost:8000/api/sales \
  -H "X-Account-ID: 1" \
  -H "X-Operator: ai" \
  -H "Content-Type: application/json" \
  -d '{"customer_name":"张三","items":[{"product_id":1,"quantity":2,"unit_price":25.00}]}'
```

**必填请求头**：

| Header | 说明 |
|--------|------|
| `X-Account-ID` | 账本 ID（区分多套账本，缺失返回 401） |
| `X-Operator: ai` | AI 请求标识（写入操作日志） |
| `Content-Type: application/json` | 写操作必需 |

### 完整手册（按需深入）

| 文档 | 内容 | 适用场景 |
|------|------|----------|
| 📖 **[docs/AI_AGENT_GUIDE.md](./docs/AI_AGENT_GUIDE.md)** | 操作铁律 + API 速查表 + 记账场景 + 字段速查 | **AI 加载为 skill，快速记账** |
| 🗂️ **[AGENTS.md](./AGENTS.md)** | Issue tracker / triage labels / domain 文档约定 | Agent 协作开发本仓库代码时 |

**操作铁律**（详见 [`docs/AI_AGENT_GUIDE.md`](./docs/AI_AGENT_GUIDE.md)）：

1. 必须调用 API 获取真实数据，禁止假设/编造
2. 所有记账走本系统 API，禁止用文本/表格替代
3. 所有请求必须带 `X-Account-ID` header
4. 先查后写（幂等创建，避免重复）
5. 发票录入优先用 `POST /api/invoices/quick`（自动算税）

### 默认账本

| 账本名称 | 代码 | 类型 |
|---------|------|------|
| 日运办公 | riyun | 公司 |
| 巧游电子科技有限公司 | qiaoyou | 公司 |
| 个人 | personal | 个人 |
| 李友巧个人流水账 | liyouqiao | 个人 |

> ID 可能变化，始终以 `GET /api/accounts` 返回为准。

---

## 环境变量

| 变量 | 默认 | 说明 |
|------|------|------|
| `INVENTORY_PORT` | 自动 8000~8099 | 指定端口则跳过自动检测 |
| `INVENTORY_WORKSPACE` | `%APPDATA%\进销存管理系统` | 自定义工作区根目录（优先级最高） |
| `CORS_ORIGINS` | localhost 白名单 | 追加允许的前端源（逗号分隔） |

```bash
# Windows (cmd)
set INVENTORY_PORT=8080
# Windows (PowerShell)
$env:INVENTORY_PORT = '8080'
```

**工作区布局**：数据库 `inventory.db`、上传文件 `uploads/images`、日志 `app.log`、端口记录 `port.txt` 均位于工作区根目录。

## 测试

```bash
pytest
```

包含单元测试（`tests/unit/`）、集成测试（`tests/integration/`）、E2E 测试（`tests/e2e/`，基于 FastAPI TestClient + 真实 SQLite）。

## 文档导航

| 文档 | 内容 |
|------|------|
| [CONTEXT.md](./CONTEXT.md) | 项目上下文、技术栈、架构分层 |
| [AGENTS.md](./AGENTS.md) | Agent 工作流、5 条规则 |
| [docs/INDEX.md](./docs/INDEX.md) | 完整文档索引 |
| [docs/AI_AGENT_GUIDE.md](./docs/AI_AGENT_GUIDE.md) | AI Agent 操作手册 |

## 贡献与许可

- 欢迎 Issue 与 PR：Fork → 新分支 → 添加/更新测试 → PR
- 本仓库使用本地 markdown 跟踪 issue（`.scratch/<feature>/`），详见 [`AGENTS.md`](./AGENTS.md)
- 仓库当前未包含 LICENSE 文件，发布前建议补充合适的许可证（如 MIT）

---

<p align="center">Built with Vue 3 · FastAPI · Element Plus</p>
