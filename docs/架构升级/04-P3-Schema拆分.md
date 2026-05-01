# P3：Schema按领域拆分

> 阶段：P3 | 工作量：1天 | 风险：低 | 收益：schema可维护
>
> **前置依赖**：无（可独立实施，纯结构重构）
>
> **冲突警告**：若P1(Numeric)同时进行，P1会修改schemas.py的float→Decimal。必须P1先改内容，P3再拆分目录。顺序：P1→P3。
>
> **独立实施说明**：拆分后通过 `__init__.py` 统一导出，现有 `import schemas` 完全兼容，不依赖任何其他阶段。

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

- `schemas.py` 686行拆分为按领域组织的多个文件
- 保持现有 `import schemas` 完全兼容

## 目标目录结构

```
backend/
└── schemas/
    ├── __init__.py          # 统一导出（保持现有import兼容）
    ├── account.py           # AccountOut
    ├── product.py           # ProductBase/Create/Update/Out
    ├── partner.py           # SupplierBase/Create/Out, CustomerBase/Create/Out
    ├── order.py             # PurchaseOrder*, SaleOrder*, PurchaseItem*, SaleItem*
    ├── invoice.py           # InvoiceBase/Create/Update/Out
    ├── project.py           # ProjectBase/Create/Update/Out
    ├── project_cost.py      # ProjectCostBase/Create/Update/Out
    ├── project_income.py    # ProjectIncomeBase/Create/Update/Out
    ├── expense.py           # ExpenseBase/Create/Update/Out
    ├── finance.py           # OpeningBalance*, CashFlow*, BalanceSheet, IncomeStatement
    ├── personal.py          # PersonalTransaction*
    └── common.py            # 分页参数、通用响应模型
```

## 兼容性保证

```python
# schemas/__init__.py — 统一导出，现有代码无需修改import
from .account import AccountOut
from .product import ProductBase, ProductCreate, ProductUpdate, ProductOut
from .partner import SupplierBase, SupplierCreate, SupplierUpdate, SupplierOut, CustomerBase, CustomerCreate, CustomerUpdate, CustomerOut
from .order import (PurchaseOrderBase, PurchaseOrderCreate, PurchaseOrderUpdate, PurchaseOrderOut,
                    SaleOrderBase, SaleOrderCreate, SaleOrderUpdate, SaleOrderOut,
                    PurchaseItemBase, SaleItemBase)
from .invoice import InvoiceBase, InvoiceCreate, InvoiceUpdate, InvoiceOut
from .project import ProjectBase, ProjectCreate, ProjectUpdate, ProjectOut
from .project_cost import ProjectCostBase, ProjectCostCreate, ProjectCostUpdate, ProjectCostOut
from .project_income import ProjectIncomeBase, ProjectIncomeCreate, ProjectIncomeUpdate, ProjectIncomeOut
from .expense import ExpenseBase, ExpenseCreate, ExpenseUpdate, ExpenseOut
from .finance import (OpeningBalanceBase, OpeningBalanceCreate, OpeningBalanceUpdate, OpeningBalanceOut,
                      CashFlowTransactionCreate, CashFlowTransactionOut)
from .personal import PersonalTransactionBase, PersonalTransactionCreate, PersonalTransactionUpdate, PersonalTransactionOut
from .common import PaginationParams, PaginatedResponse

__all__ = [
    "AccountOut", "ProductBase", "ProductCreate", "ProductUpdate", "ProductOut",
    # ... 完整列表
]
```

## 验证方式

1. `import schemas` 后，所有现有schema名称可正常访问
2. 现有路由 `import schemas` 无需修改
3. 每个schema文件 < 100行

## 检查清单

- [ ] 创建 `schemas/` 目录
- [ ] 按领域拆分13个schema文件
- [ ] `schemas/__init__.py` 统一导出
- [ ] 确认现有 `import schemas` 无需修改