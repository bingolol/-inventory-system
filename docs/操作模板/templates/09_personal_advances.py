"""模板 09：其他应付款 / 个人垫付

业务流程：员工/老板先垫 → 公司还 → 银行付款偿还

⚠️ 用户说"老板垫的"、"员工先垫的"、"个人垫付" → 走本模板，不要走 08 费用。
"""
import sys
sys.path.insert(0, r"C:\Users\Administrator\Desktop\-inventory-system\docs\操作模板")
from _client import post, get, extract_id


def create_personal_advance(advancer_name, amount, advance_date,
                             debit_account_code="6601", description=None):
    """创建个人垫付（形成其他应付款负债）。

    参数：
        advancer_name: 垫付人姓名（如"老板张三"、"员工李四"）
        amount: 垫付金额
        advance_date: 垫付日期 "YYYY-MM-DD"
        debit_account_code: 借方科目代码（可选，默认 "6601"），合法值：
            - "6601"：管理费用（办公设备、办公用品等）
            - "6602"：销售费用（销售相关）
            - "1405"：库存商品（购买商品）
            - "1601"：固定资产（购入设备）
            - "1701"：无形资产（购入无形资产）
        description: 备注说明
    """
    body = {
        "advancer_name": advancer_name,
        "amount": amount,
        "advance_date": advance_date,
        "debit_account_code": debit_account_code,
    }
    if description: body["description"] = description
    return post("/api/personal-advances", body)


def repay_personal_advance(advance_id, amount, repayment_date, bank_account_id):
    """偿还个人垫付（银行付款，减少其他应付款）。

    参数：
        advance_id: 垫付单 ID
        amount: 偿还金额（可部分偿还）
        repayment_date: 偿还日期 "YYYY-MM-DD"
        bank_account_id: 付款银行账户 ID
    """
    return post(f"/api/personal-advances/{advance_id}/repay", {
        "amount": amount,
        "repayment_date": repayment_date,
        "bank_account_id": bank_account_id,
    })


def get_personal_advance(advance_id):
    """查询垫付单详情（含已还金额、未还余额）。"""
    return get(f"/api/personal-advances/{advance_id}")


def list_personal_advances(advancer_name=None):
    """查询全部垫付单。"""
    qs = f"?advancer_name={advancer_name}" if advancer_name else ""
    return get(f"/api/personal-advances{qs}")


# === 端到端示例 ===
if __name__ == "__main__":
    from _client import set_account
    set_account(1)
    BANK_ID = 1

    print("1. 老板垫付 2000（管理费用）")
    adv = create_personal_advance(
        advancer_name="老板张三",
        amount=2000,
        advance_date="2026-06-08",
        description="垫付办公设备采购款",
        debit_account_code="6601",
    )
    print(f"   {adv}")
    adv_id = extract_id(adv)

    print("\n2. 部分偿还 1000")
    repay = repay_personal_advance(
        advance_id=adv_id,
        amount=1000,
        repayment_date="2026-06-25",
        bank_account_id=BANK_ID,
    )
    print(f"   {repay}")

    print("\n3. 查询未还余额")
    detail = get_personal_advance(adv_id)
    print(f"   剩余未还: {detail.get('remaining_amount')}")
