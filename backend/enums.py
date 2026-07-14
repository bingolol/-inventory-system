# 枚举单一真相源：所有分类枚举在此定义，前后端共享

# ── 分类枚举（已有）──

# 费用类别（公司账本）
EXPENSE_CATEGORIES = ["房租", "水电", "工资", "材料", "办公用品", "运费", "维修", "税金及附加", "所得税", "其他"]

# 费用功能分类（小企业会计准则）
EXPENSE_FUNCTIONAL_CATEGORIES = ["销售费用", "管理费用", "财务费用", "税金及附加"]

# 固定资产折旧方法
DEPRECIATION_METHODS = ["年限平均法", "双倍余额递减法", "年数总和法"]

# 固定资产状态
ASSET_STATUS = ["在用", "停用", "报废", "已冲红"]

# 无形资产状态
INTANGIBLE_ASSET_STATUS = ["使用中", "已报废"]

# 个人支出类别
PERSONAL_EXPENSE_CATEGORIES = ["餐饮", "日用", "交通", "娱乐", "医疗", "烟酒", "其他"]

# 个人收入类别
PERSONAL_INCOME_CATEGORIES = ["工资", "兼职", "理财", "其他"]

# 个人流水交易类型
PERSONAL_TRANSACTION_TYPES = ["income", "expense"]

# ── 状态枚举（新增）──


class TaxpayerType:
    SMALL_SCALE = "small_scale"
    GENERAL = "general"
    SMALL_MICRO = "small_micro"


class OrderStatus:
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PaymentStatus:
    PAID = "paid"
    UNPAID = "unpaid"
    PENDING = "pending"
    PARTIAL = "partial"


class PaymentMethod:
    COMPANY = "company"
    PRIVATE_ADVANCE = "private_advance"


class InvoiceDirection:
    IN = "in"
    OUT = "out"


class InvoiceType:
    ORDINARY = "ordinary"
    SPECIAL = "special"


class CertificationStatus:
    PENDING = "pending"
    CERTIFIED = "certified"
    N_A = "n_a"


class InvoiceStatus:
    INVOICED = "已开"
    NOT_INVOICED = "未开"
    NOT_NEEDED = "不需开"


class FlowCategory:
    OPERATING = "operating"
    INVESTING = "investing"
    FINANCING = "financing"


class TransactionType:
    INFLOW = "inflow"
    OUTFLOW = "outflow"


class OrderType:
    RETAIL = "retail"                  # 零售型销售单/采购单


class PersonalAdvanceStatus:
    """个人垫付还款状态"""
    UNPAID = "unpaid"          # 未偿还
    PARTIAL = "partial"        # 部分偿还
    PAID = "paid"              # 已还清


# 个人垫付借方科目白名单（创建垫付时 debit_account_code 只能取这里）
# 含义：垫付的资金被用于什么用途 → 决定借方科目
#   6601 管理费用 — 日常零星费用（默认，最常见）
#   6602 销售费用 — 销售相关支出
#   1405 库存商品 — 垫付采购货款（货已入库但款由个人付）
#   1601 固定资产 — 垫付购买固定资产
#   1701 无形资产 — 垫付购买无形资产
#   222103 应交增值税-小规模 — 个人垫付代缴增值税（贷2241其他应付款）
#   222105 应交所得税 — 个人垫付代缴所得税（贷2241其他应付款）
#   222110 应交城市维护建设税 — 个人垫付代缴城建税（贷2241其他应付款）
#   1221 其他应收款 — 多缴所得税挂账（待退税/抵扣，贷2241其他应付款）
#   6711 营业外支出-税收滞纳金 — 个人垫付代缴滞纳金（贷2241其他应付款）
PERSONAL_ADVANCE_DEBIT_ACCOUNTS = [
    "6601", "6602", "1405", "1601", "1701",  # 费用/资产
    "222103", "222105", "222107", "222110",  # 应交税费（个人垫付代缴税: 小规模增值税/所得税/未交增值税/城建税）
    "1221", "6711",                          # 其他应收款(多缴税挂账)/营业外支出(滞纳金)
]


# ── 中文标签映射（前端展示用）──
ENUM_LABELS = {
    "order_status": {
        OrderStatus.PENDING: "待处理",
        OrderStatus.COMPLETED: "已完成",
        OrderStatus.CANCELLED: "已取消",
    },
    "payment_status": {
        PaymentStatus.PAID: "已支付",
        PaymentStatus.UNPAID: "未支付",
        PaymentStatus.PENDING: "待确认",
        PaymentStatus.PARTIAL: "部分支付",
    },
    "payment_method": {
        PaymentMethod.COMPANY: "公司",
        PaymentMethod.PRIVATE_ADVANCE: "个人垫付",
    },
    "invoice_status": {
        InvoiceStatus.INVOICED: "已开",
        InvoiceStatus.NOT_INVOICED: "未开",
        InvoiceStatus.NOT_NEEDED: "不需开",
    },
    "invoice_direction": {
        InvoiceDirection.IN: "进项",
        InvoiceDirection.OUT: "销项",
    },
    "invoice_type": {
        InvoiceType.ORDINARY: "普通发票",
        InvoiceType.SPECIAL: "专用发票",
    },
    "certification_status": {
        CertificationStatus.PENDING: "待认证",
        CertificationStatus.CERTIFIED: "已认证",
        CertificationStatus.N_A: "不适用",
    },
    "flow_category": {
        FlowCategory.OPERATING: "经营活动",
        FlowCategory.INVESTING: "投资活动",
        FlowCategory.FINANCING: "筹资活动",
    },
    "taxpayer_type": {
        TaxpayerType.SMALL_SCALE: "小规模纳税人",
        TaxpayerType.GENERAL: "一般纳税人",
        TaxpayerType.SMALL_MICRO: "小型微利企业",
    },
    "order_type": {
        OrderType.RETAIL: "零售",
    },
    "personal_advance_status": {
        PersonalAdvanceStatus.UNPAID: "未偿还",
        PersonalAdvanceStatus.PARTIAL: "部分偿还",
        PersonalAdvanceStatus.PAID: "已还清",
    },
}

# ── 枚举导出映射（供 /api/enums 使用）──
ALL_ENUMS = {
    "expense_categories": EXPENSE_CATEGORIES,
    "expense_functional_categories": EXPENSE_FUNCTIONAL_CATEGORIES,
    "depreciation_methods": DEPRECIATION_METHODS,
    "asset_status": ASSET_STATUS,
    "intangible_asset_status": INTANGIBLE_ASSET_STATUS,
    "personal_expense_categories": PERSONAL_EXPENSE_CATEGORIES,
    "personal_income_categories": PERSONAL_INCOME_CATEGORIES,
    "order_status": [OrderStatus.PENDING, OrderStatus.COMPLETED, OrderStatus.CANCELLED],
    "payment_status": [PaymentStatus.PAID, PaymentStatus.UNPAID, PaymentStatus.PENDING, PaymentStatus.PARTIAL],
    "payment_method": [PaymentMethod.COMPANY, PaymentMethod.PRIVATE_ADVANCE],
    "invoice_direction": [InvoiceDirection.IN, InvoiceDirection.OUT],
    "invoice_type": [InvoiceType.ORDINARY, InvoiceType.SPECIAL],
    "certification_status": [CertificationStatus.PENDING, CertificationStatus.CERTIFIED, CertificationStatus.N_A],
    "invoice_status": [InvoiceStatus.INVOICED, InvoiceStatus.NOT_INVOICED, InvoiceStatus.NOT_NEEDED],
    "flow_category": [FlowCategory.OPERATING, FlowCategory.INVESTING, FlowCategory.FINANCING],
    "personal_transaction_type": PERSONAL_TRANSACTION_TYPES,
    "taxpayer_type": [TaxpayerType.SMALL_SCALE, TaxpayerType.GENERAL, TaxpayerType.SMALL_MICRO],
    "order_type": [OrderType.RETAIL],
    "personal_advance_status": [PersonalAdvanceStatus.UNPAID, PersonalAdvanceStatus.PARTIAL, PersonalAdvanceStatus.PAID],
    "personal_advance_debit_accounts": PERSONAL_ADVANCE_DEBIT_ACCOUNTS,
}