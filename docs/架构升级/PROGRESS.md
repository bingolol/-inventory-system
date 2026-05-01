# 架构升级进度交接文档

> 最后更新：2026-05-01 21:45 | 会话交接用

---

## 总览

架构升级共8个阶段（P0-P7），当前已完成 P0 和 P1，P2-P7 待实施。

```
P0 ✅ → P1 ✅ → P2 ⏳ → P3 ⏳ → P5 ⏳ → P4 ⏳ → P6 ⏳ → P7 ⏳
```

**推荐实施顺序**：P0 → P1 → P2 → P3 → P5 → P4 → P6 → P7（按依赖链）

---

## 已完成阶段

### P0：Unit of Work ✅

**状态**：已完成并通过验证

**变更文件清单**：

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/uow.py` | **新建** | Unit of Work 上下文管理器（38行） |
| `backend/routers/project_costs.py` | 修改 | 5处双commit合并到uow |
| `backend/routers/sales.py` | 修改 | 3处写操作包裹uow |
| `backend/routers/purchases.py` | 修改 | 3处写操作包裹uow |
| `backend/routers/invoices.py` | 修改 | 6处写操作包裹uow |
| `backend/routers/products.py` | 修改 | 3处写操作包裹uow |
| `backend/routers/suppliers.py` | 修改 | 3处写操作包裹uow |
| `backend/routers/customers.py` | 修改 | 3处写操作包裹uow |
| `backend/routers/personal.py` | 修改 | 3处写操作包裹uow |
| `backend/routers/projects.py` | 修改 | 3处写操作包裹uow |
| `backend/routers/opening_balances.py` | 修改 | 3处写操作包裹uow |
| `backend/crud/finance.py` | 修改 | 6处commit→flush, 删rollback |
| `backend/crud/orders.py` | 修改 | 6处commit→flush, 删rollback |
| `backend/crud/invoices.py` | 修改 | 全部commit→flush |
| `backend/crud/personal.py` | 修改 | 全部commit→flush |
| `backend/crud/products.py` | 修改 | 全部commit→flush |
| `backend/crud/partners.py` | 修改 | 全部commit→flush |

**验证结果**：
- `crud/` 和 `routers/` 中 `db.commit()` = 0处 ✅
- `crud/` 和 `routers/` 中 `db.rollback()` = 0处 ✅
- `routers/` 中 `unit_of_work` 引用 = 56处 ✅
- API测试：商品/销售单/采购单/发票/成本 全部正常 ✅

---

### P1：Float→Numeric金额 ✅

**状态**：已完成并通过验证（发现并修复了1个小问题）

**变更文件清单**：

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/models.py` | 修改 | 30个Float金额字段→Numeric(12,2) |
| `backend/schemas.py` | 修改 | 所有float金额字段→Decimal |
| `backend/database.py` | 修改 | 新增 `_migrate_numeric_fields()` 迁移函数 |
| `backend/crud/orders.py` | 修改 | Decimal运算 |
| `backend/crud/finance.py` | 修改 | Decimal运算 |
| `backend/utils.py` | 修改 | Decimal运算，0.01容差→精确比较 |

**修复的问题**：
- `schemas.py` 的 `ProductBase.sku` 原为 `str = Field(...)`（必填），但数据库有 `sku=NULL` 的记录导致500错误。已改为 `Optional[str] = Field(default=None)`

**验证结果**：
- `models.py` 中 `Column(Float` = 0处 ✅
- `models.py` 中 `Numeric(12,2)` = 30处 ✅
- 数据库迁移成功（"Float→Numeric 迁移: 已完成，跳过"） ✅
- 资产负债表精确平衡：462.97 = 0 + 462.97（无需容差比较） ✅
- API返回的金额字段为字符串格式（Decimal的Pydantic序列化行为） ✅

**⚠️ 注意事项**：
- Decimal字段在Pydantic序列化时输出为字符串（如 `"99.99"` 而非 `99.99`），这是正确行为（保证精度）
- 前端现有代码用 `parseFloat()` 解析金额，字符串格式兼容无需改动
- `Numeric(12,2)` 在SQLite中存储为TEXT类型（SQLite的decimal模式），功能完全正常

---

## 待实施阶段

### P2：枚举单一真相源 ⏳（下一个优先）

**状态**：未开始 | 工作量：1天 | 风险：低 | 可独立实施

**核心任务**：
1. `enums.py` 补全状态枚举类（OrderStatus, PaymentStatus, PaymentMethod等8个类）
2. 新增 `ENUM_LABELS` 中文标签映射 + `ALL_ENUMS` 导出映射
3. `/api/enums` 端点扩展，返回 `values` + `labels`
4. 后端全局替换硬编码枚举字符串（`== "completed"` → `== OrderStatus.COMPLETED`）
5. 前端 `stores/enums.js` Pinia store

**方案文档**：`docs/架构升级/03-P2-枚举统一.md`

### P3：Schema拆分 ⏳

**状态**：未开始 | 工作量：1天 | ⚠️ 需P1先行（已完成） | 纯结构重构

**核心任务**：`schemas.py` 686行→13个领域文件 + `__init__.py`统一导出

**方案文档**：`docs/架构升级/04-P3-Schema拆分.md`

### P4：命令模式 ⏳

**状态**：未开始 | 工作量：3天 | ❌ 依赖P0(✅)+P5(未开始)

**核心任务**：每个业务操作封装为Command类 + Dispatcher + Router极简化

**方案文档**：`docs/架构升级/05-P4-命令模式.md`

### P5：领域事件v2 ⏳

**状态**：未开始 | 工作量：2天 | ⚠️ 依赖P0(✅)

**核心任务**：EventBus中间件链 + 优先级 + 条件过滤 + 不变量自动校验

**方案文档**：`docs/架构升级/06-P5-领域事件v2.md`

### P6：领域模型 ⏳

**状态**：未开始 | 工作量：3天 | ❌ 依赖P0(✅)+P1(✅)+P4+P5

**核心任务**：Money值对象 + 状态机 + Domain.from_orm() + Repository升级

**方案文档**：`docs/架构升级/07-P6-领域模型.md`

### P7：前端重构 ⏳

**状态**：未开始 | 工作量：4天 | ⚠️ 部分依赖P2

**核心任务**：Pinia store + API响应校验 + Composable + 组件<200行

**方案文档**：`docs/架构升级/08-P7-前端重构.md`

---

## 依赖关系速查

```
✅ P0 ──→ P4 ──→ P6
            ↑        ↑
⏳ P5 ──→─┘───────┘

✅ P1 ──────→ P6(Money依赖Numeric)
  ↕ 冲突
⏳ P3(都改schemas，P1先P3后 ✅)

⏳ P2 ──→ P5(handlers用枚举常量)
  └──→ P7(Pinia枚举store)
```

---

## 关键约定

1. **强制工作流程**：写方案 → 审查 → 修正 → 再审查 → 执行 → 测试 → 更新文档
2. **方案文档位置**：`docs/架构升级/00~08-*.md`，每个阶段独立文件
3. **总览文档**：`docs/架构升级/00-总览与诊断.md`
4. **后端服务启动**：`cd backend && python -m uvicorn main:app --host 0.0.0.0 --port 8000`
5. **数据库位置**：`backend/inventory.db`（已有 `inventory.db.pre_numeric_backup` 备份）
6. **当前服务状态**：后端服务运行在 localhost:8000，所有已实现API正常

---

## 当前数据库状态

- SQLite，路径：`backend/inventory.db`
- Numeric迁移已完成，所有金额字段为 `NUMERIC(12,2)`
- 备份文件：`backend/inventory.db.pre_numeric_backup`
- 迁移幂等：重复运行 `init_db()` 安全（已迁移则跳过）

---

## 潜在风险和已知问题

1. **Decimal序列化**：Pydantic将Decimal序列化为字符串（`"99.99"`），前端 `parseFloat()` 可正常解析，但新增前端代码应使用 `Number()` 或 `parseFloat()` 处理
2. **sku字段**：`ProductBase.sku` 已改为 `Optional`，但创建商品时仍建议必填（数据库层面有NOT NULL约束的历史数据可能为NULL）
3. **P1和P3冲突**：P1已改完schemas.py内容，P3拆分目录时以当前schemas.py为基准
4. **db.refresh()**：必须在 `unit_of_work` 块外调用（commit后才能refresh），P0改造已遵守此规则