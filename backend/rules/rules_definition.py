"""15 条会计准则规则定义

AS-01~AS-07 会计实务基石(《小企业会计准则》及业务因果链)
AS-08~AS-15 系统实现约定(数据链层级、Writer 唯一等)

每条规则通过 Rule(...) 实例化自动注册到全局 RULES。
"""
from .dsl import (
    Rule,
    SEVERITY_ERROR,
    SEVERITY_WARNING,
    CATEGORY_ACCOUNTING,
    CATEGORY_IMPLEMENTATION,
)


def load_all_rules() -> int:
    """加载所有规则定义(通过 import 触发模块级 Rule 实例化)

    返回规则数量。
    """
    # Rule 实例在模块加载时已注册,此处仅返回计数
    from . import rules_definition  # noqa: F401  触发注册
    from .dsl import RULES
    return len(RULES)


# ═══════════════════════════════════════════════════════════════
# 一、会计实务基石 (AS-01 ~ AS-07)
# ═══════════════════════════════════════════════════════════════

Rule(
    id="AS-01",
    name="借贷平衡与资产负债恒等式",
    source="《小企业会计准则》资产负债表恒等式;《会计基础工作规范》第五十一条;业务因果链 O1",
    trigger="凭证过账(JournalEngine.post)及报表生成(generate_balance_sheet)",
    expected_chain="L2(AccountMoveLine.debit_l2/credit_l2) → L4(LedgerAccountBalance.balance_l4 → BS total_assets/total_liabilities/total_equity)",
    invariants=[
        "每张凭证: Σ(debit_l2) == Σ(credit_l2)",
        "期末: total_assets == total_liabilities + total_equity (误差 ≤ 0.01)",
        "反向凭证 date_l1 == 原凭证 date_l1 (避免 cutoff 漏一面)",
    ],
    prohibited=[
        "借贷不平的凭证过账",
        "BS 报表读 L4 缓存而非 L2 真相源",
    ],
    severity=SEVERITY_ERROR,
    category=CATEGORY_ACCOUNTING,
    related_fields=[
        "AccountMoveLine.debit_l2",
        "AccountMoveLine.credit_l2",
        "LedgerAccountBalance.balance_l4",
    ],
)

Rule(
    id="AS-02",
    name="价税分离",
    source="《小企业会计准则》§二/2.4 增值税;系统设计决策",
    trigger="发票创建(calculate_invoice_amounts)及采购/销售过账",
    expected_chain="L1(Invoice.amount_with_tax_l1, InvoiceItem.tax_rate_l1) → L2(amount_without_tax, tax_amount)",
    invariants=[
        "amount_without_tax + tax_amount == amount_with_tax",
        "amount_without_tax = amount_with_tax ÷ (1 + tax_rate)",
        "tax_rate 从 InvoiceItem.tax_rate_l1 读取,非硬编码",
    ],
    prohibited=[
        "硬编码 Decimal('0.13') 估算税额",
        "税率从 Product 静态字段读取而非行项 tax_rate_l1",
    ],
    severity=SEVERITY_ERROR,
    category=CATEGORY_ACCOUNTING,
    related_fields=[
        "Invoice.amount_with_tax_l1",
        "InvoiceItem.tax_rate_l1",
    ],
)

Rule(
    id="AS-03",
    name="移动加权平均法",
    source="《小企业会计准则》§一/1.3;BR-7;单一真相源原则 §3.1;设计决策 D-9",
    trigger="入库(InventoryEngine.inbound)/出库(outbound)/退货(reverse)",
    expected_chain="L1(PurchaseItem.unit_price_l1) → L2(StockMove.unit_cost_l2, SaleItem.unit_cost_l2) → L4(Inventory.average_cost_l4 仅缓存)",
    invariants=[
        "入库后: average_cost_l4 = (old_total_value + new_cost) / (old_qty + new_qty)",
        "出库: SaleItem.unit_cost_l2 锁定当时的 average_cost (只读 @property)",
        "退货: 反向 StockMove.unit_cost_l2 必须用原 StockMove.unit_cost_l2,非当前 average_cost_l4",
        "Inventory.total_value_l4 == Σ(方向 × StockMove.total_cost_l2)",
    ],
    prohibited=[
        "退货用 Inventory.average_cost_l4 冲回成本",
        "SaleItem.unit_cost 被外部 UPDATE",
    ],
    severity=SEVERITY_ERROR,
    category=CATEGORY_ACCOUNTING,
    related_fields=[
        "StockMove.unit_cost_l2",
        "StockMove.total_cost_l2",
        "Inventory.average_cost_l4",
        "Inventory.total_value_l4",
    ],
)

Rule(
    id="AS-04",
    name="权责发生制",
    source="《小企业会计准则》第五十九条、第六十条;业务因果链 A3/A4/A5",
    trigger="销售过账(FinanceEngine.record_sale)及收入确认",
    expected_chain="L1(Invoice.issue_date, SaleOrder.sale_date_l1) → L2(record_sale 过账 6001) → L4(LedgerAccountBalance 6001 贷方发生额)",
    invariants=[
        "发货+开票即确认收入+销项税+应收账款",
        "预收款是负债(2203 预收账款),发货时才转收入",
        "期间收入取 LedgerAccountBalance(6001) 贷方发生额,非 Σ(SaleOrder.total_price)",
    ],
    prohibited=[
        "报表期间收入读 Σ(SaleOrder.total_price) 而非总账 6001",
        "预收款直接确认收入",
    ],
    severity=SEVERITY_ERROR,
    category=CATEGORY_ACCOUNTING,
    related_fields=[
        "SaleOrder.sale_date_l1",
        "AccountMoveLine.credit_l2",
    ],
)

Rule(
    id="AS-05",
    name="折旧与摊销(当月增下月提 vs 当月增当月摊)",
    source="《小企业会计准则》第三十一条;BR-12;业务因果链 F2/G2",
    trigger="月结 batch_depreciate 及 FixedAssetEngine.record_depreciation",
    expected_chain="L1(FixedAsset.original_value_l1, start_date_l1) + L3(salvage_rate_l3, useful_life_l3) → L2(FixedAssetDepreciation.amount_l2) → L4(accumulated_depreciation_l4)",
    invariants=[
        "固定资产: 当月增加,下月提折旧",
        "无形资产: 当月增加,当月摊销;处置当月不再摊销",
        "月折旧额 = original_value_l1 × (1 - salvage_rate_l3) ÷ useful_life_l3 (useful_life_l3 为月数)",
        "累计折旧上限 = original_value_l1 × (1 - salvage_rate_l3)",
    ],
    prohibited=[
        "固定资产当月增当月提",
        "无形资产当月增下月摊",
        "折旧超原值×(1-残值率)",
    ],
    severity=SEVERITY_ERROR,
    category=CATEGORY_ACCOUNTING,
    related_fields=[
        "FixedAsset.original_value_l1",
        "FixedAsset.salvage_rate_l3",
        "FixedAsset.useful_life_l3",
        "FixedAssetDepreciation.amount_l2",
        "FixedAsset.accumulated_depreciation_l4",
    ],
)

Rule(
    id="AS-06",
    name="增值税红字冲减",
    source="BR-18;业务因果链 C1/D3;《会计基础工作规范》第五十一条",
    trigger="退货/折让(ReverseInvoice, ReturnSaleOrder, ReturnPurchaseOrder)",
    expected_chain="L1(红字 Invoice.amount_with_tax_l1 为负) → L2(反向凭证冲减 6001/222101/1122) + InventoryEngine.reverse() 库存回退",
    invariants=[
        "红字发票 amount_without_tax < 0, tax_amount < 0",
        "红字发票级联冲减收入/销项税/应收/库存",
        "销售退货 COGS 冲回用原 StockMove.unit_cost_l2",
    ],
    prohibited=[
        "退货不开红字发票(导致季度报税销项税虚高)",
        "红字发票金额为正数",
    ],
    severity=SEVERITY_ERROR,
    category=CATEGORY_ACCOUNTING,
    related_fields=[
        "Invoice.amount_with_tax_l1",
        "StockMove.unit_cost_l2",
    ],
)

Rule(
    id="AS-07",
    name="固定资产处置损益入营业外收支",
    source="业务因果链 F3;BR-23;《小企业会计准则》(小企业简化处理)",
    trigger="固定资产处置(FixedAssetEngine.record_disposal)",
    expected_chain="L1(FixedAsset.original_value_l1 + 处置收入) + L4(accumulated_depreciation_l4) → L2(凭证过账到 6301/6701)",
    invariants=[
        "处置价 > 净值 → 营业外收入(6301)",
        "处置价 < 净值 → 营业外支出(6701)",
        "现金流归投资活动,非经营活动",
        "反向凭证 date_l1 == 原处置 date_l1 (AS-15 同源)",
    ],
    prohibited=[
        "使用 6111 资产处置收益 / 6711 资产处置损失科目",
        "处置现金流归经营活动",
    ],
    severity=SEVERITY_ERROR,
    category=CATEGORY_ACCOUNTING,
    related_fields=[
        "FixedAsset.original_value_l1",
        "FixedAsset.accumulated_depreciation_l4",
    ],
)

# ═══════════════════════════════════════════════════════════════
# 二、系统实现约定 (AS-08 ~ AS-15)
# ═══════════════════════════════════════════════════════════════

Rule(
    id="AS-08",
    name="字段层级单调(L4 禁作下游真相源)",
    source="系统设计决策;单一真相源原则 §一;project_memory TS02/TS03/TS04",
    trigger="装饰器注册表校验(validate_invariants)及报表读取",
    expected_chain="L1 → L2 → L4 (单调递增,禁止回写)",
    invariants=[
        "无 L4 → L1/L2/L3 路径 (TS03)",
        "L4 派生字段仅用于输出展示,不可作为下游真相源 (TS02)",
        "L1 → L4 跳层需警告 (TS04)",
    ],
    prohibited=[
        "L4 字段被 @reads 引用作为下游真相源",
        "层级回写(writer tier < reader tier)",
    ],
    severity=SEVERITY_ERROR,
    category=CATEGORY_IMPLEMENTATION,
    related_fields=[
        "Inventory.quantity_l4",
        "Inventory.average_cost_l4",
        "Inventory.total_value_l4",
        "LedgerAccountBalance.balance_l4",
        "FixedAsset.accumulated_depreciation_l4",
        "BankAccount.balance_l4",
    ],
)

Rule(
    id="AS-09",
    name="Writer 唯一 + 不可变真相源",
    source="单一真相源原则 §3.1/§3.2/§3.3;BR-7;BR-8",
    trigger="装饰器注册表校验(TS01)及数据库触发器",
    expected_chain="L2(StockMove/AccountMove/FixedAssetDepreciation 写入层)",
    invariants=[
        "每个真相源字段只有一个 writer 类 (TS01 跨类唯一)",
        "StockMove/AccountMove/FixedAssetDepreciation 一旦写入禁止 UPDATE",
        "SaleItem.unit_cost_l2 用 @property 只读 + set_calculated_cost()",
    ],
    prohibited=[
        "跨类多个 writer 写同一 L2 字段 (双算法)",
        "UPDATE StockMove/AccountMove/FixedAssetDepreciation 已存记录",
    ],
    severity=SEVERITY_ERROR,
    category=CATEGORY_IMPLEMENTATION,
    related_fields=[
        "StockMove.unit_cost_l2",
        "AccountMoveLine.debit_l2",
        "AccountMoveLine.credit_l2",
        "FixedAssetDepreciation.amount_l2",
    ],
)

Rule(
    id="AS-10",
    name="L4 字段报表禁读",
    source="系统设计决策;project_memory TS02 已知违规清单",
    trigger="报表/CRUD 函数读取 L4 字段时",
    expected_chain="报表应读 L1/L2 真相源,禁读 L4 派生缓存",
    invariants=[
        "list_inventory/get_stock_alerts 禁读 Inventory.quantity_l4 (已修复,读 StockMove.quantity_l1 聚合)",
        "balance_sheet 禁读 BankAccount.balance_l4 (已修复,读 L2)",
        "get_overview 禁读 Inventory.total_value_l4/quantity_l4 (已修复,读 StockMove 聚合)",
    ],
    prohibited=[
        "crud/products.py 读 Inventory.quantity_l4 (已修复)",
    ],
    severity=SEVERITY_ERROR,
    category=CATEGORY_IMPLEMENTATION,
    related_fields=[
        "Inventory.quantity_l4",
        "Inventory.total_value_l4",
        "BankAccount.balance_l4",
        "FixedAsset.accumulated_depreciation_l4",
    ],
)

Rule(
    id="AS-11",
    name="退货成本溯源到原 StockMove",
    source="设计决策 D-9;BR-7;单一真相源原则 §2.1",
    trigger="销售退货(ReturnSaleOrderHandler)/采购退货(ReturnPurchaseOrderHandler)",
    expected_chain="L2(原 StockMove.unit_cost_l2 历史快照)",
    invariants=[
        "销售退货 COGS 冲回 = 原 StockMove.unit_cost_l2 × 退货数量",
        "采购退货库存贷方 = 原发票 PurchaseItem.unit_price_l1 × 退货数量",
        "反向 StockMove.total_cost_l2 = 原入库 total_cost_l2 / 原数量 × 退货数量",
    ],
    prohibited=[
        "用 Inventory.average_cost_l4 冲回退货成本",
        "用 original.unit_cost(移动加权平均) 而非 total_cost/quantity",
    ],
    severity=SEVERITY_ERROR,
    category=CATEGORY_IMPLEMENTATION,
    related_fields=[
        "StockMove.unit_cost_l2",
        "StockMove.total_cost_l2",
        "Inventory.average_cost_l4",
    ],
)

Rule(
    id="AS-12",
    name="报税数据源单一(发票汇总,禁硬编码)",
    source="BR-1;BR-4;单一真相源原则 §2.2",
    trigger="增值税申报(calculate_vat, generate_vat_declaration)",
    expected_chain="L1(Invoice.tax_amount_l1, InvoiceItem.tax_rate_l1) + L3(Account.taxpayer_type_l3) → L2(AccountingEngine.calculate_vat 输出)",
    invariants=[
        "销项税额 = Σ(Invoice.tax_amount_l1 WHERE direction=OUT)",
        "进项税额 = Σ(Invoice.tax_amount_l1 WHERE direction=IN AND certified AND special)",
        "税率从 Account.taxpayer_type_l3 推导或 InvoiceItem.tax_rate_l1 读取",
    ],
    prohibited=[
        "total_revenue × Decimal('0.13') 硬编码估算销项税",
        "无票收入强制计提销项税 (BR-4 故意设计不强制)",
    ],
    severity=SEVERITY_ERROR,
    category=CATEGORY_IMPLEMENTATION,
    related_fields=[
        "Invoice.tax_amount_l1",
        "InvoiceItem.tax_rate_l1",
        "Account.taxpayer_type_l3",
    ],
)

Rule(
    id="AS-13",
    name="危险操作拦截 + 库存调整必填原因",
    source="BR-19;BR-20",
    trigger="DELETE 请求 / /reverse 接口 / 库存调整(delta != 0)",
    expected_chain="L1/L2 写入拦截层(覆盖所有写操作)",
    invariants=[
        "已过账数据 DELETE 被 readonly_middleware 拦截(403)",
        "/reverse 接口受 confirm_middleware 二次确认",
        "库存调整 delta != 0 时 reason 必填",
    ],
    prohibited=[
        "直接 DELETE 已过账的 StockMove/AccountMove",
        "库存调整 reason 为空",
        "AI 自动确认危险操作(必须用户确认)",
    ],
    severity=SEVERITY_ERROR,
    category=CATEGORY_IMPLEMENTATION,
    related_fields=[],
)

Rule(
    id="AS-14",
    name="服务产品不扣库存",
    source="系统设计决策;models.py Product 字段注释;templates/02_products.py",
    trigger="销售/采购含 track_inventory_l3=False 的商品",
    expected_chain="L3(Product.track_inventory_l3=False) → 跳过 InventoryEngine 调用",
    invariants=[
        "track_inventory_l3=False 的商品销售不触发库存出入库",
        "维修服务/咨询费/技术服务/租赁费/运费等应设 track_inventory_l3=False",
    ],
    prohibited=[
        "服务类商品设 track_inventory_l3=True (导致 INVENTORY_INSUFFICIENT)",
        "track_inventory_l3=False 的商品仍调用 InventoryEngine",
    ],
    severity=SEVERITY_ERROR,
    category=CATEGORY_IMPLEMENTATION,
    related_fields=[
        "Product.track_inventory_l3",
    ],
)

Rule(
    id="AS-15",
    name="冲红凭证日期与原凭证一致",
    source="设计决策 D-8;BR-22",
    trigger="反向凭证(reverse_journal, InventoryEngine.reverse, dispose)",
    expected_chain="L1(原 AccountMove.date_l1) → L2(反向凭证同日期写入)",
    invariants=[
        "反向 AccountMove.date_l1 == 原凭证 date_l1",
        "反向 StockMove.move_date_l1 == 原单据业务日期",
        "处置 FixedAsset.disposal_date 同类处理",
    ],
    prohibited=[
        "反向凭证用 date.today() 作为日期",
        "反向 StockMove 用当前日期而非原单据日期",
    ],
    severity=SEVERITY_ERROR,
    category=CATEGORY_IMPLEMENTATION,
    related_fields=[
        "AccountMove.date_l1",
        "StockMove.move_date_l1",
    ],
)

# ═══════════════════════════════════════════════════════════════
# 三、系统边界声明 (AS-22)
# ═══════════════════════════════════════════════════════════════

Rule(
    id="AS-22",
    name="显式不支持场景边界声明",
    source="用户决策 2026-07-02;业务因果链边界审查;project_memory 显式不实现清单",
    trigger="静态扫描(validator._check_as22)及运行时 API 调用",
    expected_chain="不支持场景的模型(PurchaseEstimate/BadDebt)不应被 commands/routers 引用;API 层遇不支持操作返回 501",
    invariants=[
        "B2 暂估入库:PurchaseEstimate 模型存在但无 commands 层引用",
        "I 坏账核销:BadDebt 模型存在但无 commands 层引用",
        "A5 分期收款销售:无模型、无命令、无路由",
        "B3 在途物资:无 1402 科目、无模型",
        "D2 现金折扣:无自动入账逻辑",
        "D3 销售折让:无独立流程(可用红字发票手工模拟)",
        "N 长期待摊费用:无 1801 科目、无模型",
    ],
    prohibited=[
        "为不支持场景创建 commands 层 Handler",
        "为不支持场景创建 routers 层端点",
        "AI 向用户声称系统支持这些场景",
    ],
    severity=SEVERITY_WARNING,
    category=CATEGORY_IMPLEMENTATION,
    related_fields=[
        "PurchaseEstimate",
        "BadDebt",
    ],
)
