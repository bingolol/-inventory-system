from sqlalchemy import Column, Integer, String, Float, Numeric, DateTime, ForeignKey, Boolean, Text, func, UniqueConstraint, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from decimal import Decimal
from database import Base


# 账本表：支持多公司/个人记账切换
class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, comment="账本名")
    type = Column(String(20), nullable=False, default="company", comment="类型: company/personal")
    code = Column(String(50), unique=True, nullable=False, comment="代码标识: riyun=日运办公, qiaoyou=巧游电子, personal=个人")
    taxpayer_type = Column(String(20), nullable=False, default="small_scale", comment="纳税人类型: small_scale / general")
    created_at = Column(DateTime, server_default=func.now())


# 期初余额表
class OpeningBalance(Base):
    __tablename__ = "opening_balances"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True, comment="所属账本")
    date = Column(Date, nullable=False, comment="期初日期")
    
    # 资产类
    cash_balance = Column(Numeric(12, 2), default=Decimal('0'), comment="现金余额")
    bank_balance = Column(Numeric(12, 2), default=Decimal('0'), comment="银行存款")
    accounts_receivable = Column(Numeric(12, 2), default=Decimal('0'), comment="应收账款")
    inventory_value = Column(Numeric(12, 2), default=Decimal('0'), comment="库存价值")
    
    # 负债类
    accounts_payable = Column(Numeric(12, 2), default=Decimal('0'), comment="应付账款")
    tax_payable = Column(Numeric(12, 2), default=Decimal('0'), comment="应交税费")
    
    # 权益类
    retained_earnings = Column(Numeric(12, 2), default=Decimal('0'), comment="未分配利润")
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    account = relationship("Account", backref="opening_balances")


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
    description = Column(Text, default="", comment="描述")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    inventory = relationship("Inventory", back_populates="product", uselist=False)
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
    created_at = Column(DateTime, server_default=func.now())

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
    created_at = Column(DateTime, server_default=func.now())

    sale_orders = relationship("SaleOrder", back_populates="customer")


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True, comment="所属账本")
    order_no = Column(String(20), index=True, comment="采购单号")
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), comment="供应商ID")
    project_name = Column(String(200), nullable=True, index=True, comment="项目名称，文本归集")
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True,
                        comment="关联项目ID")
    total_price = Column(Numeric(12, 2), default=Decimal('0'), comment="订单总额")
    has_invoice = Column(Boolean, nullable=False, default=False, comment="是否有发票")
    payment_method = Column(String(20), nullable=False, default="company", comment="支付方式: company / private_advance")
    payment_status = Column(String(20), nullable=False, default="unpaid", comment="付款状态: paid / unpaid")
    status = Column(String(20), default="completed", comment="状态: pending/completed/cancelled")
    notes = Column(Text, default="", comment="备注")
    image_url = Column(String(500), default="", comment="附件图片URL")
    purchase_date = Column(DateTime, server_default=func.now(), comment="采购日期")
    created_at = Column(DateTime, server_default=func.now())

    supplier = relationship("Supplier", back_populates="purchase_orders")
    items = relationship("PurchaseItem", back_populates="order", cascade="all, delete-orphan")
    project = relationship("Project")


class PurchaseItem(Base):
    __tablename__ = "purchase_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=False, comment="采购订单ID")
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, comment="商品ID")
    quantity = Column(Integer, nullable=False, comment="数量")
    unit_price = Column(Numeric(12, 2), nullable=False, comment="单价")
    tax_rate = Column(Numeric(12, 2), nullable=False, default=Decimal('0.13'), comment="税率: 0.01/0.03/0.06/0.09/0.13")
    total_price = Column(Numeric(12, 2), nullable=False, comment="小计")

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
    order_no = Column(String(20), index=True, comment="销售单号")
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True, comment="客户ID(可为空=散客)")
    project_name = Column(String(200), nullable=True, index=True, comment="项目名称，文本归集")
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True,
                        comment="关联项目ID")
    deduct_inventory = Column(Boolean, nullable=True, default=False,
                              comment="是否由销售单直接扣库存（零售=true；项目业务应为false）")
    total_price = Column(Numeric(12, 2), default=Decimal('0'), comment="订单总额")
    has_invoice = Column(Boolean, nullable=False, default=False, comment="是否已开票")
    payment_status = Column(String(20), nullable=False, default="unpaid", comment="支付状态: paid / unpaid")
    status = Column(String(20), default="completed", comment="状态: pending/completed/cancelled")
    notes = Column(Text, default="", comment="备注")
    image_url = Column(String(500), default="", comment="附件图片URL")
    sale_date = Column(DateTime, server_default=func.now(), comment="销售日期")
    created_at = Column(DateTime, server_default=func.now())

    customer = relationship("Customer", back_populates="sale_orders")
    items = relationship("SaleItem", back_populates="order", cascade="all, delete-orphan")
    project = relationship("Project")


class SaleItem(Base):
    __tablename__ = "sale_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("sale_orders.id"), nullable=False, comment="销售订单ID")
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, comment="商品ID")
    quantity = Column(Integer, nullable=False, comment="数量")
    unit_price = Column(Numeric(12, 2), nullable=False, comment="单价")
    tax_rate = Column(Numeric(12, 2), nullable=False, default=Decimal('0.01'), comment="税率: 0.01/0.03/0.06/0.09/0.13")
    total_price = Column(Numeric(12, 2), nullable=False, comment="小计")

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
    last_updated = Column(DateTime, server_default=func.now(), onupdate=func.now())

    product = relationship("Product", back_populates="inventory")

    __table_args__ = (
        # 每个账本内同一商品只能有一条库存记录
        UniqueConstraint('account_id', 'product_id', name='uix_inventory_account_product'),
    )


class OperationLog(Base):
    __tablename__ = "operation_logs"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True, comment="所属账本")
    operation = Column(String(20), nullable=False, comment="操作: create/update/delete/adjust")
    entity_type = Column(String(50), nullable=False, comment="实体类型")
    entity_id = Column(Integer, nullable=False, comment="实体ID")
    detail = Column(Text, default="", comment="操作详情")
    operator = Column(String(20), nullable=False, default="user", comment="操作者: user / ai")
    created_at = Column(DateTime, server_default=func.now())


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
    date = Column(DateTime, server_default=func.now(), comment="交易日期")
    created_at = Column(DateTime, server_default=func.now())


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
    issue_date = Column(DateTime, nullable=False, comment="开票日期")
    pdf_path = Column(String(500), nullable=True, comment="PDF文件路径")
    image_url = Column(String(500), default="", comment="附件图片URL")
    certification_status = Column(String(20), nullable=False, default="n_a", comment="认证状态: pending / certified / n_a")
    certification_date = Column(DateTime, nullable=True, comment="认证日期")
    project_name = Column(String(200), nullable=True, index=True, comment="项目名称")
    related_order_id = Column(Integer, nullable=True, comment="关联订单ID")
    related_order_type = Column(String(20), nullable=True, comment="关联订单类型: sale / purchase")
    notes = Column(Text, default="", comment="备注")
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint('account_id', 'invoice_no', name='uix_account_invoice_no'),
    )


# 项目管理
class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True, comment="所属账本")
    name = Column(String(200), nullable=False, comment="项目名称")
    customer_id = Column(Integer, ForeignKey("customers.id"), comment="客户ID")
    status = Column(String(20), default="ongoing", comment="状态: ongoing/completed/cancelled")
    start_date = Column(DateTime, server_default=func.now(), comment="开始日期")
    end_date = Column(DateTime, comment="结束日期")
    total_income = Column(Numeric(12, 2), default=Decimal('0'), comment="总收入")
    total_cost = Column(Numeric(12, 2), default=Decimal('0'), comment="总成本")
    profit = Column(Numeric(12, 2), default=Decimal('0'), comment="利润")
    notes = Column(Text, default="", comment="备注")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    customer = relationship("Customer", backref="projects")
    costs = relationship("ProjectCost", back_populates="project", cascade="all, delete-orphan")
    incomes = relationship("ProjectIncome", back_populates="project", cascade="all, delete-orphan")


class ProjectCost(Base):
    __tablename__ = "project_costs"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, comment="项目ID")
    cost_type = Column(String(50), nullable=False, comment="成本类型: 材料/人工/差旅/外包/设备/其他")
    amount = Column(Numeric(12, 2), nullable=False, comment="金额")
    payment_method = Column(String(20), default="company", comment="支付方式: company / private_advance")
    invoice_status = Column(String(20), default="未开", comment="发票状态: 已开/未开/不需开")
    supplier_name = Column(String(100), comment="供应商名称")
    notes = Column(Text, default="", comment="备注")
    image_url = Column(String(500), default="", comment="附件图片URL")
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True,
                        comment="商品ID（材料类成本关联库存）")
    quantity = Column(Integer, nullable=True,
                      comment="数量（材料类成本关联库存）")
    cost_date = Column(DateTime, server_default=func.now(), comment="成本日期")
    created_at = Column(DateTime, server_default=func.now())

    project = relationship("Project", back_populates="costs")
    product = relationship("Product")


class ProjectIncome(Base):
    __tablename__ = "project_incomes"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, comment="项目ID")
    amount = Column(Numeric(12, 2), nullable=False, comment="金额")
    payment_status = Column(String(20), default="pending", comment="收款状态: pending/partial/completed")
    received_amount = Column(Numeric(12, 2), default=Decimal('0'), comment="已收金额")
    invoice_status = Column(String(20), default="未开", comment="发票状态: 已开/未开/不需开")
    notes = Column(Text, default="", comment="备注")
    source_type = Column(String(20), nullable=True, default="manual",
                         comment="来源: manual=手动 / sale_order=销售单自动生成")
    source_id = Column(Integer, nullable=True,
                       comment="来源ID（sale_order时为销售单ID）")
    income_date = Column(DateTime, server_default=func.now(), comment="收入日期")
    received_date = Column(DateTime, comment="到账日期")
    created_at = Column(DateTime, server_default=func.now())

    project = relationship("Project", back_populates="incomes")

    __table_args__ = (
        UniqueConstraint("source_type", "source_id", name="uq_income_source"),
    )


# 费用表（企业所得税用：无票支出记录）
class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True, comment="所属账本")
    project_name = Column(String(200), nullable=True, index=True, comment="项目名称")
    category = Column(String(50), nullable=False, comment="类别: 房租/水电/工资/材料/办公用品/运费/维修/其他")
    amount = Column(Numeric(12, 2), nullable=False, comment="金额")
    expense_date = Column(DateTime, nullable=False, comment="支出日期")
    has_invoice = Column(Boolean, nullable=False, default=False, comment="是否有发票")
    payment_method = Column(String(20), nullable=False, default="company", comment="支付方式: company / private_advance")
    description = Column(String(500), default="", comment="描述")
    image_url = Column(String(500), default="", comment="附件图片URL")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")


class CashFlowTransaction(Base):
    __tablename__ = "cash_flow_transactions"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True, comment="所属账本")
    type = Column(String(10), nullable=False, comment="类型: inflow/outflow")
    amount = Column(Numeric(12, 2), nullable=False, comment="金额")
    flow_category = Column(String(20), nullable=False, default="operating", comment="现金流量分类: operating/investing/financing")
    description = Column(Text, default="", comment="描述")
    transaction_date = Column(DateTime, nullable=False, comment="交易日期")
    related_entity_type = Column(String(20), nullable=True, comment="关联实体类型: sale/purchase/expense/project_cost/other")
    related_entity_id = Column(Integer, nullable=True, comment="关联实体ID")
    created_at = Column(DateTime, server_default=func.now())

    account = relationship("Account", backref="cash_flow_transactions")