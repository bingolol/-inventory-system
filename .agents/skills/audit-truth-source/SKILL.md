---
name: audit-truth-source
description: Systematically scan codebase for "truth source bypass" bugs — where reporting logic reads static master-data fields instead of engine-built actual-cost records. Use when fixing "reporting reads wrong field", "COGS/inventory value mismatch", "purchase_price vs unit_cost", "balance sheet imbalance", or after changing inventory/tax flows to ensure all downstream readers are updated.
---

# 信源审计 Skill

## 核心概念

```
引擎层写入真相源          →        报表层应读
StockMove.total_cost              Inventory.total_value (or StockMove sum)
Inventory.total_value              Inventory.total_value
SaleItem.unit_cost                 SaleItem.unit_cost (NOT Product.purchase_price)
Account.vat_rate                   All tax computations (NOT hardcoded 0.13)
```

**典型反模式**: 报表面绕过引擎建立的"实际成本账"，读了主数据的静态字段。

## 扫描流程

### 1. 扫 `purchase_price` 中毒

查所有**非 CRUD/非 Schema/非 Test** 文件中用了 `purchase_price` 做计算的地方：

```
grep -rn "purchase_price" backend/ --include="*.py"
  | grep -v "routers/products.py\|commands/product\|schemas/\|models.py\|database.py\|test_helpers"
```

每处都是潜在的 Bug B 残留。

### 2. 扫硬编码税率

```
grep -rn "Decimal(\"0\.13\")" backend/ --include="*.py"
  | grep -v "test\|models.py\|database.py"
```

每处计算税额的地方都应该检查是否应该用 `Account.vat_rate` 而非硬编码。

### 3. 扫 StockMove 符号一致性

```python
# engine_inventory.py 出库：
total_cost = out_cost           # 正数！
quantity = -out_qty             # 负数

# 报表聚合时必须处理符号：
# 存货 = sum(total_cost where quantity > 0) - sum(total_cost where quantity < 0)
# COGS = sum(total_cost where source_type='sale_order')  # total_cost 为正数
```

### 4. 扫双份 COGS 算法

一个常见陷阱：利润表有一个 COGS 计算，资产负债表为了算留存收益**又写了一份**。保证两份用同源。

```
grep -n "period_cogs\|cost_of_goods_sold" backend/crud/finance.py
```

## 修复模式

| 有问题的代码 | 替换为 |
|-------------|--------|
| `product.purchase_price` | `item.unit_cost` (加权平均出库成本) |
| `inv.quantity * product.purchase_price` | `Inventory.total_value` (库存缓存) |
| `total_cost = item_qty * rate / (1+rate)` with hardcoded 0.13 | Use `account_config['vat_rate']` |

## 验证清单

- [ ] 小规模：利润表 COGS = 实际出库数量 × 移动加权成本
- [ ] 小规模：资产负债表存货 = Inbound总成本 - Outbound总成本
- [ ] 小规模：资产负债表 A = L + E 持平
- [ ] 一般纳税人：COGS = 不含税成本（与价税分离后的inbound一致）
- [ ] `purchase_price` 只在 master data / schema / test 中出现
