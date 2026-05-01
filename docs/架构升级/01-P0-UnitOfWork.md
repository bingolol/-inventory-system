# P0：统一事务边界（Unit of Work）

> 阶段：P0 | 工作量：1.5天 | 风险：低 | 收益：消除数据损坏根因
>
> **前置依赖**：无（可独立实施）
>
> **被依赖**：P4(Command)、P5(Event)、P6(Domain) 均依赖 `uow.py`

---

## ⚠️ 强制工作流程

```
1. 写方案    → 从架构视角出发，输出简洁优雅的代码方案（涉及哪些文件、改什么、怎么改）
2. 代码审查  → 语法检查 + 逻辑检查 + 架构检查，确保方案无遗漏无错误
3. 修正方案  → 根据审查结果修正方案
4. 再次审查  → 修正后的方案再次审查语法+逻辑+架构，确认无问题
5. 执行修改  → 按修正后的方案改代码
6. 测试验证  → 对更新过的功能和模块进行实际测试，确保100%落地无bug
7. 通过后更新文档进入下一个阶段
```

**禁止**：不写方案直接改代码、改完不测试就跳到下一个

---

## 目标

- 消除所有双commit
- CRUD函数只做 `flush()`，不调 `commit()`/`rollback()`
- 事务控制权统一归 `unit_of_work` 上下文管理器

## 新增文件

```
backend/
└── uow.py          # Unit of Work 上下文管理器（约30行）
```

## 实现方案

```python
# uow.py
from contextlib import contextmanager
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger("inventory")


@contextmanager
def unit_of_work(db: Session):
    """所有业务操作必须在 uow 内执行，保证单一commit点

    规则：
    1. CRUD函数只做 db.flush()，不调 commit()/rollback()
    2. with块内所有操作原子生效：全部成功或全部回滚
    3. _log() 也只做 flush()，日志与业务数据在同一事务中
    4. HTTPException 在 uow 内抛出也会触发 rollback
    """
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise


@contextmanager
def read_only(db: Session):
    """只读操作上下文：自动关闭session，不commit"""
    try:
        yield db
    finally:
        db.close()
```

## 改造清单

### 消除双commit（5处）

**文件：`routers/project_costs.py`**

以 `add_project_cost` 为例：

```python
# 改造前：
try:
    db.add(cost)
    db.flush()
    cost_deduct_inventory(db, account_id, cost, operator)
    update_project_summary(db, cost.project_id)
    db.commit()       # ← 第1次commit
    db.refresh(cost)
except ...:
    db.rollback()

crud._log(db, account_id, "create", "project_cost", cost.id, ...)
db.commit()           # ← 第2次commit（日志）

# 改造后：
with unit_of_work(db):
    db.add(cost)
    db.flush()
    cost_deduct_inventory(db, account_id, cost, operator)
    update_project_summary(db, cost.project_id)
    crud._log(db, account_id, "create", "project_cost", cost.id, ...)
db.refresh(cost)      # refresh在uow外执行（commit后才能refresh）
```

5处改造点：

| 函数 | 第一次commit行 | 第二次commit行 |
|------|---------------|---------------|
| `add_project_cost` | 73 | 85 |
| `update_project_cost` | 320 | 332 |
| `delete_project_cost` | 390 | 401 |
| `add_project_income` | 165 | 177 |
| `update_project_income` | 447 | 459 |

### CRUD函数去掉内部commit

**规则**：CRUD函数末尾的 `db.commit()` 改为 `db.flush()`，`db.rollback()` 删除（由uow统一处理），`db.refresh()` 改为在uow外执行。

| 文件 | 涉及函数数 | 改造方式 |
|------|-----------|----------|
| `crud/finance.py` | 6 | commit→flush, 删rollback |
| `crud/orders.py` | 6 | 同上 |
| `crud/invoices.py` | 全部 | 同上 |
| `crud/personal.py` | 全部 | 同上 |
| `crud/products.py` | 全部 | 同上 |
| `crud/partners.py` | 全部 | 同上 |

### 路由层统一使用uow

所有写操作路由用 `with unit_of_work(db):` 包裹：

```python
# 改造后：
@router.post("/", response_model=schemas.SaleOrderOut)
def create_sale(data, account_id=Depends(get_account_id), operator=Depends(get_operator), db=Depends(get_db)):
    try:
        with unit_of_work(db):
            order = crud.create_sale_order(db, account_id, data, operator)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    db.refresh(order)
    return _build_sale_out(order)
```

## 验证方式

1. 搜索 `db.commit()` — 应该只在 `uow.py` 中出现
2. 搜索 `db.rollback()` — 应该只在 `uow.py` 中出现
3. 运行全量API测试，确认所有写操作正常
4. 模拟异常场景（如库存不足），确认数据完全回滚

## 检查清单

- [ ] 创建 `uow.py`
- [ ] 消除 `routers/project_costs.py` 5处双commit
- [ ] `crud/finance.py` 6处内部commit改为flush
- [ ] `crud/orders.py` 6处内部commit改为flush
- [ ] `crud/invoices.py` 全部内部commit改为flush
- [ ] `crud/personal.py` 全部内部commit改为flush
- [ ] `crud/products.py` 全部内部commit改为flush
- [ ] `crud/partners.py` 全部内部commit改为flush
- [ ] 所有路由层写操作用 `with unit_of_work(db):` 包裹
- [ ] 全局搜索 `db.commit()` 确认只在 `uow.py` 中
- [ ] 全局搜索 `db.rollback()` 确认只在 `uow.py` 中