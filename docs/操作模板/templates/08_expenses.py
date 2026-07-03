"""模板 08：费用

⚠️ 重要：用户说"房租/水电/工资/办公/运费/差旅/招待"等都属于【费用】，不是销项、不是支出。
本系统没有单独的"支出"模块，所有花钱出去（非买商品/资产）都走费用。
费用创建后默认 payment_status=unpaid，要付款用本模板的 pay_expense()。
"""
import sys
sys.path.insert(0, r"C:\Users\Administrator\Desktop\-inventory-system\docs\操作模板")
from _client import post, get, extract_id


def create_expense(category, amount, expense_date, functional_category,
                   description=None):
    """创建费用。

    参数：
        category: 费用类别（简短标签，必须是合法值，否则报 VALIDATION_ERROR）。
            合法值（共 10 个，严格匹配）：
            - "房租"（房租/物业费/场地费）
            - "水电"（水费/电费/水电费/燃气费）
            - "工资"（工资/奖金/社保）
            - "材料"（原材料/辅料）
            - "办公用品"（办公文具/打印纸/耗材）
            - "运费"（快递费/物流费/运输费）
            - "维修"（维修费/保养费）
            - "税金及附加"（附加税/印花税）
            - "所得税"（企业所得税）
            - "其他"（差旅费/招待费/宽带/电话费等不在上列的，统一填"其他"）
            ⚠️ 差旅费/招待费不在合法值里 → 填 "其他"，在 description 里写明真实用途
        amount: 金额（用户说多少填多少，不要问税率，费用不走发票）
        expense_date: "YYYY-MM-DD"
        functional_category: 功能分类（必填）。按场景自动判断，不要问用户：
            - 管理费用：房租、水电、办公、工资、招待、物业
            - 销售费用：运费、快递、销售佣金、广告费
            - 财务费用：手续费、利息支出、汇兑损失
            - 税金及附加：月末计提自动生成，日常不手动录
            - 差旅费按部门：销售部→销售费用，其他→管理费用（用户没说部门默认管理费用）
            - ⚠️ 折旧不是手动录费用，是固定资产模块自动计提，不要录折旧费用
        description: 备注（后端字段名是 description，不是 notes）。
            收款方信息（房东/电力公司名称）写这里。

    返回：费用记录，默认 payment_status=unpaid（未付款）。
          要付款用本模板的 pay_expense(expense_id, ...)。

    ⚠️ 关于"付给谁"（房东/电力公司/物业公司）：
       后端费用和付款 schema 都没有 supplier_id 字段，收款方信息只能记在
       description 里。所以不需要为了付款去建供应商，直接：
       1. 录费用时把收款方写进 description（如 description="付房东王老板 2026年6月房租"）
       2. 拿 expense_id 调本模板 pay_expense() 付款
    """
    body = {
        "category": category,
        "amount": amount,
        "expense_date": expense_date,
        "functional_category": functional_category,
    }
    if description: body["description"] = description
    return post("/api/expenses", body)


def pay_expense(expense_id, amount, payment_date, bank_account_id,
                payment_type="expense", description=None,
                withholding_tax_amount=0):
    """为费用付款（封装 /api/payments，方便 AI 直接调用）。

    参数：
        expense_id: 费用 ID（来自 create_expense 返回）
        amount: 付款金额
            ⚠️ 工资场景(payment_type="salary"): amount = 实发金额(打到员工银行卡的钱)
        payment_date: "YYYY-MM-DD"
        bank_account_id: 付款银行账户 ID
        payment_type: "expense"（付费用，默认）/ "salary"（发工资）
        description: 备注（后端字段名是 description，不是 notes）
        withholding_tax_amount: 代扣个人所得税(仅 payment_type="salary" 时使用,默认 0)
            ⚠️ 工资场景: 应发 = amount + withholding_tax_amount
            凭证: 借2211(应发) / 贷1002(实发=amount) / 贷222108(代扣=withholding_tax_amount)
    """
    body = {
        "payment_type": payment_type,
        "related_entity_type": "expense",
        "related_entity_id": expense_id,
        "amount": amount,
        "payment_date": payment_date,
        "bank_account_id": bank_account_id,
    }
    if withholding_tax_amount:
        body["withholding_tax_amount"] = withholding_tax_amount
    if description: body["description"] = description
    return post("/api/payments", body)


def list_expenses(category=None, year=None):
    """查询费用列表。

    参数：
        category: 按费用类别筛选（如 "房租"），None 则不筛选
        year: 按年份筛选（如 2026），None 则不筛选
    """
    q = []
    if category: q.append(f"category={category}")
    if year: q.append(f"year={year}")
    qs = ("?" + "&".join(q)) if q else ""
    return get(f"/api/expenses{qs}")


# === 端到端示例 ===
if __name__ == "__main__":
    from _client import set_account
    set_account(1)
    BANK_ID = 1

    print("A. 房租 5000，已付房东王老板")
    exp_rent = create_expense("房租", 5000, "2026-06-15", "管理费用",
                               description="2026年6月房租，付房东王老板")
    rent_id = extract_id(exp_rent)
    print(f"   费用 ID: {rent_id}")
    pay = pay_expense(rent_id, 5000, "2026-06-15", BANK_ID)
    print(f"   付款: {pay}")

    print("\nB. 水电费 150，未付")
    exp_utility = create_expense("水电", 150, "2026-06-30", "管理费用",
                                  description="2026年6月水电费，待付市供电公司")
    print(f"   费用: {exp_utility}")

    print("\nC. 工资 30000，已付（payment_type=salary,代扣个税5000,实发25000）")
    exp_salary = create_expense("工资", 30000, "2026-06-30", "管理费用")
    salary_id = extract_id(exp_salary)
    pay = pay_expense(salary_id, 25000, "2026-06-30", BANK_ID, payment_type="salary",
                      withholding_tax_amount=5000)
    print(f"   付款: {pay}")

    print("\nD. 按类别筛选查询")
    print(f"   {list_expenses(category='房租')}")
