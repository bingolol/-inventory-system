# 统一错误处理：BusinessError + ErrorCode + ActionType
# 所有业务逻辑错误应抛出 BusinessError，而非 ValueError/HTTPException

from enum import Enum
from typing import Any
from decimal import Decimal


class ActionType(str, Enum):
    """错误响应中的 action 指令，告诉前端/agent 该做什么"""
    NONE = "none"                    # 无特殊操作，默认
    RETRY = "retry"                  # 重试当前操作
    USER_CONFIRM = "user_confirm"    # 请用户确认（如删除、覆盖）
    USER_INPUT = "user_input"        # 请用户修改输入（如必填字段缺失）
    USER_SELECT = "user_select"      # 请用户选择（如多个选项中选一个）
    LOGIN = "login"                  # 需要重新登录
    CONTACT_ADMIN = "contact_admin"  # 联系管理员


class ErrorCode(str, Enum):
    """业务错误码，按领域分组"""
    # 库存 (1xxx)
    INVENTORY_INSUFFICIENT = "INVENTORY_INSUFFICIENT"
    INVENTORY_NEGATIVE_AMOUNT = "INVENTORY_NEGATIVE_AMOUNT"

    # 订单 (2xxx)
    ORDER_NOT_FOUND = "ORDER_NOT_FOUND"
    ORDER_INVALID_STATE = "ORDER_INVALID_STATE"
    ORDER_EMPTY_ITEMS = "ORDER_EMPTY_ITEMS"
    ORDER_DUPLICATE_PRODUCT = "ORDER_DUPLICATE_PRODUCT"

    # 发票 (3xxx)
    INVOICE_NOT_FOUND = "INVOICE_NOT_FOUND"
    INVOICE_DUPLICATE_NUMBER = "INVOICE_DUPLICATE_NUMBER"
    INVOICE_INVALID_DATE = "INVOICE_INVALID_DATE"

    # 财务 (4xxx)
    BALANCE_ALREADY_EXISTS = "BALANCE_ALREADY_EXISTS"
    BALANCE_SHEET_UNBALANCED = "BALANCE_SHEET_UNBALANCED"
    INCOME_STATEMENT_INVALID = "INCOME_STATEMENT_INVALID"
    CASH_FLOW_STATEMENT_INVALID = "CASH_FLOW_STATEMENT_INVALID"

    # 商品 (5xxx)
    PRODUCT_NOT_FOUND = "PRODUCT_NOT_FOUND"
    PRODUCT_HAS_TRANSACTIONS = "PRODUCT_HAS_TRANSACTIONS"

    # 合作伙伴 (6xxx)
    SUPPLIER_HAS_ORDERS = "SUPPLIER_HAS_ORDERS"
    CUSTOMER_HAS_ORDERS = "CUSTOMER_HAS_ORDERS"
    CUSTOMER_NOT_FOUND = "CUSTOMER_NOT_FOUND"

    # 现金流 (7xxx)
    CASH_FLOW_NOT_FOUND = "CASH_FLOW_NOT_FOUND"

    # 费用 (8xxx)
    EXPENSE_NOT_FOUND = "EXPENSE_NOT_FOUND"

    # 固定资产 (8.5xxx)
    FIXED_ASSET_NOT_FOUND = "FIXED_ASSET_NOT_FOUND"

    # 银行账户 (9xxx)
    BANK_ACCOUNT_NOT_FOUND = "BANK_ACCOUNT_NOT_FOUND"

    # 会计准则违规 (10xxx)
    RULE_VIOLATION = "RULE_VIOLATION"

    # 通用 (9xxx)
    VALIDATION_ERROR = "VALIDATION_ERROR"
    DUPLICATE_ENTRY = "DUPLICATE_ENTRY"
    DATA_INTEGRITY_ERROR = "DATA_INTEGRITY_ERROR"
    READONLY_DATA = "READONLY_DATA"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    ENDPOINT_NOT_ALLOWED_FOR_AI = "ENDPOINT_NOT_ALLOWED_FOR_AI"
    SECURITY_VIOLATION = "SECURITY_VIOLATION"


# ErrorCode → (HTTP status, default action, 中文消息模板, AI指令)
ERROR_REGISTRY: dict[ErrorCode, tuple[int, ActionType, str, str]] = {
    # 库存
    ErrorCode.INVENTORY_INSUFFICIENT: (
        409, ActionType.USER_CONFIRM,
        "库存不足: 需要 {required}, 当前 {current}",
        "STOP_RETRYING. 库存不足，请向用户确认：是否强制出库？还是取消本次操作？"
    ),
    ErrorCode.INVENTORY_NEGATIVE_AMOUNT: (
        422, ActionType.USER_INPUT,
        "扣减数量不能为负: {amount}",
        "STOP_RETRYING. 数量无效，请向用户确认正确的扣减数量。"
    ),

    # 订单
    ErrorCode.ORDER_NOT_FOUND: (
        404, ActionType.NONE,
        "{order_type}不存在: ID={order_id}",
        "STOP_RETRYING. {order_type}不存在，请检查ID是否正确，或向用户确认正确的{order_type}。"
    ),
    ErrorCode.ORDER_INVALID_STATE: (
        409, ActionType.USER_SELECT,
        "当前状态 {status} 不允许 {action}",
        "STOP_RETRYING. 状态不允许该操作，请向用户说明当前状态，并询问想执行什么操作。"
    ),
    ErrorCode.ORDER_EMPTY_ITEMS: (
        422, ActionType.USER_INPUT,
        "{order_type}至少包含1个商品",
        "STOP_RETRYING. 订单为空，请向用户确认要添加哪些商品。"
    ),
    ErrorCode.ORDER_DUPLICATE_PRODUCT: (
        422, ActionType.USER_INPUT,
        "同一商品不可重复添加，重复商品ID: {product_ids}",
        "STOP_RETRYING. 存在重复商品，请向用户确认是否合并数量，或移除重复项。"
    ),

    # 发票
    ErrorCode.INVOICE_NOT_FOUND: (
        404, ActionType.NONE,
        "发票不存在",
        "STOP_RETRYING. 发票不存在，请检查发票ID或号码是否正确。"
    ),
    ErrorCode.INVOICE_DUPLICATE_NUMBER: (
        409, ActionType.USER_INPUT,
        "发票号码已存在: {invoice_number}",
        "STOP_RETRYING. 发票号码重复，请向用户确认正确的发票号码。"
    ),
    ErrorCode.INVOICE_INVALID_DATE: (
        422, ActionType.USER_INPUT,
        "日期格式无效: {date}，应为 YYYY-MM-DD",
        "STOP_RETRYING. 日期格式错误，请向用户确认正确的日期（格式：YYYY-MM-DD）。"
    ),

    # 财务
    ErrorCode.BALANCE_ALREADY_EXISTS: (
        409, ActionType.USER_INPUT,
        "该日期已存在期初余额: {date}",
        "STOP_RETRYING. 该日期已有期初余额，请向用户确认是覆盖还是选择其他日期。"
    ),
    ErrorCode.BALANCE_SHEET_UNBALANCED: (
        422, ActionType.USER_CONFIRM,
        "资产负债表不平衡: 资产={assets}, 负债+权益={liabilities}",
        "STOP_RETRYING. 资产负债表不平衡，请向用户确认是否强制保存，或检查数据是否有误。"
    ),
    ErrorCode.INCOME_STATEMENT_INVALID: (
        422, ActionType.USER_CONFIRM,
        "利润表公式错误: {message}",
        "STOP_RETRYING. 利润表数据不一致，请检查各项金额计算是否正确。"
    ),
    ErrorCode.CASH_FLOW_STATEMENT_INVALID: (
        422, ActionType.USER_CONFIRM,
        "现金流量表公式错误: {message}",
        "STOP_RETRYING. 现金流量表数据不一致，请检查各项金额计算是否正确。"
    ),

    # 商品
    ErrorCode.PRODUCT_NOT_FOUND: (
        404, ActionType.NONE,
        "商品不存在: ID={product_id}",
        "STOP_RETRYING. 商品不存在，请检查商品ID或名称是否正确，或向用户确认要使用哪个商品。"
    ),
    ErrorCode.PRODUCT_HAS_TRANSACTIONS: (
        409, ActionType.USER_CONFIRM,
        "该商品存在 {purchase_count} 条采购记录和 {sale_count} 条销售记录，无法删除",
        "STOP_RETRYING. 商品有业务记录，无法删除。请向用户说明情况，询问是否停用而非删除。"
    ),

    # 合作伙伴
    ErrorCode.SUPPLIER_HAS_ORDERS: (
        409, ActionType.USER_CONFIRM,
        "该供应商存在 {order_count} 条采购记录，无法删除",
        "STOP_RETRYING. 供应商有采购记录，无法删除。请向用户说明情况，询问是否停用而非删除。"
    ),
    ErrorCode.CUSTOMER_HAS_ORDERS: (
        409, ActionType.USER_CONFIRM,
        "该客户存在 {order_count} 条销售记录，无法删除",
        "STOP_RETRYING. 客户有销售记录，无法删除。请向用户说明情况，询问是否停用而非删除。"
    ),
    ErrorCode.CUSTOMER_NOT_FOUND: (
        404, ActionType.NONE,
        "客户不存在: ID={customer_id}",
        "STOP_RETRYING. 客户不存在，请检查客户ID或名称是否正确。"
    ),

    # 现金流
    ErrorCode.CASH_FLOW_NOT_FOUND: (
        404, ActionType.NONE,
        "现金流水不存在: ID={transaction_id}",
        "STOP_RETRYING. 现金流水记录不存在，请检查ID是否正确。"
    ),

    # 费用
    ErrorCode.EXPENSE_NOT_FOUND: (
        404, ActionType.NONE,
        "费用不存在: ID={expense_id}",
        "STOP_RETRYING. 费用记录不存在，请检查ID是否正确。"
    ),

    # 固定资产
    ErrorCode.FIXED_ASSET_NOT_FOUND: (
        404, ActionType.NONE,
        "固定资产不存在: ID={asset_id}",
        "STOP_RETRYING. 固定资产不存在，请检查资产ID是否正确。"
    ),

    # 银行账户
    ErrorCode.BANK_ACCOUNT_NOT_FOUND: (
        404, ActionType.NONE,
        "银行账户不存在: ID={bank_account_id}",
        "STOP_RETRYING. 银行账户不存在，请检查账户ID是否正确。"
    ),

    # 会计准则违规
    ErrorCode.RULE_VIOLATION: (
        422, ActionType.USER_INPUT,
        "会计准则校验失败: {details}",
        "STOP_RETRYING. 操作违反会计准则校验,请检查数据并修正后重试,或联系管理员排查。"
    ),

    # 通用
    ErrorCode.VALIDATION_ERROR: (
        422, ActionType.USER_INPUT,
        "字段验证失败: {details}",
        "STOP_RETRYING. 数据验证失败，请检查输入数据并修正后重试。"
    ),
    ErrorCode.DUPLICATE_ENTRY: (
        409, ActionType.USER_INPUT,
        "数据冲突: {details}",
        "STOP_RETRYING. 数据重复，请检查输入是否与已有数据冲突。"
    ),
    ErrorCode.DATA_INTEGRITY_ERROR: (
        409, ActionType.CONTACT_ADMIN,
        "数据完整性保护: {details}",
        "STOP_RETRYING. 该数据受保护，无法直接修改。需通过红冲/调整单等合规渠道操作。"
    ),
    ErrorCode.READONLY_DATA: (
        403, ActionType.NONE,
        "只读数据不可修改: {details}",
        "STOP_RETRYING. 当前系统处于维护模式，数据为只读状态。"
    ),
    ErrorCode.INTERNAL_ERROR: (
        500, ActionType.CONTACT_ADMIN,
        "服务器内部错误",
        "STOP_RETRYING. 系统异常，请向用户说明情况，建议稍后重试或联系管理员。"
    ),
    ErrorCode.ENDPOINT_NOT_ALLOWED_FOR_AI: (
        403, ActionType.NONE,
        "AI 不允许调用此接口: {method} {path}",
        "STOP_RETRYING. 该接口对 AI 未开放，请改用规范接口（见 ai_instruction / suggested_endpoint）。"
    ),
    ErrorCode.SECURITY_VIOLATION: (
        403, ActionType.NONE,
        "安全违规: {message}",
        "STOP_RETRYING. 该操作被安全策略拦截，请通过合规 API 进行操作。"
    ),
}


def _build_maps():
    status_map = {}
    action_map = {}
    instruction_map = {}
    for code, (status, action, _, instruction) in ERROR_REGISTRY.items():
        status_map[code] = status
        action_map[code] = action
        instruction_map[code] = instruction
    return status_map, action_map, instruction_map


ERROR_STATUS_MAP, ERROR_ACTION_MAP, ERROR_INSTRUCTION_MAP = _build_maps()


class BusinessError(Exception):
    """业务逻辑错误，区别于系统异常（数据库错误、网络错误等）"""

    def __init__(
        self,
        code: ErrorCode,
        message: str | None = None,
        action: ActionType | None = None,
        action_data: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        ai_instruction: str | None = None,
    ):
        self.code = code
        # 如果没传 message，从 registry 的模板生成（需要 data 中有对应字段）
        if message is None:
            _, _, template, _ = ERROR_REGISTRY[code]
            try:
                self.message = template.format(**(data or {}))
            except (KeyError, IndexError):
                self.message = template
        else:
            self.message = message
        self.action = action or ERROR_ACTION_MAP.get(code, ActionType.NONE)
        self.action_data = action_data or {}
        self.data = data or {}
        # AI 指令：优先用传入的，否则从 registry 取默认值
        self.ai_instruction = ai_instruction or ERROR_INSTRUCTION_MAP.get(code, "")
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """序列化为 JSON 响应体"""
        # 将 Decimal 转换为 float，确保 JSON 序列化
        def convert_decimals(obj):
            if isinstance(obj, Decimal):
                return float(obj)
            elif isinstance(obj, dict):
                return {k: convert_decimals(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_decimals(v) for v in obj]
            return obj

        return {
            "error": {
                "code": self.code.value,
                "message": self.message,
                "action": self.action.value,
                "action_data": convert_decimals(self.action_data),
                "data": convert_decimals(self.data),
                "ai_instruction": self.ai_instruction,
            }
        }
