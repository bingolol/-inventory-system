from sqlalchemy import Column, Integer, String, Float, Numeric, DateTime, ForeignKey, Boolean, Text, UniqueConstraint, CheckConstraint, Date, and_, event, JSON
from sqlalchemy.orm import relationship
from decimal import Decimal
from datetime import datetime
from database import Base
from enums import OrderStatus, PaymentStatus, PaymentMethod, CertificationStatus, InvoiceStatus, FlowCategory, OrderType


# 用户表：支持登录认证
class User(Base, JSON):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, comment="用户名")
    password_hash = Column(String(128), nullable=False, comment="密码哈希")
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, comment="默认账本")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)


# 账本表：支持多公司/个人记账切换
class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, comment="账本名")
    type = Column(String(20), nullable=False, default="company", comment="类型: company/personal")
    code = Column(String(50), unique=True, nullable=False, comment="代码标识: riyun=日运办公, qiaoyou=巧游电子, personal=个人")
    taxpayer_type = Column(String(20), nullable=False, default="small_scale", comment="纳税人类型: small_scale / general")
    created_at = Column(DateTime, default=datetime.now)


# 期初余额表
class OpeningBalance(Base):
    __tablename__ = "opening_balances"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True, comment="所属账本")
    date = Column(Date, nullable=False, comment="期初日期")
    
    # 流动资产类
    cash_balance = Column(Numeric(12, 2), default=Decimal('0'), comment="现金余额")
    bank_balance = Column(Numeric(12, 2), default=Decimal('0'), comment="银行存款")
    accounts_receivable = Column(Numeric(12, 2), default=Decimal('0'), comment="应收账款")
    inventory_value = Column(Numeric(12, 2), default=Decimal('0'), comment="库存价值")
    
    # 非流动资产类
    fixed_assets_original = Column(Numeric(12, 2), default=Decimal('0'), comment="固定资产原值")
    accumulated_depreciation = Column(Numeric(12, 2), default=Decimal('0'), comment="累计折旧")
    intangible_assets_original = Column(Numeric(12, 2), default=Decimal('0'), comment="无形资产原值")
    accumulated_amortization = Column(Numeric(12, 2), default=Decimal('0'), comment="累计摊销")
    
    # 流动负债类
    accounts_payable = Column(Numeric(12, 2), default=Decimal('0'), comment="应付账款")
    tax_payable = Column(Numeric(12, 2), default=Decimal('0'), comment="应交税费")
    
    # 非流动负债类
    long_term_borrowings = Column(Numeric(12, 2), default=Decimal('0'), comment="长期借款")
    
    # 权益类
    paid_in_capital = Column(Numeric(12, 2), default=Decimal('0'), comment="实收资本")
    retained_earnings = Column(Numeric(12, 2), default=Decimal('0'), comment="未分配利润")
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    account = relationship("Account", backref="opening_balances")


# 固定资产表
class FixedAsset(Base):
    __tablename__ = "fixed_assets"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True, comment="所属账本")
    asset_code = Column(String(50), comment="资产编码（账本内唯一）")
    name = Column(String(100), nullable=False, comment="资产名称")
    category = Column(String(50), comment="资产类别")
    original_value = Column(Numeric(12, 2), nullable=False, comment="原值")
    salvage_rate = Column(Numeric(5, 2), default=Decimal('0.05'), comment="残值率")
    useful_life = Column(Integer, nullable=False, comment="使用寿命(月)")
    depreciation_method = Column(String(20), default="年限平均法", comment="折旧方法")
    start_date = Column(Date, nullable=False, comment="开始折旧日期")
    accumulated_depreciation = Column(Numeric(12, 2), default=Decimal('0'), comment="累计折旧")
    status = Column(String(20), default="在用", comment="在用/停用/报废")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    account = relationship("Account", backref="fixed_assets")

    __table_args__ = (
        UniqueConstraint('account_id', 'asset_code', name='uix_account_asset_code'),
    )


# 固定资产折旧流水（真相源）
class FixedAssetDepreciation(Base):
    __tablename__ = "fixed_asset_depreciations"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("fixed_assets.id"), nullable=False, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    period = Column(String(7), nullable=False, comment="折旧期间 YYYY-MM")
    amount = Column(Numeric(12, 2), nullable=False, comment="本期折旧额")
    accumulated_before = Column(Numeric(12, 2), default=Decimal('0'), comment="折旧前累计折旧")
    accumulated_after = Column(Numeric(12, 2), default=Decimal('0'), comment="折旧后累计折旧")
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        UniqueConstraint('asset_id', 'period', name='uix_depreciation_period'),
    )


# 无形资产表
class IntangibleAsset(Base):
    __tablename__ = "intangible_assets"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True, comment="所属账本")
    asset_code = Column(String(50), comment="资产编码（账本内唯一）")
    name = Column(String(100), nullable=False, comment="资产名称")
    category = Column(String(50), comment="类别(专利/软件/商标等)")
    original_value = Column(Numeric(12, 2), nullable=False, comment="原值")
    useful_life = Column(Integer, nullable=False, comment="使用寿命(月)")
    start_date = Column(Date, nullable=False, comment="开始摊销日期")
    accumulated_amortization = Column(Numeric(12, 2), default=Decimal('0'), comment="累计摊销")
    status = Column(String(20), default="使用中", comment="使用中/已报废")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    account = relationship("Account", backref="intangible_assets")

    __table_args__ = (
        UniqueConstraint('account_id', 'asset_code', name='uix_intangible_account_asset_code'),
    )


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True, comment="所属账本")
    name = Column(String(100), nullable=False, comment="商品名称")
    sku = Column(String(50), index=True, comment="商品编码")
    category = Column(String(50), default="", comment="分类")
    unit = Column(String(20), default="个", comment="单位")
    purchase_price = Column(Numeric(12, 2), default=Decimal('0'), comment="进价")
    sale_price = Column(Numeric(12, 2), default=Decimal('0'), comment="售价")
    min_stock = Column(Integer, default=0, comment="最低库存预警")
    track_inventory = Column(Boolean, nullable=False, default=True, comment="是否追踪库存（人力商品=False）")
    description = Column(Text, default="", comment="描述")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    inventory = relationship("Inventory", back_populates="product", uselist=False,
                             primaryjoin="and_(Product.id==Inventory.product_id, Product.account_id==Inventory.account_id)")
    purchase_items = relationship("PurchaseItem", back_populates="product")
    sale_items = relationship("SaleItem", back_populates="product")


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True, comment="所属账本")
    name = Column(String(100), nullable=False, comment="供应商名称")
    contact = Column(String(50), default="", comment="联系人")
    phone = Column(String(20), default="", comment="电话")
    address = Column(String(200), default="", comment="地址")
    notes = Column(Text, default="", comment="备注")
    created_at = Column(DateTime, default=datetime.now)

    purchase_orders = relationship("PurchaseOrder", back_populates="supplier")


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True, comment="所属账本")
    name = Column(String(100), nullable=False, comment="客户名称")
    contact = Column(String(50), default="", comment="联系人")
    phone = Column(String(20), default="", comment="电话")
    address = Column(String(200), default="", comment="地址")
    notes = Column(Text, default="", comment="备注")
    created_at = Column(DateTime, default=datetime.now)

    sale_orders = relationship("SaleOrder", back_populates="customer")


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True, comment="所属账本")
    order_no = Column(String(30), index=True, comment="采购单号")
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), comment="供应商ID")
    order_type = Column(String(20), nullable=False, default=OrderType.RETAIL, comment="单据类型: retail/purchase_labor")
    total_price = Column(Numeric(12, 2), default=Decimal('0'), comment="订单总额（价税合计）")
    tax_amount = Column(Numeric(12, 2), default=Decimal('0'), comment="增值税额")
    payment_method = Column(String(20), nullable=False, default=PaymentMethod.COMPANY, comment="支付方式: company / private_advance")
    payment_status = Column(String(20), nullable=False, default=PaymentStatus.UNPAID, comment="付款状态: paid / unpaid")
    status = Column(String(20), default=OrderStatus.COMPLETED, comment="状态: pending/completed/cancelled")
    notes = Column(Text, default="", comment="备注")
    image_url = Column(String(500), default="", comment="附件图片URL")
    purchase_date = Column(DateTime, default=datetime.now, comment="采购日期")
    created_at = Column(DateTime, default=datetime.now)

    supplier = relationship("Supplier", back_populates="purchase_orders")
    items = relationship("PurchaseItem", back_populates="order", cascade="all, delete-orphan")


class PurchaseItem(Base):
    __tablename__ = "purchase_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=False, comment="采购订单ID")
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, comment="商品ID")
    quantity = Column(Integer, nullable=False, comment="数量")
    unit_price = Column(Numeric(12, 6), nullable=False, comment="单价")
    tax_rate = Column(Numeric(12, 2), nullable=False, default=Decimal('0.13'), comment="税率: 0.01/0.03/0.06/0.09/0.13")
    total_price = Column(Numeric(12, 2), nullable=False, comment="小计")
    notes = Column(Text, default="", comment="备注（合并行追踪 cost_id 用）")

    order = relationship("PurchaseOrder", back_populates="items")
    product = relationship("Product", back_populates="purchase_items")

    __table_args__ = (
        # 同一采购单内同一商品只能出现一次
        UniqueConstraint('order_id', 'product_id', name='uix_purchase_item_order_product'),
    )


class SaleOrder(Base):
    __tablename__ = "sale_orders"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True, comment="所属账本")
    order_no = Column(String(30), index=True, comment="销售单号")
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True, comment="客户ID(可为空=散客)")
    order_type = Column(String(20), nullable=False, default=OrderType.RETAIL, comment="单据类型: retail")
    total_price = Column(Numeric(12, 2), default=Decimal('0'), comment="订单总额（价税合计）")
    tax_amount = Column(Numeric(12, 2), default=Decimal('0'), comment="增值税额")
    payment_status = Column(String(20), nullable=False, default=PaymentStatus.UNPAID, comment="支付状态: paid / unpaid")
    status = Column(String(20), default=OrderStatus.COMPLETED, comment="状态: pending/completed/cancelled")
    notes = Column(Text, default="", comment="备注")
    image_url = Column(String(500), default="", comment="附件图片URL")
    sale_date = Column(DateTime, default=datetime.now, comment="销售日期")
    created_at = Column(DateTime, default=datetime.now)

    customer = relationship("Customer", back_populates="sale_orders")
    items = relationship("SaleItem", back_populates="order", cascade="all, delete-orphan")


class SaleItem(Base):
    __tablename__ = "sale_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("sale_orders.id"), nullable=False, comment="销售订单ID")
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, comment="商品ID")
    quantity = Column(Integer, nullable=False, comment="数量")
    unit_price = Column(Numeric(12, 6), nullable=False, comment="单价")
    tax_rate = Column(Numeric(12, 2), nullable=False, default=Decimal('0.01'), comment="税率: 0.01/0.03/0.06/0.09/0.13")
    total_price = Column(Numeric(12, 2), nullable=False, comment="小计")
    _unit_cost = Column("unit_cost", Numeric(14, 6), default=Decimal('0'), comment="出库时移动加权平均成本")

    @property
    def unit_cost(self):
        return self._unit_cost

    def set_calculated_cost(self, value):
        self._unit_cost = value
    notes = Column(Text, default="", comment="备注（合并行追踪 cost_id 用）")

    order = relationship("SaleOrder", back_populates="items")
    product = relationship("Product", back_populates="sale_items")

    __table_args__ = (
        # 同一销售单内同一商品只能出现一次
        UniqueConstraint('order_id', 'product_id', name='uix_sale_item_order_product'),
    )



class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True, comment="所属账本")
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, comment="商品ID")
    quantity = Column(Integer, default=0, comment="当前库存(允许负数)")
    average_cost = Column(Numeric(14, 6), default=Decimal('0'), comment="移动加权平均成本")
    total_value = Column(Numeric(14, 2), default=Decimal('0'), comment="库存总金额")
    last_updated = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    product = relationship("Product", back_populates="inventory")

    __table_args__ = (
        UniqueConstraint('account_id', 'product_id', name='uix_inventory_account_product'),
    )


class StockMove(Base):
    __tablename__ = "stock_moves"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True, comment="所属账本")
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, comment="商品ID")
    quantity = Column(Numeric(12, 0), nullable=False, comment="入库为正，出库为负")
    unit_cost = Column(Numeric(14, 6), default=Decimal('0'), comment="移动加权平均单价")
    total_cost = Column(Numeric(14, 2), default=Decimal('0'), comment="行总金额")
    source_type = Column(String(50), nullable=False, comment="来源类型: purchase_order/sale_order/adjustment/reversal")
    source_id = Column(Integer, nullable=False, comment="来源单据ID")
    move_date = Column(DateTime, nullable=True, comment="业务日期（取自源单据）")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")


class OperationLog(Base):
    __tablename__ = "operation_logs"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True, comment="所属账本")
    operation = Column(String(20), nullable=False, comment="操作: create/update/delete/adjust")
    entity_type = Column(String(50), nullable=False, comment="实体类型")
    entity_id = Column(Integer, nullable=False, comment="实体ID")
    detail = Column(Text, default="", comment="操作详情")
    operator = Column(String(20), nullable=False, default="user", comment="操作者: user / ai")
    created_at = Column(DateTime, default=datetime.now)


class AuditLog(Base):
    """审计日志 — 记录实体变更前后状态（通过 SQLAlchemy 事件自动写入）"""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, index=True, nullable=True, comment="所属账本")
    operator = Column(String(50), default="system", comment="操作者")
    action = Column(String(20), nullable=False, comment="create / update / delete")
    entity_type = Column(String(50), nullable=False, comment="实体类型")
    entity_id = Column(Integer, nullable=True, comment="实体ID")
    before_data = Column(JSON, nullable=True, comment="变更前（JSON）")
    after_data = Column(JSON, nullable=True, comment="变更后（JSON）")
    changed_fields = Column(JSON, nullable=True, comment="变更字段列表")
    created_at = Column(DateTime, default=datetime.now, index=True)


# 个人流水账（仅 personal 账本使用）
class PersonalTransaction(Base):
    __tablename__ = "personal_transactions"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True, comment="所属账本")
    type = Column(String(10), nullable=False, comment="类型: income/expense")
    amount = Column(Numeric(12, 2), nullable=False, comment="金额")
    category = Column(String(50), default="", comment="分类")
    description = Column(Text, default="", comment="描述")
    image_url = Column(String(500), default="", comment="附件图片URL")
    date = Column(DateTime, default=datetime.now, comment="交易日期")
    created_at = Column(DateTime, default=datetime.now)


# 发票管理
class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True, comment="所属账本")
    invoice_no = Column(String(50), nullable=False, comment="发票号码")
    direction = Column(String(10), nullable=False, comment="方向: in 进项 / out 销项")
    invoice_type = Column(String(20), nullable=False, comment="类型: ordinary 普票 / special 专票")
    tax_rate = Column(Numeric(12, 2), nullable=False, comment="税率: 0.01/0.03/0.06/0.09/0.13")
    amount_without_tax = Column(Numeric(12, 2), nullable=False, comment="不含税金额")
    tax_amount = Column(Numeric(12, 2), nullable=False, comment="税额")
    amount_with_tax = Column(Numeric(12, 2), nullable=False, comment="价税合计")
    counterparty_name = Column(String(200), nullable=False, comment="对方名称")
    seller_name = Column(String(200), nullable=False, default="", comment="销方名称")
    buyer_name = Column(String(200), nullable=False, default="", comment="买方名称")
    issue_date = Column(DateTime, nullable=False, comment="开票日期")
    pdf_path = Column(String(500), nullable=True, comment="PDF文件路径")
    image_url = Column(String(500), default="", comment="附件图片URL")
    certification_status = Column(String(20), nullable=False, default=CertificationStatus.N_A, comment="认证状态: pending / certified / n_a")
    certification_date = Column(DateTime, nullable=True, comment="认证日期")
    related_order_id = Column(Integer, nullable=True, comment="关联订单ID")
    related_order_type = Column(String(20), nullable=True, comment="关联订单类型: sale_order/purchase_order/expense/fixed_asset")
    is_reversed = Column(Boolean, default=False, comment="是否已被冲红")
    reversed_at = Column(DateTime, nullable=True, comment="冲红时间")
    notes = Column(Text, default="", comment="备注")
    created_at = Column(DateTime, default=datetime.now)

    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint('account_id', 'invoice_no', name='uix_account_invoice_no'),
        # DB 层兜底:防止 agent 越过 handler 直接写非法 related_order_type
        CheckConstraint(
            "related_order_type IS NULL OR related_order_type IN ('sale_order','purchase_order','expense','fixed_asset')",
            name='ck_invoice_related_order_type'
        ),
    )


class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False, comment="发票ID")
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, comment="商品ID")
    quantity = Column(Integer, nullable=False, comment="数量")
    unit_price = Column(Numeric(12, 6), nullable=False, comment="单价")
    tax_rate = Column(Numeric(12, 2), nullable=False, default=Decimal('0.01'), comment="税率")
    total_price = Column(Numeric(12, 2), nullable=False, comment="小计")

    invoice = relationship("Invoice", back_populates="items")
    product = relationship("Product")

    __table_args__ = (
        UniqueConstraint('invoice_id', 'product_id', name='uix_invoice_item_product'),
    )



# 费用表（企业所得税用：无票支出记录）
class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True, comment="所属账本")
    category = Column(String(50), nullable=False, comment="类别: 房租/水电/工资/材料/办公用品/运费/维修/其他")
    functional_category = Column(String(20), nullable=False, default="管理费用", comment="功能分类: 销售费用/管理费用/财务费用")
    amount = Column(Numeric(12, 2), nullable=False, comment="金额")
    expense_date = Column(DateTime, nullable=False, comment="支出日期")
    payment_method = Column(String(20), nullable=False, default=PaymentMethod.COMPANY, comment="支付方式: company / private_advance")
    payment_status = Column(String(20), nullable=False, default="unpaid", comment="付款状态: unpaid/paid")
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=True, comment="付款记录ID")
    description = Column(String(500), default="", comment="描述")
    image_url = Column(String(500), default="", comment="附件图片URL")
    is_reversed = Column(Boolean, default=False, comment="是否已被冲红")
    reversed_at = Column(DateTime, nullable=True, comment="冲红时间")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")

    payment = relationship("Payment", backref="expense", foreign_keys=[payment_id])


class CashFlowTransaction(Base):
    __tablename__ = "cash_flow_transactions"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True, comment="所属账本")
    type = Column(String(10), nullable=False, comment="类型: inflow/outflow")
    amount = Column(Numeric(12, 2), nullable=False, comment="金额")
    flow_category = Column(String(20), nullable=False, default=FlowCategory.OPERATING, comment="现金流量分类: operating/investing/financing")
    description = Column(Text, default="", comment="描述")
    transaction_date = Column(DateTime, nullable=False, comment="交易日期")
    related_entity_type = Column(String(20), nullable=True, comment="关联实体类型: sale/purchase/expense/other")
    related_entity_id = Column(Integer, nullable=True, comment="关联实体ID")
    is_reversed = Column(Boolean, default=False, comment="是否已被冲红")
    reversed_at = Column(DateTime, nullable=True, comment="冲红时间")
    created_at = Column(DateTime, default=datetime.now)

    account = relationship("Account", backref="cash_flow_transactions")


# ═══════════════════════════════════════════════════════════
# 权责发生制新增表
# ═══════════════════════════════════════════════════════════

class BankAccount(Base):
    """银行账户"""
    __tablename__ = "bank_accounts"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True, comment="所属账本")
    bank_name = Column(String(100), nullable=False, comment="银行名称")
    account_number = Column(String(50), nullable=False, comment="银行账号")
    balance = Column(Numeric(12, 2), nullable=False, default=Decimal('0'), comment="当前余额")
    description = Column(String(500), default="", comment="描述")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")

    account = relationship("Account", backref="bank_accounts")


class BankTransaction(Base):
    """银行流水"""
    __tablename__ = "bank_transactions"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True, comment="所属账本")
    bank_account_id = Column(Integer, ForeignKey("bank_accounts.id"), nullable=False, index=True, comment="银行账户")
    transaction_type = Column(String(10), nullable=False, comment="类型: inflow/outflow")
    amount = Column(Numeric(12, 2), nullable=False, comment="金额")
    balance_after = Column(Numeric(12, 2), nullable=False, comment="交易后余额")
    transaction_date = Column(DateTime, nullable=False, comment="交易日期")
    description = Column(String(500), default="", comment="描述")
    reference_no = Column(String(100), default="", comment="银行流水号")
    flow_category = Column(String(20), nullable=False, default=FlowCategory.OPERATING, comment="现金流量分类: operating/investing/financing")
    related_entity_type = Column(String(20), nullable=True, comment="关联实体类型: payment/receipt")
    related_entity_id = Column(Integer, nullable=True, comment="关联实体ID")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")

    account = relationship("Account", backref="bank_transactions")
    bank_account = relationship("BankAccount", backref="transactions")


class Payment(Base):
    """付款记录"""
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True, comment="所属账本")
    payment_type = Column(String(20), nullable=False, comment="付款类型: expense/purchase/salary/tax(缴税清负债)")
    related_entity_type = Column(String(20), nullable=False, comment="关联实体类型: expense/purchase_order")
    related_entity_id = Column(Integer, nullable=False, comment="关联实体ID")
    amount = Column(Numeric(12, 2), nullable=False, comment="付款金额")
    payment_method = Column(String(20), nullable=False, default="company", comment="付款方式: company/private_advance")
    payment_date = Column(DateTime, nullable=False, comment="付款日期")
    bank_account_id = Column(Integer, ForeignKey("bank_accounts.id"), nullable=True, comment="银行账户")
    bank_transaction_id = Column(Integer, ForeignKey("bank_transactions.id"), nullable=True, comment="银行流水")
    description = Column(String(500), default="", comment="描述")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")

    account = relationship("Account", backref="payments")
    bank_account = relationship("BankAccount", backref="payments")
    bank_transaction = relationship("BankTransaction", backref="payment")


class Receipt(Base):
    """收款记录"""
    __tablename__ = "receipts"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True, comment="所属账本")
    receipt_type = Column(String(20), nullable=False, comment="收款类型: sale")
    related_entity_type = Column(String(20), nullable=False, comment="关联实体类型: sale_order")
    related_entity_id = Column(Integer, nullable=False, comment="关联实体ID")
    amount = Column(Numeric(12, 2), nullable=False, comment="收款金额")
    receipt_method = Column(String(20), nullable=False, default="company", comment="收款方式: company/private_advance")
    receipt_date = Column(DateTime, nullable=False, comment="收款日期")
    bank_account_id = Column(Integer, ForeignKey("bank_accounts.id"), nullable=True, comment="银行账户")
    bank_transaction_id = Column(Integer, ForeignKey("bank_transactions.id"), nullable=True, comment="银行流水")
    description = Column(String(500), default="", comment="描述")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")

    account = relationship("Account", backref="receipts")
    bank_account = relationship("BankAccount", backref="receipts")
    bank_transaction = relationship("BankTransaction", backref="receipt")


# ═══════════════════════════════════════════════════════════
# before_update 事件：真相源流水表禁止 UPDATE
# ═══════════════════════════════════════════════════════════

@event.listens_for(StockMove, 'before_update')
def prevent_stock_move_update(mapper, connection, target):
    from errors import BusinessError, ErrorCode
    raise BusinessError(
        code=ErrorCode.DATA_INTEGRITY_ERROR,
        data={"details": "StockMove 是库存真相源，一经生成严禁修改"}
    )


@event.listens_for(FixedAssetDepreciation, 'before_update')
def prevent_depreciation_update(mapper, connection, target):
    from errors import BusinessError, ErrorCode
    raise BusinessError(
        code=ErrorCode.DATA_INTEGRITY_ERROR,
        data={"details": "FixedAssetDepreciation 是折旧真相源，一经生成严禁修改"}
    )