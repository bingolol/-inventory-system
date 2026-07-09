from sqlalchemy import Column, Integer, String, Float, Numeric, DateTime, ForeignKey, Boolean, Text, UniqueConstraint, CheckConstraint, Date, and_, event, JSON
from sqlalchemy.orm import relationship
from decimal import Decimal
from datetime import datetime
from database import Base
from enums import OrderStatus, PaymentStatus, PaymentMethod, CertificationStatus, InvoiceStatus, FlowCategory, OrderType


# 用户表：支持登录认证
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, comment="用户名")
    password_hash = Column(String(128), nullable=False, comment="密码哈希(PBKDF2)")
    password_salt = Column(String(32), nullable=True, comment="密码盐(NULL表示旧SHA256格式)")
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, comment="默认账本")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)


class UserToken(Base):
    __tablename__ = "user_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    access_token_hash = Column(String(64), nullable=False, index=True, comment="访问令牌哈希")
    refresh_token_hash = Column(String(64), nullable=False, index=True, comment="刷新令牌哈希")
    access_expires_at = Column(DateTime, nullable=False, comment="访问令牌过期时间")
    refresh_expires_at = Column(DateTime, nullable=False, comment="刷新令牌过期时间")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")


# 账本表：支持多公司/个人记账切换
class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, comment="账本名")
    type = Column(String(20), nullable=False, default="company", comment="类型: company/personal")
    code = Column(String(50), unique=True, nullable=False, comment="代码标识: riyun=日运办公, qiaoyou=巧游电子, personal=个人")
    taxpayer_type_l3 = Column(String(20), nullable=False, default="small_scale", comment="[L3-政策] 纳税人类型: small_scale / general", info={"tier":"L3","source":"policy"})
    taxpayer_id_l1 = Column(String(50), nullable=True, comment="[L1-外部] 纳税人识别号（统一社会信用代码）", info={"tier":"L1","source":"external"})
    taxpayer_name_l1 = Column(String(200), nullable=True, comment="[L1-外部] 纳税人名称", info={"tier":"L1","source":"external"})
    surcharge_halved = Column(Boolean, default=False, comment="附加税减半标志（创建账本时配置，年末评估更新）")
    created_at = Column(DateTime, default=datetime.now)


class TaxpayerTypeHistory(Base):
    __tablename__ = "taxpayer_type_history"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    taxpayer_type_l3 = Column(String(20), nullable=False, comment="纳税人类型: small_scale / general")
    effective_period = Column(String(7), nullable=False, default="", comment="生效期间 YYYY-MM")
    changed_at = Column(DateTime, default=datetime.now, comment="变更时间")


# 期初余额表
class OpeningBalance(Base):
    __tablename__ = "opening_balances"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True, comment="所属账本")
    date_l1 = Column(Date, nullable=False, comment="[L1-外部] 期初日期", info={"tier":"L1","source":"external"})

    # 流动资产类
    cash_balance_l1 = Column(Numeric(12, 2), default=Decimal('0'), comment="[L1-外部] 现金余额", info={"tier":"L1","source":"external"})
    bank_balance_l1 = Column(Numeric(12, 2), default=Decimal('0'), comment="[L1-外部] 银行存款", info={"tier":"L1","source":"external"})
    accounts_receivable_l1 = Column(Numeric(12, 2), default=Decimal('0'), comment="[L1-外部] 应收账款", info={"tier":"L1","source":"external"})
    inventory_value_l1 = Column(Numeric(12, 2), default=Decimal('0'), comment="[L1-外部] 库存价值", info={"tier":"L1","source":"external"})

    # 非流动资产类
    fixed_assets_original_l1 = Column(Numeric(12, 2), default=Decimal('0'), comment="[L1-外部] 固定资产原值", info={"tier":"L1","source":"external"})
    accumulated_depreciation_l1 = Column(Numeric(12, 2), default=Decimal('0'), comment="[L1-外部] 累计折旧", info={"tier":"L1","source":"external"})
    intangible_assets_original_l1 = Column(Numeric(12, 2), default=Decimal('0'), comment="[L1-外部] 无形资产原值", info={"tier":"L1","source":"external"})
    accumulated_amortization_l1 = Column(Numeric(12, 2), default=Decimal('0'), comment="[L1-外部] 累计摊销", info={"tier":"L1","source":"external"})

    # 流动负债类
    accounts_payable_l1 = Column(Numeric(12, 2), default=Decimal('0'), comment="[L1-外部] 应付账款", info={"tier":"L1","source":"external"})
    tax_payable_l1 = Column(Numeric(12, 2), default=Decimal('0'), comment="[L1-外部] 应交税费", info={"tier":"L1","source":"external"})

    # 非流动负债类
    long_term_borrowings_l1 = Column(Numeric(12, 2), default=Decimal('0'), comment="[L1-外部] 长期借款", info={"tier":"L1","source":"external"})

    # 权益类
    paid_in_capital_l1 = Column(Numeric(12, 2), default=Decimal('0'), comment="[L1-外部] 实收资本", info={"tier":"L1","source":"external"})
    retained_earnings_l1 = Column(Numeric(12, 2), default=Decimal('0'), comment="[L1-外部] 未分配利润", info={"tier":"L1","source":"external"})
    
    is_reversed = Column(Boolean, default=False, comment="是否已冲红/作废")
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
    original_value_l1 = Column(Numeric(12, 2), nullable=False, comment="[L1-外部] 原值", info={"tier":"L1","source":"external"})
    salvage_rate_l3 = Column(Numeric(5, 2), default=Decimal('0.05'), comment="[L3-政策] 残值率", info={"tier":"L3","source":"policy"})
    useful_life_l3 = Column(Integer, nullable=False, comment="[L3-政策] 使用寿命(月)", info={"tier":"L3","source":"policy"})
    depreciation_method_l3 = Column(String(20), default="年限平均法", comment="[L3-政策] 折旧方法", info={"tier":"L3","source":"policy"})
    start_date_l1 = Column(Date, nullable=False, comment="[L1-外部] 开始折旧日期", info={"tier":"L1","source":"external"})
    accumulated_depreciation_l4 = Column(Numeric(12, 2), default=Decimal('0'), comment="[L4-派生] 累计折旧", info={"tier":"L4","source":"derived"})
    status = Column(String(20), default="在用", comment="在用/停用/报废/已冲红")
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
    amount_l2 = Column(Numeric(12, 2), nullable=False, comment="[L2-计算] 本期折旧额", info={"tier":"L2","source":"engine"})
    accumulated_before_l2 = Column(Numeric(12, 2), default=Decimal('0'), comment="[L2-计算] 折旧前累计折旧", info={"tier":"L2","source":"engine"})
    accumulated_after_l2 = Column(Numeric(12, 2), default=Decimal('0'), comment="[L2-计算] 折旧后累计折旧", info={"tier":"L2","source":"engine"})
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
    original_value_l1 = Column(Numeric(12, 2), nullable=False, comment="[L1-外部] 原值", info={"tier":"L1","source":"external"})
    useful_life_l3 = Column(Integer, nullable=False, comment="[L3-政策] 使用寿命(月)", info={"tier":"L3","source":"policy"})
    start_date_l1 = Column(Date, nullable=False, comment="[L1-外部] 开始摊销日期", info={"tier":"L1","source":"external"})
    accumulated_amortization_l4 = Column(Numeric(12, 2), default=Decimal('0'), comment="[L4-派生] 累计摊销", info={"tier":"L4","source":"derived"})
    status = Column(String(20), default="使用中", comment="使用中/已报废")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    account = relationship("Account", backref="intangible_assets")

    __table_args__ = (
        UniqueConstraint('account_id', 'asset_code', name='uix_intangible_account_asset_code'),
    )


# 无形资产摊销流水（真相源）
class IntangibleAssetAmortization(Base):
    __tablename__ = "intangible_asset_amortizations"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey('intangible_assets.id'), nullable=False, index=True)
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False, index=True)
    period = Column(String(7), nullable=False, comment="摊销期间 YYYY-MM")
    amount_l2 = Column(Numeric(12, 2), nullable=False, comment="[L2-计算] 本期摊销额", info={"tier":"L2","source":"engine"})
    accumulated_before_l2 = Column(Numeric(12, 2), default=Decimal('0'), comment="[L2-计算] 摊销前累计摊销", info={"tier":"L2","source":"engine"})
    accumulated_after_l2 = Column(Numeric(12, 2), default=Decimal('0'), comment="[L2-计算] 摊销后累计摊销", info={"tier":"L2","source":"engine"})
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        UniqueConstraint('asset_id', 'period', name='uix_intangible_amortization_period'),
    )


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True, comment="所属账本")
    name = Column(String(100), nullable=False, comment="商品名称")
    sku = Column(String(50), index=True, comment="商品编码")
    category = Column(String(50), default="", comment="分类")
    unit = Column(String(20), default="个", comment="单位")
    purchase_price_l3 = Column(Numeric(12, 2), default=Decimal('0'), comment="[L3-政策] 进价(主数据静态,非成本真相源)", info={"tier":"L3","source":"policy"})
    sale_price_l3 = Column(Numeric(12, 2), default=Decimal('0'), comment="[L3-政策] 售价", info={"tier":"L3","source":"policy"})
    min_stock_l3 = Column(Integer, default=0, comment="[L3-政策] 最低库存预警", info={"tier":"L3","source":"policy"})
    track_inventory_l3 = Column(Boolean, nullable=False, default=True, comment="[L3-政策] 是否追踪库存（人力商品=False）", info={"tier":"L3","source":"policy"})
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
    total_price_l1 = Column(Numeric(12, 2), default=Decimal('0'), comment="[L1-外部] 订单总额（价税合计）", info={"tier":"L1","source":"external"})
    tax_amount_l1 = Column(Numeric(12, 2), default=Decimal('0'), comment="[L1-外部] 增值税额", info={"tier":"L1","source":"external"})
    payment_method = Column(String(20), nullable=False, default=PaymentMethod.COMPANY, comment="支付方式: company / private_advance")
    payment_status = Column(String(20), nullable=False, default=PaymentStatus.UNPAID, comment="付款状态: paid / unpaid")
    status = Column(String(20), default=OrderStatus.COMPLETED, comment="状态: pending/completed/cancelled")
    notes = Column(Text, default="", comment="备注")
    image_url = Column(String(500), default="", comment="附件图片URL")
    purchase_date_l1 = Column(DateTime, nullable=False, comment="[L1-外部] 采购日期（BR-21必填，禁止ORM层默认值）", info={"tier":"L1","source":"external"})
    created_at = Column(DateTime, default=datetime.now)

    supplier = relationship("Supplier", back_populates="purchase_orders")
    items = relationship("PurchaseItem", back_populates="order", cascade="all, delete-orphan")


class PurchaseItem(Base):
    __tablename__ = "purchase_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=False, comment="采购订单ID")
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, comment="商品ID")
    quantity_l1 = Column(Integer, nullable=False, comment="[L1-外部] 数量", info={"tier":"L1","source":"external"})
    unit_price_l1 = Column(Numeric(12, 6), nullable=False, comment="[L1-外部] 单价", info={"tier":"L1","source":"external"})
    tax_rate_l1 = Column(Numeric(12, 2), nullable=False, comment="[L1-外部] 税率: 0.01/0.03/0.06/0.09/0.13", info={"tier":"L1","source":"external"})
    total_price_l1 = Column(Numeric(12, 2), nullable=False, comment="[L1-外部] 小计", info={"tier":"L1","source":"external"})
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
    total_price_l1 = Column(Numeric(12, 2), default=Decimal('0'), comment="[L1-外部] 订单总额（价税合计）", info={"tier":"L1","source":"external"})
    tax_amount_l1 = Column(Numeric(12, 2), default=Decimal('0'), comment="[L1-外部] 增值税额", info={"tier":"L1","source":"external"})
    has_invoice_l1 = Column(Boolean, nullable=False, default=True, comment="[L1-外部] 是否已开发票(散客现金销售=False,未开票收入仍需申报销项税)", info={"tier":"L1","source":"external"})
    payment_status = Column(String(20), nullable=False, default=PaymentStatus.UNPAID, comment="支付状态: paid / unpaid")
    status = Column(String(20), default=OrderStatus.COMPLETED, comment="状态: pending/completed/cancelled")
    notes = Column(Text, default="", comment="备注")
    image_url = Column(String(500), default="", comment="附件图片URL")
    sale_date_l1 = Column(DateTime, nullable=False, comment="[L1-外部] 销售日期（BR-21必填，禁止ORM层默认值）", info={"tier":"L1","source":"external"})
    created_at = Column(DateTime, default=datetime.now)

    customer = relationship("Customer", back_populates="sale_orders")
    items = relationship("SaleItem", back_populates="order", cascade="all, delete-orphan")


class SaleItem(Base):
    __tablename__ = "sale_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("sale_orders.id"), nullable=False, comment="销售订单ID")
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, comment="商品ID")
    quantity_l1 = Column(Integer, nullable=False, comment="[L1-外部] 数量", info={"tier":"L1","source":"external"})
    unit_price_l1 = Column(Numeric(12, 6), nullable=False, comment="[L1-外部] 单价", info={"tier":"L1","source":"external"})
    tax_rate_l1 = Column(Numeric(12, 2), nullable=False, comment="[L1-外部] 税率: 0.01/0.03/0.06/0.09/0.13", info={"tier":"L1","source":"external"})
    total_price_l1 = Column(Numeric(12, 2), nullable=False, comment="[L1-外部] 小计", info={"tier":"L1","source":"external"})
    unit_cost_l2 = Column(Numeric(14, 6), default=Decimal('0'), comment="[L2-计算] 出库时锁定的移动加权平均成本快照", info={"tier":"L2","source":"engine"})
    notes = Column(Text, default="", comment="备注（合并行追踪 cost_id 用）")

    def set_calculated_cost(self, cost: Decimal):
        self.unit_cost_l2 = cost

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
    quantity_l4 = Column(Integer, default=0, comment="[L4-派生] 当前库存，业务层禁止为负", info={"tier":"L4","source":"derived"})
    average_cost_l4 = Column(Numeric(14, 6), default=Decimal('0'), comment="[L4-派生] 移动加权平均成本", info={"tier":"L4","source":"derived"})
    total_value_l4 = Column(Numeric(14, 2), default=Decimal('0'), comment="[L4-派生] 库存总金额", info={"tier":"L4","source":"derived"})
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
    quantity_l1 = Column(Numeric(12, 0), nullable=False, comment="[L1-外部] 入库为正，出库为负(值来自源单据)", info={"tier":"L1","source":"external"})
    unit_cost_l2 = Column(Numeric(14, 6), default=Decimal('0'), comment="[L2-计算] 移动加权平均单价", info={"tier":"L2","source":"engine"})
    total_cost_l2 = Column(Numeric(14, 2), default=Decimal('0'), comment="[L2-计算] 行总金额", info={"tier":"L2","source":"engine"})
    source_type = Column(String(50), nullable=False, comment="来源类型: purchase_order/sale_order/adjustment/reversal")
    source_id = Column(Integer, nullable=False, comment="来源单据ID")
    ref_source_id = Column(Integer, nullable=True, index=True, comment="原始单据ID（部分退货时记录原销售/采购单ID，用于关联）")
    move_date_l1 = Column(DateTime, nullable=True, comment="[L1-外部] 业务日期（取自源单据）", info={"tier":"L1","source":"external"})
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
    amount_l1 = Column(Numeric(12, 2), nullable=False, comment="[L1-外部] 金额", info={"tier":"L1","source":"external"})
    category = Column(String(50), default="", comment="分类")
    description = Column(Text, default="", comment="描述")
    image_url = Column(String(500), default="", comment="附件图片URL")
    date_l1 = Column(DateTime, nullable=False, comment="[L1-外部] 交易日期（BR-21必填，禁止ORM层默认值）", info={"tier":"L1","source":"external"})
    is_reversed = Column(Boolean, default=False, comment="是否已冲红/作废")
    created_at = Column(DateTime, default=datetime.now)


# 发票管理
class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True, comment="所属账本")
    invoice_no = Column(String(50), nullable=False, comment="发票号码")
    direction = Column(String(10), nullable=False, comment="方向: in 进项 / out 销项")
    invoice_type = Column(String(20), nullable=False, comment="类型: ordinary 普票 / special 专票")
    tax_rate_l1 = Column(Numeric(12, 2), nullable=False, comment="[L1-外部] 税率: 0.01/0.03/0.06/0.09/0.13", info={"tier":"L1","source":"external"})
    amount_without_tax_l1 = Column(Numeric(12, 2), nullable=False, comment="[L1-外部] 不含税金额", info={"tier":"L1","source":"external"})
    tax_amount_l1 = Column(Numeric(12, 2), nullable=False, comment="[L1-外部] 税额", info={"tier":"L1","source":"external"})
    amount_with_tax_l1 = Column(Numeric(12, 2), nullable=False, comment="[L1-外部] 价税合计", info={"tier":"L1","source":"external"})
    counterparty_name = Column(String(200), nullable=False, comment="对方名称")
    seller_name = Column(String(200), nullable=False, default="", comment="销方名称")
    buyer_name = Column(String(200), nullable=False, default="", comment="买方名称")
    issue_date_l1 = Column(DateTime, nullable=False, comment="[L1-外部] 开票日期", info={"tier":"L1","source":"external"})
    pdf_path = Column(String(500), nullable=True, comment="PDF文件路径")
    image_url = Column(String(500), default="", comment="附件图片URL")
    certification_status_l3 = Column(String(20), nullable=False, default=CertificationStatus.N_A, comment="[L3-政策] 认证状态: pending / certified / n_a", info={"tier":"L3","source":"policy"})
    certification_date_l3 = Column(DateTime, nullable=True, comment="[L3-政策] 认证日期", info={"tier":"L3","source":"policy"})
    related_order_id = Column(Integer, nullable=True, comment="关联订单ID")
    related_order_type = Column(String(20), nullable=True, comment="关联订单类型: sale_order/purchase_order/expense/fixed_asset")
    related_original_invoice_id = Column(Integer, nullable=True, comment="红字发票关联的原发票ID")
    is_normal_invoice = Column(Boolean, default=True, nullable=False, comment="真=普通发票，假=红冲发票")
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
    quantity_l1 = Column(Integer, nullable=False, comment="[L1-外部] 数量", info={"tier":"L1","source":"external"})
    unit_price_l1 = Column(Numeric(12, 6), nullable=False, comment="[L1-外部] 单价", info={"tier":"L1","source":"external"})
    tax_rate_l1 = Column(Numeric(12, 2), nullable=False, comment="[L1-外部] 税率", info={"tier":"L1","source":"external"})
    total_price_l1 = Column(Numeric(12, 2), nullable=False, comment="[L1-外部] 小计", info={"tier":"L1","source":"external"})

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
    amount_l1 = Column(Numeric(12, 2), nullable=False, comment="[L1-外部] 金额", info={"tier":"L1","source":"external"})
    expense_date_l1 = Column(DateTime, nullable=False, comment="[L1-外部] 支出日期", info={"tier":"L1","source":"external"})
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
    amount_l2 = Column(Numeric(12, 2), nullable=False, comment="[L2-计算] 金额", info={"tier":"L2","source":"engine"})
    flow_category_l2 = Column(String(20), nullable=False, default=FlowCategory.OPERATING, comment="[L2-计算] 现金流量分类: operating/investing/financing", info={"tier":"L2","source":"engine"})
    cash_flow_item_code_l2 = Column(String(10), nullable=True, comment="[L2-计算] 现金流量表项目代码: CF01~CF19", info={"tier":"L2","source":"engine"})
    description = Column(Text, default="", comment="描述")
    transaction_date_l1 = Column(DateTime, nullable=False, comment="[L1-外部] 交易日期", info={"tier":"L1","source":"external"})
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
    balance_l4 = Column(Numeric(12, 2), nullable=False, default=Decimal('0'), comment="[L4-派生] 当前余额", info={"tier":"L4","source":"derived"})
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
    amount_l2 = Column(Numeric(12, 2), nullable=False, comment="[L2-计算] 金额", info={"tier":"L2","source":"engine"})
    balance_after_l4 = Column(Numeric(12, 2), nullable=False, comment="[L4-派生] 交易后余额", info={"tier":"L4","source":"derived"})
    transaction_date_l1 = Column(DateTime, nullable=False, comment="[L1-外部] 交易日期", info={"tier":"L1","source":"external"})
    description = Column(String(500), default="", comment="描述")
    reference_no = Column(String(100), default="", comment="银行流水号")
    flow_category_l2 = Column(String(20), nullable=False, default=FlowCategory.OPERATING, comment="[L2-计算] 现金流量分类: operating/investing/financing", info={"tier":"L2","source":"engine"})
    cash_flow_item_code_l2 = Column(String(10), nullable=True, comment="[L2-计算] 现金流量表项目代码: CF01~CF19", info={"tier":"L2","source":"engine"})
    related_entity_type = Column(String(20), nullable=True, comment="关联实体类型: payment/receipt")
    related_entity_id = Column(Integer, nullable=True, comment="关联实体ID")
    created_at = Column(DateTime, default=datetime.now)

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
    amount_l1 = Column(Numeric(12, 2), nullable=False, comment="[L1-外部] 付款金额(工资场景为实发金额)", info={"tier":"L1","source":"external"})
    withholding_tax_amount_l1 = Column(Numeric(12, 2), nullable=False, default=Decimal("0"),
        comment="[L1-外部] 代扣个人所得税(工资场景,非工资为0)",
        info={"tier":"L1","source":"external"})
    payment_method = Column(String(20), nullable=False, default="company", comment="付款方式: company/private_advance")
    payment_date_l1 = Column(DateTime, nullable=False, comment="[L1-外部] 付款日期", info={"tier":"L1","source":"external"})
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
    amount_l1 = Column(Numeric(12, 2), nullable=False, comment="[L1-外部] 收款金额", info={"tier":"L1","source":"external"})
    receipt_method = Column(String(20), nullable=False, default="company", comment="收款方式: company/private_advance")
    receipt_date_l1 = Column(DateTime, nullable=False, comment="[L1-外部] 收款日期", info={"tier":"L1","source":"external"})
    bank_account_id = Column(Integer, ForeignKey("bank_accounts.id"), nullable=True, comment="银行账户")
    bank_transaction_id = Column(Integer, ForeignKey("bank_transactions.id"), nullable=True, comment="银行流水")
    description = Column(String(500), default="", comment="描述")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")

    account = relationship("Account", backref="receipts")
    bank_account = relationship("BankAccount", backref="receipts")
    bank_transaction = relationship("BankTransaction", backref="receipt")


# 其他应付款/个人垫付（公司账本专用，与 personal_transactions 个人流水不同）
# 业务场景：老板/员工用个人资金替公司垫付费用，公司形成一笔对个人的"其他应付款"负债（2241）
class PersonalAdvance(Base):
    """个人垫付记录（其他应付款）

    生成凭证：dr debit_account_code(默认6601管理费用) cr 2241 其他应付款
    偿还时由 PersonalAdvanceRepayment 记录，生成 dr 2241 cr 1002/1001 反向分录。
    """
    __tablename__ = "personal_advances"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True, comment="所属账本")
    advance_no = Column(String(30), index=True, comment="垫付单号 PA-YYYY-0001")
    advancer_name = Column(String(100), nullable=False, comment="垫付人姓名（自由填写）")
    amount_l1 = Column(Numeric(12, 2), nullable=False, comment="[L1-外部] 垫付金额", info={"tier":"L1","source":"external"})
    advance_date_l1 = Column(DateTime, nullable=False, comment="[L1-外部] 垫付日期", info={"tier":"L1","source":"external"})

    # 借方科目编码：默认 6601 管理费用，可选 1405 库存商品 / 1601 固定资产 / 6602 销售费用 等
    # 由 PERSONAL_ADVANCE_DEBIT_ACCOUNTS 白名单校验（enums.py 单一真相源）
    debit_account_code = Column(String(20), nullable=False, default="6601", comment="借方科目编码")

    description = Column(String(500), default="", comment="用途说明")
    image_url = Column(String(500), default="", comment="附件图片URL")

    # 还款状态与已还金额（paid_amount_l4 用于多次部分偿还累计）
    repayment_status = Column(String(20), nullable=False, default="unpaid", comment="还款状态: unpaid/partial/paid")
    paid_amount_l4 = Column(Numeric(12, 2), default=Decimal('0'), comment="[L4-派生] 已偿还金额", info={"tier":"L4","source":"derived"})

    is_reversed = Column(Boolean, default=False, comment="是否已冲红")
    reversed_at = Column(DateTime, nullable=True, comment="冲红时间")

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    account = relationship("Account", backref="personal_advances")
    repayments = relationship("PersonalAdvanceRepayment", back_populates="advance",
                               cascade="all, delete-orphan",
                               foreign_keys="PersonalAdvanceRepayment.advance_id")

    @property
    def remaining_amount(self):
        """未偿还余额 = 垫付金额 - 已偿还金额（冲红的垫付单余额为0）"""
        if self.is_reversed:
            return Decimal('0')
        return (Decimal(str(self.amount_l1)) - Decimal(str(self.paid_amount_l4 or 0))).quantize(Decimal('0.01'))


class PersonalAdvanceRepayment(Base):
    """个人垫付偿还记录

    每次偿还生成一笔：dr 2241 其他应付款 cr 1002 银行存款 / 1001 库存现金
    支持部分偿还，多次累计。带 bank_account_id 时自动生成 BankTransaction。
    """
    __tablename__ = "personal_advance_repayments"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True, comment="所属账本")
    advance_id = Column(Integer, ForeignKey("personal_advances.id"), nullable=False, index=True, comment="关联垫付单")
    amount_l1 = Column(Numeric(12, 2), nullable=False, comment="[L1-外部] 偿还金额", info={"tier":"L1","source":"external"})
    repayment_date_l1 = Column(DateTime, nullable=False, comment="[L1-外部] 偿还日期", info={"tier":"L1","source":"external"})
    bank_account_id = Column(Integer, ForeignKey("bank_accounts.id"), nullable=True, comment="银行账户")
    bank_transaction_id = Column(Integer, ForeignKey("bank_transactions.id"), nullable=True, comment="银行流水")
    description = Column(String(500), default="", comment="描述")
    is_reversed = Column(Boolean, default=False, comment="是否已冲红")
    reversed_at = Column(DateTime, nullable=True, comment="冲红时间")
    created_at = Column(DateTime, default=datetime.now)

    advance = relationship("PersonalAdvance", back_populates="repayments",
                           foreign_keys=[advance_id])
    bank_account = relationship("BankAccount", foreign_keys=[bank_account_id])
    bank_transaction = relationship("BankTransaction", foreign_keys=[bank_transaction_id])


# ═══════════════════════════════════════════════════════════
# before_update 事件：真相源流水表禁止 UPDATE
# ═══════════════════════════════════════════════════════════

_IMMUTABLE_TABLES = {
    StockMove: "StockMove 是库存真相源，一经生成严禁修改",
    FixedAssetDepreciation: "FixedAssetDepreciation 是折旧真相源，一经生成严禁修改",
    BankTransaction: "BankTransaction 是银行流水真相源，一经生成严禁修改",
    IntangibleAssetAmortization: "IntangibleAssetAmortization 是摊销流水真相源，一经生成严禁修改",
}

for _table, _msg in _IMMUTABLE_TABLES.items():
    def _make_guard(msg: str):
        def _raise(mapper, connection, target):
            from errors import BusinessError, ErrorCode
            raise BusinessError(code=ErrorCode.DATA_INTEGRITY_ERROR, data={"details": msg})
        return _raise
    event.listens_for(_table, 'before_update')(_make_guard(_msg))