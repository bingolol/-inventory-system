# P1：Float→Numeric金额字段

> 阶段：P1 | 工作量：1.5天 | 风险：低 | 收益：消除浮点误差
>
> **前置依赖**：无（可独立实施）
>
> **冲突警告**：P1和P3都修改 `schemas.py`。若并行实施，P1先改schemas.py的float→Decimal，P3再拆分目录，顺序不能反。
>
> **与P6的关系**：P6的Money值对象是P1的终极形态。P1阶段先用原生Decimal，P6阶段再封装为Money类，不冲突。

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

- 所有金额字段从 `Float` 改为 `Numeric(12,2)`
- Python层用 `Decimal` 运算，消除浮点累积误差
- 迁移过程不丢失数据精度

## models.py 字段类型替换

```python
# 改造前：
total_price = Column(Float, default=0)

# 改造后：
from sqlalchemy import Numeric
total_price = Column(Numeric(12, 2), default=Decimal('0'))
```

需替换30+个字段：

| 模型 | 字段 |
|------|------|
| Product | purchase_price, sale_price |
| PurchaseOrder | total_price |
| PurchaseItem | unit_price, tax_rate, total_price |
| SaleOrder | total_price |
| SaleItem | unit_price, tax_rate, total_price |
| Invoice | tax_rate, amount_without_tax, tax_amount, amount_with_tax |
| Project | total_income, total_cost, profit |
| ProjectCost | amount |
| ProjectIncome | amount, received_amount |
| Expense | amount |
| OpeningBalance | cash_balance, bank_balance, accounts_receivable, inventory_value, accounts_payable, tax_payable, retained_earnings |
| CashFlowTransaction | amount |
| PersonalTransaction | amount |

## schemas.py Float→Decimal

```python
# 改造前：
purchase_price: float = 0

# 改造后：
purchase_price: Decimal = Field(default=Decimal('0'), max_digits=12, decimal_places=2)
```

## Python层Decimal运算

| 文件 | 函数 | 改造点 |
|------|------|--------|
| `crud/orders.py` | `_distribute_total_price` | round()→Decimal运算 |
| `crud/orders.py` | `create_purchase_order` / `create_sale_order` | line_total计算 |
| `crud/finance.py` | `generate_balance_sheet` / `generate_income_statement` | 全部金额运算 |
| `utils.py` | `update_project_summary` / `verify_invariants` | round()→Decimal，0.01容差→精确比较 |

## 数据库迁移策略

SQLite不支持 `ALTER TABLE ALTER COLUMN`，需重建表：

```python
# database.py 新增迁移函数
def _migrate_numeric_fields(engine):
    """Float→Numeric(12,2) 迁移"""
    insp = inspect(engine)
    cols = [c for c in insp.get_columns("purchase_orders") if c["name"] == "total_price"]
    if cols and str(cols[0]["type"]).startswith("NUMERIC"):
        return  # 已迁移

    # 安全方案：备份 → 创建新表结构 → INSERT INTO ... SELECT → DROP旧表 → RENAME
    import shutil
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "inventory.db")
    backup_path = db_path + ".pre_numeric_backup"
    if not os.path.exists(backup_path):
        shutil.copy2(db_path, backup_path)
        logger.info(f"迁移前备份: {backup_path}")

    with engine.connect() as conn:
        # 对每个受影响的表：
        # 1. CREATE TABLE {table}_new (... Numeric字段 ...)
        # 2. INSERT INTO {table}_new SELECT * FROM {table}
        # 3. DROP TABLE {table}
        # 4. ALTER TABLE {table}_new RENAME TO {table}
        pass

    import models
    Base.metadata.create_all(bind=engine)  # 补全约束和索引
```

## 验证方式

1. 运行 `verify_invariants` API，确认三大不变量无违规
2. 创建销售单→检查金额是否精确到分
3. 生成资产负债表→确认资产=负债+权益（无需容差比较）

## 检查清单

- [x] `models.py` 所有Float金额字段→Numeric(12,2)
- [x] `schemas.py` 所有float金额字段→Decimal（含报表schema）
- [x] `database.py` 新增 `_migrate_numeric_fields` 迁移函数（幂等+备份+RENAME重建）
- [x] `crud/orders.py` Decimal运算（_d()安全转换+Q2量化+_distribute_total_price）
- [x] `crud/finance.py` Decimal运算（_d()包装sqlfunc.sum+精确!=比较+quantize）
- [x] `crud/invoices.py` Decimal运算（get_tax_report中round→Decimal）
- [x] `crud/personal.py` Decimal运算（round→quantize+_d()安全转换）
- [x] `utils.py` Decimal运算（update_project_summary+verify_invariants精确比较）
- [x] `routers/income_tax.py` Decimal运算（round→quantize+_d()包装sqlfunc.sum）
- [x] `routers/tax.py` Decimal运算（累加器初始化Decimal('0')+quantize）
- [x] `routers/reconciliations.py` Decimal运算（sum(..., Decimal('0'))+quantize+_d()）
- [x] `routers/reports.py` Decimal运算（sum(..., Decimal('0'))+quantize）
- [x] `routers/invoices.py` Decimal运算（quick_create/upload中金额计算+Form参数Decimal化）
- [x] `routers/personal.py` Decimal运算（round→quantize+_d()）
- [x] verify_invariants 无违规
- [x] 创建采购单→金额精确到分（166.65 == 166.65）
- [x] 资产负债表确认精确平衡（资产=负债+权益，无需容差）