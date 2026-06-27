# PRD：用户登录认证 + 操作者溯源

## Problem Statement

当前系统无任何登录认证。审计日志的 `operator` 字段通过 `X-Operator` 头判断，前端请求默认值为 `"user"` 且不设此头，AI 请求显式设 `"ai"`。问题：任何人只要知道设 `X-Operator: user` 头就能模拟前端操作，审计日志无法追溯到具体操作者。

目标：加一层轻量登录，让审计日志能区分"哪个用户"以及"AI 还是人类"。

## Solution

最简 token 认证方案：

1. 后端加一张 `User` 表 + `POST /api/auth/login` 返回 token
2. 鉴权中间件从 `Authorization: Bearer <token>` 解析用户身份，替换 `get_operator()` 的默认值
3. 前端加登录页 + axios interceptor 自动带 token
4. 审计日志 `_log()` 的 `operator` 记录实际用户名（或 `"ai"`）
5. AI Agent 不受登录影响，继续走 `X-Operator: ai` + 白名单

## User Stories

1. As a 系统使用者, I want to 用用户名+密码登录, so that 我的操作可被追踪
2. As a 系统管理员, I want to 查看操作日志, so that 我知道谁做了什么
3. As an AI Agent, I want to 继续用 X-Operator: ai 调用白名单 API, so that 我不受影响
4. As a 开发者, I want to 审计日志区分 human vs AI, so that 我能排查问题
5. As a 前端页面, I want to 登录后自动带 token, so that 用户体验无感知

## Implementation Decisions

### Modules to build/modify

| Module | Action | Description |
|--------|--------|-------------|
| `backend/models.py` | ADD | `User` 表：id, username, password_hash, account_id, created_at |
| `backend/schemas/user.py` | ADD | `LoginRequest`, `LoginResponse`, `UserOut` |
| `backend/routers/auth.py` | ADD | `POST /api/auth/login` → 校验密码 → 返回 token |
| `backend/auth_middleware.py` | ADD | ASGI 中间件：从 `Authorization` 头解析 token → 设置 `X-User` scope |
| `backend/account_dep.py` | MODIFY | `get_operator()` 优先从 token 解析的用户名取值，fallback 到 Header 值 |
| `backend/crud/base.py` | MODIFY | `_log()` 的 operator 参数来源切换为鉴权后的用户名 |
| `backend/main.py` | MODIFY | 注册 auth router + auth middleware |
| `backend/database.py` | MODIFY | `init_db()` 补充默认 admin 用户 |
| `frontend/src/views/Login.vue` | ADD | 登录页面 |
| `frontend/src/stores/auth.js` | ADD | Pinia store：token + 用户状态 |
| `frontend/src/api/index.js` | MODIFY | axios interceptor 自动带 `Authorization` 头 |
| `frontend/src/router/index.js` | MODIFY | 加 `beforeEach` 守卫，未登录跳转登录页 |

### Token Scheme

```
token = sha256(username + ":" + secret_key + ":" + expiry_timestamp)
```

- 无 JWT 依赖，Python 标准库 `hashlib` 即可
- 服务端存 `username → {token_hash, expiry}` 映射
- 每次请求中间件查映射表校验
- Token 24 小时过期

### Auth Middleware 行为

```
请求 → AuthMiddleware
  ├─ Authorization: Bearer <token> → 校验 token →
  │   ├─ 有效 → 在 scope["user"] 设 username, scope["operator"] 设 username
  │   └─ 无效 → scope["user"] = None, scope["operator"] = ""
  │
  ├─ X-Operator: ai (无 Authorization) → AI Agent →
  │   scope["user"] = None, scope["operator"] = "ai"
  │
  └─ 无头 → scope["user"] = None, scope["operator"] = ""
```

### 审计日志行为变化

| 场景 | 当前 `operator` | 登录后 `operator` |
|------|----------------|-------------------|
| 前端页面操作 | `user` | 实际用户名（如 `admin`） |
| AI Agent 调用 | `ai` | `ai`（不变） |
| 脚本无头 | 无 → 403 | 无 → 403（不变） |

### 密码方案

- 非真实密码系统，使用固定 secret 做演示
- `password_hash = sha256("用户名:固定盐值")`
- `POST /api/auth/login` 校验密码哈希 → 返回 token
- 生产环境可替换为真实密码系统

## Testing Decisions

### Test approach

- **Auth middleware**: 参考 `test_ai_gateway.py` 的 ASGI 内层 app + TestClient 模式。验证：
  - 有效 token → scope["user"] 正确设置
  - 无效 token → scope["user"] 为 None
  - 无 Authorization 头 → scope["user"] 为 None
- **Login endpoint**: TestClient + 临时内存 DB
- **`_log()` 集成**: 验证 operator 是否按预期传入

### Prior art

- `tests/unit/test_ai_gateway.py` — ASGI 中间件单元测试模式（最小内层 app + TestClient 包装）
- `tests/unit/test_engine_finance.py` — pytest fixture 模式（`db`, `account`, `product`）

## Out of Scope

- 角色权限（RBAC）：只做身份识别，不做权限控制
- OAuth / SSO：不做第三方登录
- 密码重置流程：不做
- 注册功能：用户由管理员手动创建

## Further Notes

- 此方案的核心价值在审计日志的"可溯源性"，而非安全防护
- token 存内存而非 DB：简化实现，重启后所有 token 失效（用户重新登录）
- `Account`（账本）选择逻辑不变，仍通过 `X-Account-ID` 头
